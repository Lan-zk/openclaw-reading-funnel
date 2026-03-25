# `compose-daily-review` 原子能力设计

## 1. 文档目的

本文档定义 `compose-daily-review` workflow 内部的原子能力边界。

本文档重点回答五个问题：

- 这一层最小但有独立边界的能力单元是什么
- 这些能力如何把 `DigestCandidate` 组织成日报成稿
- 候选未入选、需要编辑复核、执行失败如何严格分离
- 中间对象如何保持稳定，不在实现中漂移
- 最终 `DailyReviewIssue` 的字段分别由哪一步产生

本文档是 [reading-funnel-global-implementation-guide.md](./reading-funnel-global-implementation-guide.md) 的下钻设计。
如果后续继续展开其他 workflow，建议沿用相同模板。

## 2. 设计范围

本文档只覆盖一个 workflow：

- `compose-daily-review`

本文档不覆盖：

- `ingest-normalize`
- `digest-candidates`
- `curate-retain`
- `generate-long-cycle-assets`
- 顶层编排脚本实现

## 3. workflow 目标与边界

### 3.1 统一任务

`compose-daily-review` 的统一任务是：

> 把 `DigestCandidate` 组织成当天真正值得读的 `DailyReviewIssue`，让用户面对的是结构化日报成稿，而不是候选列表。

### 3.2 负责范围

本 workflow 负责：

- 同一事件候选归并
- 栏目归属判断
- 核心主题提炼
- 当日重要性评估
- 深挖主题识别
- 日报结构编排
- 人类可读成稿渲染

### 3.3 明确不做

本 workflow 不负责：

- 上游候选清洗与摘要生成
- 长期价值判断
- 人工留存决策
- 长周期资产生成

## 4. 运行结果语义

### 4.1 step 结果

`compose-daily-review` 中的步骤结果统一分为三类：

- `SUCCESS_WITH_OUTPUT`
成功生成至少一个包含正式内容条目的 `DailyReviewIssue`
- `SUCCESS_EMPTY`
运行成功，但当天没有足够内容进入正式 issue
- `FAILED`
执行异常，无法完成预期步骤

说明：
`SUCCESS_EMPTY` 允许仍然产出一个空 issue 骨架或空报告，但不能伪装成有内容的日报。

### 4.2 事件包去向

对单个事件包而言，只能进入三类业务结果：

- `SELECTED`
进入当日 issue
- `OMITTED`
未进入当日 issue，但不是失败
- `REVIEW_REQUIRED`
判断不稳定，需人工编辑复核

### 4.3 三者必须分开

这里有三个硬约束：

- `OMITTED` 不是失败
- `REVIEW_REQUIRED` 不是失败
- `FAILED` 只存在于运行级 failure ledger

### 4.4 最终产物状态

最终 `DailyReviewIssue` 的产物状态单独定义，不复用事件包去向：

- `COMPOSED`
issue 已形成正式日报成稿
- `NEEDS_EDITOR_REVIEW`
issue 已形成成稿，但包含待人工复核项

说明：

- 事件包去向只描述单个事件包是否入选
- step 结果只描述本次 workflow 执行情况
- issue 产物状态只描述最终日报成品状态

## 5. 失败事实与编辑复核规则

### 5.1 单一失败真相

`compose-daily-review` 的运行级失败真相只有一个权威来源：

- `DailyReviewFailureRecord[]`

它记录：

- 执行异常
- 模板渲染失败
- 输入结构损坏
- 不可恢复的对象级异常

### 5.2 编辑复核不是失败

这一层的低置信度对象进入：

- `EditorialReviewItem[]`

它承接的不是执行失败，而是编辑判断不稳定的事件包，例如：

- 事件归并置信度不足
- 栏目归属有争议
- 当日重要性判断不稳定
- 深挖主题候选不明确
- 成稿结构需要人工压缩或重排

### 5.3 唯一最终裁决点

本 workflow 只有一个能力可以正式决定事件包是否进入 issue，并同时决定 issue 的产物状态：

- `compose_issue_structure`

前面的原子能力只允许做三件事：

- 生成证据
- 生成分类建议
- 生成风险标记

前面的能力不得直接把事件包裁决为 `SELECTED`、`OMITTED` 或 `REVIEW_REQUIRED`。

### 5.4 偏好信号约束

如果这一层未来接入 `PreferenceSignal`，只能用于同重要性层内的轻量排序辅助，不能单独决定：

- 是否进入 issue
- 是否进入某个栏目
- 是否覆盖公共重要性更高的事件

## 6. 中间对象最小契约

为了稳定能力边界，本文档定义 5 个中间对象。

### 6.1 固定栏目枚举 `DailyReviewSection`

`compose-daily-review` 的栏目只能取全局固定 6 个值：

- `今日大事`
- `变更与实践`
- `安全与风险`
- `开源与工具`
- `洞察与数据点`
- `主题深挖`

说明：

- 中间对象中的栏目建议只能使用这 6 个值
- 最终 `DailyReviewIssue.sections` 也只能使用这 6 个 key
- 不允许中间步骤发明额外栏目

### 6.2 `EventBundle`

最小字段：

- `event_bundle_id`
- `source_digest_candidate_ids`
- `primary_digest_candidate_id`
- `merge_confidence`
- `event_scope`

定义：
同一事件、同一议题或同一变更条线的候选包。

### 6.3 `ThemeSignal`

最小字段：

- `theme_id`
- `supporting_event_bundle_ids`
- `theme_score`
- `theme_type`

定义：
由多个事件包共同支持的当日主题信号。

### 6.4 `DailyReviewEvidence`

最小字段：

- `event_bundle_id`
- `proposed_section`
- `section_confidence`
- `section_reasons`
- `daily_importance_score`
- `deep_dive_signal`
- `theme_ids`
- `review_flags`

定义：
进入最终编排前的统一证据对象。

说明：
前置能力产生的栏目建议、重要性分、主题信号和低置信度标记，都统一写入 `DailyReviewEvidence`。
本 workflow 不再单独维护 `SectionProposal`，避免分类建议和最终证据流重复。

### 6.5 `DailyReviewDraft`

最小字段：

- `issue_date`
- `section_entries`
- `top_themes`
- `editorial_notes`
- `selected_event_bundle_ids`
- `review_item_ids`
- `issue_status`

定义：
完成结构编排、但尚未渲染成最终可读文稿的日报草稿。

## 7. 最终对象字段来源映射

为了避免最终字段无法溯源，`DailyReviewIssue` 的关键字段来源必须固定。

### 7.1 `DailyReviewIssue` 字段映射

- `issue_date`
来自运行上下文，由 `compose_issue_structure` 写入
- `sections`
来自 `compose_issue_structure`
- `top_themes`
来自 `identify_top_themes`，由 `compose_issue_structure` 收束写入
- `editorial_notes`
来自 `compose_issue_structure`，结合 `review_flags` 和编辑提示生成
- `source_digest_candidate_ids`
来自 `merge_same_event_candidates` 生成的 `EventBundle`
- `render_status`
由 `compose_issue_structure` 在 `DailyReviewDraft.issue_status` 中先行确定，再由 `render_human_readable_issue` 无分支投影写入

### 7.2 `EditorialReviewItem` 字段映射原则

`EditorialReviewItem` 必须至少包含：

- `event_bundle_id`
- `review_flags`
- `supporting_evidence`
- `suggested_action`

它只能由 `compose_issue_structure` 统一生成。

## 8.3 对象流转映射

本 workflow 的唯一对象流转如下：

1. `DigestCandidate[]`
2. `EventBundle[]`
3. `ThemeSignal[]`
4. `DailyReviewEvidence[]`
5. `DailyReviewDraft`
6. `EditorialReviewItem[]`
7. `DailyReviewIssue`

说明：

- `DailyReviewEvidence[]` 是唯一证据汇总层
- 不再额外维护与之平行的 `SectionProposal`
- `render_human_readable_issue` 只消费 `DailyReviewDraft`

## 8. 原子能力清单

`compose-daily-review` 的原子能力清单如下：

1. `merge_same_event_candidates`
2. `classify_sections`
3. `identify_top_themes`
4. `score_daily_importance`
5. `detect_deep_dive_topics`
6. `compose_issue_structure`
7. `render_human_readable_issue`

## 9. 原子能力逐项设计

### 9.1 `merge_same_event_candidates`

#### 解决的问题 / 目标效果

把同一事件、同一变更或同一议题线上的多个 `DigestCandidate` 归并成事件包，减少日报中的重复占位。

#### 边界范围 / 明确不做

负责：

- 事件归并
- 主候选选择
- 归并置信度评估

不负责：

- 栏目归属裁决
- 最终是否入选日报
- 长期主题判断

#### 输入对象 / 输出对象

- 输入：`DigestCandidate[]`
- 输出：`EventBundle[]`

#### 核心实现思路

日报面对的是“事件”而不是“候选条目”。这一步只做事件层收敛，不做栏目和重要性结论。

#### 失败语义 / 人工介入点

- 归并执行异常：写入 `DailyReviewFailureRecord[]`
- 归并置信度低：只写 `review_flags`
- 人工介入点：高争议事件归并样本复核

### 9.2 `classify_sections`

#### 解决的问题 / 目标效果

为每个事件包生成栏目归属建议，并写入统一证据层，使后续编排面对的是结构化证据，而不是裸事件包。

#### 边界范围 / 明确不做

负责：

- 栏目候选判断
- 栏目理由生成
- 栏目置信度标记

不负责：

- 最终栏目裁决
- 是否入选日报
- 深挖主题判断

#### 输入对象 / 输出对象

- 输入：`EventBundle[]`
- 输出：更新后的 `DailyReviewEvidence[]`

#### 核心实现思路

栏目分类只输出建议，且栏目值只能取固定 6 个 `DailyReviewSection`。
它不直接落定最终栏目，避免过早绑定结构。

#### 失败语义 / 人工介入点

- 分类执行异常：写入 `DailyReviewFailureRecord[]`
- 分类不稳定：写入 `review_flags`
- 人工介入点：栏目边界规则校准

### 9.3 `identify_top_themes`

#### 解决的问题 / 目标效果

识别当天最值得成为日报主线的主题信号。

#### 边界范围 / 明确不做

负责：

- 提取主题信号
- 聚合同主题事件包
- 计算主题强度

不负责：

- 最终 issue 结构裁决
- 深挖条目落位
- 长周期主题判断

#### 输入对象 / 输出对象

- 输入：`EventBundle[]`
- 输出：`ThemeSignal[]`

#### 核心实现思路

主题是日报的“主线”，不是简单标签。这里先识别信号，再交给结构编排决定是否写入最终 issue。

#### 失败语义 / 人工介入点

- 识别执行异常：写入 `DailyReviewFailureRecord[]`
- 主题不稳定：写入 `review_flags`
- 人工介入点：主题抽象粒度校准

### 9.4 `score_daily_importance`

#### 解决的问题 / 目标效果

为每个事件包评估当天重要性，帮助后续决定入选优先级与排序。

#### 边界范围 / 明确不做

负责：

- 当日重要性评分
- 公共重要性与个人相关性综合评估

不负责：

- 最终入选裁决
- 最终排序落位
- 长期价值判断

#### 输入对象 / 输出对象

- 输入：`DailyReviewEvidence[]`、可选主题信号
- 输出：更新后的 `DailyReviewEvidence[]`

#### 核心实现思路

这里只生成重要性证据，不直接决定是否进入日报。
公共重要性优先级高于个人偏好。

#### 失败语义 / 人工介入点

- 评分执行异常：写入 `DailyReviewFailureRecord[]`
- 评分不稳定：写入 `review_flags`
- 人工介入点：重要性权重校准

### 9.5 `detect_deep_dive_topics`

#### 解决的问题 / 目标效果

识别哪些事件包或主题适合进入“主题深挖”栏目。

#### 边界范围 / 明确不做

负责：

- 深挖候选识别
- 深挖信号标记

不负责：

- 最终是否进入深挖栏目
- 长周期专题资产生成

#### 输入对象 / 输出对象

- 输入：`DailyReviewEvidence[]`、`ThemeSignal[]`
- 输出：更新后的 `DailyReviewEvidence[]`

#### 核心实现思路

“适合深挖”只是建议信号，不是最终栏目裁决。

#### 失败语义 / 人工介入点

- 检测执行异常：写入 `DailyReviewFailureRecord[]`
- 信号不稳定：写入 `review_flags`
- 人工介入点：深挖门槛校准

### 9.6 `compose_issue_structure`

#### 解决的问题 / 目标效果

把前面各能力产出的证据收束成正式日报结构，决定哪些事件包进入 issue、进入哪个栏目，以及是否需要编辑复核。

#### 边界范围 / 明确不做

负责：

- 正式裁决 `SELECTED` / `OMITTED` / `REVIEW_REQUIRED`
- 生成 `DailyReviewDraft`
- 生成 `EditorialReviewItem[]`
- 决定 `DailyReviewDraft.issue_status`

不负责：

- 最终文稿渲染
- 长期知识沉淀

#### 输入对象 / 输出对象

- 输入：`EventBundle[]`、`ThemeSignal[]`、`DailyReviewEvidence[]`
- 输出：`DailyReviewDraft`、`EditorialReviewItem[]`

#### 核心实现思路

这是 workflow 唯一正式裁决点。
它根据栏目建议、重要性分、主题信号和复核标记，决定：

- 哪些事件包进入 issue
- 每个入选事件包进入哪个固定栏目
- 哪些事件包进入复核池
- 最终 `issue_status` 是 `COMPOSED` 还是 `NEEDS_EDITOR_REVIEW`

#### 失败语义 / 人工介入点

- 结构编排失败属于系统执行失败
- 若最终没有任何 `SELECTED` 且没有任何 `REVIEW_REQUIRED`，返回 `SUCCESS_EMPTY`
- 人工介入点在 `EditorialReviewItem[]`，而不是前置步骤

### 9.7 `render_human_readable_issue`

#### 解决的问题 / 目标效果

把 `DailyReviewDraft` 渲染为人类可读日报，并将 draft 中已确定的产物状态投影到最终 `DailyReviewIssue`。

#### 边界范围 / 明确不做

负责：

- 文稿渲染
- 模板填充
- 将 `DailyReviewDraft.issue_status` 无分支投影到最终 `DailyReviewIssue.render_status`

不负责：

- 再次裁决事件包是否入选
- 再次决定 issue 是否需要编辑复核
- 调整栏目结构
- 长期资产输出

#### 输入对象 / 输出对象

- 输入：`DailyReviewDraft`
- 输出：`DailyReviewIssue`、`daily-review.md`

#### 核心实现思路

渲染层只负责把已确定的结构转成可读成稿，不再次承担编辑判断或状态判断。

#### 失败语义 / 人工介入点

- 渲染失败：写入 `DailyReviewFailureRecord[]`
- 渲染成功时：最终 `render_status` 必须等于 `DailyReviewDraft.issue_status`
- 人工介入点：模板或文稿样式修正

## 10. 设计结论

`compose-daily-review` 到此为止只完成三件事：

1. 把 digest 候选收敛成事件包
2. 为每个事件包积累栏目、主题、重要性和深挖证据
3. 在唯一裁决点上把事件包正式落入 `SELECTED`、`OMITTED` 或 `REVIEW_REQUIRED`，并确定最终 issue 状态，再渲染成日报成稿

这版设计特别强调三条规则：

- 事件包去向、step 结果、issue 产物状态必须三套分离
- 只有 `compose_issue_structure` 可以做最终入选裁决
- `render_human_readable_issue` 只负责渲染，不再承担编辑判断
