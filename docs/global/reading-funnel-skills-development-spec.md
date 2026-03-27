# 漏斗式阅读工作流 Skills 开发 Spec

## 1. 文档目的

本文档把 `./skills-design` 目录中的研究、设计说明、设计规范和架构说明，收敛成当前仓库可直接执行的 skills 开发规范。

它只回答五件事：

- 这个项目后续的 skill 应该按什么边界设计
- skill 在仓库中应该如何组织
- `SKILL.md`、`scripts/`、`references/`、`data/`、`evals/` 分别承担什么职责
- 一个新 skill 从设计到实现应该按什么顺序落地
- 什么状态才算“一个 workflow skill 已经开发完成”

本文档是项目内规范，不是通用平台规范。

## 2. 适用范围

本 spec 适用于当前仓库 `skills/` 目录下所有后续新增或重构的 workflow skill。

当前固定的顶层 workflow skill 为：

1. `ingest-normalize`
2. `digest-candidates`
3. `compose-daily-review`
4. `curate-retain`
5. `generate-long-cycle-assets`

约束如下：

- 顶层只按业务 workflow 暴露，不按原子能力暴露
- 一个 skill 只服务一个主要用户任务
- skill 是工作流外壳，不是知识堆积点
- 详细规则先落文档，再写脚本与运行入口
- 评估、失败语义、空结果语义必须从第一天开始定义

## 3. 规范优先级

当不同文档之间出现冲突时，按下面顺序决策：

1. `docs/global/reading-funnel-global-implementation-guide.md`
2. 本文档
3. 对应 workflow 目录下的原子能力设计文档
4. 对应 workflow 的对象契约、编排规则、评估规则文档
5. skill 目录下的 `references/design-authority.md`
6. `SKILL.md`
7. 具体脚本实现

含义很明确：

- 全局文档决定顶层 workflow 边界
- 本文档决定 skill 开发方式
- workflow 文档决定该 skill 的业务真相
- `SKILL.md` 和代码只能实现这些规则，不能反向发明新边界

## 4. 顶层设计原则

### 4.1 顶层按 workflow 切，不按原子能力切

后续不得把以下能力直接做成顶层 skill：

- `dedup`
- `summary`
- `ranking`
- `topic-tagging`
- `knowledge-store`
- `feedback-rerank`

这些都属于 workflow 内部能力，应该下沉到：

- `scripts/`
- `references/`
- `data/`
- `templates/`

### 4.2 一个 skill 只拥有一个统一用户任务

允许一个 skill 内部有多个子步骤，但它们必须同时满足：

- 服务于同一个用户任务
- 共享同一条主工作流
- 共享同一家族输出物
- 共享同一套成功标准

如果不能同时满足这四点，就不应该继续塞进同一个 skill。

### 4.3 顶层 skill 数量保持稳定

这个项目已经固定为 5 个顶层 workflow。后续原则上不新增第 6 个顶层 skill。

只有同时满足下面四项，才允许讨论拆出新的顶层 skill：

1. 触发语言明显不同
2. 主工作流明显不同
3. 主输出物明显不同
4. 评估标准明显不同

如果只是：

- 数据变多
- adapter 变多
- 模板变多
- 脚本变多
- 规则变细

都不构成新建顶层 skill 的理由。

## 5. 仓库组织规范

每个 workflow skill 默认采用下面结构：

```text
skills/<skill-name>/
|-- SKILL.md
|-- run.py
|-- agents/
|   `-- openai.yaml
|-- references/
|   `-- design-authority.md
|-- scripts/
|   `-- <skill_package>/
|-- templates/               # 可选
|-- assets/                  # 可选
|-- data/                    # 可选
`-- evals/                   # 强烈推荐
```

补充规则：

- `skills/` 只放顶层 workflow skill
- `run.py` 负责 workflow 入口，不承载大段业务逻辑
- 真正实现放在 `scripts/<skill_package>/`
- `agents/openai.yaml` 负责 UI 展示元数据
- `references/design-authority.md` 必须回指项目文档，而不是重复业务规则
- 公共 schema、全局规则、跨 workflow 编排，不放进单个 skill 私有目录

## 6. `SKILL.md` 规范

### 6.1 角色定义

`SKILL.md` 是工作流入口说明，不是设计总文档，不是 README，不是知识库。

它只负责五件事：

- 说明这个 skill 做什么
- 说明什么时候该用
- 说明什么时候不该用
- 说明输出什么产物
- 指向运行入口和详细资源

### 6.2 frontmatter 规则

当前项目默认只要求两个字段：

- `name`
- `description`

规则如下：

- `name` 使用小写加连字符
- `description` 必须同时描述“做什么”和“什么时候触发”
- 不把触发规则藏在正文里
- 不使用空泛描述，如“处理数据”“帮助文档工作”

### 6.3 正文推荐结构

每个 `SKILL.md` 默认按下面结构写：

1. skill 名称
2. 简短定义
3. Use it when
4. Do not use it when
5. Outputs
6. Runtime entry
7. Implementation
8. Reference
9. Static sample data（如有）

项目内要求：

- 正文保持精简
- 不复制 workflow 细则
- 不写大段业务背景
- 不在这里维护 schema 真相

### 6.4 description 写法

description 应遵循这个句型：

> 完成什么工作流、产出什么主结果；当用户提出哪些意图或动作时使用。

例如：

> Ingest configured content sources, normalize them into source entries and normalized candidates, and emit JSON artifacts; use when the task is about source discovery, syncing, fetching, importing, or basic normalization.

## 7. 分层放置规范

### 7.1 放在 `SKILL.md` 的内容

- 任务定义
- 触发条件
- 不触发边界
- 输出物列表
- 运行入口
- 资源导航

### 7.2 放在 `references/` 的内容

- 设计权威说明
- 领域规则
- review checklist
- 细分子域说明
- 长说明文档导航

判断标准：

如果一段内容主要用于“告诉 agent 应该参考什么规则”，放到 `references/`。

### 7.3 放在 `scripts/` 的内容

- 重复步骤
- 确定性转换
- 易错逻辑
- 数据装配
- 校验逻辑
- 报告生成

判断标准：

如果同一动作会在多个任务里反复手写，或者必须稳定执行，就下沉到 `scripts/`。

### 7.4 放在 `templates/` 或 `assets/` 的内容

- Markdown 输出模板
- JSON 输出壳
- HTML / CSS 壳子
- 固定报告模板

### 7.5 放在 `data/` 的内容

- taxonomy
- lookup tables
- scoring rules
- 结构化 heuristics
- 示例配置

### 7.6 放在 `evals/` 的内容

- trigger eval
- workflow eval
- near-miss 样例
- empty result path 样例
- failure path 样例
- 对比基线样例

## 8. 单个 skill 的开发流程

每个新 skill 或大幅重构，必须按下面顺序推进：

### Step 1：先固定设计文档

先补齐或确认以下文档：

- 对应 workflow 的原子能力设计
- 对应对象契约文档
- 对应编排规则文档
- 对应评估规则文档

没有这些文档，不进入实现。

### Step 2：建立 skill 骨架

至少创建：

- `SKILL.md`
- `run.py`
- `agents/openai.yaml`
- `references/design-authority.md`
- `scripts/<skill_package>/`

如当前阶段尚未准备完整模板、数据和 eval，也至少保留目录占位。

### Step 3：先实现 workflow shell，再填内部原子能力

实现顺序固定为：

1. `run.py` 串起主流程
2. `scripts/` 中落地核心对象模型与主 pipeline
3. 再补 adapter、normalizer、renderer、reporting 等子模块

不允许先写一堆零碎工具，再事后拼 skill 边界。

### Step 4：显式定义产物

每个 skill 都必须在实现前固定：

- 主产物是什么
- 辅助产物是什么
- 空结果是否算成功
- 失败写到哪里
- step manifest 如何落盘

### Step 5：补齐评估与测试

每个 skill 至少补齐：

- trigger eval
- should-not-trigger eval
- happy path
- ambiguous path
- failure path
- empty result path
- 基础单元测试或集成测试

### Step 6：验证运行行为

至少验证以下内容：

- 运行入口可执行
- 主产物能落盘
- 辅助产物能落盘
- 失败对象被记录
- 空结果路径不被误判为失败
- 产物字段与文档约定一致

## 9. 产物与运行时规范

### 9.1 每个 skill 都必须有主产物

主产物必须是该 workflow 对外真正交付的对象，而不是中间调试文件。

例如：

- `ingest-normalize` 的主产物是 `normalized-candidates.json`
- `digest-candidates` 的主产物是 `digest-candidates.json`
- `compose-daily-review` 的主产物是 `daily-review-issues.json`
- `curate-retain` 的主产物是 `retention-decisions.json`
- `generate-long-cycle-assets` 的主产物是 `long-cycle-assets.json`

### 9.2 每个 skill 都必须有辅助产物

辅助产物至少应覆盖：

- step manifest
- report
- failure ledger 或 review artifact

### 9.3 空结果与失败必须分离

必须遵守：

- 空结果不等于失败
- 低置信度不等于失败
- 主产物为空但结构合法，允许记为成功
- 只有主产物、manifest 或关键报告无法形成时，才可记为 workflow 失败

### 9.4 运行级汇总不属于单个 skill

`PipelineRun`、跨 workflow 索引、统一调度脚本，属于全局编排层，不属于任何单个 workflow skill。

这类能力应放在：

- `scripts/`
- `docs/global/`
- 后续全局 orchestration 规则中

## 10. 评估规范

### 10.1 触发评估

每个顶层 skill 至少准备：

- `should-trigger` 8 到 10 条
- `should-not-trigger` 8 到 10 条
- `near-miss` 4 到 6 条

这些样例要覆盖相邻 workflow 的边界竞争。

### 10.2 工作流评估

每个顶层 skill 至少覆盖：

- happy path
- ambiguous path
- failure path
- empty result path

### 10.3 断言规范

项目内不接受只有“文件存在”这一层级的弱断言。

至少要断言：

- 输出是否完成关键任务
- 输出结构是否符合契约
- 状态字段是否正确
- 失败是否被显式记录
- 结果是否满足该 workflow 的成功定义

### 10.4 基线对比

新增 skill 时，至少比较：

- with-skill vs without-skill

重构 skill 时，至少比较：

- new-skill vs old-skill

至少观察：

- pass rate
- 失败模式
- 时间
- token
- 人工 review 结果

## 11. Definition of Done

一个 workflow skill 只有同时满足下面条件，才算开发完成：

1. 边界已经被对应 workflow 文档固定
2. `SKILL.md`、`run.py`、`agents/openai.yaml`、`references/design-authority.md` 已存在
3. 主产物与辅助产物已固定，并能稳定生成
4. 主要业务逻辑已经下沉到 `scripts/`，没有堆在 `SKILL.md`
5. 空结果、失败、低置信度语义已定义
6. trigger eval 和 workflow eval 已具备最小覆盖
7. 至少有一组真实或准真实样例跑通
8. 该 skill 没有越界吞并相邻 workflow

只做到“能跑”不算完成，只写了 `SKILL.md` 更不算完成。

## 12. 项目内反模式

后续开发中，明确禁止以下做法：

- 把原子能力直接做成顶层 skill
- 用超长 `SKILL.md` 代替 `references/`
- 在一个 skill 中同时交付代码、报告、日报、知识库写入等多类无关 artifact
- 让 `run.py` 直接承载大部分业务实现
- 把全局编排逻辑偷偷塞进单个 workflow skill
- 没有失败 ledger，只返回“失败了”
- 没有 empty result path 设计
- 没有 trigger eval 就宣称 skill 已完成
- description 写得模糊，导致多个 workflow 竞争同一请求

## 13. 对当前仓库的直接要求

基于当前状态，后续开发应遵守：

1. `ingest-normalize` 继续作为工作流壳，详细规则留在 `docs/workflows/ingest-normalize/`
2. `digest-candidates`、`compose-daily-review`、`curate-retain`、`generate-long-cycle-assets` 按同样模式补齐
3. 新 skill 一律优先复用本文档结构，不另起一套目录和命名体系
4. 如需新增共享规则，优先补 `docs/global/` 或对应 workflow 文档，而不是扩写 `SKILL.md`
5. 如需新增确定性转换逻辑，优先下沉到 `scripts/`

## 14. 一句话规范

> 顶层按 workflow 暴露，skill 只做工作流外壳，原子能力下沉到资源层，评估与失败语义从第一天开始设计。
