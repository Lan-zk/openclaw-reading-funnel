# `ingest-normalize` 编排规则

## 1. 文档目的

本文档定义 `ingest-normalize` 作为顶层 workflow skill 运行时的最小编排规则。

本文档只回答五件事：

- 这个 skill 接受什么输入
- 运行顺序是什么
- step 之间怎样传对象和状态
- 哪些失败会中断运行，哪些失败只影响局部来源
- 产物如何落盘，如何 replay

本文档只覆盖 `ingest-normalize`，不展开其他 workflow。

## 2. 运行入口

### 2.1 最小输入

`ingest-normalize` skill 最少应接受以下输入：

| 输入项 | 必填 | 说明 |
|---|---|---|
| `source_config_path` | 是 | 来源配置文件路径 |
| `output_root` | 是 | 本次运行输出根目录 |
| `run_id` | 否 | 不传则在运行开始时生成 |
| `runtime_overrides` | 否 | 时间窗、来源过滤、限流等覆盖项 |
| `mode` | 否 | `NORMAL` / `REPLAY` / `BACKFILL` |

### 2.2 输出根目录

建议按 run 切目录：

```text
artifacts/ingest-normalize/<run_id>/
|-- normalized-candidates.json
|-- source-entries.json
|-- ingest-failures.json
|-- ingest-report.json
`-- step-manifest.json
```

## 3. 运行顺序

### 3.1 固定步骤

`ingest-normalize` 的执行顺序固定如下：

1. `discover_sources`
2. `sync_source_window`
3. `fetch_source_items`
4. `convert_to_feed`
5. `map_source_fields`
6. `persist_source_entries`
7. `normalize_candidates`
8. `record_ingest_failures`

### 3.2 数据流

```text
source_config
  -> SourceDescriptor[]
  -> SourceSyncPlan[]
  -> FetchedSourceBatch[]
  -> RawFeedItem[]
  -> SourceEntryDraft[]
  -> SourceEntry[]
  -> NormalizedCandidate[]

all step errors
  -> IngestFailureRecord[]
  -> ingest-report.json
```

## 4. Step 编排规则

### 4.1 `discover_sources`

- 输入：`source_config_path`、`runtime_overrides`
- 输出：`SourceDescriptor[]`
- 中断条件：所有来源都不可执行
- 局部失败：单来源配置非法，只记 ledger，继续处理其他来源

### 4.2 `sync_source_window`

- 输入：`SourceDescriptor[]`
- 输出：`SourceSyncPlan[]`
- 中断条件：无
- 局部失败：单来源计划生成失败，只影响该来源

### 4.3 `fetch_source_items`

- 输入：`SourceDescriptor[]` + `SourceSyncPlan[]`
- 输出：`FetchedSourceBatch[]`
- 编排粒度：按来源独立执行
- 局部失败：认证、超时、分页失败，只记该来源失败
- 空结果：来源窗口内无新内容时，生成 `SUCCESS_EMPTY` 批次摘要

### 4.4 `convert_to_feed`

- 输入：`FetchedSourceBatch[]`
- 输出：`RawFeedItem[]`
- 编排粒度：按批次独立转换
- 局部失败：当前批次转换失败，不回写成抓取失败

### 4.5 `map_source_fields`

- 输入：`RawFeedItem[]`
- 输出：`SourceEntryDraft[]`
- 编排粒度：按条目独立映射
- 局部失败：单条字段非法，只丢当前条目并记失败

### 4.6 `persist_source_entries`

- 输入：`SourceEntryDraft[]`
- 输出：`SourceEntry[]`
- 编排粒度：按条目或按批次写入，具体实现可选
- 系统级失败：输出目录不可写、序列化失败、存储不可达

### 4.7 `normalize_candidates`

- 输入：`SourceEntry[]`
- 输出：`NormalizedCandidate[]`
- 编排粒度：按 `SourceEntry` 独立归一
- 局部失败：单条归一化失败，只记对象级失败

### 4.8 `record_ingest_failures`

- 输入：本轮所有失败事件
- 输出：`ingest-failures.json`、`ingest-report.json`
- 系统级失败：ledger 无法写出时，整个 workflow 视为 `FAILED`

## 5. Step 状态规则

### 5.1 step 状态枚举

每个 step 只允许三种状态：

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
  所有 step 均成功，允许某些 step 为 `SUCCESS_EMPTY`
- `PARTIAL_SUCCESS`
  workflow 主流程完成，但至少存在一个来源、批次、条目或对象级失败
- `FAILED`
  发生系统级失败，导致主产物或 failure ledger 无法形成

### 5.3 成功不要求一定有候选输出

以下情况允许 workflow 最终为 `SUCCEEDED`：

- 来源全部正常，但窗口内没有新内容
- 仅抓到空批次，没有 `NormalizedCandidate`
- 来源配置筛选后，本轮没有启用来源，但这是调用方明确指定的结果

因此：

- `normalized-candidates.json` 可以是空数组
- 只要 `step-manifest.json` 和 `ingest-report.json` 成功生成，运行仍然可视为成功

## 6. 失败继续策略

### 6.1 默认策略

`ingest-normalize` 默认采用“来源级隔离，运行级汇总”：

- 单来源失败，不拖垮其他来源
- 单批次失败，不拖垮其他批次
- 单条目失败，不拖垮其他条目

### 6.2 立即中断条件

发生以下情况时立即中断：

- `run_id` 无法生成
- 产物目录无法创建
- `ingest-failures.json` 无法写出
- `step-manifest.json` 无法写出

## 7. 产物写出顺序

建议按以下顺序写出产物：

1. `source-entries.json`
2. `normalized-candidates.json`
3. `ingest-failures.json`
4. `step-manifest.json`
5. `ingest-report.json`

原因：

- 先写主事实对象
- 再写失败账本
- 最后写投影和汇总

## 8. Replay 规则

### 8.1 支持两类 replay

- `WINDOW_REPLAY`
  按既有 `since` / `until` / `cursor` 重新执行来源抓取
- `ARTIFACT_REPLAY`
  不重新抓网络，只基于已落盘的中间或最终产物重新生成报告

### 8.2 Replay 最小要求

要支持 replay，至少保留：

- `run_id`
- `source_config_path` 或配置哈希
- 每个来源的 `SourceSyncPlan`
- `step-manifest.json`
- `ingest-failures.json`

### 8.3 Replay 不做的事

- 不要求 replay 得到完全相同的外部抓取结果
- 不要求 replay 自动修复失败来源
- 不允许 replay 篡改原始失败账本

## 9. 与下游 workflow 的边界

`ingest-normalize` 对下游只暴露三类信息：

- `NormalizedCandidate[]`
- `IngestStepManifest`
- `IngestReport`

它不负责：

- 触发 `digest-candidates`
- 替下游做去重、摘要或排序判断
- 替下游解释失败原因

如果后续需要事件触发下游，应由顶层 orchestrator 根据 `step-manifest.json` 决定，而不是由该 skill 自己决定。

## 10. 当前阶段明确不定的内容

本文档当前不固定：

- 具体并发模型
- 具体限流算法
- 具体文件命名中的时间戳格式
- 是否在本 workflow 内持久化游标状态

这些细节可以在不破坏本编排规则的前提下后续补充。
