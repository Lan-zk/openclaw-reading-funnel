# `generate-long-cycle-assets` 评估规则

## 1. 文档目的

本文档定义 `generate-long-cycle-assets` 作为顶层 skill 时的最小评估规则。

本文档只覆盖三类评估：

- 触发评估
- workflow 结果评估
- 运行观测指标

本文档不覆盖：

- 其他 workflow 的评估
- 人工作者最终成稿评审
- UI 视觉评审

## 2. 触发评估

### 2.1 `should-trigger`

以下请求应触发 `generate-long-cycle-assets`：

1. 把累计沉淀整理成周刊素材包
2. 基于日报和知识资产生成长周期输出
3. 产出周尺度的长期复盘资产
4. 组装一批值得写专题的素材包
5. 跑一遍第五步，生成 long-cycle assets
6. 根据已有沉淀识别热点主线和长期主题
7. 输出周刊和专题尺度的结构化资产
8. 给我一批周刊或专题可写素材

### 2.2 `should-not-trigger`

以下请求不应触发 `generate-long-cycle-assets`：

1. 同步我的 RSS 来源
2. 把来源条目归一成候选池
3. 给候选做去重、抽取、摘要和初排
4. 生成日报成稿
5. 把日报编成今天的阅读 issue
6. 记录人工留存决策
7. 把高价值内容写入知识库
8. 只想重跑第一步到第四步

### 2.3 `near-miss`

以下请求容易混淆，需要额外确认：

1. 整理一批长期内容
2. 把重要内容做成资产
3. 产出下一轮写作材料
4. 刷新周刊准备池
5. 把沉淀内容再整理一下

判定规则：

- 如果用户重点在“抓取、同步、归一”，触发 `ingest-normalize`
- 如果用户重点在“去重、抽取、摘要、初排”，触发 `digest-candidates`
- 如果用户重点在“日报栏目、主题主线、成稿”，触发 `compose-daily-review`
- 如果用户重点在“人工长期价值判断、留存记录、知识入库”，触发 `curate-retain`
- 如果用户重点在“周刊、专题、长周期输出、可写素材包”，触发 `generate-long-cycle-assets`

## 3. Workflow 评估

### 3.1 happy path

场景：

- 上游给出合法 `KnowledgeAsset[]` 与 `DailyReviewIssue[]`
- 至少形成 1 个清晰热点主题
- 至少形成 1 个长期信号
- 最终形成周刊资产、专题资产，或两者之一

期望：

- `workflow_status = SUCCEEDED`
- `long-cycle-assets.json` 非空
- `author-review.json` 可为空
- `long-cycle-failures.json` 为空数组
- `long-cycle-report.md` 成功产出

### 3.2 empty result path

场景：

- 输入合法
- 但当前周期没有足够证据形成正式周刊或专题
- 也没有对象进入作者复核

期望：

- `workflow_status = SUCCEEDED`
- `long-cycle-assets.json` 为空数组
- `author-review.json` 为空数组
- 不生成伪失败记录
- 至少一个正式选入 step 为 `SUCCESS_EMPTY`

### 3.3 author-review path

场景：

- 热点主题接近阈值
- 长期信号不稳定
- 专题可写性边界模糊
- 最终未形成正式资产，但应保留作者判断入口

期望：

- `workflow_status = SUCCEEDED`
- `long-cycle-assets.json` 可为空数组
- `author-review.json` 非空
- 低置信度对象不被误记为失败

### 3.4 partial success path

场景：

- 周刊线成功
- 但专题线某些主题装配失败
- 或单主题长期性判断失败
- 其余对象继续流转

期望：

- `workflow_status = PARTIAL_SUCCESS`
- 成功对象继续产出
- `long-cycle-failures.json` 显式记录失败对象
- 失败不阻断其他主题或另一条产线

### 3.5 failure path

场景：

- 输入文件损坏无法解析
- 或输出目录不可写
- 或 failure ledger / manifest / report 无法落盘
- 或运行入口级参数无法解析

期望：

- `workflow_status = FAILED`
- 主产物与辅助产物不应伪装成成功
- 至少向调用方返回最小可见错误

### 3.6 ambiguous path

场景：

- 热点主题是否值得拉成长线存在争议
- 专题证据密度接近门槛
- 某主题既可进周刊主线，也可能单独做专题

期望：

- `workflow_status = SUCCEEDED` 或 `PARTIAL_SUCCESS`
- 有争议对象进入 `author-review.json`
- `OMITTED`、`REVIEW_REQUIRED` 与 `FAILED` 严格分离
- 只有执行异常才进入 ledger

## 4. 产物评估

### 4.1 主产物要求

每次运行至少要满足以下之一：

- 产出非空 `long-cycle-assets.json`
- 或产出空数组 `long-cycle-assets.json`，同时 `step-manifest.json` 明确表明为空结果

### 4.2 辅助产物要求

每次运行必须有：

- `step-manifest.json`
- `long-cycle-report.md`
- `long-cycle-failures.json`
- `author-review.json`

## 5. 关键断言

### 5.1 结果语义断言

- `SUCCESS_EMPTY` 不等于失败
- `REVIEW_REQUIRED` 不等于失败
- `NEEDS_AUTHOR_REVIEW` 不等于失败
- `FAILED` 只存在于 `LongCycleFailureRecord[]`
- 只有 `compose_weekly_assets` 与 `assemble_topic_asset_bundle` 可以正式写最终资产

### 5.2 数据断言

- 每个 `LongCycleAsset.theme_ids` 都必须能回溯到 `HotTopicSignal` 或 `LongSignal`
- 每个 `TOPIC` 资产的 `writability_score` 都必须能回溯到 `TopicWritabilityAssessment`
- 每个 `AuthorReviewItem.related_object_id` 都必须能回溯到对应对象
- 所有失败记录都必须带 `step_name`
- 周刊与专题资产都必须只溯源到已有 `KnowledgeAsset` 与 `DailyReviewIssue`

### 5.3 路由断言

- 热点信号不直接决定正式资产
- 长期信号不等于专题可写
- 可写性评估不直接等于正式专题资产
- 空结果路径不应被误判为失败

## 6. 观测指标

建议最少记录以下指标：

| 指标 | 说明 |
|---|---|
| `knowledge_asset_input_count` | 输入知识资产数 |
| `daily_review_issue_input_count` | 输入日报 issue 数 |
| `hot_topic_count` | 热点主题数 |
| `long_signal_count` | 长期信号数 |
| `topic_assessment_count` | 专题可写性评估数 |
| `weekly_asset_count` | 周刊资产数 |
| `topic_asset_count` | 专题资产数 |
| `author_review_item_count` | 作者复核条目数 |
| `failure_record_count` | ledger 失败记录总数 |
| `workflow_duration_ms` | workflow 总耗时 |

## 7. 最小测试矩阵

建议至少覆盖以下 10 类测试：

1. 合法输入能形成 `PeriodAssetSet`
2. 热点主题能从知识资产与日报 issue 中正确聚合
3. 低热点主题进入 review 或 omitted，而不是失败
4. 长期信号能从热点主题中正确分化
5. 周刊线可在合法输入下形成 `WEEKLY` 资产
6. 专题线可在高可写性主题下形成 `TOPIC` 资产
7. 周刊线空结果不阻断专题线
8. 有争议主题进入 `author-review.json`
9. 单主题装配失败不阻断其他主题
10. `long-cycle-failures.json` 或 `step-manifest.json` 写入失败时 workflow 为 `FAILED`

## 8. 人工复盘入口

出现以下情况时应进入人工复盘：

- `author_review_item_count` 异常升高
- 连续多轮没有任何长周期资产
- `topic_asset_count` 长期为 `0` 但 `hot_topic_count` 很高
- 同一 `review_flag` 连续多轮集中出现
- 周刊资产长期只依赖日报、几乎不依赖知识资产

人工复盘最少查看：

- `long-cycle-failures.json`
- `author-review.json`
- `step-manifest.json`
- 本轮输入 `KnowledgeAsset` 样本
- 本轮输入 `DailyReviewIssue` 样本

## 9. 当前阶段明确不定的内容

当前阶段暂不强行固定：

- 专题正文质量评估
- 周刊人工排版质量评估
- 多 run 资产去重评估
