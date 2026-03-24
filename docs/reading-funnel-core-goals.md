# Reading Funnel Core Goals

## 我们要做什么

我们要做的不是一个完整的信息系统，而是一组可以被 agent 编排调用的 skills。

这些 skills 共同服务于“漏斗式阅读工作流”的上游阶段：把杂乱、重复、质量参差不齐的外部信息，稳定转化为后续流程可以继续处理的结构化候选对象。

这个项目当前阶段的核心产物不是日报、消息推送或知识卡片，而是：

- 一组职责明确的 repo-local skills
- 每个 skill 自带的执行脚本
- 每个 skill 产出的本地持久化文件

最终保留下来的业务对象仍然是两层中间对象：

- `CandidateItem`：单条、规范化、可评分、可追踪的候选内容
- `ReadingCandidate`：由多条候选内容去重、聚合后形成的待后续处理对象

## 我们为什么做

信息过载的主要问题不是信息不够，而是判断成本太高。

每天进入视野的信息太多，来源太杂，质量差异大，重复内容多。人在真正开始精读之前，已经把大量注意力消耗在这些无效判断上：

- 这条内容值不值得点开
- 这是不是另一条内容的重复版本
- 这条信息是否噪音过大
- 这条内容是否值得进入后续处理流程

Reading Funnel Core 要解决的是这个上游问题：先把输入整理干净，再把值得继续处理的内容稳定留下来。

## 我们当前阶段要实现什么

Phase 1 只做漏斗上游预处理，不做后续编辑和投递。

当前阶段要实现的是一组最小可用的 skills，它们通过本地持久化文件串联，完成：

1. 从 `FreshRSS` 真实接入内容
2. 生成来源原始产物文件
3. 生成 `CandidateItem` 产物文件
4. 生成 `ReadingCandidate` 产物文件
5. 生成 run 级元数据和失败报告文件

当前阶段明确不做：

- 消息投递
- Daily Review
- Lumina 沉淀
- 用户反馈回流
- 正文抓取
- 以 OpenClaw 为核心的业务编排
- 共享 Python 通用库

当前阶段的工程约束固定为：

- `FreshRSS` 只是第一个 `SourceAdapter`
- 每个 skill 自带自己的 Python 脚本
- skill 之间通过机器可读 `json` 主产物和 `step-manifest.json` 通信
- agent 编排时通过把上游产物路径传给下游 skill 来完成串联
- 每个 skill 都必须输出机器可读的 step manifest，agent 不需要解析 Markdown 就能判断是否继续
- `md` 只作为可选的人类可读伴随产物，不参与下游准入
- 可以有一份固定 schema 文档，也允许在每份产物中冗余记录 schema/version/meta

## 设计原则

### 先做 skill，再做 agent 组合

当前阶段的第一等交付单元是 skill，不是系统模块，更不是共享运行时。

### 先做文件产物，再做复杂状态系统

skills 之间共享的是产物文件和对象契约，不共享 Python 库代码。

### 先做本地可验证链路，不提前做终局产品

当前阶段的目标不是生成最终内容，而是为后续精选、人工判断、沉淀和投递准备稳定输入。

### 先定义编排接口，再接 OpenClaw

`OpenClaw` 在后续阶段只负责调用 skills，并把上游产物路径传给下游 skill。它不是当前 Phase 1 的业务中心。

## 当前阶段完成标志

当下面几件事都成立时，Phase 1 的目标才算达成：

- 存在一组职责清晰的 repo-local skills
- 每个 skill 都有自己的脚本和输入/输出契约
- 每个 skill 都有自己的机器可读 manifest 与准入规则
- 系统能从 `FreshRSS` 拉到真实数据
- skills 能产出 `CandidateItem`
- skills 能产出 `ReadingCandidate`
- 上游 skill 的产物路径可以被下游 skill 继续消费
- agent 可以只依据 `json` 产物与 manifest 完成继续/停止判断
- 失败、过滤和低置信度情况是可见的
- 本地产物可以被后续 agent 编排使用
