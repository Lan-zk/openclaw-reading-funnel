# `generate-long-cycle-assets` 信号与可写性细则

## 1. 文档目的

本文档定义 `generate-long-cycle-assets` 当前阶段最小可落地的两类技术细节：

- 热点主题与长期信号依赖的启发式规则
- 周刊与专题装配依赖的打分与门槛细则

本文档的目标不是把第一版做成黑盒模型，而是给第一版 skill 一个稳定、可解释、可调参的规则层。

## 2. 总体原则

### 2.1 证据优先，裁决后置

前置步骤只负责：

- 提供事实
- 提供信号
- 提供分数
- 提供风险标记

最终是否形成正式周刊或专题资产，统一留给：

- `compose_weekly_assets`
- `assemble_topic_asset_bundle`

### 2.2 错失比误入更危险

以下步骤默认宁可保守，也不要过早裁掉潜在主题：

- `detect_hot_topics`
- `identify_long_signals`
- `evaluate_topic_writability`

只要证据不够稳定，就优先：

- 不硬过滤
- 写 `review_flags`
- 在正式选入点再做 `OMITTED` 或 `REVIEW_REQUIRED`

### 2.3 已有沉淀高于外部新鲜感

当前阶段所有信号只允许来自：

- `KnowledgeAsset`
- `DailyReviewIssue`

不允许使用：

- 临时外部抓取结果
- “看起来最近很热”的站外事实
- 未沉淀到本系统的单条候选

### 2.4 规则可解释优先于规则复杂

第一版优先使用：

- 显式规则
- 稳定阈值
- 可回放的分数

暂不追求：

- 大量隐式模型逻辑
- 难以解释的多层黑盒加权

## 3. `collect_period_assets` 规则

### 3.1 周期窗口

当前阶段建议：

- `NORMAL` 模式默认取最近 7 天
- `REPLAY` 模式显式传入 `period_start` 与 `period_end`

### 3.2 输入投影规则

构造 `PeriodAssetSet` 时建议保留：

- `knowledge_asset_id`
- `topic_tags`
- `asset_type`
- `long_term_value_reason`
- `daily_review_issue_id`
- `top_themes`
- `sections`

### 3.3 当前阶段明确不做

- 跨 run 时间衰减建模
- 多周期主题回溯拼接
- 外部素材补洞

## 4. `detect_hot_topics` 规则

### 4.1 主题来源

第一版建议优先使用以下信号聚合主题：

- `KnowledgeAsset.topic_tags`
- `DailyReviewIssue.top_themes`
- 标题中的高频关键词
- 摘要中的高频关键词

### 4.2 `heat_score` 组成

建议将 `heat_score` 拆成以下维度后再汇总：

- `asset_support`
  有多少知识资产支撑该主题
- `issue_support`
  有多少日报 issue 支撑该主题
- `cross_source_support`
  是否同时得到知识资产与日报支持
- `keyword_density`
  主题关键词是否稳定反复出现

建议权重：

- `asset_support`: 0.35
- `issue_support`: 0.30
- `cross_source_support`: 0.20
- `keyword_density`: 0.15

### 4.3 建议阈值

- `heat_score >= 0.65`：可视为强热点主题
- `0.45 - 0.65`：中等强度，优先进入 review 或观察
- `< 0.45`：一般不建议进入正式产线

### 4.4 `topic_confidence` 规则

建议由以下信号归一化得到：

- 标签直接命中程度
- 关键词聚合稳定度
- 主题是否过度宽泛

建议阈值：

- `topic_confidence >= 0.75`：高置信度
- `0.55 - 0.75`：中等置信度
- `< 0.55`：建议写 `TOPIC_CONFIDENCE_LOW`

## 5. `identify_long_signals` 规则

### 5.1 长期性判断维度

第一版建议把 `signal_score` 拆成以下维度：

- `repeatability`
  是否能反复成为写作素材
- `reference_value`
  是否能作为以后决策或实现参考
- `breadth`
  是否跨多个条目或多个 issue 反复出现
- `specificity`
  是否足够具体，不是泛泛的大词

建议权重：

- `repeatability`: 0.35
- `reference_value`: 0.30
- `breadth`: 0.20
- `specificity`: 0.15

### 5.2 `signal_type` 建议映射

- 明显是可复用工程套路：`PATTERN`
- 明显是持续关注主题：`THEME`
- 可整理成操作手册：`PLAYBOOK`
- 需长期跟踪的风险脉络：`RISK_TRACK`
- 尚未收束、但值得持续观察：`OPEN_QUESTION`

### 5.3 建议阈值

- `signal_score >= 0.70`：可视为强长期信号
- `0.50 - 0.70`：中等强度，适合 review
- `< 0.50`：一般不建议直接进入正式资产

### 5.4 review 优先场景

以下情况优先写 `review_flags`：

- 热点明显，但长期性不足
- 主题太宽，难以落成具体写作对象
- 证据几乎全部来自单一日报 issue
- 证据几乎全部来自单一知识资产

## 6. `compose_weekly_assets` 规则

### 6.1 周刊形成条件

第一版建议满足以下任一条件可形成周刊：

- 至少 2 个强热点主题
- 至少 1 个强热点主题 + 1 个强长期信号
- 主题不多，但素材密度足够支撑清晰的周刊结构

### 6.2 `weekly_structure` 最小骨架

建议至少包含：

- `headline`
- `summary`
- `sections`
- `why_now`

其中 `sections` 当前阶段建议固定包含：

- `本周主线`
- `关键资产`
- `后续可写方向`

### 6.3 周刊进入 review 的条件

以下情况建议写 `NEEDS_AUTHOR_REVIEW`：

- 主线主题只有 1 个，且边界不清
- 主题间相关性弱，但被迫拼成一刊
- 结构成立，但标题不稳定

## 7. `evaluate_topic_writability` 规则

### 7.1 可写性判断维度

第一版建议把 `writability_score` 拆成以下维度：

- `material_density`
  素材量是否足够
- `structure_readiness`
  是否已能整理出专题结构
- `novelty`
  是否不是简单重复日报
- `focus`
  是否有足够清晰的专题边界

建议权重：

- `material_density`: 0.35
- `structure_readiness`: 0.30
- `novelty`: 0.20
- `focus`: 0.15

### 7.2 建议阈值

- `writability_score >= 0.72`：建议 `SELECTED`
- `0.52 - 0.72`：建议 `REVIEW_REQUIRED`
- `< 0.52`：建议 `OMITTED`

### 7.3 `writability_reasons` 组成

当前阶段建议至少记录以下类型理由：

- `ENOUGH_ASSET_SUPPORT`
- `ENOUGH_ISSUE_SUPPORT`
- `CLEAR_STRUCTURE`
- `REPEATS_DAILY_REVIEW_ONLY`
- `TOPIC_TOO_BROAD`
- `TOPIC_TOO_THIN`
- `LONG_SIGNAL_CONFIRMED`

### 7.4 `bundle_outline_seed`

第一版建议输出 3 到 5 个推荐结构小节，例如：

- 背景与主题定义
- 本周期关键事实
- 可复用模式或方法
- 风险与未决问题
- 下轮观察点

## 8. `assemble_topic_asset_bundle` 规则

### 8.1 正式装配条件

只有当 `TopicWritabilityAssessment.recommended_outcome = SELECTED` 时，才建议直接生成正式专题资产。

若为 `REVIEW_REQUIRED`：

- 优先写 `AuthorReviewItem`
- 可按策略生成 `NEEDS_AUTHOR_REVIEW` 的专题资产，也可不生成正式资产

### 8.2 `bundle_outline` 最小骨架

建议至少包含：

- `headline`
- `summary`
- `angles`
- `sections`
- `source_map`

### 8.3 review 优先场景

以下情况建议专题资产标记为 `NEEDS_AUTHOR_REVIEW`：

- 证据足够，但专题边界偏宽
- 可写性分数接近门槛
- 同一主题既适合周刊主线，又可能独立成专题

## 9. 当前阶段明确不定的内容

当前阶段暂不强行固定：

- 自动判断专题篇幅
- 基于历史资产的跨期去重
- 多层级主题树建模
