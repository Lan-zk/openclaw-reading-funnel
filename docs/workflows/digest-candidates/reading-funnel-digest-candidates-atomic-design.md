# `digest-candidates` 原子能力设计

## 1. 文档目的

本文档定义 `digest-candidates` workflow 内部的原子能力边界。

本文档重点回答五个问题：

- 这一层最小但有独立边界的能力单元是什么
- 这些能力如何把 `NormalizedCandidate` 收窄为 `DigestCandidate`
- 过滤、低置信度、执行失败如何严格分离
- 中间对象如何保持稳定，不在实现中漂移
- 最终 `DigestCandidate` 的字段分别由哪一步产生

本文档是 [reading-funnel-global-implementation-guide.md](../../global/reading-funnel-global-implementation-guide.md) 的下钻设计。
如果后续继续展开其他 workflow，建议沿用相同模板。

## 2. 设计范围

本文档只覆盖一个 workflow：

- `digest-candidates`

本文档不覆盖：

- `ingest-normalize`
- `compose-daily-review`
- `curate-retain`
- `generate-long-cycle-assets`
- 顶层编排脚本实现

## 3. workflow 目标与边界

### 3.1 统一任务

`digest-candidates` 的统一任务是：

> 把 `NormalizedCandidate` 转成“可判断对象” `DigestCandidate`，让 `compose-daily-review` 面对的是一批已清洗、已收窄、可快速判断的候选，而不是原始来源条目。

### 3.2 负责范围

本 workflow 负责：

- URL 规范化复核
- 精确去重
- 相似内容聚类
- 簇主候选正文抽取
- 正文清洗
- 质量检查
- 噪音过滤
- 摘要生成
- 候选评分
- `DigestCandidate`、`DigestReviewItem` 和报告装配

### 3.3 明确不做

本 workflow 不负责：

- 日报栏目编排
- 长期价值判断
- 知识库存储
- 强推荐
- 仅凭个人偏好 hard filter 公共重要内容

## 4. 运行结果语义

### 4.1 step 结果

`digest-candidates` 中的步骤结果统一分为三类：

- `SUCCESS_WITH_OUTPUT`
成功产出至少一个 `DigestCandidate`
- `SUCCESS_EMPTY`
运行成功，但没有保留或待复核候选
- `FAILED`
执行异常，无法完成预期步骤

### 4.2 对象去向

对单个候选簇而言，只能进入三类业务结果：

- `KEPT`
进入 digest 候选池
- `FILTERED`
基于明确规则被过滤
- `NEEDS_REVIEW`
证据不足或判断不稳定，进入复核池

### 4.3 三者必须分开

这里有三个硬约束：

- `FILTERED` 不是失败
- `NEEDS_REVIEW` 不是失败
- `FAILED` 只存在于运行级 failure ledger

## 5. 失败事实与低置信度规则

### 5.1 单一失败真相

`digest-candidates` 的运行级失败真相只有一个权威来源：

- `DigestFailureRecord[]`

它记录：

- 执行异常
- 工具失败
- 批次失败
- 对象级不可恢复异常

### 5.2 低置信度不是失败

低置信度对象进入：

- `DigestReviewItem[]`

它承接的不是执行失败，而是自动判断不稳定的对象，例如：

- 聚类置信度不足
- 正文抽取可用但不完整
- 质量判断不稳定
- 噪音判断有争议
- 摘要不可用但对象可能值得保留

### 5.3 唯一最终裁决点

本 workflow 只有一个能力可以正式决定对象去向：

- `assemble_digest_candidates`

前面的原子能力只允许做三件事：

- 生成证据
- 生成分数
- 生成风险标记

前面的能力不得直接把对象裁决为 `KEPT`、`FILTERED` 或 `NEEDS_REVIEW`。

## 6. 偏好信号使用规则

### 6.1 偏好只参与 rerank

`PreferenceSignal` 只能参与同状态内排序，不参与最终状态决策。

### 6.2 排序分与决策分分离

这一层至少要区分两类分数：

- `base_digest_score`
由质量、时效性、信息密度、聚类情况等非个性化信号组成，用于最终状态决策参考。
- `rerank_score`
在 `base_digest_score` 基础上叠加轻量偏好信号，只用于同状态内排序。

### 6.3 明确禁止

以下做法是禁止的：

- 用偏好信号直接触发 `FILTERED`
- 用偏好信号把公共重要内容降出候选池
- 用偏好信号绕过质量与噪音规则

## 7. 中间对象最小契约

为了稳定能力边界，本文档定义 5 个中间对象。

### 7.1 `CanonicalCandidate`

最小字段：

- `normalized_candidate_id`
- `canonical_url`
- `url_fingerprint`
- `canonicalize_status`

定义：
完成 URL 规范化复核后的候选。

### 7.2 `ExactDedupResult`

最小字段：

- `survivor_candidate_id`
- `duplicate_candidate_ids`
- `dedup_key`
- `dedup_reason`

定义：
精确去重后的保留对象及其被折叠重复项。

### 7.3 `CandidateCluster`

最小字段：

- `cluster_id`
- `member_candidate_ids`
- `primary_candidate_id`
- `cluster_type`
- `cluster_confidence`

定义：
完成近重复聚类后的候选簇。

说明：
后续正文抽取严格以 `primary_candidate_id` 为对象，不在整簇层面直接抽取正文。

### 7.4 `ExtractedContent`

最小字段：

- `cluster_id`
- `primary_candidate_id`
- `raw_content`
- `clean_content`
- `content_length`
- `extract_status`

定义：
针对候选簇主候选抽取并清洗后的正文对象。

### 7.5 `DigestEvidence`

最小字段：

- `cluster_id`
- `primary_candidate_id`
- `quality_score`
- `noise_flags`
- `summary`
- `freshness_score`
- `base_digest_score`
- `rerank_score`
- `review_flags`

定义：
进入最终装配前的统一证据对象。

说明：
前置能力产生的所有质量、噪音、摘要、分数和低置信度标记，都统一写入 `DigestEvidence`，而不是各自发明新的裁决对象。

## 8. 最终对象字段来源映射

为了避免最终字段无法溯源，`DigestCandidate` 的关键字段来源必须固定。

### 8.1 `DigestCandidate` 字段映射

- `normalized_candidate_ids`
来自 `exact_dedup` 与 `near_duplicate_cluster`
- `primary_normalized_candidate_id`
来自 `near_duplicate_cluster.primary_candidate_id`
- `cluster_type`
来自 `near_duplicate_cluster`
- `cluster_confidence`
来自 `near_duplicate_cluster`
- `display_title`
由 `assemble_digest_candidates` 基于主候选标题生成
- `display_summary`
来自 `generate_summary`
- `canonical_url`
来自 `canonicalize_url`，由 `assemble_digest_candidates` 选择主候选对应值
- `quality_score`
来自 `check_quality`
- `freshness_score`
来自 `compute_digest_score`
- `digest_score`
来自 `compute_digest_score.base_digest_score`
- `noise_flags`
来自 `filter_noise`
- `needs_review`
由 `assemble_digest_candidates` 根据 `review_flags` 和裁决结果生成
- `digest_status`
由 `assemble_digest_candidates` 正式写入

### 8.2 `DigestReviewItem` 字段映射原则

`DigestReviewItem` 必须至少包含：

- `cluster_id`
- `primary_candidate_id`
- `review_flags`
- `supporting_evidence`
- `suggested_action`

它只能由 `assemble_digest_candidates` 统一生成。

## 9. 原子能力清单

`digest-candidates` 的原子能力清单如下：

1. `canonicalize_url`
2. `exact_dedup`
3. `near_duplicate_cluster`
4. `extract_main_content`
5. `clean_content`
6. `check_quality`
7. `filter_noise`
8. `generate_summary`
9. `compute_digest_score`
10. `assemble_digest_candidates`

## 10. 原子能力逐项设计

### 10.1 `canonicalize_url`

#### 解决的问题 / 目标效果

统一 URL，减少同一内容因追踪参数、短链、镜像地址而分裂。

#### 边界范围 / 明确不做

负责：

- URL 复核
- 追踪参数收敛
- 规范化标识生成

不负责：

- 正文抽取
- 内容判断
- 聚类

#### 输入对象 / 输出对象

- 输入：`NormalizedCandidate[]`
- 输出：`CanonicalCandidate[]`

#### 核心实现思路

只解决“同一链接的不同表示”，不在这一层引入内容语义判断。

#### 失败语义 / 人工介入点

- 单条 URL 规范化异常：记对象级失败并继续
- 规范化后为空或非法：写入 `DigestFailureRecord[]`
- 人工介入点：URL 规则系统性失效时调整规则

### 10.2 `exact_dedup`

#### 解决的问题 / 目标效果

去掉可以确定为同一对象的精确重复项。

#### 边界范围 / 明确不做

负责：

- 高确定性重复识别
- 重复项折叠

不负责：

- 近重复判断
- 内容价值判断

#### 输入对象 / 输出对象

- 输入：`CanonicalCandidate[]`
- 输出：`ExactDedupResult[]`

#### 核心实现思路

只处理高确定性重复，例如相同 `url_fingerprint` 或稳定重复键。

#### 失败语义 / 人工介入点

- 无法稳定判定时不误删，交给后续聚类
- 重复折叠是业务收窄，不是失败
- 人工介入点：去重键策略调整

### 10.3 `near_duplicate_cluster`

#### 解决的问题 / 目标效果

把相似报道、转载、同事件多来源内容聚成候选簇。

#### 边界范围 / 明确不做

负责：

- 近重复聚类
- 主候选选择
- 聚类置信度评估

不负责：

- 日报栏目编排
- 长期价值判断
- 最终状态裁决

#### 输入对象 / 输出对象

- 输入：`ExactDedupResult[]`
- 输出：`CandidateCluster[]`

#### 核心实现思路

目标是减少重复阅读成本，而不是提前做编辑判断。
同时在这一步明确 `primary_candidate_id`，为后续正文抽取固定 lineage。

#### 失败语义 / 人工介入点

- 聚类执行异常：写入 `DigestFailureRecord[]`
- 聚类低置信度：只写 `review_flags` 证据，不直接生成 `DigestReviewItem`
- 人工介入点：高争议聚类样本复核

### 10.4 `extract_main_content`

#### 解决的问题 / 目标效果

为每个候选簇的主候选提取可读正文。

#### 边界范围 / 明确不做

负责：

- 基于 `primary_candidate_id` 抽取正文
- 记录正文抽取状态

不负责：

- 按整簇合并正文
- 内容改写
- 摘要生成
- 排序

#### 输入对象 / 输出对象

- 输入：`CandidateCluster[]`
- 输出：`ExtractedContent[]`

#### 核心实现思路

正文抽取严格限定为逐主候选执行。
不允许一个 `ExtractedContent` 同时承担单候选和整簇两种语义。

#### 失败语义 / 人工介入点

- 抽取执行异常：写入 `DigestFailureRecord[]`
- 抽取成功但正文残缺、长度异常、结构破碎：只写入 `review_flags`
- 不是所有抽取问题都直接导致对象被过滤
- 人工介入点：高价值候选的抽取策略修正

### 10.5 `clean_content`

#### 解决的问题 / 目标效果

把抽取结果清洗成更稳定的判断输入，去掉模板噪音和格式残留。

#### 边界范围 / 明确不做

负责：

- 文本清洗
- 噪音片段剥离
- 基础结构修复

不负责：

- 质量结论
- 噪音裁决
- 最终状态判断

#### 输入对象 / 输出对象

- 输入：`ExtractedContent[]`
- 输出：更新后的 `ExtractedContent[]`

#### 核心实现思路

只做内容可读性和可判断性的基础清洗，不在这一步决定去向。

#### 失败语义 / 人工介入点

- 清洗失败但原始正文仍可用：降级保留原始文本
- 完全不可用：记执行失败
- 清洗异常信息写入 `DigestFailureRecord[]`
- 人工介入点：清洗规则长期误伤时调整

### 10.6 `check_quality`

#### 解决的问题 / 目标效果

判断候选簇主候选是否具备进入 digest 的基础质量。

#### 边界范围 / 明确不做

负责：

- 评估内容完整性
- 评估可读性
- 评估基础可信度

不负责：

- 最终过滤决策
- 日报编排
- 直接生成复核对象

#### 输入对象 / 输出对象

- 输入：`ExtractedContent[]`、候选元信息
- 输出：更新后的 `DigestEvidence[]`

#### 核心实现思路

这一步只产出质量证据和风险标记，不直接给对象定状态。

#### 失败语义 / 人工介入点

- 低质量是业务证据，不是失败
- 判断不稳定时写入 `review_flags`
- 规则执行异常才记失败
- 人工介入点：质量规则长期偏差复盘

### 10.7 `filter_noise`

#### 解决的问题 / 目标效果

识别广告、空壳页、标题党、低信息密度、与阅读目标明显不符的噪音特征。

#### 边界范围 / 明确不做

负责：

- 生成噪音证据
- 标记噪音类型
- 标记强过滤候选条件

不负责：

- 直接把对象裁决为 `FILTERED`
- 公共重要内容的强硬误删
- 个性化强推荐

#### 输入对象 / 输出对象

- 输入：`DigestEvidence[]`、正文对象、候选元信息
- 输出：更新后的 `DigestEvidence[]`

#### 核心实现思路

噪音过滤这一步只生成可解释的噪音证据和标记。
真正是否进入 `FILTERED`，统一留给最终装配。

#### 失败语义 / 人工介入点

- 噪音判断不确定时写入 `review_flags`
- 规则执行异常才记失败
- 人工介入点：误杀样本复盘

### 10.8 `generate_summary`

#### 解决的问题 / 目标效果

为候选簇生成快速判断所需摘要。

#### 边界范围 / 明确不做

负责：

- 生成摘要
- 记录摘要可用性

不负责：

- 最终排序
- 日报成稿
- 直接生成复核对象

#### 输入对象 / 输出对象

- 输入：`DigestEvidence[]`、`ExtractedContent[]`
- 输出：更新后的 `DigestEvidence[]`

#### 核心实现思路

摘要职责是降低后续判断成本，不是替代阅读，也不在这里决定最终状态。

#### 失败语义 / 人工介入点

- 摘要失败不自动等于对象失败
- 高价值候选摘要失败时写入 `review_flags`
- 摘要服务执行异常才写入 `DigestFailureRecord[]`
- 人工介入点：摘要策略复盘

### 10.9 `compute_digest_score`

#### 解决的问题 / 目标效果

为候选生成 digest 阶段的基础排序分和轻量 rerank 分。

#### 边界范围 / 明确不做

负责：

- 计算 `freshness_score`
- 计算 `base_digest_score`
- 计算 `rerank_score`

不负责：

- 最终状态裁决
- 栏目编排
- 长期价值判断

#### 输入对象 / 输出对象

- 输入：`DigestEvidence[]`、时效性、来源特征、可选 `PreferenceSignal`
- 输出：更新后的 `DigestEvidence[]`

#### 核心实现思路

把决策分和 rerank 分显式拆开：

- `base_digest_score` 用于最终裁决参考
- `rerank_score` 只用于同状态内排序

#### 失败语义 / 人工介入点

- 打分执行异常：写入 `DigestFailureRecord[]`
- 分数高低不是失败
- 偏好信号不能作为硬过滤依据
- 人工介入点：评分权重校准

### 10.10 `assemble_digest_candidates`

#### 解决的问题 / 目标效果

把前面各能力产出的证据和分数收束成正式 `DigestCandidate[]`、`DigestReviewItem[]` 和 `digest-report`。

#### 边界范围 / 明确不做

负责：

- 正式裁决 `KEPT` / `FILTERED` / `NEEDS_REVIEW`
- 生成 `DigestCandidate[]`
- 生成 `DigestReviewItem[]`
- 生成 `digest-report`

不负责：

- 日报成稿
- 知识沉淀

#### 输入对象 / 输出对象

- 输入：`CandidateCluster[]`、`DigestEvidence[]`
- 输出：`DigestCandidate[]`、`DigestReviewItem[]`、`digest-report`

#### 核心实现思路

这是 workflow 唯一正式裁决点。
它根据证据、规则和 `base_digest_score` 进行状态落定，再使用 `rerank_score` 做同状态内排序。

#### 失败语义 / 人工介入点

- 装配失败属于系统执行失败
- 若最终无 `KEPT` 且无 `NEEDS_REVIEW`，返回 `SUCCESS_EMPTY`
- 人工介入点在 review 池，不在直接改写装配过程

## 11. 设计结论

`digest-candidates` 到此为止只完成三件事：

1. 把原始候选收窄成候选簇
2. 为每个候选簇积累质量、噪音、摘要和评分证据
3. 在唯一裁决点上把对象正式落入 `KEPT`、`FILTERED` 或 `NEEDS_REVIEW`

这版设计特别强调三条规则：

- `FILTERED`、`NEEDS_REVIEW`、`FAILED` 必须三分
- 只有 `assemble_digest_candidates` 可以做最终状态裁决
- `PreferenceSignal` 只能影响同状态内排序，不能参与硬过滤
