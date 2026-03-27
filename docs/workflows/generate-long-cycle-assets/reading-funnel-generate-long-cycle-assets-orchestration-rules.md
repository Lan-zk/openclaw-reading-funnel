# `generate-long-cycle-assets` 编排规则

## 1. 文档目的

本文档定义 `generate-long-cycle-assets` 作为顶层 workflow skill 运行时的最小编排规则。

本文档只回答五件事：

- 这个 skill 接受什么输入
- 运行顺序是什么
- step 之间怎样传对象和状态
- 哪些失败会中断运行，哪些失败只影响局部对象
- 产物如何落盘，如何 replay

本文档只覆盖 `generate-long-cycle-assets`，不展开其他 workflow。

## 2. 运行入口

### 2.1 最小输入

`generate-long-cycle-assets` skill 最少应接受以下输入：

| 输入项 | 必填 | 说明 |
|---|---|---|
| `knowledge_assets_path` | 是 | 上游 `KnowledgeAsset[]` 路径 |
| `daily_review_issues_path` | 是 | 上游 `DailyReviewIssue[]` 路径 |
| `output_root` | 是 | 本次运行输出根目录 |
| `period_start` | 否 | 周期起点；`REPLAY` 模式建议显式传入 |
| `period_end` | 否 | 周期终点；`REPLAY` 模式建议显式传入 |
| `run_id` | 否 | 不传则在运行开始时生成 |
| `runtime_overrides` | 否 | 热点阈值、长期阈值、专题门槛、最小素材量等覆盖项 |
| `mode` | 否 | `NORMAL` / `REPLAY` |

### 2.2 输出根目录

建议按 run 切目录：

```text
artifacts/generate-long-cycle-assets/<run_id>/
|-- long-cycle-assets.json
|-- author-review.json
|-- long-cycle-failures.json
|-- long-cycle-report.md
`-- step-manifest.json
```

当前阶段存储格式固定为：

- `long-cycle-assets.json`
- `author-review.json`
- `long-cycle-failures.json`
- `long-cycle-report.md`
- `step-manifest.json`

### 2.3 单 run 产物约束

当前阶段固定如下：

- 同一 `run_id` 可以同时生成 `WEEKLY` 与 `TOPIC` 两类资产
- `long-cycle-assets.json` 采用数组壳，允许长度为 `0`
- `author-review.json` 允许为空数组
- 空结果 run 仍应产出完整 report、ledger、manifest

## 3. 运行顺序

### 3.1 固定业务步骤

`generate-long-cycle-assets` 的业务执行顺序固定如下：

1. `collect_period_assets`
2. `detect_hot_topics`
3. `identify_long_signals`
4. `compose_weekly_assets`
5. `evaluate_topic_writability`
6. `assemble_topic_asset_bundle`

### 3.2 workflow shell 责任

以下行为属于 workflow shell，不属于业务原子能力：

- 输入加载
- 周期窗口解析与默认值收束
- 失败 ledger 聚合
- 产物落盘
- `step-manifest.json` 生成
- `long-cycle-report.md` 渲染

### 3.3 数据流

```text
knowledge-assets.json + daily-review-issues.json
  -> PeriodAssetSet
  -> HotTopicSignal[]
  -> LongSignal[]
  -> WeeklyAssetDraft? + AuthorReviewItem[]
  -> TopicWritabilityAssessment[]
  -> TopicAssetBundleDraft? + AuthorReviewItem[]
  -> LongCycleAsset[]

all step errors
  -> LongCycleFailureRecord[]
  -> long-cycle-report.md
```

补充说明：

- `TopicWritabilityAssessment[]` 是专题线唯一正式证据层
- `compose_weekly_assets` 与 `assemble_topic_asset_bundle` 是两个正式选入点
- 周刊线与专题线共享 `PeriodAssetSet`、`HotTopicSignal[]`、`LongSignal[]`

## 4. Step 编排规则

### 4.1 `collect_period_assets`

- 输入：`KnowledgeAsset[]`、`DailyReviewIssue[]`、周期上下文
- 输出：`PeriodAssetSet`
- 编排粒度：按单次 run 汇总统一素材池
- 局部失败：无；该步骤出错通常是系统级输入异常
- 中断条件：输入文件不可读、字段无法解析、周期窗口无法确定
- 空结果语义：若周期内合法但无素材，返回 `SUCCESS_EMPTY`

### 4.2 `detect_hot_topics`

- 输入：`PeriodAssetSet`
- 输出：`HotTopicSignal[]`
- 编排粒度：按主题候选独立聚合
- 局部失败：单主题聚合异常，只影响当前主题
- 特殊语义：低热度、低置信度主题不记失败，只在后续 omitted 或 review

### 4.3 `identify_long_signals`

- 输入：`PeriodAssetSet`、`HotTopicSignal[]`
- 输出：`LongSignal[]`
- 编排粒度：按主题独立判断长期性
- 局部失败：单主题长期性判断异常，只记对象级失败
- 特殊语义：`LongSignal` 只表达长期价值，不直接决定周刊或专题入选

### 4.4 `compose_weekly_assets`

- 输入：`PeriodAssetSet`、`HotTopicSignal[]`、`LongSignal[]`
- 输出：`LongCycleAsset[]`（`asset_scope = WEEKLY`）、`AuthorReviewItem[]`
- 编排粒度：当前阶段每个 run 最多形成 1 个周刊资产
- 系统级失败：周刊草稿与正式资产都无法形成，且不属于合法空结果
- 空结果语义：若没有足够主题支撑周刊，返回 `SUCCESS_EMPTY`
- 特殊语义：该步骤是周刊线唯一正式入选点

### 4.5 `evaluate_topic_writability`

- 输入：`PeriodAssetSet`、`HotTopicSignal[]`、`LongSignal[]`
- 输出：`TopicWritabilityAssessment[]`
- 编排粒度：按主题独立判断可写性
- 局部失败：单主题评估异常，只影响当前主题
- 特殊语义：`recommended_outcome` 只生成建议，不直接形成资产

### 4.6 `assemble_topic_asset_bundle`

- 输入：`PeriodAssetSet`、`HotTopicSignal[]`、`LongSignal[]`、`TopicWritabilityAssessment[]`
- 输出：`LongCycleAsset[]`（`asset_scope = TOPIC`）、`AuthorReviewItem[]`
- 编排粒度：按主题独立装配专题草稿，再写正式资产
- 局部失败：单专题装配异常，只影响当前主题
- 空结果语义：若没有任何主题通过专题门槛，返回 `SUCCESS_EMPTY`
- 特殊语义：该步骤是专题线唯一正式入选点

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
  主流程完成，主产物已形成，或合法空结果已形成，但至少存在一个对象级失败
- `FAILED`
  发生系统级失败，导致主产物、failure ledger、step manifest 或关键报告无法形成

### 5.3 成功不要求一定有正式长周期资产

以下情况允许 workflow 最终为 `SUCCEEDED`：

- 周刊线为空，专题线为空
- 周刊线为空，但专题线进入 review
- 周刊线与专题线都没有入选对象，但 report、ledger、manifest 正常写出

因此：

- `long-cycle-assets.json` 可以为空数组
- `author-review.json` 可以非空且主产物仍为空

## 6. 失败继续策略

### 6.1 默认策略

`generate-long-cycle-assets` 默认采用“主题级隔离，运行级汇总”：

- 单主题聚合异常，不拖垮其他主题
- 单主题长期性判断异常，不拖垮其他主题
- 单专题装配异常，不拖垮周刊线
- 周刊线为空结果，不阻断专题线

### 6.2 立即中断条件

发生以下情况时立即中断：

- `run_id` 无法生成
- 输入文件不可读或无法解析
- 输出目录无法创建
- `long-cycle-failures.json` 无法写出
- `step-manifest.json` 无法写出
- `long-cycle-report.md` 无法写出

## 7. 产物写出顺序

建议按以下顺序写出产物：

1. `long-cycle-assets.json`
2. `author-review.json`
3. `long-cycle-failures.json`
4. `step-manifest.json`
5. `long-cycle-report.md`

原因：

- 先写结构化主产物与 review artifact，固定业务结果
- 再写 failure ledger 与 manifest，固定运行事实
- 最后写面向人的报告

## 8. Replay 规则

### 8.1 `REPLAY` 模式用途

`REPLAY` 模式用于：

- 重跑某个历史周期的周刊/专题生成
- 调整阈值后回放某次长周期资产判断
- 复核某轮失败或 review 激增的 run

### 8.2 `REPLAY` 模式最小要求

`REPLAY` 模式建议显式提供：

- `period_start`
- `period_end`
- 与原始 run 对应的 `knowledge_assets_path`
- 与原始 run 对应的 `daily_review_issues_path`

### 8.3 `REPLAY` 禁止事项

`REPLAY` 模式不允许：

- 换成新的外部抓取结果
- 补抓上游热点
- 修改上游资产内容后伪装成同一 replay

## 9. 当前阶段明确不定的内容

当前阶段暂不强行固定：

- 单 run 同时生成多个周刊资产
- 周刊 Markdown 导出
- 专题草稿自动扩写为长文
- 跨 run 长周期主题记忆
