# Skills 设计规范

本规范不是平台协议规范，而是面向设计者的工程规范。

目标是回答：

- 什么时候该新建 skill
- 什么时候该拆 skill
- 什么时候该把能力下沉到 references / scripts / data
- 什么样的 skill 才算设计完成

## 1. 顶层原则

### 1.1 可见 skill 少而清楚

默认推荐：

- 3 到 4 个顶层 skill

谨慎上限：

- 7 个左右

如果超过这个数量，必须引入：

- 分组层
- 路由层
- tool search / capability search
- 或分域插件机制

### 1.2 一个 skill 只拥有一个主要用户任务

允许一个 skill 包含很多子能力，但必须满足：

- 这些子能力共同服务于一个用户任务
- 它们共享主要工作流
- 它们共享主要输出物类型
- 它们共享主要评估标准

### 1.3 `SKILL.md` 是工作流外壳，不是知识仓库

`SKILL.md` 负责：

- 触发条件
- 何时不该使用
- 工作流步骤
- 输出物契约
- 资源入口

`SKILL.md` 不负责：

- 存放大段背景知识
- 存放大量样例
- 存放结构化数据
- 承担大量可重复的确定性逻辑

## 2. 边界判定规范

## 2.1 新建 skill 的四要素测试

只有同时满足下面四项，才建议拆成新的顶层 skill：

1. 触发语言明显不同
2. 工作流明显不同
3. 输出物明显不同
4. 评估标准明显不同

如果只是数据不同、参考资料不同、脚本不同，不应拆成新的顶层 skill。

## 2.2 不应拆 skill 的情况

以下情况建议保持为一个 skill：

- 用户仍然把它视为同一个工作
- 输出物属于同一家族
- review checklist 基本一致
- 只是知识域变多
- 只是脚本和模板增多

## 2.3 应该拆 skill 的情况

以下情况建议拆分：

- 一个 skill 同时要产出文档、代码、审计报告等完全不同 artifact
- 一个 skill 同时承担“生成”和“评审”，且评审标准与生成逻辑高度独立
- 一个 skill 的 description 已经难以写清边界
- 用户需求中经常出现“你到底应该调哪个 skill”的竞争

## 3. 结构规范

## 3.1 最小目录规范

```text
my-skill/
|-- SKILL.md
|-- references/      # 可选，但推荐
|-- scripts/         # 可选，但推荐
|-- assets/          # 可选
|-- templates/       # 可选，和 assets 二选一或并存
|-- data/            # 可选
`-- evals/           # 非平凡 skill 强烈推荐
```

## 3.2 `SKILL.md` frontmatter 规范

必选字段：

- `name`
- `description`

推荐字段：

- `license`
- `metadata`
- `compatibility`
- `allowed-tools`

### `name` 规范

- 使用小写
- 使用连字符
- 不要过长
- 不要泛化成 `helper`、`utils`、`tools`

推荐命名风格：

- 动名词或动作导向名词
- 例如：
  - `processing-pdfs`
  - `reviewing-ui`
  - `creating-brand-guidelines`

### `description` 规范

必须同时说明两件事：

1. 这个 skill 做什么
2. 什么时候应该触发它

description 是路由面，不是口号。

坏例子：

- 帮助处理文档
- 处理数据
- 做文件相关工作

好例子：

- 提取 PDF 文本与表格、填写表单、合并文档；当用户提到 PDF、表单、文档提取时使用
- 评审 UI 的视觉一致性、可访问性与交互质量；当用户要求 review UI、找 UX 问题、检查可访问性时使用

## 4. 内容分层规范

## 4.1 放在 `SKILL.md` 的内容

- 任务定义
- 触发边界
- 工作流
- 输出契约
- 资源导航

## 4.2 放在 `references/` 的内容

- 长说明
- 规范文档
- 领域规则
- 审核 checklist
- 子领域说明

## 4.3 放在 `scripts/` 的内容

- 重复性步骤
- 易错步骤
- 确定性转换
- 校验逻辑
- 打包逻辑

### 判断规则

如果同一动作在多个测试样本里反复被模型手写出来，应该下沉为 script。

## 4.4 放在 `templates/` 或 `assets/` 的内容

- 输出模板
- starter 文件
- UI / HTML / CSS 壳子
- 示例文件

## 4.5 放在 `data/` 的内容

- CSV/JSON 知识库
- taxonomy
- lookup table
- scoring rules
- structured heuristics

## 5. 工作流规范

## 5.1 推荐模式组合

复杂 skill 默认按下面组合设计：

- `Inversion` 或 `Tool Wrapper`
- 再进入 `Generator` 或 `Pipeline`
- 最后用 `Reviewer` 收尾

### 示例

- 需求不明确的 skill：
  - `Inversion -> Pipeline -> Reviewer`
- 结构化生成型 skill：
  - `Tool Wrapper -> Generator -> Reviewer`
- 高风险、多步骤 skill：
  - `Tool Wrapper -> Pipeline -> Reviewer`

## 5.2 高自由度与低自由度

### 高自由度 skill

适合：

- 上下文依赖强
- 解决方案不唯一
- 需要模型发挥判断力

做法：

- 给原则
- 给资源入口
- 不强绑死命令

### 低自由度 skill

适合：

- 步骤必须固定
- 出错代价高
- 结果需要强一致性

做法：

- 明确步骤
- 明确脚本
- 明确不要改动参数

## 6. 评估规范

## 6.1 非平凡 skill 必须可评估

至少准备两类 eval：

### 触发 eval

- should-trigger 8 到 10 条
- should-not-trigger 8 到 10 条
- 必须包含 near-miss，而不是完全无关的问题

### 工作流 eval

至少包含：

- happy path
- ambiguous path
- failure / edge path

## 6.2 baseline 规范

新 skill：

- with-skill vs without-skill

优化现有 skill：

- new-skill vs old-skill

至少比较：

- pass rate
- 时间
- token
- 失败模式
- 人工 review 结果

## 6.3 assertion 规范

assertion 必须是可区分的。

坏 assertion：

- 输出文件存在
- 输出里提到了某个词

好 assertion：

- 输出是否完成了关键任务
- 输出是否满足结构约束
- 输出是否通过验证脚本
- 输出是否真的解决了业务需求

## 6.4 人工评审规范

以下类型强烈建议人工 review：

- 设计
- 文案
- 报告
- 总结
- 多模态产物
- 高层决策建议

建议有人类反馈环，并保留：

- 反馈文本
- 对比结果
- 改进记录

## 7. 运行时规范

## 7.1 Progressive disclosure

必须遵循：

- metadata 总是轻
- `SKILL.md` 在触发后加载
- references / scripts / assets 只按需使用

## 7.2 工具空间控制

应避免：

- 一次性把大量能力平铺给模型
- 让模型在高度重叠的 skill 中盲选

更好的做法：

- 顶层 skill 少量暴露
- 大型能力面通过检索或按需加载进入

## 7.3 参数空间控制

工具或 script 接口应：

- 参数平坦
- 命名清晰
- 尽量避免深层嵌套

因为参数复杂度本身会降低工具使用质量。

## 8. 反模式清单

以下都是常见反模式：

- 把每个知识点都拆成一个 skill
- 用超长 `SKILL.md` 代替 references
- 一个 skill 同时承担多个无关 artifact
- 只有 happy path，没有失败路径
- description 含糊，边界不清
- 没有 baseline 对比
- 没有 source of truth，安装副本四处漂移

## 9. 推荐默认方案

对于大多数系统，直接采用如下默认方案：

### 顶层 skill

- `plan`
- `build`
- `review`
- `meta`

### 底层资源

- `references/`
- `scripts/`
- `templates/`
- `data/`
- `evals/`

### 原则

- 顶层按工作流切
- 底层按原子能力组织
- 评估和发布从第一天开始设计

## 10. 一句话规范

> 顶层少 skill，内部多模块；按工作流暴露，按原子能力实现；所有 skill 都必须可验证。
