# `ingest-normalize` 评估规则

## 1. 文档目的

本文档定义 `ingest-normalize` 作为顶层 skill 时的最小评估规则。

本文档只覆盖三类评估：

- 触发评估
- workflow 结果评估
- 运行观测指标

本文档不覆盖：

- 其他 workflow 的评估
- 模型打分
- UI 评审

## 2. 触发评估

### 2.1 `should-trigger`

以下请求应触发 `ingest-normalize`：

1. 同步我订阅的 RSS 来源
2. 把这些 feed 全部拉下来
3. 导入今天的新候选内容
4. 更新阅读来源池
5. 从 GitHub Feed 抓今天的新动态
6. 把这些来源统一成候选池
7. 跑一遍信息摄入和基础归一化
8. 重新抓取这个来源最近 24 小时的数据

### 2.2 `should-not-trigger`

以下请求不应触发 `ingest-normalize`：

1. 给我做今天的阅读 Digest
2. 把候选去重并生成摘要
3. 生成日报成稿
4. 帮我判断哪些内容值得长期留存
5. 产出周刊素材包
6. 评估这条内容是否重要
7. 对候选做排序和精选
8. 基于阅读偏好推荐内容

### 2.3 `near-miss`

以下请求容易混淆，需要额外确认：

1. 更新阅读内容
2. 整理今天抓到的东西
3. 刷新一下信息源
4. 重跑第一步

判定规则：

- 如果用户重点在“接入、抓取、导入、同步、归一”，触发 `ingest-normalize`
- 如果用户重点在“筛选、去重、摘要、精选”，转到 `digest-candidates`

## 3. Workflow 评估

### 3.1 happy path

场景：

- 有 3 个启用来源
- 3 个来源均可抓取
- 至少 1 个来源返回新内容
- 成功产出 `SourceEntry[]` 和 `NormalizedCandidate[]`

期望：

- `workflow_status = SUCCEEDED`
- `normalized-candidates.json` 非空
- `ingest-failures.json` 为空数组或只有非阻断警告

### 3.2 empty result path

场景：

- 来源可访问
- 同步窗口内没有新内容

期望：

- `workflow_status = SUCCEEDED`
- `fetch_source_items` 或后续 step 可出现 `SUCCESS_EMPTY`
- `normalized-candidates.json` 为空数组
- 不生成伪失败记录

### 3.3 partial success path

场景：

- 5 个来源中 2 个抓取失败
- 其余 3 个来源成功并产出候选

期望：

- `workflow_status = PARTIAL_SUCCESS`
- `normalized-candidates.json` 非空
- `ingest-failures.json` 记录 2 个失败来源
- 失败不阻断成功来源的输出

### 3.4 failure path

场景：

- 输出目录不可写
- 或 failure ledger 无法落盘

期望：

- `workflow_status = FAILED`
- 主产物和辅助产物不应伪装成成功
- 至少向调用方返回最小可见错误

### 3.5 ambiguous path

场景：

- 来源抓取成功
- 但大部分条目缺失关键字段
- 仅少量条目能形成候选

期望：

- `workflow_status = PARTIAL_SUCCESS`
- 合法条目继续产出
- 非法条目进入 `ingest-failures.json`
- 不因局部条目问题把整轮运行判为失败

## 4. 产物评估

### 4.1 主产物要求

每次运行至少要满足以下之一：

- 产出非空 `normalized-candidates.json`
- 或产出空数组 `normalized-candidates.json`，同时 `step-manifest.json` 明确表明是 `SUCCESS_EMPTY`

### 4.2 辅助产物要求

每次运行必须有：

- `step-manifest.json`
- `ingest-report.json`

以下产物也必须存在，但内容可以为空：

- `source-entries.json`
- `ingest-failures.json`

## 5. 关键断言

### 5.1 结果语义断言

- 空结果不等于失败
- 对象创建前失败不创建业务对象
- 失败 ledger 是唯一失败真相
- 单来源失败不拖垮全部来源

### 5.2 数据断言

- 所有 `NormalizedCandidate.source_entry_id` 必须能回溯到 `SourceEntry`
- 所有失败记录必须带 `step_name`
- 所有产物必须带 `run_id` 或能追溯到 `run_id`

## 6. 观测指标

建议最少记录以下指标：

| 指标 | 说明 |
|---|---|
| `source_discovery_count` | 本轮发现的来源数 |
| `source_enabled_count` | 本轮启用的来源数 |
| `source_fetch_success_count` | 抓取成功来源数 |
| `source_fetch_empty_count` | 抓取为空来源数 |
| `source_fetch_failed_count` | 抓取失败来源数 |
| `raw_feed_item_count` | feed 结构条目数 |
| `source_entry_count` | 成功落盘的来源快照数 |
| `normalized_candidate_count` | 成功归一化候选数 |
| `failure_record_count` | ledger 失败记录总数 |
| `workflow_duration_ms` | workflow 总耗时 |

## 7. 最小测试矩阵

建议至少覆盖以下 8 类测试：

1. 来源配置合法，产生可执行 `SourceDescriptor`
2. 单来源配置非法，但不影响其他来源
3. 增量窗口为空，返回 `SUCCESS_EMPTY`
4. 单来源抓取超时，被记入 ledger
5. 抓取成功但转换失败，被记入 ledger
6. 条目字段非法，只丢当前条目
7. 主产物为空但 workflow 仍为 `SUCCEEDED`
8. ledger 写入失败时 workflow 为 `FAILED`

## 8. 人工复盘入口

出现以下情况时应进入人工复盘：

- 同一来源连续多次抓取失败
- 单来源条目映射失败率异常升高
- `normalized_candidate_count` 突然跌到 0
- `source_fetch_empty_count` 长期异常偏高

人工复盘最少查看：

- `ingest-failures.json`
- `step-manifest.json`
- 对应来源配置

## 9. 当前阶段明确不定的内容

本文档当前不固定：

- 指标最终写入日志、文件还是时序系统
- 触发评估是用规则集、eval 文件还是测试框架承载
- 指标阈值的具体报警值

这些内容可以后续在不破坏评估边界的前提下补充。
