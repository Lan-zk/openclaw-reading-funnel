# `digest-candidates` 对象契约

## 1. 文档目的

本文档把 `digest-candidates` workflow 里会直接出现的对象契约落成当前阶段的 source of truth。

本文档只回答四件事：

- 这个 workflow 运行时到底会创建哪些对象
- 每个对象的最小字段、状态和约束是什么
- 哪些失败进入 failure ledger，哪些对象只表达业务结果
- 主产物、辅助产物和运行元数据分别长什么样

本文档是 [reading-funnel-digest-candidates-atomic-design.md](./reading-funnel-digest-candidates-atomic-design.md) 的契约层补充。

## 2. 设计范围

本文档只覆盖 `digest-candidates`：

- `CanonicalCandidate`
- `ExactDedupResult`
- `CandidateCluster`
- `ExtractedContent`
- `DigestEvidence`
- `DigestCandidate`
- `DigestReviewItem`
- `DigestFailureRecord`
- `DigestStepManifest`
- `DigestReport`

本文档不覆盖：

- `NormalizedCandidate` 的来源字段定义
- 顶层 `PipelineRun`
- 跨 workflow 的统一 schema 注册方式
- 具体存储引擎实现

## 3. 契约原则

### 3.1 单一失败真相

`digest-candidates` 的失败真相只有一个：

- `DigestFailureRecord[]`

对象状态字段只表达对象生命周期或业务去向，不承担第二份失败账本。

### 3.2 `FILTERED` 与 `NEEDS_REVIEW` 都不是失败

在本 workflow 内：

- `FILTERED` 表示业务过滤结果
- `NEEDS_REVIEW` 表示自动判断不稳定
- `FAILED` 只存在于运行级 failure ledger

因此：

- 进入 `DigestReviewItem` 的对象不写成失败
- 被过滤的对象不写成失败
- 只有执行异常、工具异常、不可恢复的数据处理异常才写入 ledger

### 3.3 最终去向只在装配阶段确定

只有 `assemble_digest_candidates` 可以把对象正式写成：

- `KEPT`
- `FILTERED`
- `NEEDS_REVIEW`

前置对象最多只表达：

- 事实
- 证据
- 分数
- 风险标记

### 3.4 空结果不是失败

以下情况允许主产物为空或只有被过滤对象，同时 workflow 仍然成功：

- 候选全部被高确定性规则过滤
- 没有候选达到 `KEPT`
- 没有候选进入 `NEEDS_REVIEW`
- 上游输入本身为空

## 4. 对象契约

### 4.1 `CanonicalCandidate`

定义：
完成 URL 规范化复核后的候选对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `normalized_candidate_id` | string | 是 | 对应上游候选逻辑身份 |
| `canonical_url` | string | 否 | 规范化后的 URL |
| `url_fingerprint` | string | 否 | 从 `canonical_url` 派生的稳定指纹 |
| `canonicalize_status` | enum | 是 | `CANONICALIZED` |
| `title` | string | 否 | 透传标题，供后续聚类使用 |
| `normalized_title` | string | 否 | 透传归一化标题 |
| `summary` | string | 否 | 透传摘要 |
| `published_at` | string | 否 | 透传发布时间 |
| `source_id` | string | 是 | 来源标识 |
| `source_name` | string | 是 | 来源名称 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- 在主流程输出中，`canonicalize_status` 当前只允许 `CANONICALIZED`
- URL 非法或规范化失败不创建该对象，失败写入 `DigestFailureRecord[]`
- `canonical_url` 允许为空，但只有在业务允许降级继续时才保留该对象

### 4.2 `ExactDedupResult`

定义：
精确去重后的保留对象及其折叠关系。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `survivor_candidate_id` | string | 是 | 保留对象 ID |
| `duplicate_candidate_ids` | string[] | 是 | 被折叠的重复对象 ID，可为空 |
| `dedup_key` | string | 是 | 本轮使用的高确定性去重键 |
| `dedup_reason` | string | 是 | 例如 `SAME_URL_FINGERPRINT` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `duplicate_candidate_ids` 不应包含 `survivor_candidate_id`
- `dedup_reason` 只记录高确定性理由，不记录猜测性相似
- `ExactDedupResult` 不承担完整元信息；后续如需标题、时间、来源，应通过 `survivor_candidate_id` 回查 `CanonicalCandidate`

### 4.3 `CandidateCluster`

定义：
完成近重复聚类后的候选簇。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_id` | string | 是 | 候选簇逻辑身份 |
| `member_candidate_ids` | string[] | 是 | 该簇包含的候选 ID |
| `primary_candidate_id` | string | 是 | 本簇主候选 ID |
| `cluster_type` | enum | 是 | `SINGLE` / `NEAR_DUPLICATE` / `MULTI_SOURCE_EVENT` |
| `cluster_confidence` | number | 是 | 0 到 1 的聚类置信度 |
| `cluster_signals` | string[] | 否 | 支撑聚类的核心信号 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `primary_candidate_id` 必须属于 `member_candidate_ids`
- `cluster_type = SINGLE` 时，`member_candidate_ids` 长度应为 1
- 低置信度聚类仍可创建 `CandidateCluster`，但应在后续 evidence 中写入 `review_flags`

### 4.4 `ExtractedContent`

定义：
针对候选簇主候选抽取并清洗后的正文对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_id` | string | 是 | 对应候选簇 |
| `primary_candidate_id` | string | 是 | 对应主候选 |
| `raw_content` | string | 否 | 抽取出的原始正文 |
| `clean_content` | string | 否 | 清洗后的正文 |
| `content_length` | integer | 是 | 当前可用正文长度 |
| `extract_status` | enum | 是 | `EXTRACTED` / `EXTRACTED_PARTIAL` / `RAW_ONLY` |
| `content_flags` | string[] | 否 | 正文缺陷提示，如 `TRUNCATED` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `ExtractedContent` 只对应一个 `cluster_id + primary_candidate_id`
- `clean_content` 允许为空，但此时应有 `raw_content` 或明确降级原因
- 完全不可恢复的抽取异常不创建该对象，失败写入 ledger

### 4.5 `DigestEvidence`

定义：
进入最终装配前的统一证据对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_id` | string | 是 | 对应候选簇 |
| `primary_candidate_id` | string | 是 | 对应主候选 |
| `quality_score` | number | 否 | 0 到 1 的质量分 |
| `noise_flags` | string[] | 是 | 噪音标记，可为空 |
| `summary` | string | 否 | 快速判断摘要 |
| `summary_status` | enum | 是 | `READY` / `UNAVAILABLE` |
| `freshness_score` | number | 否 | 0 到 1 的时效分 |
| `base_digest_score` | number | 否 | 最终裁决参考分 |
| `rerank_score` | number | 否 | 同状态内排序分 |
| `review_flags` | string[] | 是 | 低置信度或待复核标记，可为空 |
| `supporting_signals` | object | 否 | 质量、噪音、聚类、摘要等辅助证据 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `DigestEvidence` 是前置能力统一汇总层，不再发明新的裁决对象
- `review_flags` 可以为空数组，但字段必须存在
- `rerank_score` 不得独立替代 `base_digest_score` 参与硬裁决

### 4.6 `DigestCandidate`

定义：
完成最终装配后的正式候选对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `digest_candidate_id` | string | 是 | Digest 层逻辑身份 |
| `normalized_candidate_ids` | string[] | 是 | 被本对象折叠的上游候选 ID |
| `primary_normalized_candidate_id` | string | 是 | 主候选 ID |
| `cluster_type` | enum | 是 | 来自聚类结果 |
| `cluster_confidence` | number | 是 | 来自聚类结果 |
| `display_title` | string | 是 | 给下游或人工看的标题 |
| `display_summary` | string | 否 | 快速判断摘要 |
| `canonical_url` | string | 否 | 主候选规范化 URL |
| `quality_score` | number | 否 | 0 到 1 的质量分 |
| `freshness_score` | number | 否 | 0 到 1 的时效分 |
| `digest_score` | number | 否 | 对应 `base_digest_score` |
| `noise_flags` | string[] | 是 | 噪音标记，可为空 |
| `needs_review` | boolean | 是 | 是否需要人工复核 |
| `digest_status` | enum | 是 | `KEPT` / `FILTERED` / `NEEDS_REVIEW` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `needs_review = true` 时，`digest_status` 应为 `NEEDS_REVIEW`
- `digest_status = FILTERED` 不等于失败
- `digest_score` 当前对应 `DigestEvidence.base_digest_score`

### 4.7 `DigestReviewItem`

定义：
供人工复核的结构化条目。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `review_item_id` | string | 是 | 复核条目唯一标识 |
| `cluster_id` | string | 是 | 对应候选簇 |
| `primary_candidate_id` | string | 是 | 对应主候选 |
| `review_flags` | string[] | 是 | 触发复核的风险标记 |
| `supporting_evidence` | object | 是 | 摘要、分数、缺陷、噪音等辅助证据 |
| `suggested_action` | enum | 是 | `KEEP_IF_VERIFIED` / `FILTER_IF_CONFIRMED` / `RECHECK_EXTRACTION` / `RECHECK_CLUSTER` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `DigestReviewItem` 只能由 `assemble_digest_candidates` 统一生成
- `supporting_evidence` 是证据投影，不是第二份事实对象
- `review_flags` 不能为空数组

### 4.8 `DigestFailureRecord`

定义：
`digest-candidates` 的唯一失败账本记录。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `failure_id` | string | 是 | 失败记录唯一标识 |
| `run_id` | string | 是 | 本轮运行标识 |
| `step_name` | string | 是 | 失败发生步骤 |
| `scope_type` | enum | 是 | `RUN` / `BATCH` / `CLUSTER` / `CANDIDATE` / `OBJECT` |
| `scope_id` | string | 否 | 对应对象、簇或运行范围 ID |
| `failure_type` | enum | 是 | `INPUT_ERROR` / `CANONICALIZE_ERROR` / `DEDUP_ERROR` / `CLUSTER_ERROR` / `EXTRACT_ERROR` / `CLEAN_ERROR` / `QUALITY_RULE_ERROR` / `NOISE_RULE_ERROR` / `SUMMARY_ERROR` / `SCORING_ERROR` / `ASSEMBLY_ERROR` / `PERSIST_ERROR` / `UNKNOWN_ERROR` |
| `message` | string | 是 | 最小可见错误信息 |
| `details` | object | 否 | 调试上下文 |
| `retryable` | boolean | 是 | 是否建议重试 |
| `recorded_at` | string | 是 | 记录时间 |

约束：

- `message` 允许裁剪，但不能为空
- 不在 ledger 中保存完整正文或敏感凭证
- `failure_type` 必须能定位到明确 step 语义

### 4.9 `DigestStepManifest`

定义：
本次 workflow 运行的 step 级摘要。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_name` | string | 是 | 固定为 `digest-candidates` |
| `step_results` | array | 是 | 每个 step 的执行摘要 |
| `started_at` | string | 是 | workflow 开始时间 |
| `finished_at` | string | 是 | workflow 结束时间 |
| `workflow_status` | enum | 是 | `SUCCEEDED` / `PARTIAL_SUCCESS` / `FAILED` |
| `artifact_paths` | object | 是 | 主产物与辅助产物路径 |

`step_results[]` 最小字段：

- `step_name`
- `status`
- `input_count`
- `output_count`
- `review_count`
- `failure_count`
- `started_at`
- `finished_at`

约束：

- `status` 只允许 `SUCCESS_WITH_OUTPUT`、`SUCCESS_EMPTY`、`FAILED`
- `review_count` 表示进入待复核池的对象数，不等于失败数
- `workflow_status = SUCCEEDED` 不要求一定存在 `KEPT` 对象

### 4.10 `DigestReport`

定义：
从 evidence、review 和 failure ledger 投影出的可读报告对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_status` | enum | 是 | workflow 汇总状态 |
| `candidate_summary` | object | 是 | `KEPT` / `FILTERED` / `NEEDS_REVIEW` 计数 |
| `review_summary` | object | 是 | review flag 与 suggested action 汇总 |
| `failure_summary` | object | 是 | 各类失败计数 |
| `artifact_summary` | object | 是 | 主产物与辅助产物索引 |
| `generated_at` | string | 是 | 报告生成时间 |

约束：

- `DigestReport` 不能手工维护第二份失败真相
- 失败统计必须从 `DigestFailureRecord[]` 派生
- `digest-report.md` 可以是 `DigestReport` 的人类可读渲染，而不是独立业务真相

## 5. 产物文件映射

建议文件映射如下：

| 文件名 | 内容 |
|---|---|
| `digest-candidates.json` | `DigestCandidate[]` |
| `digest-review.json` | `DigestReviewItem[]` |
| `digest-failures.json` | `DigestFailureRecord[]` |
| `step-manifest.json` | `DigestStepManifest` |
| `digest-report.md` | `DigestReport` 的 Markdown 渲染 |

当前阶段存储约束：

- `digest-candidates` 的主存储格式固定为 JSON 文件
- `digest-report` 当前阶段允许直接渲染为 Markdown
- 不使用 CSV 作为主产物存储格式
- 不使用 SQLite 作为当前阶段对象与产物存储

## 6. 当前阶段明确不定的内容

本文档当前不固定以下细节：

- `digest_candidate_id` 的具体生成算法
- `cluster_signals` 与 `supporting_signals` 的完整字段集
- `details` 字段的完整调试结构
- `DigestReport` Markdown 的具体模板样式

这些细节在不破坏本契约的前提下可以后续补充。
