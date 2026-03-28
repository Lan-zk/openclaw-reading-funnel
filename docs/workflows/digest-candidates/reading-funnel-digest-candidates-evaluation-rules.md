# `digest-candidates` 评估规则

## 1. 文档目的

本文档定义 `digest-candidates` 作为顶层 skill 时的最小评估规则。

本文档只覆盖三类评估：

- 触发评估
- workflow 结果评估
- 运行观测指标

本文档不覆盖：

- 其他 workflow 的评估
- 人工长期价值判断
- UI 评审

## 2. 触发评估

### 2.1 `should-trigger`

以下请求应触发 `digest-candidates`：

1. 把这些候选去重并整理成 Digest
2. 先把今天抓到的内容做一轮收窄
3. 给候选池做聚类、抽取正文和摘要
4. 过滤掉明显噪音，再给我一个可判断列表
5. 对这些候选做初步排序和 review 池划分
6. 把原始候选变成 Digest 候选
7. 跑一遍候选清洗、摘要和评分
8. 从归一化候选生成今天的 Digest 输入池

### 2.2 `should-not-trigger`

以下请求不应触发 `digest-candidates`：

1. 同步我的 RSS 来源
2. 把这些来源拉下来并归一化
3. 生成日报成稿
4. 帮我判断哪些内容值得长期留存
5. 写入知识库并派生偏好信号
6. 产出周刊素材包
7. 只想重跑来源抓取
8. 只想做人类可读日报编排

### 2.3 `near-miss`

以下请求容易混淆，需要额外确认：

1. 整理今天抓到的东西
2. 刷新一下今天的阅读池
3. 重跑第二步
4. 帮我筛一下今天的内容
5. 生成今天要读的东西

判定规则：

- 如果用户重点在“抓取、导入、同步、归一”，触发 `ingest-normalize`
- 如果用户重点在“去重、抽取、清洗、摘要、初排”，触发 `digest-candidates`
- 如果用户重点在“日报栏目、重要性编排、成稿”，转到 `compose-daily-review`

## 3. Workflow 评估

### 3.1 happy path

场景：

- 上游给出 30 个 `NormalizedCandidate`
- 存在精确重复与近重复
- 至少有一部分候选能成功抽取正文
- 最终产生 `KEPT` 候选和少量 `FILTERED` 候选

期望：

- `workflow_status = SUCCEEDED`
- `digest-candidates.json` 成功产出
- `digest-review.json` 可为空
- `digest-failures.json` 为空数组或只有非阻断警告

### 3.2 empty result path

场景：

- 输入候选合法
- 但全部被高确定性噪音或低价值规则过滤
- 没有候选进入 `KEPT` 或 `NEEDS_REVIEW`

期望：

- `workflow_status = SUCCEEDED`
- `assemble_digest_candidates` 可为 `SUCCESS_EMPTY`
- 不生成伪失败记录
- `FILTERED` 与 `FAILED` 仍严格分离

### 3.3 partial success path

场景：

- 20 个候选中有 5 个抽取失败
- 其余候选成功完成摘要和评分
- 最终仍产出部分 `KEPT` 或 `NEEDS_REVIEW`

期望：

- `workflow_status = PARTIAL_SUCCESS`
- 成功对象继续产出
- `digest-failures.json` 显式记录失败候选
- 失败不阻断其他候选流转

### 3.4 failure path

场景：

- 输入文件损坏无法解析
- 或输出目录不可写
- 或 failure ledger / manifest 无法落盘

期望：

- `workflow_status = FAILED`
- 主产物与辅助产物不应伪装成成功
- 至少向调用方返回最小可见错误

### 3.5 ambiguous path

场景：

- 标题高度相似，但聚类置信度不高
- 正文抽取成功，但内容残缺
- 摘要不可用，但对象可能有价值

期望：

- `workflow_status = SUCCEEDED` 或 `PARTIAL_SUCCESS`
- 低置信度对象进入 `digest-review.json`
- 低置信度不被误记为失败
- 只有执行异常才进入 ledger

## 4. 产物评估

### 4.1 主产物要求

每次运行至少要满足以下之一：

- 产出非空 `digest-candidates.json`
- 或产出空数组 `digest-candidates.json`，同时 `step-manifest.json` 明确表明为合法空结果

### 4.2 辅助产物要求

每次运行必须有：

- `step-manifest.json`
- `digest-report.md`

以下产物也必须存在，但内容可以为空：

- `digest-review.json`
- `digest-failures.json`

## 5. 关键断言

### 5.1 结果语义断言

- `FILTERED` 不等于失败
- `NEEDS_REVIEW` 不等于失败
- `FAILED` 只存在于 `DigestFailureRecord[]`
- 只有 `assemble_digest_candidates` 可以正式写最终去向

### 5.2 数据断言

- 每个 `DigestReviewItem.cluster_id` 都必须能回溯到 `CandidateCluster`
- 每个 `DigestCandidate.primary_normalized_candidate_id` 都必须能回溯到输入候选
- 所有失败记录都必须带 `step_name`
- `rerank_score` 不得单独决定 `FILTERED`

### 5.3 路由断言

- `PreferenceSignal` 只能参与同状态内排序
- 摘要失败不自动等于对象失败
- 聚类低置信度优先进入 review，而不是被硬过滤

## 6. 观测指标

建议最少记录以下指标：

| 指标 | 说明 |
|---|---|
| `normalized_candidate_input_count` | 输入候选数 |
| `canonical_candidate_count` | URL 规范化后候选数 |
| `exact_dedup_collapse_count` | 精确去重折叠数 |
| `candidate_cluster_count` | 近重复聚类后的簇数 |
| `content_extract_success_count` | 正文抽取成功对象数 |
| `content_extract_failure_count` | 正文抽取失败对象数 |
| `summary_ready_count` | 摘要可用对象数 |
| `review_item_count` | 待复核对象数 |
| `kept_candidate_count` | `KEPT` 对象数 |
| `filtered_candidate_count` | `FILTERED` 对象数 |
| `failure_record_count` | ledger 失败记录总数 |
| `workflow_duration_ms` | workflow 总耗时 |

## 7. 最小测试矩阵

建议至少覆盖以下 10 类测试：

1. 相同 URL 指纹的候选被精确折叠
2. 标题相似但非高确定性的候选不被 `exact_dedup` 误删
3. 近重复候选被聚成同簇并选出主候选
4. 低置信度聚类进入 review 而不是失败
5. 主候选正文抽取成功后进入清洗与质量评估
6. 摘要失败但对象仍可保留或待复核
7. `PreferenceSignal` 只影响 `rerank_score`
8. 全部候选被过滤时 workflow 仍成功
9. 单对象处理失败不阻断其他对象
10. ledger 写入失败时 workflow 为 `FAILED`

## 8. 人工复盘入口

出现以下情况时应进入人工复盘：

- `review_item_count` 异常升高
- `content_extract_failure_count` 连续多轮偏高
- `filtered_candidate_count` 突然显著上升
- `kept_candidate_count` 长期接近 0
- 同一 review flag 连续多轮集中出现

人工复盘最少查看：

- `digest-failures.json`
- `digest-review.json`
- `step-manifest.json`
- 本轮输入候选样本

## 9. 当前阶段明确不定的内容

本文档当前不固定：

- 指标最终写入日志、文件还是时序系统
- 触发评估是用规则集、eval 文件还是测试框架承载
- review flag 的报警阈值

这些内容可以后续在不破坏评估边界的前提下补充。
