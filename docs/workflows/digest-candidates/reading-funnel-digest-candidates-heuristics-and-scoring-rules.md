# `digest-candidates` 规则与评分细则

## 1. 文档目的

本文档定义 `digest-candidates` 当前阶段最小可落地的两类技术细节：

- 各原子能力依赖的启发式规则
- `compute_digest_score` 与最终装配依赖的评分细则

本文档的目标不是把第一版做成黑盒模型，而是给第一版 skill 一个稳定、可解释、可调参的规则层。

## 2. 总体原则

### 2.1 证据优先，裁决后置

前置步骤只负责：

- 提供事实
- 提供证据
- 提供分数
- 提供风险标记

最终是否 `KEPT`、`FILTERED` 或 `NEEDS_REVIEW`，统一留给 `assemble_digest_candidates`。

### 2.2 错杀比漏抓更危险

在以下步骤中，默认宁可保守，也不要误删：

- `exact_dedup`
- `near_duplicate_cluster`
- `filter_noise`

只要证据不够稳定，就优先：

- 不折叠
- 不硬过滤
- 写 `review_flags`

### 2.3 公共重要性高于个人偏好

`PreferenceSignal` 只能参与轻量 rerank：

- 不能直接触发 `FILTERED`
- 不能让公共重要内容掉出候选池
- 不能绕过质量与噪音规则

### 2.4 规则可解释优先于规则复杂

第一版优先使用：

- 显式规则
- 稳定阈值
- 可回放的分数

暂不追求：

- 大量隐式模型逻辑
- 难以解释的组合打分

## 3. `canonicalize_url` 规则

### 3.1 当前阶段建议做的规范化

`canonical_url` 当前阶段建议只做：

- 去掉首尾空白
- 统一协议和 host 大小写
- 去掉默认端口
- 去掉 fragment
- 对已知追踪参数做有限清理，例如 `utm_*`、`spm`、`from`
- 保留 query 中明确承载业务身份的参数

### 3.2 当前阶段明确不做

- 基于正文内容改写 URL
- 跨站点镜像内容合并
- 短链网络展开后的复杂二次推断

### 3.3 失败与降级规则

- URL 语法非法：记 `INPUT_ERROR` 或 `CANONICALIZE_ERROR`
- 规范化后为空：记失败，不进入后续流程
- 规范化成功但 query 清理不确定：保守保留

## 4. `exact_dedup` 规则

### 4.1 去重键优先级

第一版建议按以下顺序尝试高确定性去重：

1. 相同 `url_fingerprint`
2. 相同 `canonical_url`
3. 明确配置的来源内稳定重复键

以下信号当前阶段不用于 `exact_dedup`：

- 模糊标题相似
- 同事件不同来源
- 摘要语义相似

这些都应留给 `near_duplicate_cluster`。

### 4.2 survivor 选择规则

第一版建议按以下顺序选 `survivor_candidate_id`：

1. `canonical_url` 有效
2. `published_at` 更完整
3. `normalized_title` 更完整
4. `summary` 非空
5. 仍然打平时，按稳定 ID 排序

### 4.3 错误边界

- 只要无法高确定性证明是同一对象，就不做 `exact_dedup`
- `exact_dedup` 的目标是折叠“同一条内容”，不是“同一事件”

## 5. `near_duplicate_cluster` 规则

### 5.1 聚类信号

第一版建议使用以下显式信号：

- `normalized_title` 相似度
- 发布时间窗口接近程度
- `summary` 或关键短语重叠
- URL 路径或站点结构相似性
- 来源是否明显是转载、镜像或聚合页

### 5.2 聚类置信度

`cluster_confidence` 当前阶段建议为 0 到 1 的归一化数值。

建议阈值：

- `>= 0.85`：高置信度
- `0.60 - 0.85`：中等置信度
- `< 0.60`：低置信度，应考虑写入 `review_flags`

### 5.3 `primary_candidate_id` 选择规则

第一版建议按以下顺序选主候选：

1. 正文可抽取概率更高
2. 标题更完整、非转载风格
3. 来源更像原始发布而非聚合页
4. 发布时间更早且信息更完整
5. 仍然打平时，按稳定 ID 排序

### 5.4 当前阶段明确不做

- 事件级因果链推断
- 多事件混合簇拆分
- 跨语言同事件对齐

## 6. `extract_main_content` 与 `clean_content` 规则

### 6.1 抽取策略

第一版建议按以下顺序降级：

1. 主正文抽取器
2. 通用可读性抽取器
3. 原始页面正文段落拼接
4. 在极端情况下退化到摘要级文本

### 6.2 抽取成功的最低要求

满足以下任一条件可认为“有可继续内容”：

- 抽到主体段落，结构基本完整
- 抽到部分正文，但能支撑质量、噪音和摘要判断
- 没有完整正文，但摘要与元信息足以进入 review

### 6.3 清洗规则

`clean_content` 当前阶段建议只做：

- 去掉导航、页脚、相关推荐等模板片段
- 压缩连续空白
- 去掉明显重复段落
- 修复基础换行和段落结构

当前阶段不做：

- 事实改写
- 观点改写
- 生成式润色

### 6.4 review 触发信号

以下情况应优先写 `review_flags`：

- 正文明显截断
- 段落结构破碎
- 仅剩摘要级文本
- 标题与正文不一致

## 7. `check_quality` 规则

### 7.1 质量维度

第一版建议把 `quality_score` 拆成以下维度后再汇总：

- `completeness`
  是否有足够内容支撑判断
- `readability`
  文本是否可读、结构是否稳定
- `credibility`
  来源和页面结构是否看起来像真实正文
- `specificity`
  是否提供了足够多的事实密度

### 7.2 建议分值范围

每个维度先归一化到 0 到 1，再加权得到 `quality_score`。

建议权重：

- `completeness`: 0.35
- `readability`: 0.25
- `credibility`: 0.20
- `specificity`: 0.20

### 7.3 建议阈值

- `quality_score >= 0.75`：质量较高
- `0.50 - 0.75`：可继续，但要结合噪音和摘要
- `< 0.50`：偏低，优先写入 `review_flags` 或作为过滤证据

## 8. `filter_noise` 规则

### 8.1 噪音类型

第一版建议至少覆盖以下 `noise_flags`：

- `AD_PAGE`
- `EMPTY_SHELL`
- `LINK_DUMP`
- `TITLE_BAIT`
- `LOW_INFO_DENSITY`
- `OFF_TOPIC`
- `REPOST_WITHOUT_VALUE`

### 8.2 强过滤证据

以下情况可以视为强过滤证据，但仍由最终装配决定：

- 页面几乎没有正文
- 全文主要是广告、推广或导流
- 标题与正文严重不符
- 只是目录页、标签页或链接聚合页

### 8.3 review 优先场景

以下情况优先进入 review，而不是直接过滤：

- 主题边缘相关，但可能对当前阅读目标有价值
- 正文较短，但信息密度高
- 看起来像转载，但可能补充了新信息

## 9. `generate_summary` 规则

### 9.1 摘要目标

摘要的职责是降低判断成本，而不是替代阅读。

### 9.2 第一版格式建议

建议生成 1 到 3 句摘要，并满足：

- 优先复述事实，不加评论
- 不重复标题原文
- 尽量覆盖“发生了什么、为什么值得看”
- 对不稳定对象，允许明确写出不确定性

### 9.3 摘要失败的降级

- 若正文可用但摘要失败：对象继续流转，摘要记 `UNAVAILABLE`
- 若对象价值可能较高：写 `review_flags`
- 只有摘要服务执行异常才记 ledger

## 10. `compute_digest_score` 规则

### 10.1 分数分层

`digest-candidates` 至少区分两类分数：

- `base_digest_score`
  给最终裁决参考
- `rerank_score`
  只用于同状态内排序

### 10.2 `freshness_score`

第一版建议按发布时间衰减到 0 到 1：

- 24 小时内：高分
- 2 到 3 天：中高分
- 1 周左右：中分
- 更久：低分，但不自动归零

如果无 `published_at`：

- 不直接记失败
- 给予保守中低分，并写可选 review 标记

### 10.3 `base_digest_score` 建议公式

第一版建议将 `base_digest_score` 标准化到 0 到 100。

建议计算：

```text
base_digest_score =
  100 * (
    0.35 * quality_score +
    0.25 * freshness_score +
    0.20 * information_density_score +
    0.20 * cluster_uniqueness_score
  )
  - noise_penalty
```

说明：

- `information_density_score` 由正文具体性、事实密度、非模板文本比例估计
- `cluster_uniqueness_score` 体现该簇是否提供了额外价值，而不是纯重复
- `noise_penalty` 建议上限不超过 25 分

### 10.4 `rerank_score` 建议公式

建议：

```text
rerank_score = base_digest_score + preference_adjustment
```

其中：

- `preference_adjustment` 建议限制在 `-5` 到 `+5`
- `PreferenceSignal` 只能影响这个 adjustment

### 10.5 明确禁止

以下做法是禁止的：

- 用 `rerank_score` 代替 `base_digest_score` 做硬裁决
- 让 `PreferenceSignal` 抵消强噪音证据
- 用个性化偏好把公共重要内容直接挤出候选池

## 11. `assemble_digest_candidates` 裁决建议

### 11.1 建议裁决顺序

第一版建议按以下顺序裁决：

1. 先看是否存在执行失败
2. 再看是否存在强 review 条件
3. 再看是否存在强过滤证据
4. 最后结合 `base_digest_score` 决定是否 `KEPT`

### 11.2 建议结果规则

- `NEEDS_REVIEW`
  当存在关键 `review_flags`，且自动判断不足以稳定落定
- `FILTERED`
  当强过滤证据成立，且无必要进入人工复核
- `KEPT`
  当质量、时效和噪音证据足以支持进入 digest 候选池

### 11.3 建议阈值

第一版可从以下阈值起步：

- `base_digest_score >= 70` 且无关键 review / noise 阻断：倾向 `KEPT`
- `50 <= base_digest_score < 70`：结合 review flags 和 cluster context 决定
- `< 50`：倾向 `FILTERED` 或 `NEEDS_REVIEW`

这只是起始阈值，后续应通过样本回放校准。

## 12. 当前阶段明确不做

第一版 `digest-candidates` 不提前做以下能力：

- 跨语言语义聚类
- 基于用户行为的强推荐
- 黑盒模型主导的最终裁决
- 长期价值判断
- 自动写日报栏目

## 13. 落地建议

第一版实现建议保持“单 workflow、显式规则模块、可回放分数层”：

- `rules/url.py`
- `rules/dedup.py`
- `rules/cluster.py`
- `rules/content.py`
- `rules/quality.py`
- `rules/noise.py`
- `rules/summary.py`
- `rules/scoring.py`

不要在第一版提前引入复杂策略引擎；先把规则、证据和裁决边界稳定下来。
