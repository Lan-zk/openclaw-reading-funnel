# 漏斗式阅读工作流设计总索引

## 1. 文档目的

本文档是当前设计阶段的总索引。

它只解决三件事：

- 说明设计文档现在有哪些
- 说明每份文档分别回答什么问题
- 给出推荐阅读顺序与后续衔接方式

本文档不重复展开各 workflow 的原子能力细节，也不承担对象契约的 source of truth。

## 2. 当前文档版图

### 2.1 全局总设计

- [reading-funnel-global-implementation-guide.md](./reading-funnel-global-implementation-guide.md)

作用：

- 定义系统的顶层目标、边界和原则
- 固定 5 个顶层 workflow
- 固定核心对象契约草案
- 固定编排、反馈、评估和实施顺序

适用问题：

- 这个系统整体要做什么
- 顶层为什么只拆成 5 个 workflow
- 哪些能力明确不做

### 2.2 workflow 原子能力设计

#### `ingest-normalize`

- [reading-funnel-ingest-normalize-atomic-design.md](../workflows/ingest-normalize/reading-funnel-ingest-normalize-atomic-design.md)

作用：

- 定义信息接入与基础归一化的原子能力边界
- 明确抓取、字段映射、来源快照落盘、基础归一化、失败 ledger 的关系

适用问题：

- 不同来源的实际抓取落在哪一步
- 空结果与失败如何分离
- 来源接入阶段的中间对象有哪些

#### `digest-candidates`

- [reading-funnel-digest-candidates-atomic-design.md](../workflows/digest-candidates/reading-funnel-digest-candidates-atomic-design.md)

作用：

- 定义候选收窄、正文抽取、质量检查、噪音过滤、摘要生成、候选装配的原子能力边界
- 明确 `FILTERED`、`NEEDS_REVIEW`、`FAILED` 三者分离

适用问题：

- Digest 这一层到底在什么时候正式“过滤”
- 偏好信号能不能参与最终裁决
- 哪一步负责生成最终 `DigestCandidate` 字段

#### `compose-daily-review`

- [reading-funnel-compose-daily-review-atomic-design.md](../workflows/compose-daily-review/reading-funnel-compose-daily-review-atomic-design.md)

作用：

- 定义日报事件归并、栏目建议、主题提炼、重要性评估、深挖识别、结构编排、成稿渲染的原子能力边界
- 明确只有 `compose_issue_structure` 可以做最终入选裁决

适用问题：

- 日报面对的是“候选”还是“事件包”
- render 阶段是否还能重新做编辑判断
- 固定栏目如何在中间步骤里保持不漂移

#### `curate-retain`

- [reading-funnel-curate-retain-atomic-design.md](../workflows/curate-retain/reading-funnel-curate-retain-atomic-design.md)

作用：

- 定义人工精读队列、人工留存决策、决策落盘、知识资产写入、偏好信号派生的原子能力边界
- 明确只有人能做长期价值裁决

适用问题：

- 哪一步是唯一正式留存决策点
- 知识资产写入失败能不能反改决策
- 偏好信号到底从什么派生

#### `generate-long-cycle-assets`

- [reading-funnel-generate-long-cycle-assets-atomic-design.md](../workflows/generate-long-cycle-assets/reading-funnel-generate-long-cycle-assets-atomic-design.md)

作用：

- 定义周期素材汇总、热点主题累计、长期信号识别、周刊生成、专题可写性判断、专题素材包装配的原子能力边界
- 明确长周期产物只能来自已有沉淀，不能重新抓热点

适用问题：

- 周刊和专题是不是两条不同产线
- 哪一步正式生成 `WEEKLY` 或 `TOPIC` 资产
- 长周期产物能否回头补外部事实

## 3. 推荐阅读顺序

### 3.1 第一次进入项目

推荐顺序：

1. 先看 [reading-funnel-global-implementation-guide.md](./reading-funnel-global-implementation-guide.md)
2. 再按 workflow 顺序看 5 份原子能力设计

原因：

- 先建立系统级边界
- 再进入单 workflow 的能力切分
- 避免一上来陷进局部细节

### 3.2 如果只关心某一层

- 信息接入问题：直接看 `ingest-normalize`
- Digest 收窄问题：直接看 `digest-candidates`
- 日报编排问题：直接看 `compose-daily-review`
- 人工留存问题：直接看 `curate-retain`
- 周刊 / 专题问题：直接看 `generate-long-cycle-assets`

### 3.3 如果要开始实现

推荐顺序：

1. 全局文档
2. 当前 workflow 的原子能力设计
3. 对应对象契约文档
4. 对应编排规则与评估规则

说明：

当前仓库里，原子能力设计已经补齐，但对象契约、编排规则、评估规则的下钻文档还需要继续完善。

## 4. 各文档的职责边界

为了避免后续文档互相覆盖，建议固定以下职责：

- `reading-funnel-global-implementation-guide.md`
只管全局原则、顶层 workflow、核心对象草案、编排原则、评估原则
- `reading-funnel-*-atomic-design.md`
只管单个 workflow 的原子能力切分、输入输出、中间对象、状态语义、最终字段来源映射
- 后续的对象契约文档
只管 schema 和字段 source of truth
- 后续的编排规则文档
只管调度、触发、run 汇总、失败回放
- 后续的评估规则文档
只管 empty result path、failure path、trigger eval、workflow eval、指标

## 5. 当前设计结论

到当前为止，系统的设计已经固定了三层结构：

### 5.1 顶层

顶层按 5 个 workflow 暴露：

1. `ingest-normalize`
2. `digest-candidates`
3. `compose-daily-review`
4. `curate-retain`
5. `generate-long-cycle-assets`

### 5.2 中层

每个 workflow 都已经拆成自己的原子能力，并明确了：

- 输入对象
- 输出对象
- 不做什么
- 失败语义
- 中间对象
- 最终字段来源

### 5.3 横切层

横切层原则已经在各文档中被反复固定：

- 空结果不等于失败
- 低置信度不等于失败
- 失败 ledger 是运行级唯一失败真相
- 长期价值判断保留给人
- 偏好信号只能轻量回流，不能统治系统

## 6. 后续建议补文档

如果继续沿当前路线往下走，下一批建议补的文档是：

1. `reading-funnel-object-contracts.md`
把中间对象和最终对象的 schema 真正落成 source of truth
2. `reading-funnel-orchestration-rules.md`
把 5 个 workflow 的触发、调度、run 汇总、失败回放串起来
3. `reading-funnel-evaluation-rules.md`
把 trigger eval、empty result path、failure path、review path 固定下来
4. `reading-funnel-review-checklists.md`
把设计评审和实现评审 checklist 固定下来

## 7. 一句话导航

如果只记住一句话，就记住这一句：

> 先看全局文档理解边界，再按 workflow 进入原子能力设计；实现时以对象契约为准，以编排规则串起来，以评估规则收口。
