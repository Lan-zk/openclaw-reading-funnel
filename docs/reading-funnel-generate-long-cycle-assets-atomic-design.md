# `generate-long-cycle-assets` 原子能力设计

## 1. 文档目的

本文档定义 `generate-long-cycle-assets` workflow 内部的原子能力边界。

本文档重点回答五个问题：

- 这一层最小但有独立边界的能力单元是什么
- 这些能力如何把已有沉淀转成周刊或专题尺度的长周期资产
- 未入选、待作者复核、执行失败如何严格分离
- 中间对象如何保持稳定，不在实现中漂移
- 最终 `LongCycleAsset` 的字段分别由哪一步产生

本文档是 [reading-funnel-global-implementation-guide.md](./reading-funnel-global-implementation-guide.md) 的下钻设计。
如果后续继续展开其他 workflow，建议沿用相同模板。

## 2. 设计范围

本文档只覆盖一个 workflow：

- `generate-long-cycle-assets`

本文档不覆盖：

- `ingest-normalize`
- `digest-candidates`
- `compose-daily-review`
- `curate-retain`
- 顶层编排脚本实现

## 3. workflow 目标与边界

### 3.1 统一任务

`generate-long-cycle-assets` 的统一任务是：

> 把日报、留存资产和长期主题信号转成周尺度或专题尺度的 `LongCycleAsset`，输出的是已有沉淀的重组与放大，而不是重新抓热点。

### 3.2 负责范围

本 workflow 负责：

- 周期素材收集
- 热门主题累计
- 长期信号识别
- 周刊结构生成
- 专题可写性判断
- 专题素材包装配

### 3.3 明确不做

本 workflow 不负责：

- 上游信息摄入
- 上游候选预处理
- 人工留存判定
- 从外部重新抓热点补洞
- 自动替代作者完成最终成稿

## 4. 运行结果语义

### 4.1 step 结果

`generate-long-cycle-assets` 中的步骤结果统一分为三类：

- `SUCCESS_WITH_OUTPUT`
成功生成至少一个正式 `LongCycleAsset`
- `SUCCESS_EMPTY`
运行成功，但当前周期没有形成可发布的周刊或专题素材包
- `FAILED`
执行异常，无法完成预期步骤

### 4.2 候选去向

对单个长周期候选而言，只能进入三类业务结果：

- `SELECTED`
进入正式长周期产物
- `OMITTED`
未进入本轮长周期产物，但不是失败
- `REVIEW_REQUIRED`
具备潜力，但需作者复核

### 4.3 最终产物状态

最终 `LongCycleAsset` 的状态单独定义，不复用候选去向：

- `READY`
素材包已准备完成，可供后续作者使用
- `NEEDS_AUTHOR_REVIEW`
素材包已生成，但需要作者进一步确认或取舍

### 4.4 三者必须分开

这里有三个硬约束：

- `SELECTED/OMITTED/REVIEW_REQUIRED` 只表示长周期候选去向
- `SUCCESS_WITH_OUTPUT/SUCCESS_EMPTY/FAILED` 只表示 workflow 执行结果
- `READY/NEEDS_AUTHOR_REVIEW` 只表示最终产物状态

## 5. 失败事实与作者复核规则

### 5.1 单一失败真相

`generate-long-cycle-assets` 的运行级失败真相只有一个权威来源：

- `LongCycleFailureRecord[]`

它记录：

- 输入资产集合异常
- 周期素材汇总失败
- 主题信号计算失败
- 周刊或专题装配失败

### 5.2 作者复核不是失败

这一层的低置信度对象进入：

- `AuthorReviewItem[]`

它承接的不是执行失败，而是长周期判断不稳定的对象，例如：

- 热门主题强度不足
- 长期信号不稳定
- 周刊结构尚可但主题主线不清
- 专题可写性边界不稳定

### 5.3 唯一正式选入点按产物类型分开

本 workflow 存在两条产物线，因此允许两个正式选入点：

- `compose_weekly_assets`
- `assemble_topic_asset_bundle`

前面的原子能力只允许做三件事：

- 汇总素材
- 生成主题与长期信号
- 生成可写性与风险标记

前面的能力不得直接把候选裁决为 `SELECTED`、`OMITTED` 或 `REVIEW_REQUIRED`。

### 5.4 周刊与专题必须共享输入真相

周刊和专题都必须只消费已有沉淀：

- `KnowledgeAsset[]`
- `DailyReviewIssue[]`

不允许：

- 重新访问外部来源
- 通过外部热点为长周期产物补事实

## 6. 中间对象最小契约

为了稳定能力边界，本文档定义 5 个中间对象。

### 6.1 `PeriodAssetSet`

最小字段：

- `period_id`
- `knowledge_asset_ids`
- `daily_review_issue_ids`
- `period_start`
- `period_end`

定义：
某个时间周期内的沉淀素材集合。

说明：

- `PeriodAssetSet` 表示输入素材池，不绑定单一输出 scope
- 同一个 `PeriodAssetSet` 可以同时供 `WEEKLY` 和 `TOPIC` 两条产物线消费

### 6.2 `HotTopicSignal`

最小字段：

- `topic_id`
- `supporting_knowledge_asset_ids`
- `supporting_issue_ids`
- `heat_score`
- `topic_confidence`

定义：
由周期内反复出现的主题形成的热度信号。

### 6.3 `LongSignal`

最小字段：

- `signal_id`
- `topic_id`
- `signal_type`
- `signal_score`
- `supporting_asset_ids`

定义：
超越单日热点、具有长期趋势意味的信号对象。

### 6.4 `WeeklyAssetDraft`

最小字段：

- `period_id`
- `selected_topic_ids`
- `selected_asset_ids`
- `selected_issue_ids`
- `weekly_structure`
- `review_flags`
- `asset_status`

定义：
完成周刊结构编排、但尚未正式落为 `LongCycleAsset` 的周刊草稿。

### 6.5 `TopicAssetBundleDraft`

最小字段：

- `topic_id`
- `selected_asset_ids`
- `selected_issue_ids`
- `writability_score`
- `writability_reasons`
- `bundle_outline`
- `review_flags`
- `asset_status`

定义：
完成专题素材包装配、但尚未正式落为 `LongCycleAsset` 的专题草稿。

## 7. 最终对象字段来源映射

为了避免最终字段无法溯源，`LongCycleAsset` 的关键字段来源必须固定。

### 7.1 周刊资产字段映射

当 `asset_scope = WEEKLY` 时：

- `long_cycle_asset_id`
由 `compose_weekly_assets` 在正式落盘时生成
- `asset_scope`
固定为 `WEEKLY`
- `title`
由 `compose_weekly_assets` 根据周期与主题生成
- `summary`
由 `compose_weekly_assets` 生成
- `source_knowledge_asset_ids`
来自 `collect_period_assets`
- `source_daily_review_issue_ids`
来自 `collect_period_assets`
- `theme_ids`
来自 `detect_hot_topics` 与 `identify_long_signals`
- `asset_status`
由 `compose_weekly_assets` 写入，取值为 `READY` 或 `NEEDS_AUTHOR_REVIEW`
- `generated_at`
由 `compose_weekly_assets` 写入
- `run_id`
由 `compose_weekly_assets` 写入

### 7.2 专题资产字段映射

当 `asset_scope = TOPIC` 时：

- `long_cycle_asset_id`
由 `assemble_topic_asset_bundle` 在正式落盘时生成
- `asset_scope`
固定为 `TOPIC`
- `title`
由 `assemble_topic_asset_bundle` 根据 `topic_id` 与素材包结构生成
- `summary`
由 `assemble_topic_asset_bundle` 生成
- `source_knowledge_asset_ids`
来自 `collect_period_assets`
- `source_daily_review_issue_ids`
来自 `collect_period_assets`
- `theme_ids`
来自 `detect_hot_topics` 与 `identify_long_signals`
- `writability_score`
来自 `evaluate_topic_writability`，由 `assemble_topic_asset_bundle` 收束写入专题装配依据
- `asset_status`
由 `assemble_topic_asset_bundle` 写入，取值为 `READY` 或 `NEEDS_AUTHOR_REVIEW`
- `generated_at`
由 `assemble_topic_asset_bundle` 写入
- `run_id`
由 `assemble_topic_asset_bundle` 写入

## 8. 原子能力清单

`generate-long-cycle-assets` 的原子能力清单如下：

1. `collect_period_assets`
2. `detect_hot_topics`
3. `identify_long_signals`
4. `compose_weekly_assets`
5. `evaluate_topic_writability`
6. `assemble_topic_asset_bundle`

## 9. 原子能力逐项设计

### 9.1 `collect_period_assets`

#### 解决的问题 / 目标效果

把指定周期内的知识资产和日报成稿收拢为统一素材集合，为后续周刊和专题生成提供唯一输入真相。

#### 边界范围 / 明确不做

负责：

- 周期窗口确定
- 收集 `KnowledgeAsset[]`
- 收集 `DailyReviewIssue[]`

不负责：

- 重新抓取外部内容
- 热门主题判断
- 长期信号识别

#### 输入对象 / 输出对象

- 输入：`KnowledgeAsset[]`、`DailyReviewIssue[]`、运行周期上下文
- 输出：`PeriodAssetSet[]`

#### 核心实现思路

这一层先锁死“长周期产物只能来自已有沉淀”的输入边界。

#### 失败语义 / 人工介入点

- 周期素材收集异常：写入 `LongCycleFailureRecord[]`
- 周期内无素材：允许返回 `SUCCESS_EMPTY`
- 人工介入点：周期窗口策略校准

### 9.2 `detect_hot_topics`

#### 解决的问题 / 目标效果

识别周期内反复出现、足以形成周刊主线或专题候选的热点主题。

#### 边界范围 / 明确不做

负责：

- 聚合重复主题
- 计算热度
- 生成热点主题信号

不负责：

- 长期趋势判断
- 周刊正式编排
- 专题是否可写的最终裁决

#### 输入对象 / 输出对象

- 输入：`PeriodAssetSet[]`
- 输出：`HotTopicSignal[]`

#### 核心实现思路

这里识别的是“周期内反复出现的显著主题”，而不是外部世界的通用热点。

#### 失败语义 / 人工介入点

- 检测执行异常：写入 `LongCycleFailureRecord[]`
- 主题强度不足：不记失败，只在后续被 omitted 或 review
- 人工介入点：主题抽象粒度校准

### 9.3 `identify_long_signals`

#### 解决的问题 / 目标效果

从热点主题和周期素材中识别真正具有长期延展价值的信号。

#### 边界范围 / 明确不做

负责：

- 识别长期性趋势
- 区分短期热点与长期信号
- 生成长期信号对象

不负责：

- 正式生成周刊结构
- 正式生成专题素材包

#### 输入对象 / 输出对象

- 输入：`PeriodAssetSet[]`、`HotTopicSignal[]`
- 输出：`LongSignal[]`

#### 核心实现思路

热点不等于长期信号。这里回答的是“哪些主题有持续写作和复用价值”。

#### 失败语义 / 人工介入点

- 识别执行异常：写入 `LongCycleFailureRecord[]`
- 判断不稳定：写入 `review_flags`
- 人工介入点：长期信号门槛校准

### 9.4 `compose_weekly_assets`

#### 解决的问题 / 目标效果

基于周期素材、热点主题和长期信号，生成正式周刊资产。

#### 边界范围 / 明确不做

负责：

- 选择入选主题
- 组织周刊结构
- 正式生成 `WEEKLY` 类型 `LongCycleAsset`

不负责：

- 专题可写性判断
- 专题素材包装配

#### 输入对象 / 输出对象

- 输入：`PeriodAssetSet[]`、`HotTopicSignal[]`、`LongSignal[]`
- 输出：`LongCycleAsset[]`（`asset_scope = WEEKLY`）、`AuthorReviewItem[]`

#### 核心实现思路

这是周刊产线的正式选入点。
它根据主题热度、长期信号和素材密度，决定周刊是否形成、采用哪些主题主线，以及是否需要作者复核。

#### 失败语义 / 人工介入点

- 周刊装配失败：写入 `LongCycleFailureRecord[]`
- 若没有足够主题支撑周刊，则允许返回 `SUCCESS_EMPTY`
- 存在潜在周刊但主线不清时，写为 `NEEDS_AUTHOR_REVIEW`
- 人工介入点：周刊主线确认

### 9.5 `evaluate_topic_writability`

#### 解决的问题 / 目标效果

判断某个主题是否已经积累出足够的素材密度与结构条件，值得形成专题素材包，并生成可追溯的专题可写性证据。

#### 边界范围 / 明确不做

负责：

- 评估专题可写性
- 计算可写性分数
- 标记专题风险
- 记录可写性理由

不负责：

- 正式生成专题素材包
- 生成周刊资产

#### 输入对象 / 输出对象

- 输入：`PeriodAssetSet[]`、`HotTopicSignal[]`、`LongSignal[]`
- 输出：主题级可写性评估集合

#### 核心实现思路

这一步只回答“值不值得写”“素材够不够”，并生成后续专题装配必须引用的可写性证据，不直接落专题资产。

#### 失败语义 / 人工介入点

- 评估执行异常：写入 `LongCycleFailureRecord[]`
- 评估不足：不记失败，只在后续 omitted 或 review
- 人工介入点：专题门槛校准

### 9.6 `assemble_topic_asset_bundle`

#### 解决的问题 / 目标效果

把通过可写性门槛的主题组装成正式专题素材包。

#### 边界范围 / 明确不做

负责：

- 选择入选专题主题
- 组装专题素材结构
- 正式生成 `TOPIC` 类型 `LongCycleAsset`

不负责：

- 重新评估留存价值
- 生成周刊资产

#### 输入对象 / 输出对象

- 输入：`PeriodAssetSet[]`、`HotTopicSignal[]`、`LongSignal[]`、专题级可写性评估集合
- 输出：`LongCycleAsset[]`（`asset_scope = TOPIC`）、`AuthorReviewItem[]`

#### 核心实现思路

这是专题产线的正式选入点。
它根据主题信号、长期性和可写性证据，决定哪些主题进入正式专题素材包，以及是否需要作者复核。
专题产物必须能回溯到对应的可写性评估证据。

#### 失败语义 / 人工介入点

- 专题装配失败：写入 `LongCycleFailureRecord[]`
- 若没有主题满足专题门槛，则允许返回 `SUCCESS_EMPTY`
- 有潜力但结构不稳定的专题，应标记为 `NEEDS_AUTHOR_REVIEW`
- 人工介入点：专题方向确认

## 10. 设计结论

`generate-long-cycle-assets` 到此为止只完成三件事：

1. 把周期内已有沉淀收拢成唯一素材集合
2. 从素材中识别热点主题和长期信号
3. 分别在周刊产线和专题产线上把候选正式落成 `LongCycleAsset`

这版设计特别强调三条规则：

- 长周期产物只能来自已有沉淀，不能回头重新抓热点
- 周刊与专题是两条正式产物线，但共享同一输入真相
- `READY` / `NEEDS_AUTHOR_REVIEW` 只表示最终产物状态，不复用候选去向或 step 结果
