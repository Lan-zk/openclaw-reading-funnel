# `curate-retain` 原子能力设计

## 1. 文档目的

本文档定义 `curate-retain` workflow 内部的原子能力边界。

本文档重点回答五个问题：

- 这一层最小但有独立边界的能力单元是什么
- 这些能力如何把“值得精读的对象”转成正式留存决策
- 人工裁决、执行失败、资产状态如何严格分离
- 中间对象如何保持稳定，不在实现中漂移
- 最终 `RetentionDecision`、`KnowledgeAsset`、`PreferenceSignal` 的字段分别由哪一步产生

本文档是 [reading-funnel-global-implementation-guide.md](./reading-funnel-global-implementation-guide.md) 的下钻设计。
如果后续继续展开其他 workflow，建议沿用相同模板。

## 2. 设计范围

本文档只覆盖一个 workflow：

- `curate-retain`

本文档不覆盖：

- `ingest-normalize`
- `digest-candidates`
- `compose-daily-review`
- `generate-long-cycle-assets`
- 顶层编排脚本实现

## 3. workflow 目标与边界

### 3.1 统一任务

`curate-retain` 的统一任务是：

> 把值得精读的对象组织成人工确认队列，记录正式留存决策，并把高价值内容沉淀为 `KnowledgeAsset`，同时从已确认决策中派生轻量 `PreferenceSignal`。

### 3.2 负责范围

本 workflow 负责：

- 待精读队列生成
- 人工确认入口组织
- 留存决策记录
- 长期价值标签派生与资产草稿组装
- 知识资产写入
- 偏好信号派生

### 3.3 明确不做

本 workflow 不负责：

- 上游候选清洗
- 日报编排
- 周刊或专题成稿
- 自动替代人工做长期价值判断
- 让偏好信号反向决定留存

## 4. 运行结果语义

### 4.1 step 结果

`curate-retain` 中的步骤结果统一分为三类：

- `SUCCESS_WITH_OUTPUT`
成功记录至少一个正式 `RetentionDecision`
- `SUCCESS_EMPTY`
运行成功，但本轮没有新增正式决策
- `FAILED`
执行异常，无法完成预期步骤

### 4.2 决策结果

对单个留存对象而言，只能进入四类正式决策结果：

- `KEEP`
确认值得长期沉淀
- `DROP`
确认不值得长期沉淀
- `DEFER`
暂不决定，保留待后续再看
- `NEEDS_RECHECK`
需要重新核查对象或上下文

说明：

- 这四类结果只表示人工决策结果
- 它们不是 step 执行结果
- 它们也不是知识资产状态

### 4.3 产物状态

本 workflow 还存在两套独立产物状态：

- `KnowledgeAsset.asset_status`
取值沿用全局设计：`STORED` / `ARCHIVED`
- `PreferenceSignal`
不是状态机对象，而是派生信号记录

### 4.4 三者必须分开

这里有三个硬约束：

- `KEEP/DROP/DEFER/NEEDS_RECHECK` 只表示人工决策
- `SUCCESS_WITH_OUTPUT/SUCCESS_EMPTY/FAILED` 只表示 workflow 执行结果
- `STORED/ARCHIVED` 只表示知识资产状态

## 5. 失败事实与人工决策规则

### 5.1 单一失败真相

`curate-retain` 的运行级失败真相只有一个权威来源：

- `CurationFailureRecord[]`

它记录：

- 输入结构异常
- 人工确认记录失败
- 存储写入失败
- 派生规则执行失败

### 5.2 只有人能做最终留存决策

本 workflow 只有一个能力可以正式决定对象的长期价值结果：

- `capture_human_decision`

其他能力都不得直接把对象裁决为：

- `KEEP`
- `DROP`
- `DEFER`
- `NEEDS_RECHECK`

### 5.3 后置能力不得反改决策

以下后置能力只允许消费决策，不允许重新裁决决策：

- `persist_retention_decision`
- `derive_long_term_tags`
- `store_knowledge_asset`
- `derive_preference_signals`

说明：

- `store_knowledge_asset` 不能因为写入失败就把 `KEEP` 改成 `DROP`
- `derive_preference_signals` 不能因为信号不足就回写人工决策
- 决策真相一旦落盘，后续只能派生，不得反写

## 6. 偏好信号使用规则

### 6.1 偏好信号只能从已确认决策派生

`PreferenceSignal` 只能来源于：

- 已落盘的 `RetentionDecision`

说明：

- 本 workflow 中的显式负反馈，统一表示为正式 `RetentionDecision`，通常体现为 `DROP` 决策及其负向 `reason_tags`
- `KnowledgeAsset` 不是新的裁决来源，只能作为信号派生时的补充上下文
- 本 workflow 不引入独立于 `RetentionDecision` 之外的负反馈真相模型

### 6.2 明确禁止

以下做法是禁止的：

- 用行为猜测替代正式留存决策
- 用偏好信号自动写回 `KEEP/DROP`
- 因为知识资产未写入成功，就否定人工保留判断

## 7. 中间对象最小契约

为了稳定能力边界，本文档定义 6 个中间对象。

### 7.1 `ReadQueueItem`

最小字段：

- `queue_item_id`
- `target_type`
- `target_id`
- `source_digest_candidate_ids`
- `queue_reason`
- `queue_priority`

定义：
进入人工精读或复核队列的对象。

### 7.2 `HumanDecisionDraft`

最小字段：

- `target_type`
- `target_id`
- `decision`
- `reason_tags`
- `reason_text`
- `decision_by`
- `decision_at`

定义：
由人工确认入口收集到、但尚未正式持久化的留存决策草稿。

### 7.3 `RetentionDecisionRecord`

最小字段：

- `retention_decision_id`
- `target_type`
- `target_id`
- `decision`
- `confidence`
- `reason_tags`
- `reason_text`
- `decision_at`
- `decision_by`
- `run_id`

定义：
已正式落盘的 `RetentionDecision` 对象。

说明：
这里是对全局 `RetentionDecision` 契约的本 workflow 视角展开。

### 7.4 `KnowledgeAssetDraft`

最小字段：

- `origin_retention_decision_id`
- `target_type`
- `target_id`
- `title`
- `summary`
- `canonical_url`
- `topic_tags`
- `asset_type`
- `long_term_value_reason`

定义：
基于 `KEEP` 决策派生出的知识资产草稿。

### 7.5 `RetainedTargetSnapshot`

最小字段：

- `target_type`
- `target_id`
- `title`
- `summary`
- `canonical_url`
- `source_digest_candidate_ids`

定义：
与正式 `RetentionDecision` 对应的上游对象快照。

说明：
它用于补足 `KnowledgeAssetDraft` 所需的标题、摘要、链接等上游元信息，避免 `derive_long_term_tags` 依赖未声明的隐式查找。

### 7.6 `PreferenceSignalDraft`

最小字段：

- `signal_type`
- `signal_value`
- `weight`
- `origin_retention_decision_id`
- `supplementary_knowledge_asset_id`
- `expires_at`

定义：
基于已确认决策派生出的偏好信号草稿。

说明：

- `origin_retention_decision_id` 是唯一 canonical origin
- `supplementary_knowledge_asset_id` 仅用于补充上下文，可为空

## 8. 最终对象字段来源映射

为了避免最终字段无法溯源，3 类正式产物的关键字段来源必须固定。

### 8.1 `RetentionDecision` 字段映射

- `target_type`
来自 `build_read_queue` 确认的对象类型，由 `capture_human_decision` 写入
- `target_id`
来自 `build_read_queue` 确认的对象标识，由 `capture_human_decision` 写入
- `decision`
只来自 `capture_human_decision`
- `confidence`
来自 `capture_human_decision` 的人工输入或固定规则补全
- `reason_tags`
来自 `capture_human_decision`
- `reason_text`
来自 `capture_human_decision`
- `decision_at`
来自 `capture_human_decision`
- `decision_by`
来自 `capture_human_decision`
- `run_id`
由 `persist_retention_decision` 在正式落盘时写入

### 8.2 `KnowledgeAsset` 字段映射

- `knowledge_asset_id`
由 `store_knowledge_asset` 在正式落盘时生成
- `origin_retention_decision_id`
来自 `persist_retention_decision`
- `title`
来自 `RetainedTargetSnapshot.title`，由 `derive_long_term_tags` 组装、`store_knowledge_asset` 正式写入
- `summary`
来自 `RetainedTargetSnapshot.summary` 或人工补充，不在本 workflow 内重新生成长摘要
- `canonical_url`
来自 `RetainedTargetSnapshot.canonical_url`
- `topic_tags`
来自 `derive_long_term_tags`
- `asset_type`
来自 `derive_long_term_tags`
- `long_term_value_reason`
来自 `RetentionDecision.reason_text` 与 `derive_long_term_tags` 收束写入
- `stored_at`
由 `store_knowledge_asset` 写入
- `asset_status`
由 `store_knowledge_asset` 写入，默认 `STORED`
- `run_id`
由 `store_knowledge_asset` 在正式落盘时写入

### 8.3 `PreferenceSignal` 字段映射

- `preference_signal_id`
由 `derive_preference_signals` 在正式写出信号时生成
- `signal_type`
来自 `derive_preference_signals`
- `signal_value`
来自 `derive_preference_signals`
- `weight`
来自 `derive_preference_signals`
- `origin_retention_decision_id`
来自 `derive_preference_signals`，必须指向唯一正式 `RetentionDecision`
- `supplementary_knowledge_asset_id`
来自 `derive_preference_signals`，可为空，只能用于补充上下文
- `derived_from`
由 `derive_preference_signals` 基于 `origin_retention_decision_id` 和可选 `supplementary_knowledge_asset_id` 结构化生成；其中 canonical origin 永远是 `origin_retention_decision_id`
- `expires_at`
来自 `derive_preference_signals`
- `run_id`
由 `derive_preference_signals` 在正式写出信号时写入

## 9. 原子能力清单

`curate-retain` 的原子能力清单如下：

1. `build_read_queue`
2. `capture_human_decision`
3. `persist_retention_decision`
4. `derive_long_term_tags`
5. `store_knowledge_asset`
6. `derive_preference_signals`

## 10. 原子能力逐项设计

### 10.1 `build_read_queue`

#### 解决的问题 / 目标效果

把值得进一步精读或确认的对象组织成明确的人工决策队列。

#### 边界范围 / 明确不做

负责：

- 选择进入人工处理面的对象
- 定义队列优先级
- 记录进入队列的理由

不负责：

- 自动做留存决策
- 写入正式决策
- 写入知识资产

#### 输入对象 / 输出对象

- 输入：`DigestCandidate[]`、可选 `DailyReviewIssue`
- 输出：`ReadQueueItem[]`

#### 核心实现思路

这一步只负责把“候选阅读对象”组织成人可处理的队列，而不是暗中做长期价值判断。

#### 失败语义 / 人工介入点

- 队列构建异常：写入 `CurationFailureRecord[]`
- 没有对象进入队列：允许返回 `SUCCESS_EMPTY`
- 人工介入点：队列选择策略校准

### 10.2 `capture_human_decision`

#### 解决的问题 / 目标效果

采集人工对单个对象的正式长期价值判断。

#### 边界范围 / 明确不做

负责：

- 展示决策入口
- 收集正式决策
- 收集理由、标签和置信度

不负责：

- 自动替代人做决策
- 决策正式落盘
- 写入知识资产

#### 输入对象 / 输出对象

- 输入：`ReadQueueItem[]`
- 输出：`HumanDecisionDraft[]`

#### 核心实现思路

这是 workflow 唯一正式决策点。
只有这里可以产生 `KEEP/DROP/DEFER/NEEDS_RECHECK`。

#### 失败语义 / 人工介入点

- 决策采集失败：写入 `CurationFailureRecord[]`
- 人工未做决定：对象保持未决，不自动补判
- 人工介入点：这里本身就是人工介入点

### 10.3 `persist_retention_decision`

#### 解决的问题 / 目标效果

把人工决策草稿持久化为正式 `RetentionDecision` 记录。

#### 边界范围 / 明确不做

负责：

- 正式落盘 `RetentionDecision`
- 关联 `run_id`
- 保证决策可追溯

不负责：

- 改写人工决策
- 派生标签
- 写入知识资产

#### 输入对象 / 输出对象

- 输入：`HumanDecisionDraft[]`
- 输出：`RetentionDecisionRecord[]`

#### 核心实现思路

这一步只做决策真相 materialize，不重新解释决策。

#### 失败语义 / 人工介入点

- 落盘失败：写入 `CurationFailureRecord[]`
- 失败不允许回滚成人工未决，更不允许自动改判
- 人工介入点：决策记录修复与重放

### 10.4 `derive_long_term_tags`

#### 解决的问题 / 目标效果

从正式 `KEEP` 决策和对应上游对象快照中派生长期标签、资产类型和长期价值说明，组装知识资产草稿。

#### 边界范围 / 明确不做

负责：

- 派生 `topic_tags`
- 派生 `asset_type`
- 整理长期价值理由
- 组装知识资产草稿

不负责：

- 改写决策结果
- 正式写入知识资产
- 生成偏好信号

#### 输入对象 / 输出对象

- 输入：`RetentionDecisionRecord[]`、`RetainedTargetSnapshot[]`
- 输出：`KnowledgeAssetDraft[]`

#### 核心实现思路

只有 `KEEP` 决策会继续派生知识资产草稿。
草稿中的标题、摘要、链接等上游元信息必须来自显式输入的 `RetainedTargetSnapshot`，而不是隐式查找。
`DROP/DEFER/NEEDS_RECHECK` 不在这里被重新解释。

#### 失败语义 / 人工介入点

- 标签派生执行异常：写入 `CurationFailureRecord[]`
- 标签不足时可降级为少标签草稿，不自动否定 `KEEP`
- 人工介入点：标签体系校准

### 10.5 `store_knowledge_asset`

#### 解决的问题 / 目标效果

把知识资产草稿正式写入长期知识库，形成 `KnowledgeAsset`。

#### 边界范围 / 明确不做

负责：

- 资产落盘
- 资产状态写入
- 记录写入时间
- 写入 `run_id`
- 生成正式对象 identity

不负责：

- 改写人工决策
- 改写标签语义
- 派生偏好信号

#### 输入对象 / 输出对象

- 输入：`KnowledgeAssetDraft[]`
- 输出：`KnowledgeAsset[]`

#### 核心实现思路

知识资产写入是 `KEEP` 决策的后续物化动作，不是第二次价值判断。

#### 失败语义 / 人工介入点

- 写入失败：写入 `CurationFailureRecord[]`
- 写入失败不允许把 `KEEP` 改写成其他决策
- 人工介入点：知识库写入修复

### 10.6 `derive_preference_signals`

#### 解决的问题 / 目标效果

从已确认的正式决策中派生轻量偏好信号，并在需要时引用知识资产作为补充上下文，用于后续 rerank。

#### 边界范围 / 明确不做

负责：

- 生成偏好信号
- 计算信号权重
- 写入过期时间
- 写入 `run_id`
- 生成正式对象 identity

不负责：

- 反向改写人工决策
- 替代未来决策
- 直接 hard filter 上游对象

#### 输入对象 / 输出对象

- 输入：`RetentionDecisionRecord[]`、可选 `KnowledgeAsset[]`
- 输出：`PreferenceSignal[]`

#### 核心实现思路

偏好信号只从正式决策中派生，不从猜测行为中派生。
其中 `KnowledgeAsset[]` 只用于补充上下文，不构成独立裁决源。

#### 失败语义 / 人工介入点

- 派生执行异常：写入 `CurationFailureRecord[]`
- 无可派生信号：允许返回空结果
- 人工介入点：信号类型与权重规则校准

## 11. 设计结论

`curate-retain` 到此为止只完成三件事：

1. 把对象组织成可人工确认的精读队列
2. 在唯一人工决策点上形成正式留存决策
3. 从已确认决策中派生知识资产和轻量偏好信号

这版设计特别强调三条规则：

- 只有 `capture_human_decision` 可以做正式长期价值裁决
- 后置能力只能消费决策，不得反改决策
- `PreferenceSignal` 只能从正式决策派生，不能反向统治留存判断
