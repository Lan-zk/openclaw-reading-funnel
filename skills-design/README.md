# Skills 设计研究文档

本目录包含基于以下样本与资料整理出的中文研究文档：

- 本地样本
  - `ui-ux-pro-max-skill`
  - `skills/skills/skill-creator`
  - `Agent-Skill-五种设计模式.md`
- 外部资料
  - Anthropic Agent Skills 文档与最佳实践
  - OpenAI function calling 指南
  - Google ADK workflow / multi-agent 文档
  - Microsoft Research 关于 tool-space interference 的文章
  - ToolNet 论文

## 文档列表

- [01-研究报告.md](./01-%E7%A0%94%E7%A9%B6%E6%8A%A5%E5%91%8A.md)
- [02-Skills设计说明.md](./02-Skills%E8%AE%BE%E8%AE%A1%E8%AF%B4%E6%98%8E.md)
- [03-Skills设计规范.md](./03-Skills%E8%AE%BE%E8%AE%A1%E8%A7%84%E8%8C%83.md)
- [04-Skills架构说明.md](./04-Skills%E6%9E%B6%E6%9E%84%E8%AF%B4%E6%98%8E.md)

## 阅读顺序

建议按这个顺序阅读：

1. 先看研究报告，理解结论从哪里来
2. 再看设计说明，理解为什么这样设计
3. 再看设计规范，直接落到可执行规则
4. 最后看架构说明，决定如何组织仓库和运行时

## 核心结论

- 一个好的 skill，不是“把知识塞进 prompt”，而是“用 `SKILL.md` 做工作流外壳，再把知识、脚本、模板、数据分层外置”。
- 顶层可见 skill 数量应少，默认 3 到 4 个最稳，超过 7 个时要非常谨慎。
- skill 的边界不应按最小原子能力切，而应按“用户意图 + 工作流 + 输出物 + 评估标准”来切。
- 最佳实践不是“全都做成微技能”，也不是“一个超级技能包打天下”，而是分层：
  - 顶层少量 workflow skill
  - 底层大量 references / scripts / templates / data

## 说明

本目录只输出研究与设计文档，不修改被分析样本的实现逻辑。
