# Reading Funnel Core Design Spec

## 1. 项目定位

Reading Funnel Core 当前阶段不是“一个完整系统”，而是一组围绕漏斗式阅读工作流上游阶段构建的 repo-local skills。

这些 skills 的目标是：

- 接入外部来源
- 把原始输入转成结构化候选对象
- 将结果固化为本地产物文件
- 让后续 agent 可以通过产物路径继续编排下游 skill

本项目当前阶段的主叙事固定为：

`SourceAdapter -> RawSourceItem -> CandidateItem -> ReadingCandidate`

但这个模型表达的是 **skill 产物契约**，不是先验数据库中心模型。

## 2. Phase 1 目标与边界

### 2.1 Phase 1 目标

Phase 1 只做上游漏斗预处理，交付的是一组最小可用 skills：

1. 从 `FreshRSS` 真实读取内容
2. 生成本地 `RawSourceItem` 产物
3. 生成本地 `CandidateItem` 产物
4. 生成本地 `ReadingCandidate` 产物
5. 生成 run 级元数据与失败报告

### 2.2 Phase 1 不做什么

Phase 1 明确排除：

- 消息投递
- Daily Review
- Lumina 沉淀
- 用户反馈回流
- 正文抓取
- 以 `OpenClaw` 为核心的业务编排
- 共享 Python 通用库
- 强制全多 Agent 运行时

### 2.3 FreshRSS 的角色

`FreshRSS` 是 Phase 1 的第一个真实来源实现，而不是整个体系的永久中心。

因此，本阶段把 `FreshRSS` 定义为第一个 `SourceAdapter`，而不是唯一入口。后续如果接 GitHub、新闻网站、博客、X、Reddit，也应走新的来源 skill，而不是强行经过 `FreshRSS`。

## 3. Skill-first 架构

### 3.1 Skill 是第一等交付单元

当前阶段的第一等交付单元是 skill，不是共享 Python 库，也不是单体系统模块。

每个 skill 必须自带：

- `SKILL.md`
- 自己的执行脚本
- 明确的输入产物契约
- 明确的输出产物契约
- 明确的失败产物契约

skills 之间默认不共享 Python 通用实现。

### 3.2 技术实现边界

Python 脚本只是某个具体 skill 的执行脚本，服务于该 skill 本身，而不是一个公共运行时层。

这意味着：

- 可以重复实现小段逻辑
- 不优先抽取共享 Python 基础库
- 共享的应当是对象契约和文件格式，而不是代码

### 3.3 Skill 之间如何通信

skill 之间通过本地持久化文件通信。

默认通信方式：

- 上游 skill 产出机器可读 `json` 主产物与 `step-manifest.json`
- agent 在编排时把这些产物路径传给下游 skill
- 下游 skill 只依赖输入文件与契约，不依赖上游 skill 的进程或内存对象
- `md` 仅作为可选的人类可读伴随产物，不参与下游准入

### 3.4 产物文件要求

每个产物文件至少应包含：

- `schema_name`
- `schema_version`
- `generated_at`
- `produced_by_skill`
- `run_id`
- `payload`

如果某个 skill 输出的是目录而不是单文件，该目录也必须至少包含：

- 一个主产物文件
- 一个 step 级 machine-readable manifest

### 3.5 推荐目录布局

当前阶段推荐按 run 和 skill 双层落盘：

```text
runs/
  {run_id}/
    source-fetch/
    candidate-normalize/
    candidate-score/
    dedup-cluster/
    reading-candidate-build/
    run-review/
```

每个 skill 目录至少包含：

- 一个主产物文件
- 一个 `step-manifest.json`
- 可选的人类可读 `md` 报告

### 3.6 通用 JSON 顶层结构

所有机器可读 JSON 产物都必须使用固定顶层结构，不允许只留下裸数组。

#### 集合类主产物

适用于：

- `raw-source-items.json`
- `candidate-items.normalized.json`
- `candidate-items.scored.json`
- `reading-candidates.json`

顶层结构固定为：

- `schema_name`
- `schema_version`
- `generated_at`
- `produced_by_skill`
- `run_id`
- `item_count`
- `items[]`

#### 结果类 manifest / report

适用于：

- `step-manifest.json`
- `source-fetch-report.json`
- `cluster-review.json`
- `run-review.json`

顶层结构固定为：

- `schema_name`
- `schema_version`
- `generated_at`
- `produced_by_skill`
- `run_id`
- `step_name`
- `step_status`
- `continue_recommended`
- `input_artifacts[]`
- `output_artifacts[]`
- `counts`
- `issues[]`
- `payload`

其中：

- `step_status` 固定枚举为：`SUCCEEDED`、`PARTIAL_SUCCESS`、`FAILED`
- `continue_recommended` 固定为布尔值
- `input_artifacts[]` 固定元素结构为：
  - `artifact_name`
  - `path`
  - `schema_name`
  - `schema_version`
  - `required`
- `output_artifacts[]` 固定元素结构为：
  - `artifact_name`
  - `path`
  - `schema_name`
  - `schema_version`
  - `artifact_role`
  - `consumable_by_downstream`
  - `required_for_next`

`artifact_role` 固定枚举为：

- `PRIMARY`
- `AUXILIARY`
- `FAILURE_REPORT`
- `HUMAN_REPORT`

### 3.7 Run Manifest 固定结构

`run-manifest.json` 是 run 级总索引，必须使用固定结构。

顶层字段固定为：

- `schema_name`
- `schema_version`
- `generated_at`
- `produced_by_skill`
- `run_id`
- `run_status`
- `pipeline_version`
- `ruleset_version`
- `source_config_hash`
- `step_results[]`
- `artifact_index[]`
- `counts`
- `issues[]`

其中：

- `run_status` 固定枚举为：`SUCCEEDED`、`PARTIAL_SUCCESS`、`FAILED`
- `step_results[]` 固定元素结构为：
  - `step_name`
  - `step_status`
  - `continue_recommended`
  - `step_manifest_path`
- `artifact_index[]` 固定元素结构为：
  - `artifact_name`
  - `path`
  - `produced_by_skill`
  - `schema_name`
  - `schema_version`
  - `artifact_role`
  - `consumable_by_downstream`
  - `required_for_next`

`run_status` 计算规则固定为：

- 所有必要 step 均为 `SUCCEEDED`，且存在可消费主产物时，`run_status=SUCCEEDED`
- 至少一个 step 为 `PARTIAL_SUCCESS`，且仍存在可消费主产物时，`run_status=PARTIAL_SUCCESS`
- 不存在可消费主产物，或链路在必要 step 上终止时，`run_status=FAILED`

### 3.8 空结果语义

当前阶段禁止用“文件缺失”表达空结果。

统一规则：

- 如果某一步成功执行但没有可产出的业务对象，仍然要产出主 JSON 文件
- 该文件中的 `item_count` 必须为 `0`
- `step-manifest.json` 中必须明确写出 `step_status`
- 是否允许下游继续，由 `continue_recommended` 和准入规则决定

## 4. 核心对象契约

当前阶段保留 4 个核心业务对象，加上 1 个 run 对象。

### 4.1 RawSourceItem

`RawSourceItem` 是来源条目的本地镜像对象。

它用于：

- 保留来源特有字段
- 支撑后续规范化
- 支撑回放与排障

建议字段：

- `raw_item_id`
- `source_adapter_type`
- `source_id`
- `source_name`
- `origin_item_id`
- `title`
- `url`
- `summary`
- `author`
- `published_at`
- `fetched_at`
- `raw_payload`
- `run_id`

### 4.2 CandidateItem

`CandidateItem` 是预处理阶段的最小事实单元。

它代表“一条已经被清洗、标准化、可评分、可比较的候选内容”，但不承载主题级判断。

建议字段：

- `candidate_item_id`
- `origin_raw_item_id`
- `source_adapter_type`
- `source_id`
- `source_name`
- `canonical_url`
- `url_fingerprint`
- `title`
- `normalized_title`
- `summary`
- `published_at`
- `language`
- `normalize_status`
- `freshness_score`
- `quality_score`
- `noise_flags[]`
- `filter_status`
- `dedup_key`
- `run_id`

`normalize_status` 固定枚举为：

- `NORMALIZED`

`filter_status` 固定枚举为：

- `KEPT`
- `FILTERED`

当前阶段固定规则：

- 进入 `candidate-items.normalized.json` 的条目，`normalize_status` 必须恒为 `NORMALIZED`
- 规范化失败条目不进入该主产物，只进入 `normalization-failures.json`

### 4.3 ReadingCandidate

`ReadingCandidate` 是聚合后的待后续处理对象。

它承接多个 `CandidateItem`，但不是最终编辑产物，不负责生成 `why_it_matters_today`、日报栏目、投递 payload 等后置字段。

建议字段：

- `reading_candidate_id`
- `candidate_item_ids[]`
- `primary_candidate_item_id`
- `cluster_type`
- `cluster_confidence`
- `canonical_url`
- `display_title`
- `display_summary`
- `source_count`
- `published_at_range`
- `aggregate_score`
- `merge_reason`
- `needs_review`
- `run_id`

### 4.4 PipelineRun

`PipelineRun` 用于描述一次完整技能编排运行。

建议字段：

- `run_id`
- `pipeline_version`
- `ruleset_version`
- `source_config_hash`
- `started_at`
- `finished_at`
- `source_window`
- `status`
- `artifact_index`

其中：

- `status` 固定枚举为：`SUCCEEDED`、`PARTIAL_SUCCESS`、`FAILED`
- `artifact_index` 的结构必须与 `run-manifest.json` 中的 `artifact_index[]` 保持一致

### 4.5 身份与快照规则

当前阶段采用“两层身份”：

- 逻辑身份：跨 run 稳定，用于去重和重放判断
- 运行快照：以 `run_id` 为边界，用于保留每次技能编排运行的输入、输出和失败现场

固定规则如下：

- `run_id`：每次完整运行唯一生成一次
- `raw_item_id`：来源条目的逻辑身份，跨 run 稳定
- `candidate_item_id`：由 `raw_item_id` 派生，跨 run 稳定
- `reading_candidate_id`：run 级聚类快照身份，不要求跨 run 稳定

当前阶段的“可重放”含义是：

- 给定一个历史 `run_id` 的原始产物目录，可以不重新访问在线来源，重新执行后续 skills
- 重放绑定原始 run 记录的 `pipeline_version`、`ruleset_version` 和 `source_config_hash`

## 5. Skill 清单与职责

当前阶段的每个 skill 都必须同时产出：

- 主业务产物
- 至少一个机器可读的 `step-manifest.json`
- 如有需要，再附加 Markdown 报告供人阅读

agent 编排时以 `step-manifest.json` 为首要准入依据，不解析 Markdown。

### 5.1 `source-fetch`

模式：`Tool Wrapper`

职责：

- 调用 `FreshRSS`
- 读取指定时间窗内容
- 产出 `RawSourceItem` 文件
- 产出来源级抓取结果文件

输入：

- 配置文件
- 时间窗参数

输出：

- `raw-source-items.json`
- `source-fetch-report.json`
- `step-manifest.json`

准入规则：

- 这是首个 skill，不依赖上游 manifest
- 如果至少有一个来源成功拉取，`continue_recommended=true`
- 如果所有来源均失败，`continue_recommended=false`
- 部分失败允许继续，但必须在 `source-fetch-report.json` 与 `step-manifest.json` 中显式标出

### 5.2 `candidate-normalize`

模式：`Pipeline`

职责：

- 读取 `RawSourceItem`
- 生成 `CandidateItem`
- 记录规范化失败

输入：

- `raw-source-items.json`

输出：

- `candidate-items.normalized.json`
- `normalization-failures.json`
- `step-manifest.json`

准入规则：

- 只接受 `source-fetch/step-manifest.json`
- 仅当 `source-fetch` 的 `continue_recommended=true` 且 `raw-source-items.json` 存在时继续
- 规范化失败的条目写入 `normalization-failures.json`
- 成功规范化的条目进入主产物，失败条目不得进入主产物

### 5.3 `candidate-score`

模式：`Tool Wrapper`

职责：

- 读取规范化后的 `CandidateItem`
- 写入质量、新鲜度和噪音评分
- 写入过滤结果

输入：

- `candidate-items.normalized.json`

输出：

- `candidate-items.scored.json`
- `step-manifest.json`

准入规则：

- 只接受 `candidate-normalize/step-manifest.json`
- 处理 `candidate-items.normalized.json` 中的全部条目
- 由于规范化失败条目不会进入主产物，因此评分阶段不再接触失败条目

### 5.4 `dedup-cluster`

模式：`Pipeline`

职责：

- 读取评分后的 `CandidateItem`
- 先做精确去重
- 再做轻量相似聚类
- 标记 `needs_review`

输入：

- `candidate-items.scored.json`

输出：

- `cluster-plan.json`
- `cluster-review.json`
- `cluster-review-report.md`
- `step-manifest.json`

准入规则：

- 只接受 `candidate-score/step-manifest.json`
- 仅处理 `filter_status=KEPT` 的条目
- `filter_status!=KEPT` 的条目不得进入聚类
- 低置信度 cluster 仍可进入 `cluster-plan.json`，但必须在 `cluster-review.json` 与 `cluster-review-report.md` 中标记 `needs_review`

### 5.5 `reading-candidate-build`

模式：`Generator`

职责：

- 读取聚类方案
- 生成确定性的 `ReadingCandidate`

输入：

- `cluster-plan.json`
- `candidate-items.scored.json`

输出：

- `reading-candidates.json`
- `step-manifest.json`

准入规则：

- 只接受 `dedup-cluster/step-manifest.json`
- 可以消费 `needs_review=true` 的 cluster
- 但这类 cluster 生成的 `ReadingCandidate` 必须保留 `needs_review=true`
- 如果 `cluster-plan.json` 为空，也必须产出空的 `reading-candidates.json`

### 5.6 `run-review`

模式：`Reviewer`

职责：

- 汇总 run 级结果
- 产出运行报告
- 显式列出失败、过滤和低置信度对象

输入：

- 全部上游产物路径

输出：

- `run-manifest.json`
- `run-review.json`
- `run-report.md`

准入规则：

- 只要存在任一上游 `step-manifest.json`，就应运行
- 它不决定中间步骤是否继续，只负责最终汇总
- 它产出的 `run-manifest.json` 是 run 级总索引，不替代各步的 `step-manifest.json`

## 6. 失败语义与可见性

当前阶段必须遵守“失败可见，不静默跳过”的原则。

### 6.1 失败必须作为产物落地

失败不能只存在于日志或进程退出码里。

至少要落成文件的失败包括：

- 来源级抓取失败
- 规范化失败
- 聚类低置信度

### 6.2 失败产物

失败产物固定为：

- `source-fetch-report.json`
- `normalization-failures.json`
- `cluster-review.json`
- `cluster-review-report.md`
- `run-review.json`
- `run-report.md`

### 6.3 下游可见性

默认下游读取：

- 成功产物
- 带 `needs_review` 标记的部分成功产物

下游不默认读取：

- 缺少上游主产物的失败 run

agent 编排时必须以当前上游 skill 的 `step-manifest.json` 作为直接准入依据。

`run-manifest.json` 只负责：

- 汇总本次 run 的所有产物索引
- 给后续人工复盘或更高层编排器做 run 级浏览
- 标记哪些产物可被继续消费

它不负责替代中间技能之间的逐步准入判断。

### 6.4 机器可读与人类可读的分工

当前阶段的规则是：

- `json` 负责 agent 编排、准入判断和自动消费
- `md` 负责人类阅读、审计和解释

因此：

- `cluster-review-report.md` 不能单独承担准入判断
- `run-report.md` 不能单独承担准入判断
- 所有与继续/停止决策相关的信息，都必须同时存在于对应的 `json` manifest/report 中

### 6.5 Step 准入的固定判断字段

agent 不得自行发明准入逻辑。

每一步是否继续，固定只看上游 `step-manifest.json` 中这 4 个字段：

- `step_status`
- `continue_recommended`
- `output_artifacts[]`
- `issues[]`

固定判断规则：

- 若 `continue_recommended=false`，默认停止
- 若缺少 `artifact_role=PRIMARY` 且 `consumable_by_downstream=true` 的输出，默认停止
- 若存在 `artifact_role=FAILURE_REPORT`，记录但不必然停止
- 是否继续到下一步，以该下一步自己的准入规则为最终判定

## 7. Agent 编排方式

### 7.1 先 skill，后 agent

当前阶段不先做“一个系统再拆 agent”，而是先做 skills，再让 agent 组合这些 skills。

### 7.2 Agent 如何调用

agent 编排时只需要：

1. 调用上游 skill
2. 拿到上游产物路径
3. 把产物路径传给下游 skill
4. 根据上游 `step-manifest.json` 判断是否继续

每个 step manifest 至少要告诉 agent：

- 本步是否执行成功
- 是否建议继续
- 哪些输出文件是下游允许消费的主产物
- 哪些问题只需人工关注，不阻断链路

### 7.3 多 Agent 演进策略

当前阶段不强制一开始就做成全多 Agent 运行时。

原因有两点：

1. 当前 Phase 1 的主流程是已知的固定技能链，更适合先保证稳定性
2. 过早引入多 Agent 调度、通信和一致性语义，会放大复杂度

当前阶段的正确做法是：

- 先按 skill 边界落能力
- 再用一个 agent 或多个 agent 组合这些 skills
- 等到确实存在职责隔离、工具隔离或并行收益时，再拆成独立 agent

未来自然演进方向：

- `Ingest Agent`：编排 `source-fetch`
- `Normalize Agent`：编排 `candidate-normalize` 与 `candidate-score`
- `Cluster Agent`：编排 `dedup-cluster` 与 `reading-candidate-build`
- `Audit Agent`：编排 `run-review`

## 8. OpenClaw 边界

`OpenClaw` 不是当前 Phase 1 的业务中心。

它在后续阶段的定位是：

- 消费本地产物
- 编排 skills
- 把上游产物路径传给下游 skill
- 负责后续投递与外部工作流集成

它不应在当前阶段承担：

- 主业务对象定义
- 共享 Python 通用运行时
- 候选内容的事实判定
- 聚类和装配的业务真相

## 9. 文档层验收标准

本设计成立时，应满足：

- 不再使用旧 `StoryPack/OpenClaw-first` 叙事作为当前 Phase 1 核心
- 明确采用 `SourceAdapter -> RawSourceItem -> CandidateItem -> ReadingCandidate`
- `FreshRSS` 被表述为第一个 adapter，而不是永久中心
- 第一等交付单元明确为 skills，而不是单体系统模块
- skill 之间通过本地持久化文件通信
- 每个 skill 都产出 machine-readable `step-manifest.json`
- agent 编排通过产物路径串联 skills
- agent 不需要解析 Markdown 就能完成继续/停止判断
- `OpenClaw` 被表述为后置 skill 编排层，而不是当前业务内核
