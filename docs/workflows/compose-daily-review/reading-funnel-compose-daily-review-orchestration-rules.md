# `compose-daily-review` 编排规则

## 1. 文档目的

本文档定义 `compose-daily-review` 作为顶层 workflow skill 运行时的最小编排规则。

本文档只回答五件事：

- 这个 skill 接受什么输入
- 运行顺序是什么
- step 之间怎样传对象和状态
- 哪些失败会中断运行，哪些失败只影响局部对象
- 产物如何落盘，如何 replay

本文档只覆盖 `compose-daily-review`，不展开其他 workflow。

## 2. 运行入口

### 2.1 最小输入

`compose-daily-review` skill 最少应接受以下输入：

| 输入项 | 必填 | 说明 |
|---|---|---|
| `digest_candidates_path` | 是 | 上游 `DigestCandidate[]` 路径 |
| `output_root` | 是 | 本次运行输出根目录 |
| `issue_date` | 否 | 日报日期；`NORMAL` 模式可默认取本地运行日，`REPLAY` 模式必须显式传入 |
| `run_id` | 否 | 不传则在运行开始时生成 |
| `preference_signals_path` | 否 | 轻量 rerank 信号路径 |
| `render_template_path` | 否 | 人类可读日报模板路径 |
| `runtime_overrides` | 否 | 栏目阈值、重要性阈值、栏目容量、深挖阈值等覆盖项 |
| `mode` | 否 | `NORMAL` / `REPLAY` |

### 2.2 输出根目录

建议按 run 切目录：

```text
artifacts/compose-daily-review/<run_id>/
|-- daily-review-issues.json
|-- editorial-review.json
|-- daily-review-failures.json
|-- daily-review-report.md
|-- daily-review.md
`-- step-manifest.json
```

当前阶段存储格式固定为：

- `daily-review-issues.json`
- `editorial-review.json`
- `daily-review-failures.json`
- `step-manifest.json`
- `daily-review-report.md`
- `daily-review.md`

当前阶段不使用：

- CSV 作为主产物存储格式
- SQLite 作为 workflow 运行存储

### 2.3 单 run 产物约束

当前阶段固定如下：

- 每个 `run_id` 最多产出 1 个 `DailyReviewIssue`
- `daily-review-issues.json` 采用数组壳，长度只允许为 `0` 或 `1`
- `daily-review.md` 始终尝试写出；空结果时允许写出“今日无正式成稿”的骨架说明

## 3. 运行顺序

### 3.1 固定业务步骤

`compose-daily-review` 的业务执行顺序固定如下：

1. `merge_same_event_candidates`
2. `classify_sections`
3. `identify_top_themes`
4. `score_daily_importance`
5. `detect_deep_dive_topics`
6. `compose_issue_structure`
7. `render_human_readable_issue`

### 3.2 workflow shell 责任

以下行为属于 workflow shell，不属于业务原子能力：

- 输入加载
- `issue_date` 与 `run_id` 解析
- 失败 ledger 聚合
- 产物落盘
- `step-manifest.json` 生成
- `daily-review-report.md` 渲染

### 3.3 数据流

```text
digest-candidates.json
  -> EventBundle[]
  -> DailyReviewEvidence[]
  -> ThemeSignal[]
  -> DailyReviewDraft + EditorialReviewItem[]
  -> DailyReviewIssue

all step errors
  -> DailyReviewFailureRecord[]
  -> daily-review-report.md
```

补充说明：

- `DailyReviewEvidence[]` 是前置证据统一汇总层，不允许旁路生成独立裁决对象
- `render_human_readable_issue` 只消费 `DailyReviewDraft`
- `compose_issue_structure` 是唯一正式写入 `SELECTED` / `OMITTED` / `REVIEW_REQUIRED` 的步骤

## 4. Step 编排规则

### 4.1 `merge_same_event_candidates`

- 输入：`DigestCandidate[]`
- 输出：`EventBundle[]`
- 编排粒度：按候选相似关系分组归并
- 局部失败：单组事件归并异常，只影响当前组
- 中断条件：输入文件不可读或整体解析失败
- 规则约束：低置信度归并只写后续 `review_flags`，不直接进入 review artifact

### 4.2 `classify_sections`

- 输入：`EventBundle[]`
- 输出：初始 `DailyReviewEvidence[]`
- 编排粒度：按事件包独立判断栏目建议
- 局部失败：单事件包分类异常，只记对象级失败并继续
- 规则约束：只能输出固定 6 个 `DailyReviewSection`
- 特殊语义：栏目建议不是最终栏目裁决

### 4.3 `identify_top_themes`

- 输入：`EventBundle[]`
- 输出：`ThemeSignal[]`
- 编排粒度：按事件包集合聚合主题
- 局部失败：单主题归纳异常只记 ledger，不拖垮其他主题
- 特殊语义：主题信号只表达“是否成线”，不直接决定 issue 入选

### 4.4 `score_daily_importance`

- 输入：`DailyReviewEvidence[]`、可选 `ThemeSignal[]`、可选 `PreferenceSignal[]`
- 输出：更新后的 `DailyReviewEvidence[]`
- 编排粒度：按事件包独立评估，再可选做轻量同层排序
- 局部失败：单事件包评分异常，只记对象级失败
- 规则约束：`PreferenceSignal` 只能在同重要性层内影响轻量排序，不得覆盖公共重要性

### 4.5 `detect_deep_dive_topics`

- 输入：`DailyReviewEvidence[]`、`ThemeSignal[]`
- 输出：更新后的 `DailyReviewEvidence[]`
- 编排粒度：按事件包和主题交叉判断
- 局部失败：单事件包深挖判断异常，只记 ledger
- 特殊语义：该 step 只生成“适合深挖”的建议信号，不直接把条目写入 `主题深挖`

### 4.6 `compose_issue_structure`

- 输入：`EventBundle[]`、`ThemeSignal[]`、`DailyReviewEvidence[]`
- 输出：`DailyReviewDraft`、`EditorialReviewItem[]`
- 编排粒度：先按事件包独立裁决，再按固定栏目汇总编排
- 系统级失败：结构装配整体失败或 `DailyReviewDraft` 无法形成
- 特殊语义：这是唯一正式写入 `SELECTED` / `OMITTED` / `REVIEW_REQUIRED` 的步骤
- 空结果语义：若最终没有任何 `SELECTED` 且没有任何 `REVIEW_REQUIRED`，该 step 返回 `SUCCESS_EMPTY`

### 4.7 `render_human_readable_issue`

- 输入：`DailyReviewDraft`
- 输出：`DailyReviewIssue`、`daily-review.md`
- 编排粒度：按当前 run 的唯一 draft 渲染
- 局部失败：Markdown 模板渲染失败可记入 ledger，但只要 `DailyReviewIssue` 仍能形成，workflow 允许降级为 `PARTIAL_SUCCESS`
- 系统级失败：最终 issue 对象无法形成，或主产物无法落盘
- 规则约束：不得再次裁决栏目、入选与 review 状态

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
  主流程完成，主产物已形成，但至少存在一个对象级或渲染级失败
- `FAILED`
  发生系统级失败，导致主产物、failure ledger、step manifest 或关键报告无法形成

### 5.3 成功不要求一定有正式日报

以下情况允许 workflow 最终为 `SUCCEEDED`：

- 输入合法，但所有事件包都被正式 `OMITTED`
- 没有事件包进入 `SELECTED`
- 没有事件包进入 `REVIEW_REQUIRED`
- `daily-review-issues.json` 为空数组，但 `step-manifest.json` 与 `daily-review-report.md` 正常生成

因此：

- `daily-review-issues.json` 可以为空数组
- `editorial-review.json` 可以为空数组
- `daily-review.md` 可以是空骨架说明

## 6. 失败继续策略

### 6.1 默认策略

`compose-daily-review` 默认采用“事件包级隔离，运行级汇总”：

- 单事件包归并异常，不拖垮其他事件包
- 单事件包分类或评分异常，不拖垮其他事件包
- 单主题识别异常，不拖垮其他主题
- Markdown 渲染降级失败，只要结构化 issue 已形成，不拖垮主产物

### 6.2 立即中断条件

发生以下情况时立即中断：

- `run_id` 无法生成
- 输入文件不可读或无法解析
- `REPLAY` 模式缺少 `issue_date`
- 产物目录无法创建
- `daily-review-failures.json` 无法写出
- `step-manifest.json` 无法写出

## 7. 产物写出顺序

建议按以下顺序写出产物：

1. `daily-review-issues.json`
2. `editorial-review.json`
3. `daily-review-failures.json`
4. `step-manifest.json`
5. `daily-review-report.md`
6. `daily-review.md`

原因：

- 先写结构化主产物与 review artifact，确保业务结果先落盘
- 再写 failure ledger 与 manifest，固定运行事实
- 最后写面向人的 Markdown 产物，允许单独降级

## 8. Replay 规则

### 8.1 `REPLAY` 模式目标

`REPLAY` 模式只用于：

- 重跑某个既定 `issue_date`
- 验证结构编排或渲染规则修改
- 比较新旧编排逻辑的差异

### 8.2 `REPLAY` 模式约束

- 必须显式传入 `issue_date`
- 应固定输入 `DigestCandidate[]`
- 不得借 `REPLAY` 模式回头修改上游 `DigestCandidate`
- 如接入 `PreferenceSignal`，应明确使用同轮快照或关闭该输入

## 9. 当前阶段明确不定的内容

本文档当前不固定：

- 并发执行的实现细节
- 模板引擎具体选型
- `runtime_overrides` 的完整配置 schema

这些内容可以后续补充，但不得改变本文档规定的 step 顺序、裁决边界和产物语义。
