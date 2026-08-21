# docs · 项目正式文档

项目定义与设计文档：为什么做、怎么做、做成什么样。

## 📄 文档索引

| 文档 | 内容 |
|------|------|
| [overview.md](overview.md) | 项目概述：背景、目标、飞轮总览、门禁总览、约束、参考仓库 |
| [knowledge-format.md](knowledge-format.md) | 知识形态定义：解释型 Markdown 文档规范 |
| [flywheel.md](flywheel.md) | 知识飞轮流程设计：主力路线 + 备选路线 |
| [gate.md](gate.md) | 门禁 / 评测机制：TDD 探讨、可靠性约束、职责边界 |
| [research-mapping.md](research-mapping.md) | ⭐ 调研 ↔ 飞轮关联映射：论文/仓库自动关联到飞轮环节（✅可用/⚠️矛盾） |
| [research-brief.md](research-brief.md) | ⭐ **调研决策简报**：160+ 候选浓缩 15 条关键结论 → 设计决策（收敛入口） |
| [implementation-plan.md](implementation-plan.md) | ⭐ **实现方案**：给 GLM 5.1 照着搭建的工程方案（目录/接口/分阶段/验收） |
| [multi-agent-task.md](multi-agent-task.md) | ⭐ **多 Agent 架构任务文档**：框架选型调研 + 角色/通信/状态机设计 + 搭建任务清单 |
| [operator-flywheel-case.md](operator-flywheel-case.md) | ⭐ **知识飞轮案例**：别的团队实现方案（Base→A→B→C→R 循环），含与本项目设计的角色/机制对照 |
| [glossary.md](glossary.md) | 名词表 |

## 📌 已确认的关键决策

- **知识形态**：解释型 Markdown 文档（代码片段 + 实现思路 + 设计逻辑 + 适用场景），非源码搬运
- **模型约束**：仅使用公司本地部署的 GLM 5.1
- **主力路线**：源码 → 知识生成 Agent（加载知识生成 skill）产出知识 → Coder Agent 基于知识写代码 → Review Agent 对比差异 → 反馈优化（[flywheel.md](flywheel.md)）
- **角色分工**：知识生成 Agent（生成知识，唯一的执笔者）/ Coder（写代码）/ Review（对比+归因+门禁）三者分离，生成与验证必须独立；知识飞轮（编排层）只决策不执笔
- **职责边界**：评测只读不修改知识；可改知识的只有知识飞轮（决策）+ 知识生成 Agent（执行）；Coder 不承担迭代逻辑
- **评测闭环**：用例集驱动——需求描述 + 知识库 → 临时代码 vs 标准代码 → 相似度 → 置信度（= f(通过的用例数)）→ 知识飞轮迭代（TDD 方案见 gate.md §7，探讨中）
- **知识修改定位**：溯源链接（sources）反向映射——diff 定位源码位置 → 映射到文档段落
- **反馈结构**：结构化信号（diff/AST/测试/相似度）+ 自然语言解读，两层结合
- **备选路线**：破坏源码 → Agent 补齐（能力补齐，非主线）
- **门禁阈值**：Agent 基于知识生成的代码与源码相似度 ≥ 80% 即通过
- **设计核心参考**：cannbot-knowledge（gitcode，流程锚点）+ knowledge-catalog/OKF（⭐8756，格式锚点）——OKF 定格式、cannbot 定运营流程，详见 [overview.md §6](overview.md)

> 文档如有变更，随时同步更新。
