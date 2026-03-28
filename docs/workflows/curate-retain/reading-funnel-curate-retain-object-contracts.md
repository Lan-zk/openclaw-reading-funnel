# `curate-retain` 对象契约

## 1. 文档目的

本文档把 `curate-retain` workflow 里会直接出现的对象契约落成当前阶段的 source of truth。

本文档只回答四件事：

- 这个 workflow 运行时到底会创建哪些对象
- 每个对象的最小字段、状态和约束是什么
- 哪些失败进入 failure ledger，哪些对象只表达业务结果
- 主产物、辅助产物和运行元数据分别长什么样

本文档是 [reading-funnel-curate-retain-atomic-design.md](./reading-funnel-curate-retain-atomic-design.md) 的契约层补充。

## 2. 设计范围

本文档只覆盖 `curate-retain`：

- `ReadQueueItem`
- `HumanDecisionDraft`
- `RetentionDecisionRecord`
- `RetainedTargetSnapshot`
- `KnowledgeAssetDraft`
- `PreferenceSignalDraft`
- `KnowledgeAsset`
- `PreferenceSignal`
- `CurationFailureRecord`
- `CurationStepManifest`
- `CurationReport`

本文档不覆盖：

- `DigestCandidate` 与 `DailyReviewIssue` 的来源字段定义
- 顶层 `PipelineRun`
- 跨 workflow 的统一 schema 注册方式
- 具体存储引擎实现

## 3. 契约原则

### 3.1 单一失败真相

`curate-retain` 的失败真相只有一个：

- `CurationFailureRecord[]`

对象状态字段只表达业务结果或对象生命周期，不承担第二份失败账本。

### 3.2 人工决策、step 结果、资产状态必须分开

在本 workflow 内：

- `KEEP` / `DROP` / `DEFER` / `NEEDS_RECHECK` 只表示人工决策结果
- `SUCCESS_WITH_OUTPUT` / `SUCCESS_EMPTY` / `FAILED` 只表示 step 执行结果
- `STORED` / `ARCHIVED` 只表示知识资产状态

因此：

- `DROP` 不是失败
- `DEFER` 不是失败
- `NEEDS_RECHECK` 不是失败
- `KnowledgeAsset.asset_status` 不是人工裁决结果
- `FAILED` 只存在于 step 结果与 failure ledger

### 3.3 只有 `capture_human_decision` 可以正式裁决长期价值

只有 `capture_human_decision` 可以正式产生：

- `KEEP`
- `DROP`
- `DEFER`
- `NEEDS_RECHECK`

其他步骤只允许：

- 消费已存在决策
- 组装草稿
- 落盘正式对象
- 派生补充信号

### 3.4 后置对象不得反写人工决策

以下对象都不能成为新的裁决真相来源：

- `KnowledgeAssetDraft`
- `KnowledgeAsset`
- `PreferenceSignalDraft`
- `PreferenceSignal`

它们只能消费 `RetentionDecisionRecord`，不能把结论反写成新的 `KEEP` / `DROP`。

### 3.5 空结果不是失败

以下情况允许 workflow 成功且主产物为空数组：

- 本轮只生成了待人工确认队列，但没有新增决策
- 人工没有提交任何正式决策
- 本轮新增决策全部为 `DEFER` 或 `NEEDS_RECHECK`
- 没有任何 `KEEP` 决策，因此没有新增知识资产
- 没有足够证据派生偏好信号

## 4. 对象契约

### 4.1 `ReadQueueItem`

定义：
进入人工精读或复核队列的对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `queue_item_id` | string | 是 | 队列条目唯一标识 |
| `target_type` | enum | 是 | `DIGEST_CANDIDATE` / `DAILY_REVIEW_ENTRY` / `DAILY_REVIEW_ISSUE` |
| `target_id` | string | 是 | 被人工确认的目标对象 ID |
| `source_digest_candidate_ids` | string[] | 是 | 上游 Digest 候选溯源，可为空数组 |
| `queue_reason` | string[] | 是 | 进入队列的理由标签，可为空数组 |
| `queue_priority` | enum | 是 | `HIGH` / `MEDIUM` / `LOW` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `target_id` 必须与 `target_type` 组合后可唯一回溯
- `queue_reason` 只表达入队理由，不表达最终长期价值判断
- `queue_priority` 只表达处理优先级，不表达 `KEEP` 概率

### 4.2 `HumanDecisionDraft`

定义：
由人工确认入口收集到、但尚未正式持久化的留存决策草稿。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | enum | 是 | 与 `ReadQueueItem.target_type` 保持一致 |
| `target_id` | string | 是 | 与 `ReadQueueItem.target_id` 保持一致 |
| `decision` | enum | 是 | `KEEP` / `DROP` / `DEFER` / `NEEDS_RECHECK` |
| `confidence` | number | 否 | 0 到 1 的人工置信度 |
| `reason_tags` | string[] | 是 | 决策理由标签，可为空数组 |
| `reason_text` | string | 否 | 决策理由说明 |
| `decision_by` | string | 是 | 决策人标识 |
| `decision_at` | string | 是 | 决策时间 |
| `source_queue_item_id` | string | 否 | 若由 `ReadQueueItem` 进入人工面，则记录对应队列条目 |

约束：

- `decision` 只能由人工输入或人工确认后的导入结果产生
- `reason_tags` 可以为空，但字段必须存在
- `source_queue_item_id` 可为空，以支持脱离队列的补录决策

### 4.3 `RetentionDecisionRecord`

定义：
已正式落盘的 `RetentionDecision` 对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `retention_decision_id` | string | 是 | 正式决策对象唯一标识 |
| `target_type` | enum | 是 | 决策目标类型 |
| `target_id` | string | 是 | 决策目标 ID |
| `decision` | enum | 是 | `KEEP` / `DROP` / `DEFER` / `NEEDS_RECHECK` |
| `confidence` | number | 否 | 0 到 1 的置信度 |
| `reason_tags` | string[] | 是 | 决策理由标签，可为空数组 |
| `reason_text` | string | 否 | 决策理由说明 |
| `decision_at` | string | 是 | 决策时间 |
| `decision_by` | string | 是 | 决策人标识 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `retention_decision_id` 只在 `persist_retention_decision` 正式生成
- `decision` 只能投影自 `HumanDecisionDraft.decision`
- 同一 `RetentionDecisionRecord` 不承担“后续资产写入是否成功”的状态

### 4.4 `RetainedTargetSnapshot`

定义：
与正式 `RetentionDecision` 对应的上游对象快照。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | enum | 是 | 与正式决策目标类型保持一致 |
| `target_id` | string | 是 | 与正式决策目标 ID 保持一致 |
| `title` | string | 否 | 上游标题 |
| `summary` | string | 否 | 上游摘要 |
| `canonical_url` | string | 否 | 上游规范链接 |
| `source_digest_candidate_ids` | string[] | 是 | 来源 Digest 候选，可为空数组 |
| `snapshot_payload` | object | 否 | 当前阶段允许保留最小补充元信息 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `RetainedTargetSnapshot` 是显式输入对象，不能靠运行时隐式查找补齐
- 它只表达上游快照，不表达人工裁决
- `snapshot_payload` 允许为空，但不得成为隐藏业务真相

### 4.5 `KnowledgeAssetDraft`

定义：
基于 `KEEP` 决策派生出的知识资产草稿。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `origin_retention_decision_id` | string | 是 | 来源正式决策 ID |
| `target_type` | enum | 是 | 原始目标类型 |
| `target_id` | string | 是 | 原始目标 ID |
| `title` | string | 否 | 资产标题 |
| `summary` | string | 否 | 资产摘要 |
| `canonical_url` | string | 否 | 对应链接 |
| `topic_tags` | string[] | 是 | 长期主题标签，可为空数组 |
| `asset_type` | enum | 是 | `REFERENCE_NOTE` / `PATTERN` / `DECISION_INPUT` / `WATCH_ITEM` / `SOURCE_MAP` |
| `long_term_value_reason` | string | 否 | 为什么值得长期沉淀 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- 只有 `KEEP` 决策允许进入 `KnowledgeAssetDraft`
- `title`、`summary`、`canonical_url` 应优先来自 `RetainedTargetSnapshot`
- `KnowledgeAssetDraft` 不能反向改写 `RetentionDecisionRecord`

### 4.6 `PreferenceSignalDraft`

定义：
基于已确认决策派生出的偏好信号草稿。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `signal_type` | enum | 是 | `TOPIC_PREFERENCE` / `SOURCE_PREFERENCE` / `FORMAT_PREFERENCE` / `NEGATIVE_SIGNAL` |
| `signal_value` | string | 是 | 信号值 |
| `weight` | number | 是 | 0 到 1 的归一化权重 |
| `origin_retention_decision_id` | string | 是 | 唯一 canonical origin |
| `supplementary_knowledge_asset_id` | string | 否 | 补充上下文的知识资产 ID |
| `derived_from` | object | 是 | 结构化派生来源说明 |
| `expires_at` | string | 否 | 过期时间 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `origin_retention_decision_id` 必须指向正式 `RetentionDecisionRecord`
- `supplementary_knowledge_asset_id` 可为空，且不能替代 canonical origin
- `weight` 必须存在，哪怕采用默认值

### 4.7 `KnowledgeAsset`

定义：
进入长期知识库的高价值资产。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `knowledge_asset_id` | string | 是 | 正式知识资产唯一标识 |
| `origin_retention_decision_id` | string | 是 | 来源正式决策 ID |
| `title` | string | 否 | 资产标题 |
| `summary` | string | 否 | 资产摘要 |
| `canonical_url` | string | 否 | 对应链接 |
| `topic_tags` | string[] | 是 | 主题标签，可为空数组 |
| `asset_type` | enum | 是 | 资产类型 |
| `long_term_value_reason` | string | 否 | 长期价值说明 |
| `stored_at` | string | 是 | 正式落盘时间 |
| `asset_status` | enum | 是 | `STORED` / `ARCHIVED` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `asset_status` 当前默认 `STORED`
- 资产写入失败不允许改写来源 `RetentionDecisionRecord.decision`
- `KnowledgeAsset` 只能来自 `KnowledgeAssetDraft`

### 4.8 `PreferenceSignal`

定义：
从留存决策中提炼出的正式轻量偏好信号。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `preference_signal_id` | string | 是 | 正式偏好信号唯一标识 |
| `signal_type` | enum | 是 | `TOPIC_PREFERENCE` / `SOURCE_PREFERENCE` / `FORMAT_PREFERENCE` / `NEGATIVE_SIGNAL` |
| `signal_value` | string | 是 | 信号值 |
| `weight` | number | 是 | 0 到 1 的归一化权重 |
| `origin_retention_decision_id` | string | 是 | 唯一正式来源 |
| `supplementary_knowledge_asset_id` | string | 否 | 补充上下文的知识资产 ID |
| `derived_from` | object | 是 | 结构化派生来源说明 |
| `expires_at` | string | 否 | 过期时间 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `PreferenceSignal` 不是状态机对象
- `NEGATIVE_SIGNAL` 仍然是正式信号，不等于失败记录
- 当前 workflow 派生的信号只用于后续 rerank，不用于 hard filter

### 4.9 `CurationFailureRecord`

定义：
`curate-retain` 的唯一失败账本记录。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `failure_id` | string | 是 | 失败记录唯一标识 |
| `run_id` | string | 是 | 本轮运行标识 |
| `step_name` | string | 是 | 失败发生步骤 |
| `scope_type` | enum | 是 | `RUN` / `QUEUE_ITEM` / `DECISION` / `SNAPSHOT` / `ASSET` / `SIGNAL` / `SYSTEM` |
| `scope_id` | string | 否 | 对应对象 ID |
| `failure_type` | enum | 是 | `INPUT_ERROR` / `QUEUE_BUILD_ERROR` / `DECISION_CAPTURE_ERROR` / `DECISION_PERSIST_ERROR` / `SNAPSHOT_BUILD_ERROR` / `TAG_DERIVATION_ERROR` / `ASSET_STORE_ERROR` / `SIGNAL_DERIVATION_ERROR` / `PERSIST_ERROR` / `UNKNOWN_ERROR` |
| `message` | string | 是 | 最小可见错误信息 |
| `details` | object | 否 | 调试上下文 |
| `retryable` | boolean | 是 | 是否建议重试 |
| `recorded_at` | string | 是 | 记录时间 |

约束：

- `message` 不能为空
- 不在 ledger 中保存完整正文、敏感账户或人工批注原文
- 业务性 `DROP` / `DEFER` / `NEEDS_RECHECK` 不进入 ledger

### 4.10 `CurationStepResult`

定义：
单 step 的运行结果摘要。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `step_name` | string | 是 | step 名称 |
| `status` | enum | 是 | `SUCCESS_WITH_OUTPUT` / `SUCCESS_EMPTY` / `FAILED` |
| `input_count` | integer | 是 | 输入对象数 |
| `output_count` | integer | 是 | 输出对象数 |
| `review_count` | integer | 是 | 新增待人工处理对象数 |
| `failure_count` | integer | 是 | 新增 failure 条目数 |
| `started_at` | string | 是 | step 开始时间 |
| `finished_at` | string | 是 | step 结束时间 |

说明：

- `review_count` 在本 workflow 中主要对应新增 `ReadQueueItem` 数量
- `failure_count` 只统计 `CurationFailureRecord[]` 新增量

### 4.11 `CurationStepManifest`

定义：
整个 `curate-retain` 运行的 step 汇总对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_name` | string | 是 | 固定为 `curate-retain` |
| `step_results` | `CurationStepResult`[] | 是 | 本轮 step 汇总 |
| `started_at` | string | 是 | workflow 开始时间 |
| `finished_at` | string | 是 | workflow 结束时间 |
| `workflow_status` | enum | 是 | `SUCCEEDED` / `PARTIAL_SUCCESS` / `FAILED` |
| `artifact_paths` | object | 是 | 本轮产物路径 |

约束：

- `workflow_status = FAILED` 时，仍应尽力写出最小可见 manifest
- `artifact_paths` 至少应包含主产物与 failure ledger 路径

### 4.12 `CurationReport`

定义：
供人快速复盘本轮留存结果的汇总对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_status` | enum | 是 | `SUCCEEDED` / `PARTIAL_SUCCESS` / `FAILED` |
| `queue_summary` | object | 是 | 入队数、优先级分布、入队理由汇总 |
| `decision_summary` | object | 是 | `KEEP` / `DROP` / `DEFER` / `NEEDS_RECHECK` 计数 |
| `asset_summary` | object | 是 | 新增资产数、资产类型与标签汇总 |
| `signal_summary` | object | 是 | 新增信号数、信号类型与权重分布 |
| `failure_summary` | object | 是 | failure ledger 汇总 |
| `artifact_summary` | object | 是 | 主产物与辅助产物路径 |
| `generated_at` | string | 是 | 报告生成时间 |

约束：

- `CurationReport` 不能维护第二份失败真相
- `failure_summary` 必须从 `CurationFailureRecord[]` 派生
- `curation-report.md` 可以是 `CurationReport` 的 Markdown 渲染，而不是独立业务真相

## 5. 主产物与辅助产物契约

### 5.1 主产物

当前阶段主产物固定为：

- `retention-decisions.json`

契约：

- 文件内容是 `RetentionDecisionRecord[]`
- 空数组表示“本轮没有新增正式决策”
- 空数组是合法成功结果，不等于失败

### 5.2 辅助产物

当前阶段辅助产物固定为：

- `read-queue.json`
- `knowledge-assets.json`
- `preference-signals.json`
- `curation-failures.json`
- `step-manifest.json`
- `curation-report.md`

契约：

- `read-queue.json` 内容为 `ReadQueueItem[]`
- `knowledge-assets.json` 内容为 `KnowledgeAsset[]`
- `preference-signals.json` 内容为 `PreferenceSignal[]`
- `curation-failures.json` 内容为 `CurationFailureRecord[]`
- `step-manifest.json` 内容为 `CurationStepManifest`
- `curation-report.md` 是面向人的 Markdown 汇总

## 6. 当前阶段明确不定的内容

本文档当前不固定：

- `retention_decision_id`、`knowledge_asset_id`、`preference_signal_id` 的具体生成算法
- `snapshot_payload` 与 `derived_from` 的完整子字段
- 第一版知识库存储是文件式落盘还是后续接入其他持久层

这些内容可以后续补充，但不得破坏本文档中的对象边界和状态语义。
