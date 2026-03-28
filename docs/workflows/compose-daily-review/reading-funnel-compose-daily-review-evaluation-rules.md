# `compose-daily-review` 评估规则

## 1. 文档目的

本文档定义 `compose-daily-review` 作为顶层 skill 时的最小评估规则。

本文档只覆盖三类评估：

- 触发评估
- workflow 结果评估
- 运行观测指标

本文档不覆盖：

- 其他 workflow 的评估
- 人工长期价值判断
- UI 视觉评审

## 2. 触发评估

### 2.1 `should-trigger`

以下请求应触发 `compose-daily-review`：

1. 把这些 Digest 候选编成今天的日报
2. 给我一份今天真正值得读的结构化日报
3. 按栏目整理今天的候选，并生成成稿
4. 从 Digest 输入池里挑出今日大事和主题深挖
5. 生成今天的 daily review issue
6. 把候选按重要性和主题编排成日报
7. 输出一份可读的日报 Markdown
8. 跑一遍第三步，把 Digest 候选变成日报

### 2.2 `should-not-trigger`

以下请求不应触发 `compose-daily-review`：

1. 同步我的 RSS 来源
2. 把这些来源拉下来并归一化
3. 给候选池做去重、摘要和初排
4. 帮我筛一轮今天抓到的候选
5. 帮我判断哪些内容值得长期留存
6. 把日报里高价值内容写进知识库
7. 产出周刊或专题素材包
8. 只想重跑第一步或第二步

### 2.3 `near-miss`

以下请求容易混淆，需要额外确认：

1. 整理今天的阅读内容
2. 生成今天要读的东西
3. 重跑第三步
4. 帮我出一份今日清单
5. 刷新今天的阅读池

判定规则：

- 如果用户重点在“抓取、导入、同步、归一”，触发 `ingest-normalize`
- 如果用户重点在“去重、抽取、清洗、摘要、初排”，触发 `digest-candidates`
- 如果用户重点在“日报栏目、重要性编排、主题主线、成稿”，触发 `compose-daily-review`
- 如果用户重点在“长期保留、知识入库、人工决策”，转到 `curate-retain`

## 3. Workflow 评估

### 3.1 happy path

场景：

- 上游给出 20 到 40 个 `DigestCandidate`
- 存在同一事件的多来源候选
- 至少形成 1 到 3 个明显主题
- 最终产生 1 份正式日报

期望：

- `workflow_status = SUCCEEDED`
- `daily-review-issues.json` 成功产出，且长度为 `1`
- `editorial-review.json` 可为空
- `daily-review-failures.json` 为空数组
- `daily-review.md` 成功产出

### 3.2 empty result path

场景：

- 输入 `DigestCandidate[]` 合法
- 但所有事件包都被正式 `OMITTED`
- 没有事件包进入 `REVIEW_REQUIRED`

期望：

- `workflow_status = SUCCEEDED`
- `compose_issue_structure` 为 `SUCCESS_EMPTY`
- `daily-review-issues.json` 为空数组
- `editorial-review.json` 为空数组
- 不生成伪失败记录

### 3.3 editor-review path

场景：

- 事件归并置信度不足
- 栏目边界存在争议
- 深挖候选存在歧义
- 仍然足以形成一版日报成稿

期望：

- `workflow_status = SUCCEEDED` 或 `PARTIAL_SUCCESS`
- `daily-review-issues.json` 长度为 `1`
- `editorial-review.json` 非空
- `DailyReviewIssue.render_status = NEEDS_EDITOR_REVIEW`
- 低置信度对象不被误记为失败

### 3.4 partial success path

场景：

- 一部分事件包评分失败或主题识别失败
- 其余事件包成功完成编排
- 最终仍形成正式日报

期望：

- `workflow_status = PARTIAL_SUCCESS`
- 成功对象继续产出
- `daily-review-failures.json` 显式记录失败对象
- 失败不阻断其他事件包流转

### 3.5 failure path

场景：

- 输入文件损坏无法解析
- 或输出目录不可写
- 或 failure ledger / manifest 无法落盘
- 或结构化 issue 无法形成

期望：

- `workflow_status = FAILED`
- 主产物与辅助产物不应伪装成成功
- 至少向调用方返回最小可见错误

### 3.6 ambiguous path

场景：

- 两组事件高度相关，但不确定是否应归并
- 主题强度接近阈值
- 条目既可进固定栏目，也可进 `主题深挖`

期望：

- `workflow_status = SUCCEEDED` 或 `PARTIAL_SUCCESS`
- 有争议对象进入 `editorial-review.json`
- `OMITTED`、`REVIEW_REQUIRED` 与 `FAILED` 仍严格分离
- 只有执行异常才进入 ledger

## 4. 产物评估

### 4.1 主产物要求

每次运行至少要满足以下之一：

- 产出长度为 `1` 的 `daily-review-issues.json`
- 或产出空数组 `daily-review-issues.json`，同时 `step-manifest.json` 明确表明为合法空结果

### 4.2 辅助产物要求

每次运行必须有：

- `step-manifest.json`
- `daily-review-report.md`
- `daily-review-failures.json`
- `editorial-review.json`

以下产物也应存在，但允许为空骨架：

- `daily-review.md`

## 5. 关键断言

### 5.1 结果语义断言

- `OMITTED` 不等于失败
- `REVIEW_REQUIRED` 不等于失败
- `FAILED` 只存在于 `DailyReviewFailureRecord[]`
- 只有 `compose_issue_structure` 可以正式写最终去向
- `render_human_readable_issue` 不得重新裁决栏目和入选

### 5.2 数据断言

- 每个 `EditorialReviewItem.event_bundle_id` 都必须能回溯到 `EventBundle`
- 每个 `DailyReviewEntry.event_bundle_id` 都必须能回溯到 `EventBundle`
- 每个 `DailyReviewTheme.theme_id` 都必须能回溯到 `ThemeSignal`
- `DailyReviewIssue.source_digest_candidate_ids` 必须能回溯到上游 `DigestCandidate`
- 所有失败记录都必须带 `step_name`

### 5.3 路由断言

- `PreferenceSignal` 只能参与同重要性层内的轻量排序
- 低置信度栏目分类优先进入 review，而不是直接失败
- 深挖建议不自动等于进入 `主题深挖`
- 空结果路径不应被误判为失败

## 6. 观测指标

建议最少记录以下指标：

| 指标 | 说明 |
|---|---|
| `digest_candidate_input_count` | 输入 Digest 候选数 |
| `event_bundle_count` | 事件包总数 |
| `theme_signal_count` | 主题信号总数 |
| `selected_event_bundle_count` | 正式入选日报的事件包数 |
| `omitted_event_bundle_count` | 被正式省略的事件包数 |
| `review_required_bundle_count` | 进入编辑复核的事件包数 |
| `editorial_review_item_count` | 待复核条目数 |
| `issue_count` | 本轮日报对象数，当前阶段应为 `0` 或 `1` |
| `section_entry_count` | 全部栏目条目总数 |
| `deep_dive_entry_count` | `主题深挖` 栏目条目数 |
| `failure_record_count` | ledger 失败记录总数 |
| `workflow_duration_ms` | workflow 总耗时 |

## 7. 最小测试矩阵

建议至少覆盖以下 10 类测试：

1. 同一事件的多来源候选被归并到同一个 `EventBundle`
2. 归并低置信度对象进入 review，而不是失败
3. 栏目建议只能落在固定 6 个 `DailyReviewSection`
4. 主题信号能从多个事件包中正确聚合
5. 重要性评分不会被 `PreferenceSignal` 单独统治
6. 深挖信号只产生建议，不直接决定最终栏目
7. `compose_issue_structure` 是唯一正式写最终去向的步骤
8. 全部事件被 `OMITTED` 时 workflow 仍成功
9. 单对象处理失败不阻断其他对象
10. `daily-review-failures.json` 或 `step-manifest.json` 写入失败时 workflow 为 `FAILED`

## 8. 人工复盘入口

出现以下情况时应进入人工复盘：

- `editorial_review_item_count` 异常升高
- `issue_count` 连续多轮为 `0`
- `deep_dive_entry_count` 长期为 `0` 或突然异常升高
- 同一 `review_flag` 连续多轮集中出现
- `selected_event_bundle_count` 与输入规模长期严重失衡

人工复盘最少查看：

- `daily-review-failures.json`
- `editorial-review.json`
- `step-manifest.json`
- 本轮输入 `DigestCandidate` 样本
- `daily-review.md`

## 9. 当前阶段明确不定的内容

本文档当前不固定：

- 各栏目容量阈值的最终取值
- `review_flag` 的报警阈值
- 触发评估最终是由规则集、eval 文件还是测试框架承载

这些内容可以后续补充，但不得破坏本文档中的评估边界和成功定义。
