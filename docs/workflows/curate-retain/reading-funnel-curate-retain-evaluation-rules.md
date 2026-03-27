# `curate-retain` 评估规则

## 1. 文档目的

本文档定义 `curate-retain` 作为顶层 skill 时的最小评估规则。

本文档只覆盖三类评估：

- 触发评估
- workflow 结果评估
- 运行观测指标

本文档不覆盖：

- 其他 workflow 的评估
- 人工 UI 视觉评审
- 周刊或专题产物评审

## 2. 触发评估

### 2.1 `should-trigger`

以下请求应触发 `curate-retain`：

1. 把这些候选整理成待精读队列，并记录留存决策
2. 帮我确认哪些内容值得长期沉淀
3. 把人工确认后的结果写入知识库
4. 从正式留存决策里派生偏好信号
5. 给这批高价值内容落长期标签和资产类型
6. 跑一遍第四步，把精读结论正式落盘
7. 生成留存记录、知识资产和偏好信号
8. 重跑这批正式决策的知识资产与偏好派生

### 2.2 `should-not-trigger`

以下请求不应触发 `curate-retain`：

1. 同步我的 RSS 来源
2. 把来源条目归一成候选池
3. 给候选做去重、抽取、摘要和初排
4. 生成日报成稿
5. 把日报编成今天的阅读 issue
6. 产出周刊素材包
7. 写专题文章草稿
8. 只想重跑第一步、第二步或第三步

### 2.3 `near-miss`

以下请求容易混淆，需要额外确认：

1. 整理今天真正值得留的内容
2. 处理高价值内容
3. 重跑第四步
4. 把值得保留的东西收进去
5. 把重要内容沉淀一下

判定规则：

- 如果用户重点在“去重、抽取、摘要、初排”，触发 `digest-candidates`
- 如果用户重点在“日报编排、主题主线、成稿”，触发 `compose-daily-review`
- 如果用户重点在“人工确认长期价值、知识入库、留存记录、偏好信号”，触发 `curate-retain`
- 如果用户重点在“周刊、专题、长周期产物”，转到 `generate-long-cycle-assets`

## 3. Workflow 评估

### 3.1 happy path

场景：

- 上游给出一组合法 `DigestCandidate`
- 成功构建待处理队列
- 人工提交正式决策
- 至少形成一条 `KEEP` 或 `DROP` 正式记录
- `KEEP` 决策进一步形成知识资产与偏好信号

期望：

- `workflow_status = SUCCEEDED`
- `retention-decisions.json` 成功产出
- `read-queue.json` 成功产出
- `curation-failures.json` 为空数组
- `knowledge-assets.json` 与 `preference-signals.json` 允许非空

### 3.2 queue-only path

场景：

- 上游输入合法
- 成功生成待精读队列
- 本轮没有任何人工正式决策输入

期望：

- `workflow_status = SUCCEEDED`
- `build_read_queue = SUCCESS_WITH_OUTPUT`
- `capture_human_decision = SUCCESS_EMPTY`
- `retention-decisions.json` 为空数组
- 不生成伪失败记录

### 3.3 decision-only path

场景：

- 本轮新增正式决策
- 但没有任何 `KEEP`
- 或 `KEEP` 不足以形成资产草稿

期望：

- `workflow_status = SUCCEEDED`
- `retention-decisions.json` 非空
- `knowledge-assets.json` 可为空数组
- `preference-signals.json` 可为空数组
- `DROP` / `DEFER` / `NEEDS_RECHECK` 不被误记为失败

### 3.4 partial success path

场景：

- 一部分正式决策成功落盘
- 其中部分 `KEEP` 的标签派生或资产写入失败
- 其余对象继续正常产出

期望：

- `workflow_status = PARTIAL_SUCCESS`
- 成功对象继续产出
- `curation-failures.json` 显式记录失败对象
- 失败不阻断其他对象流转
- 原始 `RetentionDecisionRecord` 不被改判

### 3.5 failure path

场景：

- 输入文件损坏无法解析
- 或输出目录不可写
- 或 failure ledger / manifest 无法落盘
- 或正式决策主产物无法形成

期望：

- `workflow_status = FAILED`
- 主产物与辅助产物不应伪装成成功
- 至少向调用方返回最小可见错误

### 3.6 ambiguous path

场景：

- 人工提交 `DEFER`
- 人工提交 `NEEDS_RECHECK`
- 标签不足，但对象可能值得保留
- 偏好信号可派生性不足

期望：

- `workflow_status = SUCCEEDED` 或 `PARTIAL_SUCCESS`
- `DEFER` 与 `NEEDS_RECHECK` 作为正式决策落盘
- 标签不足时允许形成低信息量资产草稿，或不形成资产草稿
- 只有执行异常才进入 ledger

## 4. 产物评估

### 4.1 主产物要求

每次运行至少要满足以下之一：

- 产出非空 `retention-decisions.json`
- 或产出空数组 `retention-decisions.json`，同时 `step-manifest.json` 明确表明是合法空结果

### 4.2 辅助产物要求

每次运行必须有：

- `read-queue.json`
- `curation-failures.json`
- `step-manifest.json`
- `curation-report.md`

以下产物也必须存在，但内容可以为空：

- `knowledge-assets.json`
- `preference-signals.json`

## 5. 关键断言

### 5.1 结果语义断言

- `DROP` 不等于失败
- `DEFER` 不等于失败
- `NEEDS_RECHECK` 不等于失败
- `FAILED` 只存在于 `CurationFailureRecord[]` 与 step 结果
- 只有 `capture_human_decision` 可以正式写人工决策结果
- `store_knowledge_asset` 不得因写入失败回写人工决策

### 5.2 数据断言

- 每个 `RetentionDecisionRecord.target_id` 都必须能回溯到输入对象
- 每个 `KnowledgeAsset.origin_retention_decision_id` 都必须能回溯到正式 `KEEP` 决策
- 每个 `PreferenceSignal.origin_retention_decision_id` 都必须能回溯到正式决策
- 每个 `ReadQueueItem.target_id` 都必须能回溯到上游对象
- 所有失败记录都必须带 `step_name`

### 5.3 路由断言

- 只有 `KEEP` 决策可以进入 `KnowledgeAssetDraft`
- `PreferenceSignal` 只能从正式决策派生
- `KnowledgeAsset` 只能作为信号派生时的补充上下文
- replay 不得篡改原始人工决策真相
- 空结果路径不应被误判为失败

## 6. 观测指标

建议最少记录以下指标：

| 指标 | 说明 |
|---|---|
| `digest_candidate_input_count` | 输入 Digest 候选数 |
| `read_queue_item_count` | 入队对象数 |
| `human_decision_draft_count` | 本轮收集到的决策草稿数 |
| `retention_decision_count` | 正式决策总数 |
| `keep_decision_count` | `KEEP` 决策数 |
| `drop_decision_count` | `DROP` 决策数 |
| `defer_decision_count` | `DEFER` 决策数 |
| `needs_recheck_decision_count` | `NEEDS_RECHECK` 决策数 |
| `knowledge_asset_count` | 新增知识资产数 |
| `preference_signal_count` | 新增偏好信号数 |
| `failure_record_count` | ledger 失败记录总数 |
| `workflow_duration_ms` | workflow 总耗时 |

## 7. 最小测试矩阵

建议至少覆盖以下 10 类测试：

1. 上游候选被稳定组织成 `ReadQueueItem[]`
2. 无人工输入时 workflow 只产出队列且成功
3. `capture_human_decision` 是唯一正式写 `KEEP` / `DROP` 的步骤
4. `DEFER` 与 `NEEDS_RECHECK` 可以正式落盘但不进入失败账本
5. 只有 `KEEP` 决策可以派生 `KnowledgeAssetDraft`
6. 资产写入失败不改写原始人工决策
7. `PreferenceSignal` 只能从正式决策派生
8. `supplementary_knowledge_asset_id` 不能替代 canonical origin
9. 单对象派生失败不阻断其他对象
10. `curation-failures.json` 或 `step-manifest.json` 写入失败时 workflow 为 `FAILED`

## 8. 人工复盘入口

出现以下情况时应进入人工复盘：

- `read_queue_item_count` 连续多轮异常偏高或偏低
- `defer_decision_count` 长期过高
- `needs_recheck_decision_count` 突然显著上升
- `knowledge_asset_count` 长期接近 `0`
- 同一 `failure_type` 连续多轮集中出现

人工复盘最少查看：

- `read-queue.json`
- `retention-decisions.json`
- `knowledge-assets.json`
- `preference-signals.json`
- `curation-failures.json`
- `step-manifest.json`

## 9. 当前阶段明确不定的内容

本文档当前不固定：

- 人工确认的效率指标是否单独入观测系统
- 触发评估最终由规则集、eval 文件还是测试框架承载
- `DEFER` 和 `NEEDS_RECHECK` 的 SLA 或回流时窗

这些内容可以后续补充，但不得破坏本文档中的评估边界和成功定义。
