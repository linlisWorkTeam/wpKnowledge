# 多 Agent 架构调研（知识飞轮全链路应用评估）

> 日期：2026-08-26
> 定位：调研多 Agent 架构模式与框架在知识飞轮全链路中的应用取舍。设计基线仍以 [知识飞轮实现方案](设计/知识飞轮实现方案.md) 为准；本文回答"哪些多 Agent 模式值得引入、哪些明确不引入、为什么"。
> 结论先行：**当前 3+1+1 最小充分集（知识生成/Coder/Review + 编排层 + 评测闭环）是正确基线；多 Agent 只在"文档超长分块、关键模块跨模型审查"两处按需启用，不引入重型多 Agent 框架。**

---

## 0. 结论摘要（可直接引用）

1. **主 Agent 不需要**。编排层用确定性状态机（代码）承担规划/委派/决策，比 LLM 主 Agent 更可靠、可审计、不烧 token。Anthropic 实测：多 Agent 系统 token 消耗约为普通对话的 **15 倍**，且"大多数编码任务并行度低，LLM 尚不擅长实时协调委派"，与我们场景直接相关。
2. **文档生成后是否需要 subagent 检索定位：需要，分两档**。① 超大代码库/多模块生成：按函数/模块分块，每块独立 subagent 并行生成（subagent = 上下文压缩器）；② 迭代修订：按修订指令的 knowledge_path 精准定位段落，不重读全文。
3. **Review 选型：独立上下文审查（CCR）是硬结论，但不需要辩论式多 Review**。跨上下文独立审查 F1 28.6% vs 同会话自审 24.6%；同会话重复审两次无增益（p=0.11），优势来自"上下文分离"本身。我们的 Coder/Review 分离已天然满足，继续保持。
4. **spec→TDD + spec→code + 独立检查的设想成立，但测试来源有优先级**。同一 spec 派生的 TDD 测试与代码共享盲区，只能做冒烟/需求澄清；门禁主判必须用探针跑真实源码的期望输出。独立检查 agent 用 CCR 模式（全新 session + 只读 + 判据清单）。
5. **框架选型：不引入 LangGraph/CrewAI/AutoGen/MetaGPT**。我们的流水线固定、状态机简单、产物文件交接，自研编排层已覆盖；重型框架带来的是状态管理/图执行复杂度与厂商绑定，收益为负。

---

## 1. 多 Agent 架构模式全景与适用性

### 1.1 模式清单（2026 主流分类）

| 模式 | 结构 | 典型代表 | 优势 | 劣势 |
|---|---|---|---|---|
| Orchestrator-Worker（主从） | 主 Agent 规划委派，subagent 并行执行 | Anthropic Research、Claude Code | 上下文隔离、并行压缩、可扩展 | token 消耗大、协调复杂 |
| Pipeline（流水线） | 固定顺序接力，产物交接 | ChatDev、软件工厂 | 简单可审计、每步独立 | 无并行、单点失败 |
| Fan-out（扇出） | 同一任务分发给多个 agent，聚合结果 | 投票/加权/LLM 合成 | 广度覆盖、多样性 | 成本线性增长 |
| Hierarchical（分层） | 多级主从，上级管下级 | HALO | 规模化、职责清晰 | 延迟高、调试难 |
| Debate（辩论） | 多 agent 对抗论证 | Multi-Agent Debate、ARIS | 暴露单 agent 盲区、降幻觉 | 昂贵、可能不收敛、位置偏差 |
| Blackboard（黑板） | 共享工作区，agent 异步读写 | 经典 MAS、黑板论文 2507.01701 | 松耦合、灵活 | 一致性难保证、竞争条件 |
| Swarm（群集） | 轻量 agent 池，动态路由 | OpenAI Swarm、ruflo | 灵活、任务型 | 无状态、难追踪 |
| Mesh（网状） | 任意 agent 间直接通信 | A2A 协议场景 | 最灵活 | 最难调试、无边界 |

### 1.2 对本项目的适用性评分（1-5）

| 模式 | 适用分 | 应用点 | 不应用的原因 |
|---|---|---|---|
| **Pipeline** | ⭐⭐⭐⭐⭐ | **就是我们的固定流水线**（源码→知识→代码→评测→归因→修订） | — |
| **Orchestrator-Worker** | ⭐⭐⭐⭐ | 文档分块生成（每函数/模块一个 subagent） | 只在文档超长时启用 |
| **Hierarchical** | ⭐⭐⭐ | 未来全库级：仓库→模块→函数三级 | 当前单模块不需要 |
| **Debate** | ⭐⭐ | 关键模块跨模型 review 可借鉴对抗思想 | 成本高、SWR-Bench 警告架构不保证更强 |
| **Fan-out** | ⭐⭐ | 多候选代码生成（pass@k）P1 可考虑 | 当前重复评测 5 次已覆盖稳定性 |
| **Blackboard** | ⭐ | 无 | 我们的文件交接已实现同样的松耦合，且更可审计 |
| **Swarm / Mesh** | ⭐ | 无 | 无状态、难追踪，与"可审计"基线冲突 |

**关键洞察**：我们的"固定流水线 + 文件交接"本质上就是 Pipeline 模式的工程化，且**文件交接 = 显式黑板**（每个产物：知识 md/代码/评测 json/归因 json，都是持久化的共享状态），比内存黑板更可靠（可断点续跑、可审计）。不需要额外引入黑板框架。

---

## 2. 关键实证：Review 该怎么做（CCR 与对抗审查）

### 2.1 Cross-Context Review（arXiv 2603.12123，本轮最强证据）

对照实验：30 个工件（代码/技术文档/演示脚本）+ 150 个注入错误，4 种审查条件：

| 条件 | F1 | 说明 |
|---|---|---|
| Same-session Self-Review (SR) | 24.6% | 同会话自审 |
| Repeated Self-Review (SR2) | 21.7% | 同会话审两次 |
| Context-aware Subagent (SA) | 23.8% | 带上下文的 subagent 审查 |
| **Cross-Context Review (CCR)** | **28.6%** | **全新 session，只有工件 + 审查 prompt** |

关键结论：
- **CCR 显著优于所有基线**（p<0.01），代码工件增益最大（+4.7 F1），关键错误 +11pp
- **SR2 不优于 SR（p=0.11）**：优势来自上下文分离，不是"多审一次"，这直接否决"多 Review agent 辩论"的必要性
- 机制：无锚定（不继承生成时的决策）、无确认循环、短上下文（~5K vs 50K+）、审查者不知道是自己写的（消除 sycophancy/self-preference）

**对我们的映射**：Coder 与 Review 是独立角色、独立 prompt、Review 只看评测报告，已满足 CCR。**注意保持**：Review prompt 不应携带 Coder 的推理过程、设计取舍说明，只给最终工件 + 判据。

### 2.2 Adversarial Code Review（Augment Code，2026-07）

maker-checker 模式（银行 Clark-Wilson 模型）：写代码的 agent 永远不认证自己的代码。

Reviewer 与 Maker 的 5 个结构分离维度：

| 维度 | Maker | Verifier |
|---|---|---|
| 上下文 | 完整会话历史 | **全新上下文：只有 diff + 判据** |
| System prompt | 实现导向 | **怀疑式审查清单** |
| 模型 | 任意（通常大模型规划） | **显式固定，最好跨家族** |
| 工具 | Write/Edit/Bash 全量 | **只读：Read/Grep/Glob** |
| 输出 | 自由格式 | 结构化发现 |

实证细节：
- 跨家族审查（Codex + Claude 家族同查一代码库）能补盲区：libfuse 战役中 Codex 发现了 Claude 家族漏掉的缺陷（产生公开 CVE）
- 同家族循环会漏：同族模型共享相关性盲区，常在同一处自信地一致
- **SWR-Bench 警告：架构本身不保证更强**，prompt 和上下文范围决定实际效果，不能只堆 agent 数

**对我们的映射**：Review 工具权限已是只读（沙箱），符合；模型跨家族在 GLM 5.1 单模型内网环境下不可用，记录为 P1 可选项（公司内若有第二模型可启用）。

### 2.3 LLM-as-Judge 的坑（CodeJudgeBench 2507.10535 等）

- **位置偏差**：交换 A/B 顺序可改变胜者，差异高达 14%
- **自我偏好**：模型给自己生成的内容打分更高（去掉作者信息后几乎消失）
- **详尽度偏差**：更长的答案更受偏爱

→ 门禁主判绝不用 LLM 打分，用编译+测试执行；LLM 只做归因解释（不进通过/失败判定）。我们已如此。

---

## 3. spec→TDD + spec→code + 独立检查：设想评估

### 3.1 相关实证

**TDD-Agent（arXiv 2608.16742）**：
- test-first reasoning：先写测试再写实现，LiveCodeBench 上持续优于纯推理基线（GPT 70.04 vs 68.48）
- dual-track co-refinement：代码和测试**一起**迭代精化（测试是"演化的推理工件"，不是固定验证器）
- 注意：TDD-Agent 是**单 agent 双轨**，不是多 agent

**Spec-Driven Test Gen（Google，arXiv 2608.17177）**：
- spec 驱动 agent 先显式文档化前置条件/后置条件/未定义行为，再生成测试
- bug 检出率 +9.8pp（p=0.0352）、分支覆盖 +2.5pp，spec 是"认知脚手架"

**SDAD（arXiv 2608.20341，2026-05）**：
- 正式化"意图捕获 → 机器可读 spec → agentic 合成 → **独立多 agent 验证 + 人工签字**"
- 核心论点：agentic 速度不消除工程纪律，只是把纪律前置到 spec 精度、显式门禁、可审计溯源
- **合成权与发布权分离**，与我们"谁生成谁可改、谁评测谁不改"完全一致

**AgentCoder / MASTOR**：programmer/tester 角色分离能提升正确性；MASTOR 用多 agent 从源码提取约束生成 oracle，提升 mutation score。

### 3.2 设想验证结论

你的设想（agent1: spec→TDD，agent2: spec→code，agent3: 独立检查）**成立且有理论支撑**，但有一个关键陷阱：

> ⚠️ **共享盲区问题**：agent1 和 agent2 从同一份 spec 推导，共享对 spec 的理解盲区。agent1 生成的测试只验证"它理解的 spec"，agent2 按同样理解写代码，测试全绿但双方都错（self-generated test bias，Chen et al. 2025）。

**修正后的定位（测试/判据来源优先级）**：

| 优先级 | 来源 | 角色 | 说明 |
|---|---|---|---|
| 1（最强） | **探针运行真实源码的期望输出** | 评测集（现有） | 独立于任何 agent 的理解，门禁主判 |
| 2 | 独立 tester agent（不同模型家族） | agent1 升级版 | 与生成器盲区不相关 |
| 3（最弱） | 同 spec 的 TDD agent 生成 | 冒烟/需求澄清 | 只能防"完全跑偏"，不能防"共同误解" |

**推荐实现形态**：
- agent1（TDD）生成的测试 = **需求澄清 + 冒烟用例**，输入是 spec/知识文档，输出进"候选测试池"
- agent2（Coder）按知识生成实现，现有
- agent3（独立检查，CCR 模式）= 全新 session + 只读 + 判据清单，做语义层检查（测试覆盖不到的：命名、边界设计、一致性）
- 门禁主判保持：编译 + 探针测试（agent1 的测试**不进门禁**，除非人工审过并固化进评测集）

### 3.3 成本账

Anthropic 实测：单 agent 编码 ≈ 4× chat token，多 agent ≈ 15× chat token。三 agent 分工（TDD+Code+Check）的收益主要在"需求澄清质量"和"语义层缺陷"，只在核心模块值得；普通模块保持 1 Coder + 1 Review 最小集。

---

## 4. 具体框架选型：为什么都不引入

| 框架 | 定位 | 评估 |
|---|---|---|
| **LangGraph** | 图状态机编排 | 我们状态机已实现（pass/iterate/rollback/unstable/stopped），引入 = 用复杂框架重写简单逻辑，负收益 |
| **CrewAI** | 角色团队编排 | 角色系统是声明式的，我们的角色是代码类，且需要沙箱/写保护/评测集成，框架表达不了 |
| **AutoGen** | 对话式多 agent | 我们**刻意不用对话**（文件交接，防上下文污染），与 AutoGen 范式冲突 |
| **MetaGPT** | SOP 驱动软件工厂 | SOP 思想可借鉴（角色手册），但整体太重；我们的 3 角色已收敛 |
| **OpenAI Swarm** | 轻量多 agent 路由 | 无状态、难追踪，与"可审计"冲突 |
| **Claude Code / Codex CLI** | 单 agent 编码工具 | P0-D 目标 codeagent CLI 属此类；作为"执行终端"接入而非编排框架 |

**唯一值得借鉴的思想**（不引入代码）：
- MetaGPT 的 SOP/角色手册：把知识生成 skill 写成可执行手册（已有 ADAPT_PROMPT.md 雏形）
- ChatDev 的"阶段化移交"：每个阶段产物有明确验收标准（我们的门禁已做）

---

## 5. 推荐架构（最终定稿）

```
┌─ 编排层（确定性状态机，代码实现，不烧 token）──────────────┐
│  决策 / 回滚 / 预算 / 审计 / 断点续跑                       │
├───────────────────────────────────────────────────────────┤
│ 知识生成阶段：                                              │
│   [单模块] 1 个知识生成 agent（现有）                        │
│   [超大库] 分块 + N 个 subagent 并行（每函数/模块独立上下文） │
│            主 agent 只做拼接与一致性检查                    │
├───────────────────────────────────────────────────────────┤
│ 迭代阶段（每轮）：                                          │
│   Coder agent（只读知识+接口 → 写代码）                     │
│   评测闭环（编译 + 探针测试 + 相似度）← 门禁主判            │
│   Review agent（CCR 模式：全新 session + 只读 + 判据）      │
│     ├─ 确定性信号（编译/测试/相似度）                       │
│     └─ LLM 语义检查（可选：关键模块开跨模型/对抗模式）       │
│   知识修订（按 knowledge_path 定位段落，版本 +1）           │
├───────────────────────────────────────────────────────────┤
│ P1 可选项：                                                 │
│   pass@k 多候选（fan-out）· 跨模型 review · 薄弱点地图       │
└───────────────────────────────────────────────────────────┘
```

### 引入多 Agent 的触发条件（成本闸门）

| 场景 | 动作 | 不做的代价 |
|---|---|---|
| 文档 > 单上下文可处理（如 >6000 字符后仍超） | 分块 + subagent 并行 | 知识质量下降、截断丢信息 |
| 核心/高危模块 | 独立检查 agent（CCR）或跨模型 review | 语义缺陷漏网 |
| 反复触发失败的薄弱点 | 薄弱点地图 + 优先重写（可加对抗 review） | 迭代不收敛 |
| 普通模块常规迭代 | 维持最小集，不加 agent | — |

---

## 6. 文献索引

| 编号 | 文献 | 关键结论 |
|---|---|---|
| [1] | Anthropic: How we built our multi-agent research system (2025) | orchestrator-worker；多 agent ≈ 15× token；编码任务并行度低 |
| [2] | Cross-Context Review (arXiv 2603.12123) | 上下文分离审查 F1 28.6% vs 自审 24.6%；重复审无增益 |
| [3] | Augment Code: Adversarial Code Review (2026-07) | maker-checker 5 维分离；跨家族补盲区；SWR-Bench 警告 |
| [4] | TDD-Agent (arXiv 2608.16742) | test-first reasoning + dual-track 代码/测试共精化 |
| [5] | Spec-Driven Test Gen, Google (arXiv 2608.17177) | spec 脚手架 bug 检出 +9.8pp |
| [6] | SDAD (arXiv 2608.20341) | 合成与发布权分离；独立多 agent 验证 + 人工签字 |
| [7] | CodeJudgeBench (arXiv 2507.10535) | LLM 裁判位置偏差 14%、自我偏好 |
| [8] | Blackboard 多 agent (arXiv 2507.01701) | 黑板架构探索（我们不引入，文件交接已等效） |
| [9] | ARIS (arXiv 2605.03042) | 跨模型对抗协作：executor + 外部模型 critique |
| [10] | Multi-Agent Orchestration Patterns (glukhov.org) | 六模式 + 决策框架 + 失败模式 |
| [11] | 自进化代码 Agent 综述 (arXiv 2608.03392) | 软件特有证据分类；进化对象框架 |

> 📎 相关已有笔记：研究/反馈闭环/CRITIC工具交互式自我纠错.md、自进化Agent脆弱性.md、研究/评测/CodeJudgeBench-LLM裁判可靠性.md、研究/评测/Pass@k无偏评测指标.md

---

## 7. 待定问题（需 PoC 数据）

1. 分块阈值：多大文档该开 subagent 并行？（当前 4000 字符分块阈值是经验值）
2. 跨模型 review 是否值得：公司内网若有 GLM 之外的第二模型（如 DeepSeek），用对比实验量化盲区补充收益
3. spec→TDD 的冒烟测试固化进评测集的比例：人工审过的测试进 holdout 还是 train？
4. pass@k 多候选（fan-out）的 k 值与聚合策略（P1）
