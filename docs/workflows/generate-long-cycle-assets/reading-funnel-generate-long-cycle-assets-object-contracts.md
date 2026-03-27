# `generate-long-cycle-assets` 对象契约

## 1. 文档目的

本文档把 `generate-long-cycle-assets` workflow 里会直接出现的对象契约落成当前阶段的 source of truth。

本文档只回答四件事：

- 这个 workflow 运行时到底会创建哪些对象
- 每个对象的最小字段、状态和约束是什么
- 哪些失败进入 failure ledger，哪些对象只表达业务结果
- 主产物、辅助产物和运行元数据分别长什么样

本文档是 [reading-funnel-generate-long-cycle-assets-atomic-design.md](./reading-funnel-generate-long-cycle-assets-atomic-design.md) 的契约层补充。

## 2. 设计范围

本文档只覆盖 `generate-long-cycle-assets`：

- `PeriodAssetSet`
- `HotTopicSignal`
- `LongSignal`
- `TopicWritabilityAssessment`
- `WeeklyAssetDraft`
- `TopicAssetBundleDraft`
- `AuthorReviewItem`
- `LongCycleAsset`
- `LongCycleFailureRecord`
- `LongCycleStepManifest`
- `LongCycleReport`

本文档不覆盖：

- `KnowledgeAsset` 与 `DailyReviewIssue` 的来源字段定义
- 顶层 `PipelineRun`
- 跨 workflow 的统一 schema 注册方式
- 具体存储引擎实现

## 3. 契约原则

### 3.1 单一失败真相

`generate-long-cycle-assets` 的失败真相只有一个：

- `LongCycleFailureRecord[]`

对象状态字段只表达业务结果或对象生命周期，不承担第二份失败账本。

### 3.2 候选去向、step 结果、最终资产状态必须分开

在本 workflow 内：

- `SELECTED` / `OMITTED` / `REVIEW_REQUIRED` 只表示候选去向
- `SUCCESS_WITH_OUTPUT` / `SUCCESS_EMPTY` / `FAILED` 只表示 step 结果
- `READY` / `NEEDS_AUTHOR_REVIEW` 只表示最终资产状态

因此：

- `REVIEW_REQUIRED` 不是失败
- `NEEDS_AUTHOR_REVIEW` 不是失败
- `SUCCESS_EMPTY` 不是失败
- `FAILED` 只存在于运行级 ledger 与 manifest

### 3.3 唯一正式选入点分两条产线

只有以下两个步骤可以把候选正式写成最终产物：

- `compose_weekly_assets`
- `assemble_topic_asset_bundle`

其他步骤只允许提供：

- 输入素材
- 主题与长期信号
- 可写性证据
- review flags

### 3.4 周刊与专题共享输入真相

当前阶段只允许消费以下上游真相：

- `KnowledgeAsset[]`
- `DailyReviewIssue[]`

不允许：

- 回头访问外部来源
- 为补全专题而临时抓热点
- 由偏好信号绕过已有沉淀

### 3.5 空结果不是失败

以下情况允许主产物为空数组且 workflow 仍成功：

- 指定周期内没有足够素材形成周刊
- 指定周期内没有主题通过专题可写性门槛
- 有候选进入 review，但没有正式产出
- 周刊与专题都没有形成正式资产，但 report、ledger、manifest 正常生成

## 4. 对象契约

### 4.1 `PeriodAssetSet`

定义：
某个周期内、供周刊线与专题线共享消费的统一素材集合。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `period_id` | string | 是 | 周期逻辑标识 |
| `knowledge_asset_ids` | string[] | 是 | 输入知识资产 ID 集合 |
| `daily_review_issue_ids` | string[] | 是 | 输入日报 issue ID 集合 |
| `period_start` | string | 是 | 周期开始时间，ISO 8601 |
| `period_end` | string | 是 | 周期结束时间，ISO 8601 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `period_start` 不得晚于 `period_end`
- `knowledge_asset_ids` 与 `daily_review_issue_ids` 允许同时为空，但空集合本身不记失败
- 同一 `period_id` 在一个 `run_id` 中必须稳定

### 4.2 `HotTopicSignal`

定义：
由周期内反复出现的主题形成的热点信号。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `topic_id` | string | 是 | 主题逻辑身份 |
| `supporting_knowledge_asset_ids` | string[] | 是 | 支撑该主题的知识资产 |
| `supporting_issue_ids` | string[] | 是 | 支撑该主题的日报 issue |
| `heat_score` | number | 是 | 0 到 1 的主题热度 |
| `topic_confidence` | number | 是 | 0 到 1 的主题识别置信度 |
| `topic_label` | string | 是 | 人类可读主题标题 |
| `topic_keywords` | string[] | 是 | 用于解释主题归并的关键词 |
| `review_flags` | string[] | 是 | 主题层风险标记，可为空 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- 至少有一个支撑来源：`supporting_knowledge_asset_ids` 与 `supporting_issue_ids` 不能同时为空
- `heat_score` 不直接决定正式入选
- `topic_confidence` 低优先进入 review，不直接记失败

### 4.3 `LongSignal`

定义：
超越单日热点、具有长期复用价值的主题信号。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `signal_id` | string | 是 | 长期信号逻辑身份 |
| `topic_id` | string | 是 | 对应热点主题 |
| `signal_type` | enum | 是 | `PATTERN` / `THEME` / `PLAYBOOK` / `RISK_TRACK` / `OPEN_QUESTION` |
| `signal_score` | number | 是 | 0 到 1 的长期性分数 |
| `supporting_asset_ids` | string[] | 是 | 支撑该信号的知识资产 ID |
| `supporting_issue_ids` | string[] | 是 | 支撑该信号的日报 issue ID |
| `signal_summary` | string | 否 | 为什么这不是短期热点的说明 |
| `review_flags` | string[] | 是 | 长期性判断风险标记 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `signal_type` 只表达长期价值类型，不表达最终产物类型
- `supporting_asset_ids` 与 `supporting_issue_ids` 允许其一为空，但不得同时为空
- `review_flags` 必须存在，哪怕为空数组

### 4.4 `TopicWritabilityAssessment`

定义：
针对专题线生成的主题级可写性评估对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `topic_id` | string | 是 | 对应主题 |
| `writability_score` | number | 是 | 0 到 1 的专题可写性分数 |
| `writability_reasons` | string[] | 是 | 支撑该分数的理由 |
| `recommended_outcome` | enum | 是 | `SELECTED` / `OMITTED` / `REVIEW_REQUIRED` |
| `supporting_asset_ids` | string[] | 是 | 支撑专题判断的知识资产 |
| `supporting_issue_ids` | string[] | 是 | 支撑专题判断的日报 issue |
| `bundle_outline_seed` | string[] | 是 | 推荐专题结构骨架 |
| `review_flags` | string[] | 是 | 可写性边界风险 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `recommended_outcome` 只对专题线有效，不直接生成最终资产
- `writability_reasons` 必须存在，哪怕为空数组
- 只有 `assemble_topic_asset_bundle` 可以把该评估真正落成资产

### 4.5 `WeeklyAssetDraft`

定义：
完成周刊结构编排，但尚未正式落成 `LongCycleAsset` 的草稿对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `period_id` | string | 是 | 对应素材周期 |
| `selected_topic_ids` | string[] | 是 | 进入周刊主线的主题 |
| `selected_asset_ids` | string[] | 是 | 进入周刊的知识资产 |
| `selected_issue_ids` | string[] | 是 | 进入周刊的日报 issue |
| `weekly_structure` | object | 是 | 周刊结构化骨架 |
| `review_flags` | string[] | 是 | 周刊主线或结构风险 |
| `asset_status` | enum | 是 | `READY` / `NEEDS_AUTHOR_REVIEW` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `weekly_structure` 至少要能表达标题、摘要、sections
- `asset_status` 不等于候选去向
- `selected_topic_ids` 允许为空；空草稿不视为失败

### 4.6 `TopicAssetBundleDraft`

定义：
完成专题素材装配，但尚未正式落成 `LongCycleAsset` 的专题草稿。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `topic_id` | string | 是 | 对应专题主题 |
| `selected_asset_ids` | string[] | 是 | 进入专题素材包的知识资产 |
| `selected_issue_ids` | string[] | 是 | 进入专题素材包的日报 issue |
| `writability_score` | number | 是 | 投影自专题可写性分数 |
| `writability_reasons` | string[] | 是 | 生成专题包的证据理由 |
| `bundle_outline` | object | 是 | 专题素材包结构骨架 |
| `review_flags` | string[] | 是 | 专题结构风险 |
| `asset_status` | enum | 是 | `READY` / `NEEDS_AUTHOR_REVIEW` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `bundle_outline` 至少要能表达标题、角度、推荐小节
- `writability_reasons` 必须与 `TopicWritabilityAssessment` 保持可追溯
- 只有 `assemble_topic_asset_bundle` 可以正式创建该对象

### 4.7 `AuthorReviewItem`

定义：
供作者确认的长周期复核条目。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `review_item_id` | string | 是 | 复核条目唯一标识 |
| `review_scope` | enum | 是 | `TOPIC_SIGNAL` / `LONG_SIGNAL` / `WEEKLY_DRAFT` / `TOPIC_DRAFT` |
| `related_object_id` | string | 是 | 关联对象 ID |
| `review_flags` | string[] | 是 | 触发复核的风险标记 |
| `supporting_evidence` | object | 是 | 支撑作者判断的证据 |
| `suggested_action` | enum | 是 | `TIGHTEN_SCOPE` / `CLARIFY_THEME` / `WAIT_FOR_MORE_EVIDENCE` / `PUBLISH_ANYWAY` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `AuthorReviewItem` 不是失败对象
- 同一业务对象可有多个 `review_flags`，但建议只生成一个 review item
- `supporting_evidence` 必须足够回溯到相关素材与分数

### 4.8 `LongCycleAsset`

定义：
周刊或专题尺度的正式长周期输出对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `long_cycle_asset_id` | string | 是 | 最终资产唯一标识 |
| `asset_scope` | enum | 是 | `WEEKLY` / `TOPIC` |
| `title` | string | 是 | 正式标题 |
| `summary` | string | 否 | 正式摘要 |
| `source_knowledge_asset_ids` | string[] | 是 | 溯源知识资产 |
| `source_daily_review_issue_ids` | string[] | 是 | 溯源日报 issue |
| `theme_ids` | string[] | 是 | 对应主题 ID |
| `asset_status` | enum | 是 | `READY` / `NEEDS_AUTHOR_REVIEW` |
| `generated_at` | string | 是 | 生成时间 |
| `run_id` | string | 是 | 本轮运行标识 |
| `writability_score` | number | 否 | 仅 `TOPIC` 资产可写 |
| `structure` | object | 是 | 周刊或专题的结构骨架 |

约束：

- `asset_scope = WEEKLY` 时允许 `writability_score = null`
- `asset_scope = TOPIC` 时应带 `writability_score`
- `theme_ids` 可以为空，但不应与结构骨架脱节

### 4.9 `LongCycleFailureRecord`

定义：
运行级唯一失败真相。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `failure_id` | string | 是 | 失败记录唯一标识 |
| `run_id` | string | 是 | 本轮运行标识 |
| `step_name` | string | 是 | 失败发生的 step |
| `scope_type` | string | 是 | 失败对象范围类型 |
| `scope_id` | string | 否 | 失败对象 ID |
| `failure_type` | string | 是 | 失败类型 |
| `message` | string | 是 | 失败说明 |
| `details` | object | 是 | 辅助上下文 |
| `retryable` | boolean | 是 | 是否可重试 |
| `recorded_at` | string | 是 | 记录时间 |

约束：

- 所有对象级或系统级失败都必须带 `step_name`
- 非失败业务结果不得写入该 ledger

### 4.10 `LongCycleStepManifest`

定义：
本 workflow 的结构化运行清单。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_name` | string | 是 | 固定为 `generate-long-cycle-assets` |
| `step_results` | object[] | 是 | 每步状态清单 |
| `started_at` | string | 是 | 运行开始时间 |
| `finished_at` | string | 是 | 运行结束时间 |
| `workflow_status` | enum | 是 | `SUCCEEDED` / `PARTIAL_SUCCESS` / `FAILED` |
| `artifact_paths` | object | 是 | 本轮产物路径 |

### 4.11 `LongCycleReport`

定义：
给人读的本轮运行汇总对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_status` | string | 是 | 本轮状态 |
| `period_summary` | object | 是 | 周期窗口与输入摘要 |
| `signal_summary` | object | 是 | 热点与长期信号摘要 |
| `asset_summary` | object | 是 | 周刊与专题正式产物摘要 |
| `review_summary` | object | 是 | 作者复核摘要 |
| `failure_summary` | object | 是 | 失败摘要 |
| `artifact_summary` | object | 是 | 产物路径与耗时 |
| `generated_at` | string | 是 | 报告生成时间 |

## 5. 主产物与辅助产物

### 5.1 主产物

当前阶段主产物固定为：

- `long-cycle-assets.json`

其内容是 `LongCycleAsset[]`。

### 5.2 辅助产物

当前阶段辅助产物固定为：

- `author-review.json`
- `long-cycle-failures.json`
- `step-manifest.json`
- `long-cycle-report.md`

## 6. 当前阶段明确不定的内容

当前阶段暂不强行固定：

- 周刊 Markdown 渲染模板
- 专题文章正文自动生成
- 多周期批处理产物索引
- 跨 run 的长期主题回放索引
