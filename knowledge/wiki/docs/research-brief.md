# 调研决策简报（Research Brief）

> 最后更新：2026-08-21
> 用途：**收敛**——把 160+ 候选条目浓缩成 15 条关键结论。每条结论标注依据 + 对飞轮的设计决策。
> 读法：先看结论，需要深挖再点依据链接（单篇/候选池）。
> 详细关联见 [research-mapping.md](research-mapping.md)；全量候选见 [candidate-pool.md](../research/candidate-pool.md)。

---

## 一、知识生成（第一步：源码 → 知识）

**结论 1：生成顺序 = 依赖拓扑序**
两个独立工作（RepoAgent + RepoDoc）验证同一结论：先依赖、后被依赖。显式知识图谱（RepoKG）比隐式依赖分析更可控。
→ 决策：飞轮第一步按拓扑序生成，用显式依赖图索引。
依据：[RepoAgent](../research/doc-generation/repoagent.md)、[RepoDoc](../research/doc-generation/repodoc.md)

**结论 2：知识格式 = OKF（Markdown + frontmatter），溯源链接必须**
OKF 是格式锚点；cannbot 用 okf.v1 运营。溯源链接（sources）是"改文档哪部分"的前提，Repodoc 的图回溯与 OKF 的 sources 字段一致。
→ 决策：知识文档 = OKF 格式，每段带 sources 溯源（已写入 knowledge-format.md §6）。
依据：[OKF](../research/knowledge-format/knowledge-catalog-okf.md)、[cannbot](../research/knowledge-format/cannbot-knowledge.md)

**结论 3：知识质量决定一切——低质文档不如没有**
"When LLMs Meet API Docs" 证明模糊文档对 LLM 帮助有限；Code2Doc 证明数据质量是模型上限。知识生成必须质量优先（少而精）。
→ 决策：知识库宁缺毋滥；入库走质量过滤（时效/一致/去重/防 AI 污染）。
依据：[llm-api-docs](../research/doc-generation/llm-api-docs.md)、[Code2Doc](../research/evaluation/code2doc.md)

## 二、代码生成（第二步：知识 → 代码）

**结论 4：规格驱动路线已被工业界验证**
GitHub 官方 spec-kit ⭐130k、OpenSpec ⭐65k、Spec2RTL 严格规格有效。知识=规格 → 代码的路线成立。
→ 决策：知识文档按"可执行规格"标准写（伪代码保留逻辑魂）。
依据：[candidate-pool](../research/candidate-pool.md)（spec-kit/OpenSpec）、[Spec2RTL](../research/doc-generation/spec2rtl-agent.md)

**结论 5：规格严格度要分级，不搞一刀切**
SDD: From Code to Contract 提出三级：spec-first（完整规格）/ spec-anchored（规格锚定）/ spec-as-source（规格即源）。Specification Paradox 警示规格方法有边界。
→ 决策：按模块重要性选规格严格度，核心模块 spec-first，边缘模块可放宽。
依据：[SDD](../research/candidate-pool.md)、[Specification Paradox](../research/candidate-pool.md)

**结论 6：信息损失率 = 差异来源（核心矛盾）**
文档丢掉的信息量 = Agent 生成代码与源码的差异。伪代码保留逻辑（边界/数据结构/调用），丢命名/格式/样板。
→ 决策：文档模板明确"保留什么/丢弃什么"，控制信息损失率。
依据：[llm-api-docs](../research/doc-generation/llm-api-docs.md)、[Spec2RTL](../research/doc-generation/spec2rtl-agent.md)

## 三、评测 / 门禁（第三步）

**结论 7：TDD 评测证据已充分，可考虑转正**
Spec-Driven Test Gen（Google）先写契约再生成测试，bug 检出 +9.8pp；TDD-Agent、Scaling TDD、理论分析、Do Code LMs Use Tests 多篇支撑。执行反馈是最有效信号。
→ 决策：TDD 方案（gate.md §7）证据充足，建议从"探讨"转"待定采纳"（仍保留相似度作辅助）。
依据：[Spec-Driven Test Gen](../research/candidate-pool.md)、[TDD-Agent](../research/candidate-pool.md)、[Self-Debugging](../research/feedback-loop/self-debugging.md)

**结论 8：防作弊是门禁生命线**
Code-QA-Bench 证明高分可能来自"背源码"而非"读知识"。评测必须用私有代码或变换公开代码。
→ 决策：门禁评测集独立 + 防背源码（已写入 gate.md §3.5）。
依据：[Code-QA-Bench](../research/evaluation/code-qa-bench.md)

**结论 9：多信号组合，单一指标必误判**
功能等价但写法不同的代码会被相似度误杀；测试覆盖不足时相似度补位。结构 + 编译 + 测试三信号。
→ 决策：门禁 = 多信号（TDD 主 + 相似度辅 + 编译前置）。
依据：[gate.md §3.5](gate.md)、[Code2Doc](../research/evaluation/code2doc.md)

## 四、反馈迭代（第四步）

**结论 10：外部验证 > 内部反思（三角色分离的依据）**
CRITIC 证明自我纠错必须调用外部工具；自评有确认偏误。
→ 决策：Coder 与 Review 分离，门禁不依赖任何 agent 自我感觉（已写入 flywheel.md §3）。
依据：[CRITIC](../research/feedback-loop/critic.md)

**结论 11：执行反馈 > 自然语言反馈**
Self-Debugging 证明"代码解释 + 执行反馈"组合最有效；Feedback Over Form 证明反馈质量 > 流程拓扑。
→ 决策：反馈 = 结构化信号（diff/测试结果/相似度）+ NL 解读两层。
依据：[Self-Debugging](../research/feedback-loop/self-debugging.md)、[Feedback Over Form](../research/feedback-loop/feedback-over-form.md)

**结论 12：自进化的主流答案 = 记忆/技能库**
ReasoningBank/MemGen/FLEX/SkillOS/CODESKILL 全是"经验 → 记忆/技能 → 复用"模式，与我们的知识库驱动思路吻合。
→ 决策：知识库定位 = 飞轮的记忆层；知识文档 = 可复用的技能单元。
依据：[candidate-pool](../research/candidate-pool.md)（ReasoningBank/SkillOS）、[SoK Agentic Skills](../research/knowledge-format/sok-agentic-skills.md)

**结论 13：文档-代码一致性可自动化检测**
CASCADE 用自动测试生成检测代码-文档不一致——这正是飞轮"差异对比"环节的现成思路。
→ 决策：门禁信号之一 = 一致性检测（生成代码 vs 知识描述 vs 源码三向校验）。
依据：[CASCADE](../research/candidate-pool.md)

## 五、可靠性约束（反模式）

**结论 14：自改进必须防脆弱性（方差/顺序/规格模糊）**
Fragility 证明记忆型自改进 agent 方差巨大、顺序敏感、规格模糊跑偏。自我改进会放大系统性错误（ConSelf 自举风险）。
→ 决策：硬性约束已落地——重复评测 ≥5 次、控制顺序、精确定义规格、客观信号、防污染回滚（flywheel.md §9）。
依据：[Fragility](../research/feedback-loop/fragility-self-improving.md)、[ConSelf](../research/feedback-loop/conself-self-improving.md)

**结论 15：知识库是攻击面（安全维度）**
FDI 证明用户反馈通道可被攻击；RAG 知识投毒研究出现。知识库可信性影响生成代码安全。
→ 决策：知识来源可信 + 反馈输入校验（候选池安全组）。
依据：[FDI](../research/candidate-pool.md)、[RAG 投毒](../research/candidate-pool.md)

---

## 六、仍未解决的关键问题（建议下一步）

| # | 问题 | 现状 |
|---|------|------|
| 1 | **飞轮闭环能否真的收敛（最根本的验证）** | 纯纸面设计，无实验验证 → **建议小规模 PoC** |
| 2 | AI 推荐路径具体内容 | 待用户补充 |
| 3 | 用例集来源/规模/UT 覆盖率 | 待定 |
| 4 | 上亿行代码切分策略 | 未开始 |
| 5 | 溯源链接 frontmatter 具体规范 | 待细化 |
| 6 | 相似度指标（若 TDD 不采纳） | 待定 |

> 📎 完整映射：[research-mapping.md](research-mapping.md) ｜ 全量候选：[candidate-pool.md](../research/candidate-pool.md) ｜ 检索方法：[retrieval-method.md](../research/retrieval-method.md)
