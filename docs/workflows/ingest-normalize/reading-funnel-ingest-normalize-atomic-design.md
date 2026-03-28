# `ingest-normalize` 原子能力设计

## 1. 文档目的

本文档定义 `ingest-normalize` workflow 内部的原子能力边界。

目标不是描述具体实现脚本，而是先回答四个问题：

- 这个 workflow 内最小但有独立边界的能力单元是什么
- 每个能力解决什么问题，产出什么对象
- 每个能力明确不做什么
- 空结果、失败结果、失败记录分别如何定义

本文档是 [reading-funnel-global-implementation-guide.md](../../global/reading-funnel-global-implementation-guide.md) 的下钻设计。
如果后续继续展开其他 workflow，建议沿用相同模板。

当前 workflow 的配套文档：

- [reading-funnel-ingest-normalize-object-contracts.md](./reading-funnel-ingest-normalize-object-contracts.md)
- [reading-funnel-ingest-normalize-orchestration-rules.md](./reading-funnel-ingest-normalize-orchestration-rules.md)
- [reading-funnel-ingest-normalize-evaluation-rules.md](./reading-funnel-ingest-normalize-evaluation-rules.md)
- [reading-funnel-ingest-normalize-adapter-and-normalization-rules.md](./reading-funnel-ingest-normalize-adapter-and-normalization-rules.md)

## 2. 设计范围

本文档只覆盖一个 workflow：

- `ingest-normalize`

本文档不覆盖：

- `digest-candidates`
- `compose-daily-review`
- `curate-retain`
- `generate-long-cycle-assets`
- 顶层编排脚本实现

## 3. workflow 目标与边界

### 3.1 统一任务

`ingest-normalize` 的统一任务是：

> 把多源内容接入系统，并产出统一的 `NormalizedCandidate` 候选池。

### 3.2 负责范围

本 workflow 负责：

- 来源发现与启用判断
- 增量同步窗口规划
- 实际抓取来源条目
- 将不同来源统一为标准 feed 结构
- 将来源条目映射为系统快照对象
- 原始来源快照落盘
- 基础候选归一化
- 失败事实记录

### 3.3 明确不做

本 workflow 不负责：

- 精确去重
- 相似内容聚类
- 正文抽取
- 内容清洗
- 噪音过滤
- 摘要生成
- 候选排序
- 日报编排
- 长期价值判断

## 4. 原子能力拆分原则

本文档采用中间粒度拆分。

一个能力单元只有同时满足下面四条，才算原子能力：

- 只解决一个核心判断或转换问题
- 能说清输入对象和输出对象
- 能明确说明“不做什么”
- 能独立定义空结果、失败或人工介入语义

如果一个能力内部只是固定顺序的机械步骤，不继续上升为新的原子能力。
如果一个能力内部存在高失败率、高不确定性或强人工接口，则在该能力项内展开，而不再额外升级成顶层 workflow。

## 5. 运行结果语义

### 5.1 三类结果

`ingest-normalize` 中的步骤结果统一分为三类：

- `SUCCESS_WITH_OUTPUT`
本次步骤运行成功，并产生了有效输出对象。
- `SUCCESS_EMPTY`
本次步骤运行成功，但没有可继续向下游传递的内容。
- `FAILED`
本次步骤发生执行异常，无法按预期完成。

### 5.2 空结果不是失败

以下场景应明确视为 `SUCCESS_EMPTY`，而不是失败：

- 同步窗口内没有新内容
- 某来源抓取成功但批次为空
- 上游输入为空，因此本步骤自然没有输出
- 条目经过基础归一化后没有形成任何有效候选，但执行本身没有出错

## 6. 失败事实规则

### 6.1 单一失败真相

`ingest-normalize` 的失败事实只有一个权威来源：

- `IngestFailureRecord[]`

它是运行级 failure ledger。

### 6.2 各对象的角色

- `IngestFailureRecord[]`
承载运行级失败真相，用于复盘、统计、回放和报告生成。
- `ingest-report`
是 `IngestFailureRecord[]` 的投影产物，不是第二套真相。
- 对象状态字段
只表达对象生命周期状态，不独立维护第二份失败事实。

### 6.3 同步规则

- 对象创建前发生的失败，只写入 `IngestFailureRecord[]`
- 对象创建后发生的失败，可以投影到对象状态，但仍以 ledger 为准
- 报表、统计、回放、复盘全部从 ledger 派生

## 7. 中间对象最小契约

为了稳定 `fetch_source_items`、`convert_to_feed`、`map_source_fields` 的边界，需要先定义 3 个中间对象。

### 7.1 `FetchedSourceBatch`

最小字段：

- `source_id`
- `adapter_type`
- `fetch_window`
- `raw_items`
- `fetched_at`
- `fetch_status`

定义：
某个来源在某个同步窗口中的一次抓取结果批次。

### 7.2 `RawFeedItem`

最小字段：

- `source_id`
- `origin_item_id`
- `title`
- `url`
- `summary`
- `author`
- `published_at`
- `raw_payload`

定义：
已统一到 feed 结构，但尚未映射为系统对象的来源条目。

### 7.3 `SourceEntryDraft`

最小字段：

- `source_adapter_type`
- `source_id`
- `source_name`
- `origin_item_id`
- `title`
- `url`
- `summary`
- `author`
- `published_at`
- `fetched_at`
- `raw_payload`

定义：
已满足 `SourceEntry` 落盘要求，但尚未正式持久化的对象草稿。

## 8. 原子能力清单

`ingest-normalize` 的原子能力清单如下：

1. `discover_sources`
2. `sync_source_window`
3. `fetch_source_items`
4. `convert_to_feed`
5. `map_source_fields`
6. `persist_source_entries`
7. `normalize_candidates`
8. `record_ingest_failures`

## 9. 原子能力逐项设计

### 9.1 `discover_sources`

#### 解决的问题 / 目标效果

确定本次运行应该处理哪些来源，把来源配置转换成可执行来源集合。

#### 边界范围 / 明确不做

负责：

- 读取来源配置
- 识别来源类型
- 判断来源是否启用

不负责：

- 实际抓取
- 内容去重
- 内容价值判断

#### 输入对象 / 输出对象

- 输入：来源配置、订阅清单、运行上下文
- 输出：`SourceDescriptor[]`

#### 核心实现思路

统一抽象 `SourceDescriptor`，至少包含：

- `source_id`
- `source_name`
- `adapter_type`
- `fetch_policy`
- `enabled`

这一层只解决“本轮运行处理谁”，不解决“如何抓”和“抓到什么”。

#### 失败语义 / 人工介入点

- 单个来源配置非法：记来源级失败，继续其他来源
- 全部来源不可执行：本 step 失败
- 人工介入点：来源配置修正

### 9.2 `sync_source_window`

#### 解决的问题 / 目标效果

为每个来源生成本次同步计划，明确时间窗口、游标和增量边界。

#### 边界范围 / 明确不做

负责：

- 计算同步时间窗
- 决定增量模式
- 续用或重置游标

不负责：

- 实际抓取
- 去重
- 内容质量判断

#### 输入对象 / 输出对象

- 输入：`SourceDescriptor`、历史同步状态、运行时间
- 输出：`SourceSyncPlan[]`

#### 核心实现思路

每个来源独立生成同步计划，至少包含：

- `since`
- `until`
- `cursor`
- `mode`

#### 失败语义 / 人工介入点

- 单来源无法生成同步计划：记来源级失败
- 不影响其他来源继续
- 人工介入点：游标损坏、同步策略异常

### 9.3 `fetch_source_items`

#### 解决的问题 / 目标效果

真正访问来源，按同步计划拉回原始条目批次。

#### 边界范围 / 明确不做

负责：

- 网络访问
- 认证
- 分页
- 批次抓取

不负责：

- 协议转换
- 字段映射
- 对象归一化

#### 输入对象 / 输出对象

- 输入：`SourceDescriptor`、`SourceSyncPlan`
- 输出：`FetchedSourceBatch[]`

#### 核心实现思路

把“抓取动作”单独建模，统一承接来源访问问题，避免和后续结构转换混在一起。

#### 失败语义 / 人工介入点

- `FAILED`：来源不可达、认证失败、超时、返回异常、分页中断
- `SUCCESS_EMPTY`：窗口内无新内容
- 人工介入点：来源凭证、访问策略、抓取稳定性修复

### 9.4 `convert_to_feed`

#### 解决的问题 / 目标效果

把不同来源的抓取批次统一成标准 `RawFeedItem[]`。

#### 边界范围 / 明确不做

负责：

- 协议层统一
- 结构层统一

不负责：

- 网络抓取
- 字段语义统一
- 正文抽取

#### 输入对象 / 输出对象

- 输入：`FetchedSourceBatch[]`
- 输出：`RawFeedItem[]`

#### 核心实现思路

RSS、GitHub Feed、RSSHub / RSS-Bridge、自定义抓取器都在这里收敛为统一 feed 结构。

#### 失败语义 / 人工介入点

- 转换失败只影响当前批次
- 不能掩盖“抓取已成功”的事实
- 若输入批次为 `SUCCESS_EMPTY`，这里透明传递空结果
- 人工介入点：适配器转换规则修正

### 9.5 `map_source_fields`

#### 解决的问题 / 目标效果

把 `RawFeedItem` 映射为满足 `SourceEntry` 契约的 `SourceEntryDraft`。

#### 边界范围 / 明确不做

负责：

- 字段对齐
- 缺省值处理
- 基础合法性校验

不负责：

- 语义清洗
- URL 去重
- 内容改写

#### 输入对象 / 输出对象

- 输入：`RawFeedItem[]`
- 输出：`SourceEntryDraft[]`

#### 核心实现思路

把来源适配和系统对象契约隔开，并尽量保持确定性实现。

#### 失败语义 / 人工介入点

- 单条字段非法：记条目级失败
- 其他条目继续
- 空输入透明传递为空，不转成失败
- 人工介入点：来源字段长期漂移时调整映射规则

### 9.6 `persist_source_entries`

#### 解决的问题 / 目标效果

将来源条目快照落盘，形成可追溯事实。

#### 边界范围 / 明确不做

负责：

- 快照持久化
- 运行关联
- 状态写入

不负责：

- 候选归一化
- 去重
- 排序

#### 输入对象 / 输出对象

- 输入：`SourceEntryDraft[]`
- 输出：`SourceEntry[]`

#### 核心实现思路

先保存来源快照，再做归一化，保证规则变化后仍可回放原始事实。

#### 失败语义 / 人工介入点

- 持久化失败属于系统执行失败
- 必须写入 `IngestFailureRecord[]`
- 进入 step 失败索引
- 人工介入点：存储路径、权限、序列化规则问题

### 9.7 `normalize_candidates`

#### 解决的问题 / 目标效果

从 `SourceEntry` 生成统一的 `NormalizedCandidate`，供 `digest-candidates` 使用。

#### 边界范围 / 明确不做

负责：

- URL 基础归一
- 标题基础归一
- 语言补全
- 来源信息继承

不负责：

- 精确去重
- 正文抽取
- 质量评分
- 摘要生成

#### 输入对象 / 输出对象

- 输入：`SourceEntry[]`
- 输出：`NormalizedCandidate[]`

#### 核心实现思路

把对象统一到一个稳定但不过度加工的中间层，不在这一阶段提前做 digest 判断。

#### 失败语义 / 人工介入点

- 单条归一化异常：记对象级失败并继续
- 上游为空输入：返回 `SUCCESS_EMPTY`
- 整批均无可归一对象：优先记为空结果
- 只有归一化执行本身异常才算失败
- 人工介入点：归一化规则明显失效时回调修正

### 9.8 `record_ingest_failures`

#### 解决的问题 / 目标效果

将接入、同步、抓取、转换、映射、归一化中的失败事实统一写入 failure ledger。

#### 边界范围 / 明确不做

负责：

- 失败落盘
- 失败分类
- 失败索引

不负责：

- 自动修复
- 人工诊断报告生成

#### 输入对象 / 输出对象

- 输入：各步骤错误事件、失败对象、异常上下文
- 输出：`IngestFailureRecord[]` 及其投影生成的 `ingest-report`

#### 核心实现思路

失败记录是正式产物。报告、统计、复盘都从 ledger 派生，不维护第二份失败真相。

#### 失败语义 / 人工介入点

- 该能力不能吞掉失败
- 至少保留最小可见错误信息
- ledger 写入失败按系统级失败处理
- 人工介入点：失败复盘、来源适配修复、规则调整

## 10. 设计结论

`ingest-normalize` 到此为止只完成三件事：

1. 把来源内容可靠接入系统
2. 把来源条目沉淀成可追溯快照
3. 把快照归一成统一候选对象

它明确不做 digest、日报编排或长期价值判断。

如果后续继续为其他 workflow 编写原子能力设计文档，应保持以下三条一致：

- 按 workflow 分类，不按能力池平铺
- 空结果与失败严格分离
- 失败 ledger 是唯一权威失败真相
