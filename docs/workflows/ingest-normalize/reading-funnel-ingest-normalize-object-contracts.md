# `ingest-normalize` 对象契约

## 1. 文档目的

本文档把 `ingest-normalize` workflow 里会直接出现的对象契约落成当前阶段的 source of truth。

本文档只回答四件事：

- 这个 workflow 运行时到底会创建哪些对象
- 每个对象的最小字段、状态和约束是什么
- 哪些失败写入对象，哪些失败只写入 failure ledger
- 主产物、辅助产物和运行元数据分别长什么样

本文档是 [reading-funnel-ingest-normalize-atomic-design.md](./reading-funnel-ingest-normalize-atomic-design.md) 的契约层补充。

## 2. 设计范围

本文档只覆盖 `ingest-normalize`：

- `SourceDescriptor`
- `SourceSyncPlan`
- `FetchedSourceBatch`
- `RawFeedItem`
- `SourceEntryDraft`
- `SourceEntry`
- `NormalizedCandidate`
- `IngestFailureRecord`
- `IngestStepManifest`
- `IngestReport`

本文档不覆盖：

- `DigestCandidate`
- 顶层 `PipelineRun`
- 跨 workflow 的对象复用细节
- 具体存储引擎实现

## 3. 契约原则

### 3.1 单一失败真相

`ingest-normalize` 的失败真相只有一个：

- `IngestFailureRecord[]`

对象状态字段只表达对象生命周期，不承担第二份失败账本。

### 3.2 对象创建前失败不创建业务对象

以下失败只写入 `IngestFailureRecord[]`，不创建对应业务对象：

- 来源配置非法
- 同步计划生成失败
- 来源抓取失败
- 抓取结果无法转换为 feed

因此，在 `ingest-normalize` 范围内：

- 抓取失败不会创建 `SourceEntry`
- `SourceEntry` 只表示已经成功落盘的来源快照

### 3.3 空结果不是失败

以下情况允许对象数组为空，同时 step 仍然成功：

- 同步窗口内没有新条目
- 某来源抓回空批次
- 上游为空，因此下游自然无输出
- 条目全部因基础合法性校验未形成候选，但执行本身没有异常

## 4. 对象契约

### 4.1 `SourceDescriptor`

定义：
本次运行中可被执行的来源描述对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_id` | string | 是 | 全局稳定来源标识 |
| `source_name` | string | 是 | 人类可读名称 |
| `adapter_type` | string | 是 | 例如 `RSS`、`RSSHUB`、`GITHUB_FEED`、`CUSTOM_HTTP` |
| `enabled` | boolean | 是 | 本轮是否启用 |
| `fetch_policy` | object | 是 | 抓取窗口、频率、分页等来源策略 |
| `auth_ref` | string | 否 | 凭证引用名，不直接存密钥 |
| `tags` | string[] | 否 | 来源分组、主题标签 |

约束：

- `source_id` 在整个仓库中必须稳定
- `adapter_type` 决定后续 adapter 选择
- `enabled = false` 的来源不能进入抓取阶段

### 4.2 `SourceSyncPlan`

定义：
某个来源在本次运行中的同步计划。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_id` | string | 是 | 对应来源 |
| `plan_id` | string | 是 | 本次计划唯一标识 |
| `mode` | enum | 是 | `INITIAL` / `INCREMENTAL` / `BACKFILL` / `REPLAY` |
| `since` | string | 否 | ISO 8601 起始时间 |
| `until` | string | 是 | ISO 8601 结束时间 |
| `cursor` | object | 否 | 增量或分页游标 |
| `page_limit` | integer | 否 | 本轮最大分页数 |
| `item_limit` | integer | 否 | 本轮最大条目数 |
| `planned_at` | string | 是 | 计划生成时间 |

约束：

- `INCREMENTAL` 模式下，`since`、`until`、`cursor` 至少应有一项可用
- `REPLAY` 模式必须能追溯到既有输入范围或既有批次

### 4.3 `FetchedSourceBatch`

定义：
某来源按某同步计划抓回的一批原始条目。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_id` | string | 是 | 对应来源 |
| `plan_id` | string | 是 | 对应同步计划 |
| `adapter_type` | string | 是 | 适配器类型 |
| `fetch_window` | object | 是 | 实际抓取窗口 |
| `raw_items` | array | 是 | 原始条目数组，可为空 |
| `raw_count` | integer | 是 | 原始条目数 |
| `next_cursor` | object | 否 | 下一页或下次同步游标 |
| `fetched_at` | string | 是 | 实际抓取完成时间 |
| `fetch_status` | enum | 是 | `SUCCESS_WITH_OUTPUT` / `SUCCESS_EMPTY` |

约束：

- `fetch_status = SUCCESS_EMPTY` 时，`raw_items` 必须为空数组
- 抓取失败不创建 `FetchedSourceBatch`，只记录 `IngestFailureRecord`

### 4.4 `RawFeedItem`

定义：
已统一到标准 feed 结构、但尚未映射成系统对象的条目。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_id` | string | 是 | 来源标识 |
| `origin_item_id` | string | 是 | 来源内稳定条目标识 |
| `title` | string | 否 | 原始标题 |
| `url` | string | 否 | 原始链接 |
| `summary` | string | 否 | 原始摘要 |
| `author` | string | 否 | 原始作者 |
| `published_at` | string | 否 | 原始发布时间 |
| `raw_payload` | object | 是 | 适配器保留的原始结构 |

约束：

- `origin_item_id` 必须可用于来源内幂等
- `raw_payload` 必须保留原始字段，不做语义清洗

### 4.5 `SourceEntryDraft`

定义：
满足 `SourceEntry` 落盘要求、但尚未持久化的快照草稿。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_adapter_type` | string | 是 | 适配器类型 |
| `source_id` | string | 是 | 来源标识 |
| `source_name` | string | 是 | 来源名称 |
| `origin_item_id` | string | 是 | 来源内稳定条目标识 |
| `title` | string | 否 | 标题 |
| `url` | string | 否 | 链接 |
| `summary` | string | 否 | 摘要 |
| `author` | string | 否 | 作者 |
| `published_at` | string | 否 | 发布时间 |
| `fetched_at` | string | 是 | 本轮抓取时间 |
| `raw_payload` | object | 是 | 原始快照内容 |

约束：

- `source_id + origin_item_id + fetched_at` 应足以形成快照唯一性
- 不在 `Draft` 阶段引入归一化字段

### 4.6 `SourceEntry`

定义：
已正式落盘的来源条目快照。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_entry_id` | string | 是 | 逻辑身份 |
| `source_entry_snapshot_id` | string | 是 | 本次快照身份 |
| `source_adapter_type` | string | 是 | 适配器类型 |
| `source_id` | string | 是 | 来源标识 |
| `source_name` | string | 是 | 来源名称 |
| `origin_item_id` | string | 是 | 来源内稳定条目标识 |
| `title` | string | 否 | 标题 |
| `url` | string | 否 | 原始链接 |
| `summary` | string | 否 | 原始摘要 |
| `author` | string | 否 | 作者 |
| `published_at` | string | 否 | 发布时间 |
| `fetched_at` | string | 是 | 本轮抓取时间 |
| `raw_payload` | object | 是 | 原始负载 |
| `run_id` | string | 是 | 本轮运行标识 |
| `status` | enum | 是 | `INGESTED` |

约束：

- 在 `ingest-normalize` 范围内，`SourceEntry.status` 当前只允许 `INGESTED`
- 抓取失败、转换失败、映射失败不创建 `SourceEntry`

### 4.7 `NormalizedCandidate`

定义：
完成基础归一化、可供 `digest-candidates` 继续处理的候选对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `normalized_candidate_id` | string | 是 | 逻辑身份 |
| `source_entry_id` | string | 是 | 来源快照逻辑身份 |
| `canonical_url` | string | 否 | 基础归一后的链接 |
| `url_fingerprint` | string | 否 | URL 指纹 |
| `title` | string | 否 | 原始标题 |
| `normalized_title` | string | 否 | 基础归一标题 |
| `summary` | string | 否 | 继承摘要 |
| `language` | string | 否 | 语言代码 |
| `published_at` | string | 否 | 发布时间 |
| `source_id` | string | 是 | 来源标识 |
| `source_name` | string | 是 | 来源名称 |
| `normalize_status` | enum | 是 | `NORMALIZED` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- 在 `ingest-normalize` 的主产物中，只输出 `normalize_status = NORMALIZED` 的对象
- 归一化失败不写入主产物；失败事实写入 ledger

### 4.8 `IngestFailureRecord`

定义：
`ingest-normalize` 的唯一失败账本记录。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `failure_id` | string | 是 | 失败记录唯一标识 |
| `run_id` | string | 是 | 本轮运行标识 |
| `step_name` | string | 是 | 失败发生步骤 |
| `scope_type` | enum | 是 | `RUN` / `SOURCE` / `BATCH` / `ITEM` / `OBJECT` |
| `scope_id` | string | 否 | 来源、批次、条目或对象标识 |
| `failure_type` | enum | 是 | `CONFIG_ERROR` / `AUTH_ERROR` / `NETWORK_ERROR` / `PARSE_ERROR` / `MAPPING_ERROR` / `PERSIST_ERROR` / `NORMALIZE_ERROR` / `UNKNOWN_ERROR` |
| `message` | string | 是 | 最小可见错误信息 |
| `details` | object | 否 | 调试上下文 |
| `retryable` | boolean | 是 | 是否建议重试 |
| `recorded_at` | string | 是 | 记录时间 |

约束：

- 失败记录必须可定位到 step
- `message` 允许被裁剪，但不能为空
- 不在 ledger 中直接保存敏感凭证

### 4.9 `IngestStepManifest`

定义：
本次 workflow 运行的 step 级摘要。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_name` | string | 是 | 固定为 `ingest-normalize` |
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
- `failure_count`
- `started_at`
- `finished_at`

约束：

- `status` 允许 `SUCCESS_WITH_OUTPUT`、`SUCCESS_EMPTY`、`FAILED`
- `workflow_status = SUCCEEDED` 不要求一定有输出

### 4.10 `IngestReport`

定义：
从 ledger 和 step-manifest 投影出的可读报告对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_status` | enum | 是 | workflow 汇总状态 |
| `source_summary` | object | 是 | 来源数、成功数、空结果数、失败数 |
| `failure_summary` | object | 是 | 各类失败计数 |
| `artifact_summary` | object | 是 | 主产物和辅助产物索引 |
| `generated_at` | string | 是 | 报告生成时间 |

约束：

- `IngestReport` 不能手工维护第二份失败真相
- 失败统计必须从 `IngestFailureRecord[]` 派生

## 5. 产物文件映射

建议文件映射如下：

| 文件名 | 内容 |
|---|---|
| `normalized-candidates.json` | `NormalizedCandidate[]` |
| `source-entries.json` | `SourceEntry[]` |
| `ingest-failures.json` | `IngestFailureRecord[]` |
| `step-manifest.json` | `IngestStepManifest` |
| `ingest-report.json` | `IngestReport` |

## 6. 当前阶段明确不定的内容

本文档当前不固定以下细节：

- 最终使用文件存储还是数据库存储
- `source_entry_id` 和 `normalized_candidate_id` 的具体生成算法
- `url_fingerprint` 的具体哈希算法
- `details` 字段的完整调试结构

这些细节在不破坏本契约的前提下可以后续补充。
