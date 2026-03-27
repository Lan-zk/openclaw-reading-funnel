# `digest-candidates` 编排规则

## 1. 文档目的

本文档定义 `digest-candidates` 作为顶层 workflow skill 运行时的最小编排规则。

本文档只回答五件事：

- 这个 skill 接受什么输入
- 运行顺序是什么
- step 之间怎样传对象和状态
- 哪些失败会中断运行，哪些失败只影响局部对象
- 产物如何落盘，如何 replay

本文档只覆盖 `digest-candidates`，不展开其他 workflow。

## 2. 运行入口

### 2.1 最小输入

`digest-candidates` skill 最少应接受以下输入：

| 输入项 | 必填 | 说明 |
|---|---|---|
| `normalized_candidates_path` | 是 | 上游 `NormalizedCandidate[]` 路径 |
| `output_root` | 是 | 本次运行输出根目录 |
| `run_id` | 否 | 不传则在运行开始时生成 |
| `preference_signals_path` | 否 | 轻量 rerank 信号路径 |
| `runtime_overrides` | 否 | 阈值、来源过滤、并发、抽取策略等覆盖项 |
| `mode` | 否 | `NORMAL` / `REPLAY` |

### 2.2 输出根目录

建议按 run 切目录：

```text
artifacts/digest-candidates/<run_id>/
|-- digest-candidates.json
|-- digest-review.json
|-- digest-failures.json
|-- digest-report.md
`-- step-manifest.json
```

当前阶段存储格式固定为：

- `digest-candidates.json`
- `digest-review.json`
- `digest-failures.json`
- `step-manifest.json`
- `digest-report.md`

当前阶段不使用：

- CSV 作为主产物存储格式
- SQLite 作为 workflow 运行存储

## 3. 运行顺序

### 3.1 固定业务步骤

`digest-candidates` 的业务执行顺序固定如下：

1. `canonicalize_url`
2. `exact_dedup`
3. `near_duplicate_cluster`
4. `extract_main_content`
5. `clean_content`
6. `check_quality`
7. `filter_noise`
8. `generate_summary`
9. `compute_digest_score`
10. `assemble_digest_candidates`

### 3.2 workflow shell 责任

以下行为属于 workflow shell，不属于业务原子能力：

- 输入加载
- 失败 ledger 聚合
- 产物落盘
- `step-manifest.json` 生成
- `digest-report.md` 渲染

### 3.3 数据流

```text
normalized-candidates.json
  -> CanonicalCandidate[]
  -> ExactDedupResult[]
  -> CandidateCluster[]
  -> ExtractedContent[]
  -> DigestEvidence[]
  -> DigestCandidate[] + DigestReviewItem[]

all step errors
  -> DigestFailureRecord[]
  -> digest-report.md
```

补充说明：

- `near_duplicate_cluster` 如果需要标题、发布时间、来源等元信息，应通过 `survivor_candidate_id` 回查 `CanonicalCandidate`
- `DigestEvidence[]` 是前置证据统一汇总层，不允许再旁路生成独立裁决对象

## 4. Step 编排规则

### 4.1 `canonicalize_url`

- 输入：`NormalizedCandidate[]`
- 输出：`CanonicalCandidate[]`
- 编排粒度：按候选独立执行
- 局部失败：单候选 URL 非法或规范化异常，记对象级失败并继续
- 中断条件：输入文件不可读或整体解析失败

### 4.2 `exact_dedup`

- 输入：`CanonicalCandidate[]`
- 输出：`ExactDedupResult[]`
- 编排粒度：按高确定性重复键分组
- 局部失败：单组重复键异常，只影响当前组
- 规则约束：无法稳定判定时不误删，交给后续聚类

### 4.3 `near_duplicate_cluster`

- 输入：`ExactDedupResult[]` 与所需 `CanonicalCandidate` 元信息
- 输出：`CandidateCluster[]`
- 编排粒度：按候选 survivor 集合聚类
- 局部失败：局部聚类异常只记 ledger，不拖垮其他簇
- 特殊语义：低置信度聚类不直接生成 review 对象，只写证据

### 4.4 `extract_main_content`

- 输入：`CandidateCluster[]`
- 输出：`ExtractedContent[]`
- 编排粒度：按 `primary_candidate_id` 独立抽取
- 局部失败：单候选抽取失败，只记对象级失败
- 特殊语义：只允许对主候选抽取，不按整簇合并正文

### 4.5 `clean_content`

- 输入：`ExtractedContent[]`
- 输出：更新后的 `ExtractedContent[]`
- 编排粒度：按正文对象独立清洗
- 局部失败：清洗失败但原始正文仍可用时，降级保留 `raw_content`
- 系统级失败：清洗模块无法初始化或整体规则执行失败

### 4.6 `check_quality`

- 输入：`ExtractedContent[]` 与候选元信息
- 输出：更新后的 `DigestEvidence[]`
- 编排粒度：按簇主候选独立评估
- 局部失败：单对象质量规则异常，只记该对象失败
- 特殊语义：低质量是业务证据，不是失败

### 4.7 `filter_noise`

- 输入：`DigestEvidence[]`、`ExtractedContent[]`、候选元信息
- 输出：更新后的 `DigestEvidence[]`
- 编排粒度：按候选簇独立评估
- 局部失败：单对象噪音规则异常，只记该对象失败
- 特殊语义：本 step 只生成噪音证据，不直接写 `FILTERED`

### 4.8 `generate_summary`

- 输入：`DigestEvidence[]`、`ExtractedContent[]`
- 输出：更新后的 `DigestEvidence[]`
- 编排粒度：按候选簇独立生成
- 局部失败：摘要不可用但对象仍可能保留时，记 `review_flags`
- 系统级失败：摘要服务整体不可用且无法降级

### 4.9 `compute_digest_score`

- 输入：`DigestEvidence[]`、时效性、来源特征、可选 `PreferenceSignal[]`
- 输出：更新后的 `DigestEvidence[]`
- 编排粒度：按候选簇独立计算
- 局部失败：单对象打分异常，只记该对象失败
- 规则约束：`PreferenceSignal` 只影响 `rerank_score`

### 4.10 `assemble_digest_candidates`

- 输入：`CandidateCluster[]`、`DigestEvidence[]`
- 输出：`DigestCandidate[]`、`DigestReviewItem[]`
- 编排粒度：按候选簇独立裁决，再做全局排序与汇总
- 系统级失败：装配逻辑整体失败或主产物无法形成
- 特殊语义：这是唯一正式写入 `KEPT` / `FILTERED` / `NEEDS_REVIEW` 的步骤

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
  主流程完成，但至少存在一个候选、簇或对象级失败
- `FAILED`
  发生系统级失败，导致主产物、failure ledger 或 step manifest 无法形成

### 5.3 成功不要求一定有 `KEPT` 候选

以下情况允许 workflow 最终为 `SUCCEEDED`：

- 输入为空，但调用方明确允许空运行
- 所有候选都被明确过滤
- 没有候选进入 `KEPT` 或 `NEEDS_REVIEW`
- 有 `NEEDS_REVIEW` 但没有 `KEPT`

因此：

- `digest-candidates.json` 可以为空数组
- `digest-review.json` 可以为空数组
- 只要 `step-manifest.json` 和 `digest-report.md` 成功生成，运行仍可视为成功

## 6. 失败继续策略

### 6.1 默认策略

`digest-candidates` 默认采用“候选簇级隔离，运行级汇总”：

- 单候选 URL 异常，不拖垮其他候选
- 单簇聚类或抽取失败，不拖垮其他簇
- 单对象摘要或评分失败，不拖垮其他对象

### 6.2 立即中断条件

发生以下情况时立即中断：

- `run_id` 无法生成
- 输入文件不可读或无法解析
- 产物目录无法创建
- `digest-failures.json` 无法写出
- `step-manifest.json` 无法写出

## 7. 产物写出顺序

建议按以下顺序写出产物：

1. `digest-candidates.json`
2. `digest-review.json`
3. `digest-failures.json`
4. `step-manifest.json`
5. `digest-report.md`

原因：

- 先写主事实对象
- 再写 review 池
- 再写失败账本
- 最后写汇总与人类可读报告

## 8. Replay 规则

### 8.1 支持两类 replay

- `INPUT_REPLAY`
  基于既有 `normalized-candidates.json` 重新运行本 workflow
- `ARTIFACT_REPLAY`
  不重跑正文抽取与评分，只基于既有中间或最终产物重新生成 manifest / report

### 8.2 Replay 最小要求

要支持 replay，至少保留：

- `run_id`
- 输入 `normalized-candidates.json`
- `step-manifest.json`
- `digest-failures.json`
- 本轮使用的 runtime overrides 或其哈希

### 8.3 Replay 不做的事

- 不要求 replay 得到完全相同的正文抽取结果
- 不要求 replay 自动修复失败候选
- 不允许 replay 篡改原始失败账本

## 9. 与上下游 workflow 的边界

`digest-candidates` 对下游只暴露三类信息：

- `DigestCandidate[]`
- `DigestReviewItem[]`
- `DigestStepManifest`

它不负责：

- 直接触发 `compose-daily-review`
- 替下游做栏目编排
- 替下游做长期价值判断

上游只允许向它提供：

- `NormalizedCandidate[]`
- 可选 `PreferenceSignal[]`

它不能回头要求 `ingest-normalize` 做正文抽取或聚类。

## 10. 当前阶段明确不定的内容

本文档当前不固定：

- 具体并发模型
- 具体正文抽取后端选择
- 具体限流和缓存策略
- artifact replay 可复用到哪一层中间对象

这些细节可以在不破坏本编排规则的前提下后续补充。
