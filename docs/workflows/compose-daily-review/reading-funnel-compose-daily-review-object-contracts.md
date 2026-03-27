# `compose-daily-review` 对象契约

## 1. 文档目的

本文档把 `compose-daily-review` workflow 里会直接出现的对象契约落成当前阶段的 source of truth。

本文档只回答四件事：

- 这个 workflow 运行时到底会创建哪些对象
- 每个对象的最小字段、状态和约束是什么
- 哪些失败进入 failure ledger，哪些对象只表达业务结果
- 主产物、辅助产物和运行元数据分别长什么样

本文档是 [reading-funnel-compose-daily-review-atomic-design.md](./reading-funnel-compose-daily-review-atomic-design.md) 的契约层补充。

## 2. 设计范围

本文档只覆盖 `compose-daily-review`：

- `DailyReviewSection`
- `EventBundle`
- `ThemeSignal`
- `DailyReviewEvidence`
- `DailyReviewEntry`
- `DailyReviewTheme`
- `EditorialReviewItem`
- `DailyReviewDraft`
- `DailyReviewIssue`
- `DailyReviewFailureRecord`
- `DailyReviewStepManifest`
- `DailyReviewReport`

本文档不覆盖：

- `DigestCandidate` 的来源字段定义
- 顶层 `PipelineRun`
- 跨 workflow 的统一 schema 注册方式
- 具体存储引擎实现

## 3. 契约原则

### 3.1 单一失败真相

`compose-daily-review` 的失败真相只有一个：

- `DailyReviewFailureRecord[]`

对象状态字段只表达对象生命周期或业务去向，不承担第二份失败账本。

### 3.2 `SELECTED`、`OMITTED`、`REVIEW_REQUIRED` 都不是失败

在本 workflow 内：

- `SELECTED` 表示正式进入日报
- `OMITTED` 表示未入选日报
- `REVIEW_REQUIRED` 表示需要编辑复核
- `FAILED` 只存在于运行级 failure ledger

因此：

- 进入 `EditorialReviewItem` 的对象不写成失败
- 被省略的事件包不写成失败
- 只有执行异常、模板异常、不可恢复的数据处理异常才写入 ledger

### 3.3 最终去向只在结构编排阶段确定

只有 `compose_issue_structure` 可以把事件包正式写成：

- `SELECTED`
- `OMITTED`
- `REVIEW_REQUIRED`

前置对象最多只表达：

- 事实
- 证据
- 建议
- 风险标记

### 3.4 当前阶段每次运行最多形成 1 份 issue

当前阶段约束为：

- 每个 `run_id` 最多生成 1 个 `DailyReviewIssue`
- 主产物文件仍固定为 `daily-review-issues.json`
- `daily-review-issues.json` 当前阶段是 `DailyReviewIssue[]`，长度只允许为 `0` 或 `1`

这样做的原因是：

- 与全局主产物命名保持一致
- 为未来多 issue 批处理保留扩展位
- 不强迫当前阶段在空结果时伪造日报对象

### 3.5 空结果不是失败

以下情况允许 `daily-review-issues.json` 为空数组，同时 workflow 仍然成功：

- 上游给出的 `DigestCandidate` 全部被正式 `OMITTED`
- 没有事件包进入 `SELECTED`
- 没有事件包进入 `REVIEW_REQUIRED`
- 输入合法，但当天不足以形成正式日报

## 4. 对象契约

### 4.1 `DailyReviewSection`

定义：
日报固定栏目枚举。

允许值：

1. `今日大事`
2. `变更与实践`
3. `安全与风险`
4. `开源与工具`
5. `洞察与数据点`
6. `主题深挖`

约束：

- 中间对象中的栏目建议只能取这 6 个值
- `DailyReviewDraft.section_entries` 只能使用这 6 个 key
- `DailyReviewIssue.sections` 也只能使用这 6 个 key
- 当前阶段默认展示顺序固定按上面 1 到 6 的顺序输出

### 4.2 `EventBundle`

定义：
同一事件、同一议题或同一变更条线的候选包。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `event_bundle_id` | string | 是 | 事件包逻辑身份 |
| `source_digest_candidate_ids` | string[] | 是 | 被该事件包折叠的上游 Digest 候选 ID |
| `primary_digest_candidate_id` | string | 是 | 事件包主候选 |
| `merge_confidence` | number | 是 | 0 到 1 的归并置信度 |
| `event_scope` | enum | 是 | `SINGLE_EVENT` / `SAME_CHANGE_STREAM` / `SAME_TOPIC_THREAD` |
| `bundle_title` | string | 否 | 供后续栏目判断和成稿使用的主标题 |
| `bundle_summary` | string | 否 | 对事件包的轻量摘要 |
| `supporting_signals` | object | 否 | 标题相似、URL 关系、来源交叉等辅助信号 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `primary_digest_candidate_id` 必须属于 `source_digest_candidate_ids`
- `merge_confidence` 低不等于失败，后续应通过 `review_flags` 表达风险
- `event_scope` 只表达归并范围，不表达最终栏目和重要性

### 4.3 `ThemeSignal`

定义：
由多个事件包共同支持的当日主题信号。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `theme_id` | string | 是 | 主题逻辑身份 |
| `supporting_event_bundle_ids` | string[] | 是 | 支撑该主题的事件包 ID |
| `theme_score` | number | 是 | 0 到 1 的主题强度 |
| `theme_type` | enum | 是 | `MOMENTUM` / `RISK` / `PRACTICE` / `TOOLING` / `INSIGHT` |
| `theme_label` | string | 是 | 给最终日报展示的主题标题 |
| `theme_summary` | string | 否 | 该主题为何重要的简短说明 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `supporting_event_bundle_ids` 不得为空
- `theme_score` 只表达“主题是否成线”，不直接决定日报入选
- 同一 `theme_id` 在一个 `run_id` 中必须稳定

### 4.4 `DailyReviewEvidence`

定义：
进入最终编排前的统一证据对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `event_bundle_id` | string | 是 | 对应事件包 |
| `proposed_section` | `DailyReviewSection` | 否 | 栏目建议 |
| `section_confidence` | number | 否 | 0 到 1 的栏目置信度 |
| `section_reasons` | string[] | 是 | 栏目建议理由，可为空 |
| `daily_importance_score` | number | 否 | 0 到 1 的当日重要性分 |
| `deep_dive_signal` | boolean | 是 | 是否适合进入主题深挖建议池 |
| `theme_ids` | string[] | 是 | 关联主题 ID，可为空 |
| `review_flags` | string[] | 是 | 编辑复核标记，可为空 |
| `supporting_signals` | object | 否 | 评分组成、来源覆盖、风险标签等辅助证据 |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `DailyReviewEvidence` 是唯一证据汇总层
- `review_flags` 必须存在，哪怕为空数组
- `proposed_section` 允许为空，但不得使用固定枚举之外的值
- `deep_dive_signal = true` 只表示建议，不等于正式进入 `主题深挖`

### 4.5 `DailyReviewEntry`

定义：
进入日报固定栏目后的结构化条目。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `entry_id` | string | 是 | 栏目条目唯一标识 |
| `event_bundle_id` | string | 是 | 对应事件包 |
| `section` | `DailyReviewSection` | 是 | 最终栏目 |
| `headline` | string | 是 | 展示标题 |
| `summary` | string | 否 | 条目摘要 |
| `why_it_matters` | string | 否 | 编排层生成的“为什么值得读”说明 |
| `importance_score` | number | 否 | 投影自 `daily_importance_score` |
| `source_digest_candidate_ids` | string[] | 是 | 条目溯源到的 Digest 候选 |
| `theme_ids` | string[] | 是 | 关联主题 ID，可为空 |
| `review_flags` | string[] | 是 | 仍需提示给编辑的风险标记，可为空 |

约束：

- `section` 必须等于所属栏目 key
- `source_digest_candidate_ids` 不得为空
- `DailyReviewEntry` 只由 `compose_issue_structure` 生成

### 4.6 `DailyReviewTheme`

定义：
写入日报成品的主题摘要对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `theme_id` | string | 是 | 对应 `ThemeSignal.theme_id` |
| `theme_label` | string | 是 | 展示标题 |
| `theme_summary` | string | 否 | 展示说明 |
| `supporting_event_bundle_ids` | string[] | 是 | 支撑主题的事件包 |
| `theme_score` | number | 是 | 投影自主题强度 |

约束：

- `DailyReviewTheme` 只能来自 `ThemeSignal`
- 最终写入 issue 的主题顺序应与 `theme_score` 降序保持一致

### 4.7 `EditorialReviewItem`

定义：
供人工编辑复核的结构化条目。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `review_item_id` | string | 是 | 复核条目唯一标识 |
| `event_bundle_id` | string | 是 | 对应事件包 |
| `review_flags` | string[] | 是 | 触发复核的风险标记 |
| `supporting_evidence` | object | 是 | 栏目建议、主题、分数、来源等辅助证据 |
| `suggested_action` | enum | 是 | `VERIFY_BUNDLE` / `VERIFY_SECTION` / `VERIFY_PRIORITY` / `VERIFY_DEEP_DIVE` / `COMPRESS_OR_SPLIT` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `review_flags` 不得为空
- `EditorialReviewItem` 只能由 `compose_issue_structure` 统一生成
- `EditorialReviewItem` 不等于失败对象

### 4.8 `DailyReviewDraft`

定义：
完成结构编排、但尚未完全投影为最终产物文件的日报草稿。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `issue_date` | string | 是 | 当前日报日期，格式为 `YYYY-MM-DD` |
| `section_entries` | object | 是 | 固定 6 个栏目 key，对应 `DailyReviewEntry[]` |
| `top_themes` | `DailyReviewTheme`[] | 是 | 当日主线主题，可为空 |
| `editorial_notes` | string[] | 是 | 对编辑的结构提示，可为空 |
| `selected_event_bundle_ids` | string[] | 是 | 正式入选日报的事件包 ID |
| `review_item_ids` | string[] | 是 | 待编辑复核条目 ID，可为空 |
| `issue_status` | enum | 是 | `COMPOSED` / `NEEDS_EDITOR_REVIEW` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `section_entries` 必须显式包含 6 个固定栏目 key，允许 value 为空数组
- `issue_status = NEEDS_EDITOR_REVIEW` 时，`review_item_ids` 不得为空
- `issue_status = COMPOSED` 时，`review_item_ids` 可以为空数组

### 4.9 `DailyReviewIssue`

定义：
最终正式交付的结构化日报对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `daily_review_issue_id` | string | 是 | 日报对象唯一标识 |
| `issue_date` | string | 是 | 当前日报日期，格式为 `YYYY-MM-DD` |
| `sections` | object | 是 | 固定 6 个栏目 key，对应 `DailyReviewEntry[]` |
| `top_themes` | `DailyReviewTheme`[] | 是 | 当日主线主题，可为空 |
| `editorial_notes` | string[] | 是 | 编辑说明，可为空 |
| `source_digest_candidate_ids` | string[] | 是 | 被该日报使用的全部 Digest 候选 |
| `render_status` | enum | 是 | `COMPOSED` / `NEEDS_EDITOR_REVIEW` |
| `run_id` | string | 是 | 本轮运行标识 |

约束：

- `render_status` 必须无分支投影自 `DailyReviewDraft.issue_status`
- `source_digest_candidate_ids` 应等于所有入选 `DailyReviewEntry.source_digest_candidate_ids` 的去重并集
- 当前阶段同一 `run_id` 下只允许存在 1 个 `DailyReviewIssue`

### 4.10 `DailyReviewFailureRecord`

定义：
`compose-daily-review` 的唯一失败账本对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `failure_id` | string | 是 | 失败记录唯一标识 |
| `run_id` | string | 是 | 本轮运行标识 |
| `step_name` | string | 是 | 失败发生的 step |
| `scope_type` | string | 是 | 例如 `INPUT`、`EVENT_BUNDLE`、`THEME`、`ISSUE`、`SYSTEM` |
| `scope_id` | string | 否 | 对应对象 ID |
| `failure_type` | string | 是 | 失败类型代码 |
| `message` | string | 是 | 错误摘要 |
| `details` | object | 是 | 辅助诊断信息 |
| `retryable` | boolean | 是 | 是否允许重试 |
| `recorded_at` | string | 是 | 记录时间 |

约束：

- 所有失败记录都必须带 `step_name`
- 对象级失败只进入 ledger，不在业务对象上重复写 `FAILED`

### 4.11 `DailyReviewStepResult`

定义：
单 step 的运行结果摘要。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `step_name` | string | 是 | step 名称 |
| `status` | enum | 是 | `SUCCESS_WITH_OUTPUT` / `SUCCESS_EMPTY` / `FAILED` |
| `input_count` | integer | 是 | 输入对象数 |
| `output_count` | integer | 是 | 输出对象数 |
| `review_count` | integer | 是 | 新增 review 条目数 |
| `failure_count` | integer | 是 | 新增 failure 条目数 |
| `started_at` | string | 是 | step 开始时间 |
| `finished_at` | string | 是 | step 结束时间 |

### 4.12 `DailyReviewStepManifest`

定义：
整个 `compose-daily-review` 运行的 step 汇总对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_name` | string | 是 | 固定为 `compose-daily-review` |
| `step_results` | `DailyReviewStepResult`[] | 是 | 本轮 step 汇总 |
| `started_at` | string | 是 | workflow 开始时间 |
| `finished_at` | string | 是 | workflow 结束时间 |
| `workflow_status` | enum | 是 | `SUCCEEDED` / `PARTIAL_SUCCESS` / `FAILED` |
| `artifact_paths` | object | 是 | 本轮产物路径 |

约束：

- `workflow_status = FAILED` 时，仍应尽力返回最小可见 manifest
- `artifact_paths` 至少应包含主产物与辅助产物路径

### 4.13 `DailyReviewReport`

定义：
供人快速复盘本轮日报编排结果的汇总对象。

最小字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | string | 是 | 本轮运行标识 |
| `workflow_status` | enum | 是 | `SUCCEEDED` / `PARTIAL_SUCCESS` / `FAILED` |
| `issue_summary` | object | 是 | issue 数、栏目分布、主题数等汇总 |
| `review_summary` | object | 是 | review item 数量与按 flag 统计 |
| `failure_summary` | object | 是 | ledger 失败数量与按类型统计 |
| `artifact_summary` | object | 是 | 产物路径与时长等元信息 |
| `generated_at` | string | 是 | 报告生成时间 |

## 5. 主产物与辅助产物契约

### 5.1 主产物

当前阶段主产物固定为：

- `daily-review-issues.json`

契约：

- 文件内容是 `DailyReviewIssue[]`
- 当前阶段长度只允许为 `0` 或 `1`
- `0` 表示合法空结果
- `1` 表示本轮正式形成日报

### 5.2 辅助产物

当前阶段辅助产物固定为：

- `editorial-review.json`
- `daily-review-failures.json`
- `step-manifest.json`
- `daily-review-report.md`
- `daily-review.md`

契约：

- `editorial-review.json` 内容为 `EditorialReviewItem[]`
- `daily-review-failures.json` 内容为 `DailyReviewFailureRecord[]`
- `step-manifest.json` 内容为 `DailyReviewStepManifest`
- `daily-review-report.md` 是面向人的 Markdown 汇总
- `daily-review.md` 是面向人的日报正文；空结果时允许写出空骨架说明

## 6. 当前阶段明确不定的内容

本文档当前不固定：

- `supporting_signals.details` 的完整子字段
- Markdown 模板中的具体文案风格
- 指标最终写入日志、文件还是时序系统

这些内容可以后续补充，但不得破坏本文档中的对象边界和状态语义。
