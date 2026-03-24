# Reading Funnel Core Spec Review

## 审查对象

- `reading-funnel-core-design-spec.md`
- `reading-funnel-core-goals.md`

## 审查目标

本报告同时承担两类审查：

1. 偏离审查
   - 是否偏离《信息过载时代，我的漏斗式阅读工作流》的核心漏斗思路
   - 是否偏离《Agent-Skill-五种设计模式》的 skill 设计原则
   - 是否偏离 ADP 中关于 `Planning`、`Parallelization`、`Multi-Agent Collaboration`、`Human-in-the-Loop` 的适用边界
   - 是否符合“skill-first + file-based handoff + per-skill scripts”的新约束

2. 工程可实施性审查
   - skill 边界是否清楚
   - 输入输出文件契约是否清楚
   - 失败语义是否足够明确
   - 文档是否足以支撑后续实现计划

## 审查输入

- [信息过载时代，我的漏斗式阅读工作流.md](/E:/File/self/github/openclaw-reading-funnel/%E4%BF%A1%E6%81%AF%E8%BF%87%E8%BD%BD%E6%97%B6%E4%BB%A3%EF%BC%8C%E6%88%91%E7%9A%84%E6%BC%8F%E6%96%97%E5%BC%8F%E9%98%85%E8%AF%BB%E5%B7%A5%E4%BD%9C%E6%B5%81.md)
- [Agent-Skill-五种设计模式.md](/E:/File/self/github/openclaw-reading-funnel/Agent-Skill-%E4%BA%94%E7%A7%8D%E8%AE%BE%E8%AE%A1%E6%A8%A1%E5%BC%8F.md)
- [ADP - Planning](https://adp.xindoo.xyz/original/Chapter%206_%20Planning)
- [ADP - Parallelization](https://adp.xindoo.xyz/original/Chapter%203_%20Parallelization)
- [ADP - Multi-Agent Collaboration](https://adp.xindoo.xyz/original/Chapter%207_%20Multi-Agent%20Collaboration)
- [ADP - Human-in-the-Loop](https://adp.xindoo.xyz/original/Chapter%2013_%20Human-in-the-Loop)

## 最终结论

状态：`PASS`

本次最终版本已经通过两类复审：

- 偏离审查：`PASS`
- 工程可实施性审查：`PASS`

## 审查结果

### 1. 偏离审查

结果：`PASS`

结论：

- 当前版本与《信息过载时代，我的漏斗式阅读工作流》一致：
  - 本阶段被严格限定在漏斗式阅读工作流的上游预处理层
  - 不提前扩展到 Daily Review、沉淀、投递等后续阶段
- 当前版本与《Agent-Skill-五种设计模式》一致：
  - `source-fetch` / `candidate-score` 采用 `Tool Wrapper`
  - `candidate-normalize` / `dedup-cluster` 采用 `Pipeline`
  - `reading-candidate-build` 采用 `Generator`
  - `run-review` 采用 `Reviewer`
- 当前版本与 ADP 中 `Planning`、`Parallelization`、`Multi-Agent Collaboration`、`Human-in-the-Loop` 的适用边界一致：
  - 主流程仍是固定技能链
  - 只在明确独立处保留并行空间
  - 多 agent 仍是后续演进方向
  - 高风险判断仍保留人工复核
- 当前版本与新增约束一致：
  - `skill-first`
  - `file-based handoff`
  - `per-skill scripts`
  - agent 通过上游产物路径编排下游 skill
  - 不把 Python 当共享通用层

### 2. 工程可实施性审查

结果：`PASS`

结论：

- `step-manifest.json` 已是固定契约：
  - 字段、枚举、`input_artifacts[]` / `output_artifacts[]` 结构、以及 agent 的固定判断规则都已明确
- `run-manifest.json` / `artifact_index[]` 已足够固定：
  - run 级字段、状态枚举、`step_results[]`、`artifact_index[]` 结构和 `run_status` 计算规则都已明确
  - 不再与 step-manifest 冲突
- `normalize_status` 语义已一致：
  - 主产物中的 `CandidateItem` 只允许 `NORMALIZED`
  - 失败条目只进入 `normalization-failures.json`
  - 评分阶段不再接触失败条目
- `filter_status` 已固定枚举，`candidate-score -> dedup-cluster` 的机器可读准入规则已闭合
- `json` 与 `md` 的分工清楚：
  - `json` 负责编排和准入
  - `md` 仅供人读，不参与下游判断
- 以当前精度，文档已经足以直接支撑 implementation plan：
  - skill 边界、文件契约、失败产物、准入规则、目录布局和 run/step 两级编排接口都已闭合

### 3. 偏离项列表

无。

### 4. 需要修改的具体段落或决策

无必须修改项。

### 5. 最终说明

当前 spec 与 goals 文档已经完成从 `system-first/module-first` 到 `skill-first` 的重写。

最终可确认的核心结论是：

- 第一等交付单元是 repo-local skills
- skills 通过机器可读 `json` 主产物和 `step-manifest.json` 交接
- 每个 skill 自带脚本，不依赖共享 Python 通用层
- agent 通过上游产物路径编排下游 skill
- `OpenClaw` 仍是后置编排与集成层，不是当前 Phase 1 的业务内核

因此，这份 spec 可以作为下一步 implementation plan 的直接输入。
