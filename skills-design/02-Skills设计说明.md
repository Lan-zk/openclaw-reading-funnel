# Skills 设计说明

## 1. 设计立场

本说明给出一个明确立场：

> Skill 不应被理解为“提示词片段”，而应被理解为“可被模型路由的工作流能力单元”。

一个好的 skill，至少同时包含四个维度：

- 触发维度：什么时候应该调用它
- 工作流维度：它如何完成任务
- 输出维度：它交付什么结果
- 评估维度：怎样算它成功

如果一个设计没有这四个维度，它通常还只是一个 prompt，而不是一个成熟 skill。

## 2. 为什么 `ui-ux-pro-max-skill` 能广而不乱

很多人看到 `ui-ux-pro-max-skill` 的第一反应是：

“这不就是一个 skill 做了太多事吗？”

研究后的判断是：

**不是。**

它做的不是“很多不相关的事”，而是“同一个大工作流中的很多决策子问题”。

### 2.1 它解决的是一个统一用户任务

这个统一任务是：

- 为 UI / UX 设计与实现提供设计系统级的推荐、约束、检索和落地支持

它下面的配色、字体、布局、交互、图表、风格、栈适配，都不是独立工作流，而是这个大工作流里的子维度。

### 2.2 它没有把所有复杂性直接暴露给模型

它把复杂性分成了几层：

- 顶层：`SKILL.md`
- 中间层：domain search 和 design system generation
- 底层：CSV 数据、BM25 检索、模板、CLI、分发

因此模型看到的不是“上百个零碎能力”，而是：

- 一个入口
- 一条主路径
- 若干按需加载的细节层

### 2.3 它的广度来自结构化资产，不来自 prompt 堆砌

它之所以能广，是因为：

- 知识被结构化进 `data/`
- 逻辑被固化进 `scripts/`
- 分发被模板化进 `templates/`

这比单纯写一个超长 prompt 更稳定，也更可维护。

## 3. 为什么 `skill-creator` 更像“规范工厂”

`skill-creator` 的意义，不在于“会生成 skill”，而在于它给 skill 设计下了定义：

### 3.1 它认为 description 是第一触发面

这点非常重要。

很多设计者会把大量“什么时候触发”的信息塞到 `SKILL.md` 正文，但从 Anthropic 体系看，真正参与初始发现的是 metadata，尤其是 description。

`skill-creator` 明确把 description 视为 primary triggering mechanism，这其实是在提醒：

> 你不是在写 README，你是在设计路由面。

### 3.2 它把 eval 放进了 skill 本体

这意味着 skill 不是“写完就完”，而是一个可测试对象。

它把以下内容标准化了：

- evals.json
- benchmark
- grading
- blind comparison
- feedback loop

这会直接改变 skill 的设计方式：

- 你会从一开始就考虑可验证性
- 你会被迫定义输出物
- 你会被迫定义边界

### 3.3 它定义的是“构建流程规范”，不是“文档格式规范”

这也是它比普通模板强的地方。

它告诉你：

- skill 应该怎样被写出来
- skill 应该怎样被测出来
- skill 应该怎样被优化出来

## 4. 好的 skill 到底按什么边界切

## 4.1 错误切法：按知识点切

例如：

- typography-skill
- color-skill
- layout-skill
- animation-skill

这种切法的问题在于：

- 用户不会这样提需求
- 顶层路由面会变得拥挤
- skill 之间高度耦合
- 很多任务必须同时触发多个 skill

结果就是模型更难选，用户也更难理解。

## 4.2 正确切法：按工作流切

例如：

- 设计系统 skill
- 页面构建 skill
- UI review skill
- 品牌规范 skill

这些 skill 的共同点是：

- 用户会这样表达需求
- 有明确输出物
- 有独立完成闭环
- 有清晰评估标准

## 4.3 最佳切法：外层按工作流，内层按原子能力

这是本说明的核心主张。

### 外层

外层是给模型和用户看的。

应按：

- 用户意图
- 任务闭环
- 输出物
- 评估逻辑

来切。

### 内层

内层是给实现和维护看的。

应按：

- references
- scripts
- templates
- assets
- data

这些原子能力层来组织。

## 5. 一个好的 skill 应具备哪些能力

## 5.1 基础能力

基础能力是指：只靠这个 skill，就能把它宣称的工作做完整。

至少应包含：

- 清晰触发条件
- 核心工作流
- 输出物定义
- 最小验证机制

如果这四项缺失，skill 通常还不闭环。

## 5.2 边界能力

边界能力不是“扩功能”，而是“处理现实世界里的复杂性”。

包括：

- 相邻任务的归属判断
- 模糊输入时的澄清
- 异常与失败回退
- 结果 review
- 与其他 skill 的协作接口

一个 skill 是否成熟，往往不是看 happy path，而是看边界能力。

## 5.3 最佳状态

一个 skill 的最佳状态不是“能做很多”，而是：

> 对一个明确用户任务，既能深做，也能稳做，还能被评估。

## 6. skill 数量应该怎么控制

## 6.1 为什么少量顶层 skill 更优

原因有三：

### 第一，路由精度

顶层技能越多，description 越容易重叠，模型越容易误触发或漏触发。

### 第二，认知负担

模型需要在一个 turn 里理解：

- 哪些 skill 存在
- 每个 skill 做什么
- 哪个 skill 更匹配当前任务

技能数越多，这个判断越难。

### 第三，上下文成本

即使只是 metadata，也会占用系统上下文预算。OpenAI 也明确指出，函数定义本身会占用 token。

## 6.2 推荐数量

这里给出一个实用推荐，不是硬规则：

- 1 到 2 个：适合很小的、单域系统
- 3 到 4 个：最稳，推荐默认值
- 5 到 7 个：可以接受，但必须有非常清晰的边界
- 8 个以上：应引入分组、路由层或检索层，不建议继续平铺

这是一条工程经验线，不是标准上限。

## 7. 最终设计原则

如果把本说明压缩成一句话，就是：

> 顶层 skill 要像产品菜单，底层能力要像系统组件。

也就是说：

- 对用户与模型来说，skill 是少而清楚的工作流入口
- 对实现者来说，skill 背后可以有很多细粒度能力模块

这就是为什么：

- `ui-ux-pro-max-skill` 可以广，但仍然成立
- `skill-creator` 会把 eval、packaging、description optimization 纳入规范
- Google 的五种模式应该组合使用，而不是单选

## 8. 参考资料

- Anthropic Agent Skills Overview  
  [https://docs.claude.com/en/docs/agents-and-tools/agent-skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)
- Anthropic Skill authoring best practices  
  [https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)
- OpenAI Function calling guide  
  [https://developers.openai.com/api/docs/guides/function-calling](https://developers.openai.com/api/docs/guides/function-calling)
- Microsoft Research: Tool-space interference  
  [https://www.microsoft.com/en-us/research/blog/tool-space-interference-in-the-mcp-era-designing-for-agent-compatibility-at-scale/](https://www.microsoft.com/en-us/research/blog/tool-space-interference-in-the-mcp-era-designing-for-agent-compatibility-at-scale/)
- Google ADK multi-agent systems  
  [https://google.github.io/adk-docs/agents/multi-agents/](https://google.github.io/adk-docs/agents/multi-agents/)
- ToolNet  
  [https://arxiv.org/abs/2403.00839](https://arxiv.org/abs/2403.00839)
