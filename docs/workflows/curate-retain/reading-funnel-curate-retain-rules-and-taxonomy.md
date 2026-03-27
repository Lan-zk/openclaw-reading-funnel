# `curate-retain` 规则与词表细则

## 1. 文档目的

本文档定义 `curate-retain` 当前阶段最小可落地的两类技术细节：

- 各原子能力依赖的业务规则
- 决策标签、资产类型、偏好信号的最小词表

本文档的目标不是把第一版做成复杂决策系统，而是给第一版 skill 一个稳定、可解释、可调参的规则层。

## 2. 总体原则

### 2.1 人工裁决优先，派生规则后置

本 workflow 的第一原则是：

- 人工负责判断长期价值
- 自动规则负责组装、落盘和派生
- 自动规则不得替代人工裁决

### 2.2 后置规则宁可保守，也不要反改决策

在以下步骤中，默认宁可少产出，也不要改判：

- `derive_long_term_tags`
- `store_knowledge_asset`
- `derive_preference_signals`

只要证据不足，就优先：

- 少打标签
- 少派生信号
- 记录为空结果

而不是：

- 把 `KEEP` 改成 `DROP`
- 把 `DROP` 解释成失败
- 把缺少资产写入解释成“不值得留存”

### 2.3 偏好信号只能轻量回流

`PreferenceSignal` 当前阶段只用于：

- rerank
- 轻量偏好建模
- 复盘个人取向

当前阶段明确不允许：

- 直接 hard filter 上游对象
- 自动写回 `KEEP` / `DROP`
- 覆盖公共重要性或人工最终判断

### 2.4 规则可解释优先于规则复杂

第一版优先使用：

- 显式词表
- 显式映射
- 稳定阈值
- 可回放的派生逻辑

暂不追求：

- 黑盒长期价值模型
- 行为推断主导的负反馈系统
- 难以追溯来源的大量隐式标签

## 3. `build_read_queue` 规则

### 3.1 入队目标

第一版建议只从以下对象构建队列：

- `DigestCandidate`
- `DailyReviewIssue` 内显式提及的高优先对象

默认原则：

- 先保证来源清楚
- 再保证人工面可读
- 不把复杂隐式对象直接丢给人工裁决

### 3.2 `queue_reason` 建议词表

第一版建议至少覆盖以下入队理由：

- `HIGH_DIGEST_SCORE`
- `EDITORIAL_PRIORITY`
- `MULTI_SOURCE_SIGNAL`
- `POSSIBLE_LONG_TERM_VALUE`
- `IMPLEMENTATION_RELEVANCE`
- `STRATEGIC_RELEVANCE`
- `MANUAL_RECHECK`

规则约束：

- `queue_reason` 只说明“为什么值得人工看”
- 不说明最终结论
- 同一条目允许多个 `queue_reason`

### 3.3 `queue_priority` 建议规则

第一版建议：

- `HIGH`
  已出现在日报主线，或明显与当前关注主题直接相关
- `MEDIUM`
  看起来有长期价值，但未进入强优先级
- `LOW`
  值得存疑复核，但不阻断主阅读流

当前阶段不做：

- 基于复杂用户画像动态调优优先级
- 基于行为数据自动提升或降低优先级

## 4. `capture_human_decision` 规则

### 4.1 决策枚举语义

#### `KEEP`

表示：

- 该对象值得进入长期知识沉淀
- 后续可以继续派生知识资产与偏好信号

不表示：

- 一定已经成功写入知识库
- 一定已经完成完整标签整理

#### `DROP`

表示：

- 该对象不值得长期沉淀
- 可作为正式负反馈来源

不表示：

- 该对象是执行失败
- 该对象不值得当天阅读

#### `DEFER`

表示：

- 当前信息不足以稳定判断
- 需要延后再看，但还不是“对象有问题”

适用场景：

- 内容有潜力，但当前不急
- 需要更多上下文才能判断长期价值
- 当前人工时间有限，先挂起

#### `NEEDS_RECHECK`

表示：

- 对象本身或上下文存在需要重新核查的问题
- 当前不能把它当作稳定裁决结果

适用场景：

- 来源可信度存疑
- 摘要和原文不一致
- 目标对象映射可能有误

### 4.2 `confidence` 建议规则

`confidence` 当前阶段建议使用 0 到 1 的归一化值。

建议区间：

- `>= 0.85`
  人工判断稳定
- `0.60 - 0.85`
  基本可接受，但仍带少量保留
- `< 0.60`
  决策存在较大不确定性，优先考虑 `DEFER` 或 `NEEDS_RECHECK`

规则约束：

- `confidence` 是人工信心，不是模型概率
- 允许缺失；缺失时由固定默认值补全

### 4.3 `reason_tags` 建议词表

第一版建议至少覆盖以下标签：

正向理由：

- `LONG_TERM_REFERENCE`
- `ACTIONABLE_PRACTICE`
- `STRATEGIC_SIGNAL`
- `IMPLEMENTATION_PATTERN`
- `DECISION_INPUT`
- `REUSABLE_FRAMEWORK`
- `HIGH_INFORMATION_DENSITY`
- `NOVEL_INSIGHT`

负向理由：

- `LOW_CREDIBILITY`
- `LOW_INFORMATION_DENSITY`
- `TIME_BOUND_ONLY`
- `ALREADY_KNOWN`
- `REPOST_WITHOUT_VALUE`
- `OFF_TOPIC`
- `TOO_SHALLOW`

待定与复核理由：

- `NEEDS_MORE_CONTEXT`
- `NEEDS_SOURCE_RECHECK`
- `NEEDS_PRIMARY_SOURCE`
- `CONFLICTING_SUMMARY`

规则约束：

- `reason_tags` 优先描述“为什么这样判”
- 不要拿 `topic_tags` 直接充当 `reason_tags`
- `DROP` 与 `DEFER` 也应尽量有 `reason_tags`

## 5. `derive_long_term_tags` 规则

### 5.1 只处理 `KEEP`

第一版固定规则：

- 只有 `KEEP` 决策可以进入 `derive_long_term_tags`
- `DROP` / `DEFER` / `NEEDS_RECHECK` 不在此 step 被重新解释

### 5.2 `topic_tags` 生成原则

`topic_tags` 的目标是：

- 服务长期检索
- 服务主题聚合
- 服务长周期复用

第一版建议来源优先级：

1. 显式人工判断中的主题表述
2. 上游 `RetainedTargetSnapshot` 的标题与摘要
3. 稳定映射词表或轻量规则

第一版建议约束：

- 每个资产建议 `1` 到 `5` 个 `topic_tags`
- 优先短语化、名词化
- 避免把纯情绪、纯判断词写成主题标签

示例：

- `llm-evals`
- `prompt-engineering`
- `browser-automation`
- `supply-chain-security`
- `rust-tooling`

### 5.3 `asset_type` 建议词表

第一版建议允许以下资产类型：

- `REFERENCE_NOTE`
  适合长期查阅的事实、定义、方法或概念
- `PATTERN`
  可复用的实现套路、架构模式、工作方法
- `DECISION_INPUT`
  影响后续产品、工程或研究判断的材料
- `WATCH_ITEM`
  需要长期跟踪的趋势、风险、变化信号
- `SOURCE_MAP`
  对来源、生态或资料关系有总结价值的对象

选择规则：

- 如果重点是“以后查”，优先 `REFERENCE_NOTE`
- 如果重点是“以后复用”，优先 `PATTERN`
- 如果重点是“以后决策要参考”，优先 `DECISION_INPUT`
- 如果重点是“以后继续盯”，优先 `WATCH_ITEM`
- 如果重点是“以后找资料有结构”，优先 `SOURCE_MAP`

### 5.4 `long_term_value_reason` 生成原则

第一版建议：

- 优先收束 `RetentionDecision.reason_text`
- 允许结合 `reason_tags` 生成一句简洁说明
- 不重新生成长摘要

目标格式：

- 说明“为什么值得长期留”
- 不重复原文摘要
- 不掺入新的裁决

## 6. `store_knowledge_asset` 规则

### 6.1 默认落盘状态

第一版固定规则：

- 正常写入时 `asset_status = STORED`
- `ARCHIVED` 不在首次写入时主动生成，除非显式走归档流程

### 6.2 写入失败语义

写入失败时：

- 记录 `ASSET_STORE_ERROR`
- 不改写来源 `RetentionDecisionRecord`
- 不自动生成替代决策

## 7. `derive_preference_signals` 规则

### 7.1 信号来源原则

`PreferenceSignal` 只能来源于：

- 已正式落盘的 `RetentionDecisionRecord`

其中：

- `KnowledgeAsset` 只用于补充上下文
- 行为猜测当前阶段不作为真相来源

### 7.2 `signal_type` 建议词表

第一版建议允许以下信号类型：

- `TOPIC_PREFERENCE`
- `SOURCE_PREFERENCE`
- `FORMAT_PREFERENCE`
- `NEGATIVE_SIGNAL`

建议含义：

- `TOPIC_PREFERENCE`
  对某一主题的正向长期偏好
- `SOURCE_PREFERENCE`
  对某类来源或来源域名的正向偏好
- `FORMAT_PREFERENCE`
  对某种内容形式的偏好，例如长文、案例、实现复盘
- `NEGATIVE_SIGNAL`
  基于 `DROP` 决策形成的轻量负反馈

### 7.3 `signal_value` 生成原则

第一版建议：

- `TOPIC_PREFERENCE` 优先使用 `topic_tags`
- `SOURCE_PREFERENCE` 优先使用 `canonical_url` 的来源域或来源名
- `FORMAT_PREFERENCE` 优先使用稳定格式标签
- `NEGATIVE_SIGNAL` 优先使用负向 `reason_tags` 或被拒绝主题

### 7.4 `weight` 建议规则

`weight` 当前阶段建议规范到 `0` 到 `1`。

建议基线：

- `0.85 - 1.00`
  强信号，通常来自高置信度 `KEEP` 或明确负反馈
- `0.60 - 0.85`
  中等信号，适合轻量 rerank
- `0.30 - 0.60`
  弱信号，只做边缘微调

建议组合原则：

- 人工 `confidence` 越高，`weight` 越高
- 信号越具体，`weight` 可越高
- 来源只是一跳推断时，`weight` 应降低

当前阶段明确禁止：

- 用 `weight` 放大到 hard filter
- 让单条信号独占未来排序

### 7.5 `expires_at` 建议规则

第一版建议按信号类型设置默认有效期：

- `TOPIC_PREFERENCE`
  90 天
- `SOURCE_PREFERENCE`
  60 天
- `FORMAT_PREFERENCE`
  90 天
- `NEGATIVE_SIGNAL`
  45 天

说明：

- 长期偏好也要慢衰减，不做永久锁定
- 负向信号衰减应更快，避免系统变得过度保守

### 7.6 `derived_from` 结构建议

第一版建议最少包含：

- `origin_retention_decision_id`
- `target_type`
- `target_id`
- `reason_tags`
- 可选 `knowledge_asset_id`

规则约束：

- canonical origin 永远是 `origin_retention_decision_id`
- `knowledge_asset_id` 只能是补充引用

## 8. 第一版建议映射

### 8.1 从 `KEEP` 到资产类型的建议映射

- 含 `LONG_TERM_REFERENCE`、`HIGH_INFORMATION_DENSITY`
  倾向 `REFERENCE_NOTE`
- 含 `ACTIONABLE_PRACTICE`、`IMPLEMENTATION_PATTERN`、`REUSABLE_FRAMEWORK`
  倾向 `PATTERN`
- 含 `STRATEGIC_SIGNAL`、`DECISION_INPUT`
  倾向 `DECISION_INPUT`
- 含趋势、持续变化、风险监测语义
  倾向 `WATCH_ITEM`

### 8.2 从决策到信号类型的建议映射

- `KEEP` + `topic_tags`
  派生 `TOPIC_PREFERENCE`
- `KEEP` + 来源稳定可信
  派生 `SOURCE_PREFERENCE`
- `KEEP` + 内容形式明显
  派生 `FORMAT_PREFERENCE`
- `DROP` + 负向 `reason_tags`
  派生 `NEGATIVE_SIGNAL`

## 9. 当前阶段明确不做

第一版 `curate-retain` 不提前做以下能力：

- 自动长期价值判断
- 从阅读行为直接反推正式偏好模型
- 复杂多级标签体系
- 基于 embeddings 的黑盒标签生成
- 实时自适应偏好放大

## 10. 落地建议

第一版实现建议保持“人工裁决单点、显式词表、轻量派生规则”：

- `rules/queue.py`
- `rules/decision_tags.py`
- `rules/topic_tags.py`
- `rules/asset_types.py`
- `rules/preference_signals.py`

不要在第一版提前引入复杂策略引擎；先把决策、资产、信号三层边界稳定下来。
