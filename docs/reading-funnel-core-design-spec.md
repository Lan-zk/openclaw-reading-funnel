# Reading Funnel Core Design Spec

## 1. 项目定位

Reading Funnel Core 是一个本地“漏斗式阅读预处理内核”。

它的任务不是直接生成日报、消息推送或知识卡片，而是在真正的精选、精读、沉淀、投递发生之前，先把外部输入整理成后续系统可以继续处理的结构化对象。当前阶段不把 `OpenClaw` 当作业务中心，也不把投递和沉淀当作核心目标。

本项目的主叙事固定为：

`SourceAdapter -> RawSourceItem -> CandidateItem -> ReadingCandidate`

这条链路的含义是：

- 先用适配器接入来源
- 再保留来源特有信息
- 再统一映射成单条候选事实对象
- 最后聚合成待后续处理的阅读候选对象

## 2. Phase 1 目标与边界

### 2.1 Phase 1 目标

Phase 1 只做上游漏斗预处理，目标是：

1. 从 `FreshRSS` 真实读取内容
2. 生成本地 `RawSourceItem` 快照
3. 生成本地 `CandidateItem` 快照
4. 生成本地 `ReadingCandidate` 快照
5. 记录一次运行的统计、失败和聚合结果

### 2.2 Phase 1 不做什么

Phase 1 明确排除：

- 消息投递
- Daily Review
- Lumina 沉淀
- 用户反馈回流
- 正文抓取
- 以 `OpenClaw` 为核心的业务编排
- 强制全多 Agent 运行时

### 2.3 FreshRSS 的角色

`FreshRSS` 是 Phase 1 的第一个真实来源实现，而不是整个系统的永久中心。

这样做的原因是：

- 当前 MVP 需要真实数据源来验证可行性
- 后续还会扩展到 GitHub、新闻网站、博客、X、Reddit 等来源
- 如果现在就把 `FreshRSS` 等同于核心模型，未来会被 RSS 字段和聚合池语义卡住

因此，本阶段把 `FreshRSS` 定义为第一个 `SourceAdapter`，而不是唯一入口。

## 3. 核心对象契约

当前阶段需要 5 个核心对象，外加两类显式失败记录。

### 3.1 身份、幂等与快照规则

本阶段采用“两层身份”：

- 逻辑身份：跨 run 稳定，用于去重、重放和 upsert 判断
- 运行快照：以 `run_id` 为边界，用于保留每次运行的输入、输出和失败现场

固定规则如下：

- `run_id`：每次完整运行唯一生成一次，全局唯一，不复用
- `raw_item_id`：来源条目的逻辑身份，跨 run 稳定
- `candidate_item_id`：由 `raw_item_id` 派生，跨 run 稳定
- `reading_candidate_id`：run 级聚类快照身份，不要求跨 run 稳定

固定范围如下：

- `RawSourceItem` 的持久化主键视为 `(run_id, raw_item_id)`
- `CandidateItem` 的持久化主键视为 `(run_id, candidate_item_id)`
- `ReadingCandidate` 的持久化主键视为 `(run_id, reading_candidate_id)`

这样设计的原因是：

- 相同来源条目在不同 run 中应复用逻辑身份
- 每次运行仍要保留独立快照，支持回放和差异检查
- 聚类结果天然依赖当次输入集合，因此 `ReadingCandidate` 先按 run 级快照处理

“可重放”在本阶段的明确含义是：

- 给定一个历史 `run_id`，系统可以从该 run 持久化的 `RawSourceItem` 快照重新执行规范化、评分、去重和聚类
- 重放不会依赖当时的在线来源状态
- 相同输入的重放必须生成相同的 `candidate_item_id`
- 聚类结果应在相同规则和相同输入下得到相同输出

为了让“相同规则”可执行，本阶段还必须为每次 run 记录：

- `pipeline_version`
- `ruleset_version`
- `source_config_hash`

重放默认绑定到原始 run 记录的这三个值；如果规则版本变化，应视为新 run，不视为同一次重放。

### 3.2 SourceAdapter

`SourceAdapter` 是接入层边界，不是持久化对象。

它的职责是：

- 与某一类来源通信
- 拉取一个批次的原始内容
- 返回统一格式的 `RawSourceItem`
- 返回来源级别的运行结果

最小接口语义：

- `fetch(batch_request) -> RawSourceItem[]`
- `get_run_status() -> source-level status`

`batch_request` 在 Phase 1 固定为时间窗模式，而不是 cursor 模式。

建议字段：

- `source_ids[] | null`
- `window_start`
- `window_end`
- `limit_per_source`
- `order = published_at_desc`
- `replay = false`

固定约束：

- 同一次 run 必须记录精确的 `window_start` 与 `window_end`
- 相同时间窗允许重复拉取；重复拉取应复用同样的 `raw_item_id`
- 单来源失败不应中断其他来源；只要至少一个来源成功并完成原始落盘，本次 run 可进入后续阶段
- “其他来源在安全时继续处理”的定义是：失败来源不再进入当前 run 的后续链路，成功来源继续进入下游

Phase 1 只实现 `FreshRSSAdapter`。

### 3.3 RawSourceItem

`RawSourceItem` 是来源条目的本地镜像对象。

它必须满足两个要求：

- 尽量保留来源特有字段，不在这一层过度压平
- 支持重放、排障和后续规范化

建议字段：

- `raw_item_id`
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
- `run_id`

逻辑身份生成规则：

- 优先使用 `hash(source_adapter_type, source_id, origin_item_id)`
- 如果来源缺少稳定 `origin_item_id`，降级为 `hash(source_adapter_type, source_id, canonicalized_url, published_at, normalized_title)`

这个规则要求 `raw_item_id` 在相同来源条目被重复拉取时保持稳定。

### 3.4 CandidateItem

`CandidateItem` 是预处理阶段的最小事实单元，也是“单条候选对象”的唯一统一模型。

它代表“一条已经被清洗、标准化、可评分、可比较的候选内容”，但不承载主题级判断。

建议字段：

- `candidate_item_id`
- `origin_raw_item_id`
- `source_adapter_type`
- `source_id`
- `source_name`
- `canonical_url`
- `url_fingerprint`
- `title`
- `normalized_title`
- `summary`
- `published_at`
- `language`
- `normalize_status`
- `freshness_score`
- `quality_score`
- `noise_flags[]`
- `filter_status`
- `dedup_key`
- `run_id`

逻辑身份生成规则：

- `candidate_item_id = hash(raw_item_id)`

阶段写入规则：

- `Candidate Normalizer` 创建同一 run 内的初始 `CandidateItem` 快照
- `Candidate Filter + Score` 只更新同一条 `(run_id, candidate_item_id)` 快照上的评分和过滤字段
- `Dedup + Cluster` 只补充 `dedup_key`，不把聚类引用写回 `CandidateItem`

字段归属固定如下：

- 规范化后保证存在：`candidate_item_id`、来源字段、`canonical_url`、`normalized_title`、`summary`、`published_at`、`normalize_status`
- 评分后保证存在：`freshness_score`、`quality_score`、`noise_flags[]`、`filter_status`
- 去重后保证存在：`dedup_key`

状态语义固定如下：

- `normalize_status`: `NORMALIZED | NORMALIZATION_FAILED`
- `filter_status`: `KEPT | FILTERED`

### 3.5 ReadingCandidate

`ReadingCandidate` 是聚合后的待后续处理对象。

它承接多个 `CandidateItem`，但不是最终编辑产物，不负责生成 `why_it_matters_today`、日报栏目、投递 payload 等后置字段。

建议字段：

- `reading_candidate_id`
- `candidate_item_ids[]`
- `primary_candidate_item_id`
- `cluster_type`
- `cluster_confidence`
- `canonical_url`
- `display_title`
- `display_summary`
- `source_count`
- `published_at_range`
- `aggregate_score`
- `merge_reason`
- `needs_review`
- `run_id`

输出不变量固定如下：

- 每个 `normalize_status = NORMALIZED` 且 `filter_status = KEPT` 的 `CandidateItem`，在同一 run 中必须落入且只落入一个 `ReadingCandidate`
- `filter_status = FILTERED` 的 `CandidateItem` 不参与 `ReadingCandidate`
- 单条候选也要生成 singleton `ReadingCandidate`
- `cluster_type` 固定为：`SINGLETON | EXACT_DUP | SIMILAR_CLUSTER`
- `cluster_confidence` 对 `SINGLETON` 和 `EXACT_DUP` 固定为 `1.0`
- `merge_reason` 至少说明所使用的合并依据，不能只给空结论

`needs_review` 固定语义：

- 仅当 `cluster_type = SIMILAR_CLUSTER` 且 `cluster_confidence` 低于阈值时为 `true`
- `needs_review = true` 代表后续必须进入人工复核点

低置信度阈值固定规则：

- Phase 1 默认阈值为 `0.75`
- 阈值属于 `ruleset_version` 管辖范围
- 如果未来改为可配置项，变更后的阈值仍必须被纳入新的 `ruleset_version`

装配规则固定如下：

- `primary_candidate_item_id`：取同一 `ReadingCandidate` 内 `quality_score` 最高的 `CandidateItem`；若并列，按 `published_at` 更新者优先；若仍并列，按 `candidate_item_id` 字典序最小者优先
- `canonical_url`：取 `primary_candidate_item_id` 对应的 `canonical_url`
- `display_title`：取 `primary_candidate_item_id` 对应的 `title`
- `display_summary`：取 `primary_candidate_item_id` 对应的 `summary`
- `aggregate_score`：取该 `ReadingCandidate` 内所有 `CandidateItem.quality_score` 的最大值

### 3.6 PipelineRun

`PipelineRun` 用于描述一次完整运行。

它不是业务对象，但它是可追踪、可重放、可审核的基础。

建议字段：

- `run_id`
- `pipeline_version`
- `ruleset_version`
- `source_config_hash`
- `started_at`
- `finished_at`
- `source_window`
- `raw_items_count`
- `source_failures_count`
- `candidate_items_count`
- `normalization_failures_count`
- `reading_candidates_count`
- `filtered_count`
- `needs_review_count`
- `status`

`PipelineRun.status` 固定为：

- `SUCCEEDED`
- `PARTIAL_SUCCESS`
- `FAILED`

`PipelineRun` 同时承担“发布边界”角色：

- `SUCCEEDED` 和 `PARTIAL_SUCCESS` 的 run 可以被后续流程读取
- `FAILED` 的 run 只保留审计和排障价值，不进入默认下游消费视图

## 4. 模块边界

### 4.1 Source Adapter

职责：

- 连接来源系统
- 拉取原始内容
- 生成 `RawSourceItem`
- 报告来源级失败

边界：

- 不做规范化
- 不做聚合
- 不隐藏来源失败

### 4.2 Raw Intake Store

职责：

- 保存原始内容
- 保存来源级 intake 结果
- 保存来源级错误或空批次信息

写入归属固定如下：

- `Raw Intake Store` 是 `RawSourceItem` 快照的唯一持久化归属
- 它也是 `SourceFetchRecord` 的唯一持久化归属
- 它不写 `CandidateItem`、`ReadingCandidate` 或 `PipelineRun`

边界：

- 不修改业务判断
- 不直接承担去重和聚合逻辑

### 4.3 Candidate Normalizer

职责：

- 将 `RawSourceItem` 映射为 `CandidateItem`
- 统一 URL、标题、时间、来源标识
- 生成基础结构化信号

写入归属固定如下：

- `Candidate Normalizer` 创建 `CandidateItem` 初始快照
- 它负责写入 `normalize_status`
- 规范化失败时，它必须写入 `NormalizationFailureRecord`，并保留 `origin_raw_item_id` 与失败原因

边界：

- 不做主题聚合
- 不做终局编辑判断
- 不抓正文

### 4.4 Candidate Filter + Score

职责：

- 在单条候选级别做基础过滤
- 生成质量、新鲜度、噪音等评分信号

写入归属固定如下：

- `Candidate Filter + Score` 更新既有 `CandidateItem` 快照
- 它负责写入 `freshness_score`、`quality_score`、`noise_flags[]` 和 `filter_status`
- 它不创建新的候选对象类型

边界：

- 不做聚类
- 不输出最终结果给人类

### 4.5 Dedup + Cluster

职责：

- 先做精确去重
- 再做轻量相似聚合
- 产出聚类理由和置信度

写入归属固定如下：

- `Dedup + Cluster` 更新 `CandidateItem.dedup_key`
- 它产出聚类结果供 `ReadingCandidate Builder` 装配
- 它不直接持久化 `ReadingCandidate`

边界：

- 优先避免误合并
- 低置信度情况显式保留，不静默吞掉

### 4.6 ReadingCandidate Builder

职责：

- 将聚类结果装配成统一的 `ReadingCandidate`
- 指定主条目、展示标题、展示摘要和聚类说明

写入归属固定如下：

- `ReadingCandidate Builder` 是 `ReadingCandidate` 的唯一持久化归属
- 它负责落盘 singleton、exact dedup 和 similar cluster 三类聚类快照
- 它必须严格遵守 `primary_candidate_item_id`、`canonical_url`、`display_title`、`display_summary` 和 `aggregate_score` 的固定装配规则

边界：

- 不生成日报
- 不生成投递内容
- 不写入外部编排系统

### 4.7 Run Orchestrator

职责：

- 协调一次完整运行
- 串联模块顺序
- 写出 `PipelineRun`

固定流程：

`SourceAdapter -> Raw Intake Store -> Candidate Normalizer -> Candidate Filter + Score -> Dedup + Cluster -> ReadingCandidate Builder`

写入归属固定如下：

- `Run Orchestrator` 只写 `PipelineRun`
- 它负责汇总各阶段计数与最终状态
- 它不代替其他模块写原始条目、候选条目或聚类对象

边界：

- 只编排，不拥有业务真相
- 不把临时执行上下文当作持久状态来源

## 5. 失败语义与可见性

当前阶段必须遵守“失败可见，不静默跳过”的原则。

### 5.1 拉取失败

要求：

- 来源级失败必须记录
- 失败不能伪装成“没有内容”
- 单来源失败时，其他成功来源继续处理
- 如果所有来源都失败，整次 run 标记为 `FAILED`

来源级状态固定为：

- `SUCCEEDED`
- `EMPTY`
- `FAILED`

`SourceFetchRecord` 为 run 级显式记录，最小字段固定为：

- `run_id`
- `source_adapter_type`
- `source_id`
- `status`
- `fetched_count`
- `error_code | null`
- `error_message | null`

### 5.2 规范化失败

要求：

- 失败条目必须可追踪回 `RawSourceItem`
- 失败原因必须留存
- 失败不应直接消失

计数规则：

- `normalization_failures_count` 统计所有 `normalize_status = NORMALIZATION_FAILED` 的条目
- 规范化失败的条目不进入评分、去重和聚类

`NormalizationFailureRecord` 为 run 级显式记录，最小字段固定为：

- `run_id`
- `raw_item_id`
- `candidate_item_id | null`
- `failure_stage = NORMALIZATION`
- `error_code`
- `error_message`

### 5.3 聚类低置信度

要求：

- 聚类逻辑保守
- 不确定时宁可分开，也不应误合并
- 低置信度对象应标记 `needs_review`

计数规则：

- `needs_review_count` 统计所有 `needs_review = true` 的 `ReadingCandidate`
- 低置信度聚类不会让 run 失败，但会让 run 至少为 `PARTIAL_SUCCESS`

### 5.4 运行可追踪、可重放

要求：

- 每次运行都有唯一 `run_id`
- 每个对象能追踪到本次运行
- 一次 run 的输入、输出、失败统计可回放

状态判定规则：

- 当至少一个来源成功、所有必需持久化都成功、且不存在 `needs_review` 时，`PipelineRun.status = SUCCEEDED`
- 当至少一个来源成功，但存在来源失败、规范化失败或 `needs_review` 时，`PipelineRun.status = PARTIAL_SUCCESS`
- 当原始落盘失败、没有任何成功来源，或 `PipelineRun` 自身无法完成写入时，`PipelineRun.status = FAILED`

过滤计数规则：

- `filtered_count` 只统计 `filter_status = FILTERED` 的 `CandidateItem`

本阶段的重放边界：

- 支持从历史 `RawSourceItem` 快照重放
- 不要求重放阶段重新访问 FreshRSS
- 重放必须绑定原始 run 记录的 `pipeline_version`、`ruleset_version` 和 `source_config_hash`

下游可见性规则：

- 默认下游读取 `SUCCEEDED` 与 `PARTIAL_SUCCESS` 的 run
- `PARTIAL_SUCCESS` 的 `ReadingCandidate` 可以被读取，但必须保留 `needs_review` 标记
- `FAILED` run 的中间产物可以留在存储中，但默认不进入后续消费视图

## 6. Skill 设计映射

本项目采用《Agent-Skill-五种设计模式》里的组合思路，但不把所有模块都实现成完全自治 agent。

### 6.1 Tool Wrapper

适用：

- `SourceAdapter`
- 评分规则与来源配置

原因：

- 封装来源协议和策略规则最合适
- 让来源差异留在适配层

### 6.2 Pipeline

适用：

- `Run Orchestrator`
- `Candidate Normalizer`
- `Dedup + Cluster`

原因：

- `Run Orchestrator` 承担最严格的全链路顺序控制
- `Candidate Normalizer` 与 `Dedup + Cluster` 是 pipeline-shaped 子阶段
- 不应跳步
- 每步结果都应可解释
- `Reviewer` 可以作为 pipeline 的检查点插入，而不是替代 pipeline 本身

### 6.3 Generator

适用：

- `ReadingCandidate Builder`

原因：

- 其职责是稳定装配统一结构
- 不是开放式生成

### 6.4 Reviewer

适用：

- 聚类质量检查
- spec 审查

原因：

- 可以把“检查什么”与“如何执行”分开
- 便于后续扩展质量审查标准

## 7. 多 Agent 演进策略

当前阶段不强制一开始就做成全多 Agent 运行时。

原因有两点：

1. 当前 Phase 1 的主流程是已知的固定流水线，更适合先保证稳定性
2. 过早引入多 Agent 调度、通信和一致性语义，会放大复杂度

这也符合 ADP 对 `Planning` 模式的判断：当“how”已经清楚时，固定工作流通常比动态规划更可靠。[来源](https://adp.xindoo.xyz/original/Chapter%206_%20Planning)

当前阶段的正确做法是：

- 先按多 Agent 友好的边界划模块
- 再用固定编排器把它们串起来
- 等到确实存在职责隔离、工具隔离或并行收益时，再拆成独立 agent

未来自然演进方向：

- `Ingest Agent`
- `Normalize Agent`
- `Cluster Agent`
- `Audit Agent`

其依据来自 ADP 的 `Multi-Agent Collaboration`：多 Agent 最适合处理可分解、需要专门工具或专门能力的子问题。[来源](https://adp.xindoo.xyz/original/Chapter%207_%20Multi-Agent%20Collaboration)

## 8. 并行化策略

Phase 1 默认按顺序串行跑完整条主链路。

只有在子任务彼此独立时才考虑并行化。初始推荐的可并行区只有：

- 多来源拉取
- 批量候选评分
- 多条独立聚类候选的质量检查

这也符合 ADP 对 `Parallelization` 的约束：并行化最适合独立任务，不应把有直接依赖的步骤硬并发。[来源](https://adp.xindoo.xyz/original/Chapter%203_%20Parallelization)

## 9. Human-in-the-Loop 边界

当前阶段没有面向终端用户的人工反馈闭环，但系统内部仍应保留 HITL 接缝。

具体体现在：

- 聚类低置信度对象不自动吞并
- `needs_review` 明确标记人工复核点
- 任何高风险聚类的最终裁决都属于人工复核，不属于子 agent
- 子 agent 审查只作为预审支持，不等同于 Human-in-the-Loop 本身

这符合 ADP 对 `Human-in-the-Loop` 的要求：在复杂、模糊或高风险判断上，应保留人类审查与纠偏能力。[来源](https://adp.xindoo.xyz/original/Chapter%2013_%20Human-in-the-Loop)

## 10. OpenClaw 边界

`OpenClaw` 不是当前 Phase 1 的业务中心。

它在后续阶段的定位是：

- 消费本地产物
- 负责编排
- 负责投递
- 负责与外部工作流集成

它不应在当前阶段承担：

- 主业务对象定义
- 核心状态管理
- 候选内容的事实判定
- 聚类和装配的业务真相

## 11. 文档层验收标准

本设计成立时，应满足：

- 不再使用旧 `StoryPack/OpenClaw-first` 叙事作为当前 Phase 1 核心
- 明确采用 `SourceAdapter -> RawSourceItem -> CandidateItem -> ReadingCandidate`
- `FreshRSS` 被表述为第一个 adapter，而不是永久中心
- `OpenClaw` 被表述为后置适配层，而不是当前业务内核
- Phase 1 的目标和非目标边界清晰
- 多 Agent 被定义为演进方向，而不是当前强制实现方式
