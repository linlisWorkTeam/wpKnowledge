# 🔄 feedback-loop · 反馈循环与自进化

> 飞轮核心：差异对比与反馈优化。如何让 Agent 从"生成代码 vs 源码"的差异中学习、进化知识。
> 按时间排序（最新在前）。

## 📄 文档索引

| 文档 | 类型 | 时间 | 置信度 | 一句话 |
|------|------|------|--------|--------|
| [conself-self-improving.md](conself-self-improving.md) | 论文 | 2026-03 | ⚠️ 谨慎 | 无教师无 oracle 自改进（语义熵+行为一致性） |
| [fragility-self-improving.md](fragility-self-improving.md) | 论文 | 2026-08 | ⚠️ 谨慎* | **自改进脆弱性：方差/顺序/规格。飞轮必读** |
| [self-evolving-coding-agents.md](self-evolving-coding-agents.md) | 综述 | 2026-08 | 🟡 中 | 软件工程场景自进化（证据分类） |
| [feedback-over-form.md](feedback-over-form.md) | 论文 | 2026-04 | ⚠️ 谨慎 | 执行反馈比流水线拓扑更重要 |
| [evolver.md](evolver.md) | 论文 | 2025-10 | 🟡 中 | 经验生命周期：经历→反思→抽象→沉淀→复用 |
| [self-evolving-survey.md](self-evolving-survey.md) | 综述 | 2025-07 | 🟡 中 | 自进化全景：进化什么/何时/怎么/在哪 |
| [reveal.md](reveal.md) | 论文 | 2025-06 | 🟡 中 | 自主生成测试 + 可靠验证 + RL |
| [sew.md](sew.md) | 论文 | 2025-05 | 🟡 中 | 工作流拓扑 + 提示词一起进化 |
| [promptbreeder.md](promptbreeder.md) | 论文 | 2023-09 | ✅ 高 | 自我指涉提示词进化（DeepMind） |
| [critic.md](critic.md) | 论文 | 2023-05 | ✅ 高 | 自我纠错必须调用外部工具 |
| [self-debugging.md](self-debugging.md) | 论文 | 2023-04 | ✅ 高 | 代码解释 + 执行反馈组合最有效 |
| [reflexion.md](reflexion.md) | 论文 | 2023-03 | ✅ 高 | 反思记忆 = 轻量强化学习（奠基工作） |

> *fragility 论文刚发布（2026-08），结论本身待验证，但它揭示的风险有独立佐证，作为设计约束采纳（见 docs/flywheel.md §5）。

## 📌 核心结论

1. **反馈 > 形式**：执行反馈质量比流程复杂度重要（feedback-over-form）
2. **外部验证 > 内部反思**：客观信号（测试/执行/对比）比 LLM 自查可靠（reflexion/critic/self-debugging）
3. **⚠️ 可靠性警告**：必须重复实验、控制顺序、精确定义门禁（fragility）
4. **进化框架**：进化对象 × 时机 × 证据类型 的三维分析（self-evolving-coding-agents）
