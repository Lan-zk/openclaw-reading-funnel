# `curate-retain` 编排规则

## 1. 文档目的

本文档定义 `curate-retain` 作为顶层 workflow skill 运行时的最小编排规则。

本文档只回答五件事：

- 这个 skill 接受什么输入
- 运行顺序是什么
- step 之间怎样传对象和状态
- 哪些失败会中断运行，哪些失败只影响局部对象
- 产物如何落盘，如何 replay

本文档只覆盖 `curate-retain`，不展开其他 workflow。

## 2. 运行入口

### 2.1 最小输入

`curate-retain` skill 最少应接受以下输入：

| 输入项 | 必填 | 说明 |
|---|---|---|
| `digest_candidates_path` | 是 | 上游 `DigestCandidate[]` 路径 |
| `output_root` | 是 | 本次运行输出根目录 |
| `daily_review_issue_path` | 否 | 上游 `DailyReviewIssue[]` 或单 issue 路径，用于队列优先级辅助 |
| `human_decisions_path` | 否 | 外部人工决策输入路径；不传时允许只生成待处理队列 |
| `run_id` | 否 | 不传则在运行开始时生成 |
| `runtime_overrides` | 否 | 入队阈值、标签规则、信号过期策略等覆盖项 |
| `mode` | 否 | `NORMAL` / `REPLAY` |

补充约束：

- 当前阶段 `digest_candidates_path` 是基础输入，不允许完全脱离上游 Digest 对象运行
- `human_decisions_path` 缺失时，workflow 允许只生成 `read-queue.json`
- `daily_review_issue_path` 只用于辅助排序和上下文补充，不得直接代替人工决策

### 2.2 输出根目录

建议按 run 切目录：

```text
artifacts/curate-retain/<run_id>/
|-- retention-decisions.json
|-- read-queue.json
|-- knowledge-assets.json
|-- preference-signals.json
|-- curation-failures.json
|-- curation-report.md
`-- step-manifest.json
```

当前阶段存储格式固定为：

- `retention-decisions.json`
- `read-queue.json`
- `knowledge-assets.json`
- `preference-signals.json`
- `curation-failures.json`
- `step-manifest.json`
- `curation-report.md`

当前阶段不使用：

- CSV 作为主产物存储格式
- SQLite 作为 workflow 运行存储

### 2.3 人工决策输入适配

当前阶段允许两类 `capture_human_decision` 输入方式：

1. 交互式确认入口
2. 结构化决策导入文件

两者都必须统一产出：

- `HumanDecisionDraft[]`

规则约束：

- workflow shell 可以切换输入适配方式
- 业务真相必须保持不变
- 不允许因为输入适配方式不同而产生不同决策语义

## 3. 运行顺序

### 3.1 固定业务步骤

`curate-retain` 的业务执行顺序固定如下：

1. `build_read_queue`
2. `capture_human_decision`
3. `persist_retention_decision`
4. `derive_long_term_tags`
5. `store_knowledge_asset`
6. `derive_preference_signals`

### 3.2 workflow shell 责任

以下行为属于 workflow shell，不属于业务原子能力：

- 输入加载
- `run_id` 解析
- 上游目标快照组装
- 失败 ledger 聚合
- 产物落盘
- `step-manifest.json` 生成
- `curation-report.md` 渲染

### 3.3 数据流

```text
digest-candidates.json + optional daily-review-issue
  -> ReadQueueItem[]
  -> HumanDecisionDraft[]
  -> RetentionDecisionRecord[]
  -> RetainedTargetSnapshot[]
  -> KnowledgeAssetDraft[]
  -> KnowledgeAsset[]
  -> PreferenceSignal[]

all step errors
  -> CurationFailureRecord[]
  -> curation-report.md
```

补充说明：

- `RetainedTargetSnapshot[]` 由 workflow shell 基于上游输入显式组装
- `derive_long_term_tags` 只能消费 `KEEP` 决策与显式 snapshot
- `derive_preference_signals` 只能消费正式 `RetentionDecisionRecord[]`

## 4. Step 编排规则

### 4.1 `build_read_queue`

- 输入：`DigestCandidate[]`、可选 `DailyReviewIssue`
- 输出：`ReadQueueItem[]`
- 编排粒度：按候选对象独立评估，再统一排序
- 局部失败：单对象入队判断异常，只影响当前对象
- 中断条件：输入文件不可读或整体解析失败
- 规则约束：该 step 只能生成“人工待处理对象”，不能暗中生成 `KEEP` / `DROP`

### 4.2 `capture_human_decision`

- 输入：`ReadQueueItem[]`、可选外部人工决策输入
- 输出：`HumanDecisionDraft[]`
- 编排粒度：按队列对象逐条收集或导入
- 局部失败：单条决策采集或解析异常，只影响当前对象
- 空结果语义：人工未提交任何正式决策时，该 step 允许返回 `SUCCESS_EMPTY`
- 规则约束：这是唯一正式产生 `KEEP` / `DROP` / `DEFER` / `NEEDS_RECHECK` 的步骤

### 4.3 `persist_retention_decision`

- 输入：`HumanDecisionDraft[]`
- 输出：`RetentionDecisionRecord[]`
- 编排粒度：按决策草稿独立落盘
- 局部失败：单条决策持久化失败，只记对象级 failure 并继续
- 系统级失败：决策主产物无法形成或整体持久化模块不可用
- 规则约束：只做正式落盘，不重新解释人工判断

### 4.4 `derive_long_term_tags`

- 输入：`RetentionDecisionRecord[]`、`RetainedTargetSnapshot[]`
- 输出：`KnowledgeAssetDraft[]`
- 编排粒度：按正式 `KEEP` 决策独立派生
- 局部失败：单条 `KEEP` 决策派生失败，只影响对应资产草稿
- 空结果语义：本轮无 `KEEP` 决策时，该 step 允许返回 `SUCCESS_EMPTY`
- 规则约束：非 `KEEP` 决策不得进入该 step 的正式产出

### 4.5 `store_knowledge_asset`

- 输入：`KnowledgeAssetDraft[]`
- 输出：`KnowledgeAsset[]`
- 编排粒度：按资产草稿独立写入
- 局部失败：单资产写入失败，只记对象级 failure 并继续
- 空结果语义：无资产草稿时允许返回 `SUCCESS_EMPTY`
- 规则约束：资产写入失败不得回写或改判原始 `RetentionDecisionRecord`

### 4.6 `derive_preference_signals`

- 输入：`RetentionDecisionRecord[]`、可选 `KnowledgeAsset[]`
- 输出：`PreferenceSignal[]`
- 编排粒度：按正式决策独立派生，再做去重与聚合
- 局部失败：单决策信号派生失败，只影响当前信号
- 空结果语义：无可派生信号时允许返回 `SUCCESS_EMPTY`
- 规则约束：`KnowledgeAsset[]` 只用于补充上下文，不能独立成为信号真相来源

## 5. Step 状态规则

### 5.1 step 状态枚举

每个业务 step 只允许三种状态：

- `SUCCESS_WITH_OUTPUT`
- `SUCCESS_EMPTY`
- `FAILED`

### 5.2 workflow 汇总状态

workflow 级状态只允许三种：

- `SUCCEEDED`
- `PARTIAL_SUCCESS`
- `FAILED`

判定规则：

- `SUCCEEDED`
  主流程完成，允许存在 `SUCCESS_EMPTY` step，且无执行失败 ledger
- `PARTIAL_SUCCESS`
  主流程完成，但至少存在一个对象级失败
- `FAILED`
  发生系统级失败，导致主产物、failure ledger、step manifest 或关键报告无法形成

### 5.3 成功不要求一定有新增正式决策

以下情况允许 workflow 最终为 `SUCCEEDED`：

- 只构建了 `read-queue.json`，但人工未提交决策
- 人工决策输入为空且这是预期路径
- 所有正式决策都是 `DEFER` 或 `NEEDS_RECHECK`
- `knowledge-assets.json` 与 `preference-signals.json` 为空数组

因此：

- `retention-decisions.json` 可以为空数组
- `knowledge-assets.json` 可以为空数组
- `preference-signals.json` 可以为空数组
- 只要 `step-manifest.json` 与 `curation-report.md` 成功生成，运行仍可视为成功

## 6. 失败继续策略

### 6.1 默认策略

`curate-retain` 默认采用“对象级隔离，运行级汇总”：

- 单对象入队异常，不拖垮其他对象
- 单条决策导入失败，不拖垮其他决策
- 单条 `KEEP` 标签派生失败，不拖垮其他资产草稿
- 单资产写入失败，不拖垮其他资产
- 单信号派生失败，不拖垮其他信号

### 6.2 立即中断条件

发生以下情况时立即中断：

- `run_id` 无法生成
- 输入文件不可读或无法解析
- 产物目录无法创建
- `curation-failures.json` 无法写出
- `step-manifest.json` 无法写出
- `retention-decisions.json` 无法形成最小合法结构

## 7. 产物写出顺序

建议按以下顺序写出产物：

1. `read-queue.json`
2. `retention-decisions.json`
3. `knowledge-assets.json`
4. `preference-signals.json`
5. `curation-failures.json`
6. `step-manifest.json`
7. `curation-report.md`

原因：

- 先写人工处理面与正式决策对象
- 再写决策消费产物
- 再固定 failure ledger 与 manifest
- 最后写面向人的 Markdown 报告

## 8. Replay 规则

### 8.1 `REPLAY` 模式目标

`REPLAY` 模式只用于：

- 重跑某轮留存决策的派生规则
- 校验标签与信号规则变更
- 对比新旧资产与信号输出差异

### 8.2 `REPLAY` 模式最小要求

`REPLAY` 模式至少应固定以下输入：

- 上轮 `DigestCandidate[]`
- 上轮 `RetentionDecisionRecord[]` 或等价正式决策输入
- 上轮 `runtime_overrides` 或其哈希

### 8.3 `REPLAY` 模式约束

- 不得借 replay 改写原始人工决策内容
- 不得借 replay 篡改既有 failure ledger
- 可以重跑 `derive_long_term_tags`、`store_knowledge_asset`、`derive_preference_signals`
- 如要重跑 `capture_human_decision`，必须显式声明使用新的人工输入，而不是伪装成 replay

## 9. 与上下游 workflow 的边界

`curate-retain` 对下游只暴露三类正式信息：

- `RetentionDecisionRecord[]`
- `KnowledgeAsset[]`
- `PreferenceSignal[]`

它不负责：

- 回头要求 `digest-candidates` 重新聚类或打分
- 替 `compose-daily-review` 重新编排日报
- 直接生成周刊或专题素材包

上游只允许向它提供：

- `DigestCandidate[]`
- 可选 `DailyReviewIssue`
- 显式人工决策输入

## 10. 当前阶段明确不定的内容

本文档当前不固定：

- 交互式人工确认入口的具体 UI 形态
- 幂等写入是 append、upsert 还是版本化落盘
- `runtime_overrides` 的完整配置 schema

这些内容可以后续补充，但不得改变本文档规定的 step 顺序、人工裁决边界和产物语义。
