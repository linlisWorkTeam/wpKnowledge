# 多 Agent 架构调研（知识飞轮全链路应用评估）

> 日期：2026-08-26
> 定位：调研多 Agent 架构模式与框架在知识飞轮全链路中的应用取舍。设计基线仍以 [知识飞轮实现方案](设计/知识飞轮实现方案.md) 为准；本文回答"哪些多 Agent 模式值得引入、哪些明确不引入、为什么"。
> 结论先行：**当前 3+1+1 最小充分集（知识生成/Coder/Review + 编排层 + 评测闭环）是正确基线；多 Agent 只在"文档超长分块、关键模块跨模型审查"两处按需启用，不引入重型多 Agent 框架。**

---

## 0. 结论摘要（可直接引用）

1. **主 Agent 不需要**。编排层用确定性状态机（代码）承担规划/委派/决策，比 LLM 主 Agent 更可靠、可审计、不烧 token。Anthropic 实测：多 Agent 系统 token 消耗约为普通对话的 **15 倍**，且"大多数编码任务并行度低，LLM 尚不擅长实时协调委派"，与我们场景直接相关。
2. **文档生成后是否需要 subagent 检索定位：需要，分两档**。① 超大代码库/多模块生成：DocGenAgent 分块 + DocWorkerAgent 并行（每块独立上下文，subagent = 上下文压缩器）；② 迭代修订：按修订指令的 knowledge_path 精准定位段落，不重读全文。
3. **Review 选型：独立上下文审查（CCR）是硬结论，但不需要辩论式多 Review**。跨上下文独立审查 F1 28.6% vs 同会话自审 24.6%；同会话重复审两次无增益（p=0.11），优势来自"上下文分离"本身。我们的 Coder/Review 分离已天然满足，继续保持。
4. **TestGenAgent + CodeAgent + CheckAgent 的设想成立，且盲区问题被消除**。TestGenAgent **读源代码**（而非知识文档）提取行为 oracle，期望输出经 EvalRunner 验证真实性后进门禁，与 CodeAgent 的知识文档理解解耦。CheckAgent 用 CCR 模式（全新 session + 只读 + 判据清单）。
5. **框架选型：不引入 LangGraph/CrewAI/AutoGen/MetaGPT**。我们的流水线固定、状态机简单、产物文件交接，自研编排层已覆盖；重型框架带来的是状态管理/图执行复杂度与厂商绑定，收益为负。

---

## 1. 多 Agent 架构模式全景与适用性

### 1.1 模式清单（2026 主流分类）

| 模式 | 结构 | 典型代表 | 优势 | 劣势 |
|---|---|---|---|---|
| Orchestrator-Worker（主从） | 主 Agent 规划委派，subagent 并行执行 | Anthropic Research、Claude Agent SDK | 上下文隔离、并行压缩、可扩展 | token 消耗大、协调复杂 |
| Pipeline（流水线） | 固定顺序接力，产物交接 | gpt-engineer、DocAgent | 简单可审计、每步独立 | 无并行、单点失败 |
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

```text
流程图：Review 方案选型（按可靠性/成本权衡）
   生成代码/文档（Coder / Writer）
                │
                ▼
   ┌──────────────────────────┐
   │ ① 同会话自审（Self-Review） │ ← 最省，但 F1 最低（24.6%）
   │    审查者=生成者，同一上下文 │    锚定/确认偏误/自我偏好
   └────────────┬─────────────┘
                ▼
   ┌──────────────────────────┐
   │ ② 独立上下文审查（CCR）★    │ ← 推荐：F1 最高（28.6%）
   │    审查者=独立 session     │    只给工件+判据，无生成历史
   │    只读权限，不知道作者     │    成本：仅多一个 session
   └────────────┬─────────────┘
                ▼
   ┌──────────────────────────┐
   │ ③ 对抗/辩论式多审查         │ ← 按需：关键模块才开
   │    多 agent 相互批判        │    成本随 轮次×agent数 暴涨
   │    或跨模型家族（补盲区）     │    同会话重复审两次无增益(p=0.11)
   └──────────────────────────┘

   关键结论：
   - ②（CCR）显著优于①③，代码工件增益最大（+4.7 F1，关键错误 +11pp）
   - ③中"同会话多审"无效，有效的是"跨上下文/跨模型"多样性
   - 本项目 Coder/Review 分离已天然满足 CCR，保持即可
```

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

## 3. TestGenAgent + CodeAgent + CheckAgent：设想评估

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

你的设想（agent1: spec→TDD，agent2: spec→code，agent3: 独立检查）**成立且有理论支撑**，但原形式有一个关键陷阱：

> ⚠️ **共享盲区问题（原设想）**：agent1 和 agent2 从同一份 spec 推导，共享对 spec 的理解盲区。agent1 生成的测试只验证"它理解的 spec"，agent2 按同样理解写代码，测试全绿但双方都错（self-generated test bias，Chen et al. 2025）。

**用户 2026-08 拍板更正：TestGenAgent 读源代码，消除共享盲区**。测试基准从"agent 对 spec 的理解"改为"真实源码行为"：

| 优先级 | 来源 | 角色 | 说明 |
|---|---|---|---|
| 1（最强） | **TestGenAgent 读源码的行为 oracle**（期望输出经 EvalRunner 跑真实源码验证） | 门禁主判 | 独立于 CodeAgent 对知识文档的理解；真实行为基准 |
| 2 | **探针运行真实源码的期望输出** | 评测集（现有） | 与 TestGenAgent 同源（真实行为）；作为 oracle 验证基准 |
| 3 | 独立 tester agent（不同模型家族） | agent1 升级版 | 与生成器盲区不相关（P1 可选） |
| 4（已弃） | 同 spec 的 TDD agent 生成 | ~~冒烟/需求澄清~~ | **用户已拍板不用**：读知识文档的测试与 CodeAgent 共享盲区 |

**推荐实现形态（2026-08 定稿）**：
- TestGenAgent **读源代码 + 接口头文件** → 提取行为 oracle → 候选测试池 → EvalRunner 跑真实源码验证期望输出 → 固化进门禁
- CodeAgent 读知识文档（DocGenAgent 产物）+ 接口 → 生成实现（Sandbox 强制，看不到源码）
- CheckAgent（独立检查，CCR 模式）= 全新 session + 只读 + 判据清单，做语义层检查（测试覆盖不到的：命名、边界设计、一致性）
- ReviewAgent 归因失败 → 修订指令反馈给 DocGenAgent 优化知识文档（版本 +1）→ CodeAgent 基于新知识重新生成 → 重测
- 门禁主判 = 经验证的行为 oracle 测试（客观），CheckAgent 语义检查为补充

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
| **Claude Agent SDK / Codex CLI** | 单 agent 编码工具（开源） | P0-D 目标 codeagent CLI 属此类；作为"执行终端"接入而非编排框架（Claude Code 本体闭源黑盒不选，用开源 SDK 版） |

**唯一值得借鉴的思想**（不引入代码）：
- MetaGPT 的 SOP/角色手册：把知识生成 skill 写成可执行手册（已有 ADAPT_PROMPT.md 雏形）
- gpt-engineer/DocAgent 的"阶段化移交"：每个阶段产物有明确验收标准（我们的门禁已做）

---

## 4.5 本项目目标 Agent 架构（定稿：Agent 清单 + 工作流程）

> 本节是目标架构的**最终定义**：明确的 Agent 数量、命名（统一 `xxxAgent`）、职责边界、工作流程。技术栈统一 **TypeScript**。论文依据仅采用 2025 年及以后的研究（见 §4.6）。
> 语言约定：所有 Agent 命名后缀统一为 `Agent`，如 `CodeAgent`；代码接口用 TypeScript 定义。

### 4.5.0 Agent 清单（共 7 类，3 类可选实例）

| # | Agent | 职责 | 输入 | 输出 | 类型 |
|---|---|---|---|---|---|
| 1 | **OrchestratorAgent** | **只负责调度**：规划任务/拆解模块/委派 subagent/汇总/驱动重试（决策归门禁规则，不执笔、不判断内容） | 用户需求、评测报告 | 任务计划、调度指令（pass/iterate/rollback/stopped 由门禁 decide 状态机给出） | 核心（必选） |
| 2 | **DocGenAgent** | 知识文档生成（读源码→解释型知识），唯一执笔者；接收 ReviewAgent 修订指令优化知识文档 | 源码文件、模块清单、修订指令 | 知识文档（OKF 格式，sources 溯源） | 核心（必选） |
| 3 | **DocWorkerAgent** | 分块并行生成知识（每块独立上下文），DocGenAgent 的并行实例 | 模块子集、依赖图 | 分块知识片段（回传结构化摘要+溯源） | 可选（大库才开） |
| 4 | **TestGenAgent** | **读源代码→测试/冒烟用例**（行为 oracle 提取，期望输出须经真实源码验证） | **源代码、接口头文件** | 测试用例集（候选测试池，经 EvalRunner 验证后进门禁） | 核心（必选） |
| 5 | **CodeAgent** | 知识文档+接口头文件→实现代码（物理隔离源码） | **知识文档（DocGenAgent 产物）**、接口 | 实现代码文件 | 核心（必选） |
| 6 | **CheckAgent** | 独立检查（CCR 模式）：语义层审查代码/测试 | 代码 diff、判据清单 | 检查报告（发现清单，非打分） | 核心（必选） |
| 7 | **ReviewAgent** | 评测失败归因 + 修订指令（readlist 三字段），**反馈给 DocGenAgent 优化知识文档** | 评测报告、知识文档 | 归因报告（weak_spots/corrections，→ DocGenAgent） | 核心（必选） |

> 非 Agent 组件（确定性程序，不算 Agent）：**EvalRunner**（编译+探针测试+相似度，门禁主判；负责验证 TestGenAgent 产出的期望输出真实性）、**Sandbox**（路径白名单隔离）、**Protection**（SHA-256 写保护）、**KnowledgeStore**（知识库落盘/版本/ledger）。

### 4.5.1 总体工作流程（纯文本流程图）

```text
流程图：知识飞轮目标架构工作流程（Agent 统一 xxxAgent 命名）
                 ┌──────────────────────────────────────────────────┐
                 │            OrchestratorAgent（主 Agent）          │
                 │   只负责调度：规划 / 拆解 / 委派 / 汇总 / 驱动重试  │
                 │   （决策由门禁 decide 状态机给出，不执笔、不判内容）  │
                 └───────┬──────────────────────┬───────────────────┘
                         │                      │
   源码 src_dir          │ 委派文档生成           │ 委派测试+代码生成
   （只读）               ▼                      ▼
        │      ┌────────────────────┐  ┌──────────────────────────┐
        │      │  DocGenAgent        │  │ TestGenAgent（读源码）     │
        │      │  读源码→知识文档      │  │  CodeAgent（读知识文档）    │
        │      │  （大库时 spawn      │  │  两 agent 并行、上下文隔离  │
        │      │   DocWorkerAgent×N） │  │                           │
        │      └─────────┬──────────┘  └─────────────┬────────────┘
        │                │ 知识文档 .md               │ 测试集 + 实现代码
        │                ▼                           ▼
        │      ┌────────────────────┐  ┌──────────────────────────┐
        │      │  KnowledgeStore     │  │  CheckAgent（CCR 独立检查） │
        │      │  （候选区+版本+ledger）│  │  只读 diff+判据，语义层审查 │
        │      └────────────────────┘  └─────────────┬────────────┘
        │                                            │ 检查报告
        │                                            ▼
        │      ┌──────────────────────────────────────────────────┐
        │      │        EvalRunner（确定性程序，非 Agent）           │
        │      │  编译必过（g++ -Werror）+ 探针测试 + 相似度（仅归因）  │
        │      │  验证 TestGenAgent 测试的期望输出与真实源码一致        │
        │      └───────────────────────┬──────────────────────────┘
        │                              │ 评测报告 .json
        │                              ▼
        │      ┌──────────────────────────────────────────────────┐
        │      │  ReviewAgent（独立上下文 CCR，只读）                 │
        │      │  归因：失败用例→定位知识段落→修订指令（三字段）        │
        │      └───────────────────────┬──────────────────────────┘
        │                              │ 归因/修订 .json
        │                              ▼
        │      ┌──────────────────────────────────────────────────┐
        │      │  OrchestratorAgent 调度 + 门禁 decide 状态机        │
        │      │  pass / iterate / rollback / stopped（规则给出）    │
        │      └──────────────┬───────────────────────────────────┘
        │        iterate：修订指令→ DocGenAgent 优化知识文档（v+1）
        │                  → CodeAgent 基于新知识重新生成→重测
        │                                                        pass
        └───────────────────────────────────────────────────►    ▼
                                                  知识发布 KnowledgeStore
                                                  （verified，SHA-256 快照）

   分工边界（硬规则）：
   - 谁生成谁可改，谁评测谁不改（生成与验证分离）
   - DocGenAgent 产出的知识文档是 CodeAgent 的唯一事实输入（Sandbox 强制，CodeAgent 物理看不到源码）
   - TestGenAgent 读源码提取行为 oracle；期望输出必须经真实源码验证，禁止 LLM 编造
   - ReviewAgent 评审结果反馈给 DocGenAgent 优化知识文档（不改代码；代码由新知识文档驱动重生成）
   - OrchestratorAgent 只调度不执笔，决策归门禁规则
   - 全部产物文件交接，可审计、可断点续跑
```

### 4.5.2 文档生成阶段（DocGenAgent 分块 + DocWorkerAgent 检索定位）

```text
流程图：文档生成分块 + DocWorkerAgent 检索定位
   ┌─────────────┐   按依赖拓扑拆块   ┌─────────────────────┐
   │ 源码仓库      │ ────────────────►│ OrchestratorAgent    │
   │ 30万行/仓     │  (include/依赖图)  │  规划分块（≤5 块并行） │
   └─────────────┘                   └──────────┬──────────┘
                                                │ 每块一个独立上下文
                                    ┌───────────┼───────────┐
                                    ▼           ▼           ▼
                            ┌───────────┐┌───────────┐┌───────────┐
                            │DocWorker  ││DocWorker  ││DocWorker  │
                            │Agent_1    ││Agent_2    ││Agent_3    │
                            │ 模块A知识  ││ 模块B知识  ││ 模块C知识  │
                            └────┬──────┘└────┬──────┘└────┬──────┘
                                 │            │            │
                                 ▼            ▼            ▼
                            ┌────────────────────────────────────┐
                            │ DocGenAgent 汇总/一致性检查/拼接      │
                            │ → 知识文档（OKF + sources 溯源）      │
                            └────────────────────────────────────┘

   检索定位（迭代修订时，不重读全文）：
   修订指令 ──► 按 knowledge_path 定位段落 ──► 只取命中段落给 DocGenAgent
   每个 DocWorkerAgent 独立上下文 = 防上下文超长的核心手段
   （Anthropic 实证：subagent 本质是压缩器，各自窗口并行探索后压缩回传）
```

### 4.5.3 代码生成阶段（TestGenAgent + CodeAgent + CheckAgent 三 Agent）

```text
流程图：TestGenAgent + CodeAgent + CheckAgent（三 Agent 分工）
         ┌──────────────────┐          ┌──────────────────┐
         │   源代码 src_dir   │          │  知识文档（spec）  │
         │  （TestGen 只读）  │          │  （DocGenAgent 产物）│
         └────────┬─────────┘          └────────┬─────────┘
                  │ 行为 oracle                │ 唯一事实输入
     ┌────────────┼────────────┐              │
     ▼            ▼            │              ▼
┌──────────┐ ┌──────────┐     │      ┌────────────────┐
│TestGen   │ │ EvalRunner│     │      │ CodeAgent      │
│Agent     │ │ 验证期望   │     │      │ 生成实现代码    │
│读源码→测试│ │ 输出真实性 │     │      │ 只读知识+接口   │
│(行为oracle)│ └────┬─────┘     │      │ 输出：实现 .cpp │
└────┬─────┘      │ 固化      │      └───────┬────────┘
     │ 候选测试池  │ 进门禁     │              │
     ▼            ▼           │              ▼
┌────────────────────────┐    │      ┌────────────────────────┐
│ 门禁测试集（经真实源码验证）│◄───┘      │ CheckAgent（CCR 模式）   │
│ = 探针期望输出，独立于     │            │ 全新 session，只读：     │
│   CodeAgent 可见范围     │            │ diff+判据清单           │
└────────────────────────┘            │ 检查：语义/边界/一致性   │
                                      └───────────┬────────────┘
                                                  │ 检查报告（发现清单）
                                                  ▼
   ┌─────────────────────────────────────────────────────┐
   │ EvalRunner：编译必过 + 门禁测试（期望输出=经真实源码验证）│
   │ 门禁主判 = 客观期望输出测试，不依赖任何 agent 自我感觉    │
   └─────────────────────────────────────────────────────┘

   注（盲区消除）：TestGenAgent 读的是源代码（行为 oracle），CodeAgent
   读的是知识文档（事实输入），两者不共享同一份文档的理解盲区：
   - TestGenAgent 期望输出 = 真实源码行为 → 由 EvalRunner 跑真实源码验证，禁 LLM 编造
   - CodeAgent 只能看知识文档 → 知识文档若有错，测试（真实行为）必失败 → 触发迭代
   - CheckAgent 独立检查 = 语义层补充（测试覆盖不到的：命名/边界/设计）
```

### 4.5.4 Review 阶段（ReviewAgent 独立上下文 CCR，反馈给 DocGenAgent）

```text
流程图：ReviewAgent（CCR 独立上下文模式）
   ┌─────────────────┐
   │ 评测报告（客观信号）│
   └────────┬────────┘
            ▼
   ┌─────────────────────────────────────┐
   │ ReviewAgent（全新 session，无生成历史）│
   │  · 只给：工件 + 评测失败详情 + 判据清单  │
   │  · 不给：CodeAgent 的推理过程/设计取舍  │
   │  · 只读权限（Read/Grep），无写权限      │
   │  · 不知道作者是谁（消除自我偏好）        │
   └────────┬────────────────────────────┘
            ▼
   ┌─────────────────────────────────────┐
   │ 输出：归因报告（summary/weak_spots/    │
   │ corrections 修订指令三字段）            │
   └────────┬────────────────────────────┘
            ▼
   ┌─────────────────────────────────────┐
   │ 反馈给 DocGenAgent：按 knowledge_path │
   │ 定位段落 → 优化知识文档（版本 +1）      │
   │ → CodeAgent 基于新知识重新生成 → 重测   │
   └─────────────────────────────────────┘

   可选增强（P1，关键模块才开）：
   - 跨模型家族二查（GLM + DeepSeek 同查，补同族盲区）
   - 对抗式（PrimaryReviewer + Challenger + Arbiter）
   实证（CCR，2026）：F1 28.6% vs 同会话自审 24.6%；同会话重复审两次无增益
```

### 4.5.5 Agent 接口定义（TypeScript）

```typescript
// 知识飞轮目标架构 · Agent 接口（TypeScript）
// 约定：所有 Agent 命名后缀统一为 Agent；产物全部文件交接（可审计/断点续跑）

/** 统一 Agent 基类：输入 → 输出（产物落盘路径） */
interface Agent<I, O> {
  readonly name: string;
  run(input: I): Promise<O>;
}

// ---------- 产物类型（文件交接的契约） ----------
interface KnowledgeDoc {
  module: string;
  version: number;
  content: string;          // OKF Markdown
  sources: SourceRef[];     // 溯源锚点（file + symbol + commit）
  status: "draft" | "verified" | "rejected";
  sha256: string;
}

interface SourceRef {
  file: string;
  symbol: string;
  commit: string;
}

interface TestCase { id: string; description: string; expected: string; }
interface CodeArtifact { path: string; language: "c" | "cpp"; }

interface EvalReport {
  compileOk: boolean;
  passed: number;
  total: number;
  confidence: number;       // passed / total
  repetitions: { mean: number; variance: number; unstable: boolean };
  similarity: number;       // 仅归因，不进门禁
  failures: string[];
  reasonCodes: string[];
}

interface Correction {
  id: string;               // 修订指令 ID
  knowledgePath: string;    // 知识段落路径
  criterion: string;        // 可执行验证判据
}

interface AttributionReport {
  summary: string;
  weakSpots: string[];
  corrections: Correction[];
}

// ---------- Agent 接口（7 类） ----------
// OrchestratorAgent：只调度（规划/委派/汇总/驱动重试），决策由门禁 decide 状态机给出
interface OrchestratorAgent extends Agent<{
  request: string;
  moduleGraph: ModuleGraph;
  evalReport?: EvalReport;   // 每轮评测后传入，供调度决策
}, {
  plan: TaskPlan;
  dispatch: DispatchCommand; // 委派指令（谁→什么输入→期望产物）
  decision: "pass" | "iterate" | "rollback" | "stopped"; // 由门禁 decide 规则给出
}> {}

// DocGenAgent：知识文档生成（唯一执笔者）；接收 ReviewAgent 修订指令优化知识文档
interface DocGenAgent extends Agent<{
  module: string;
  srcFile: string;
  sources: SourceRef[];
  corrections?: Correction[];   // ReviewAgent 修订指令（迭代时传入）
}, KnowledgeDoc> {}

interface DocWorkerAgent extends Agent<{
  moduleSubset: string[];
  depGraph: DepGraph;
}, { chunk: string; sources: SourceRef[] }> {}

// TestGenAgent：读源代码提取行为 oracle（期望输出须经 EvalRunner 验证）
interface TestGenAgent extends Agent<{
  srcFile: string;            // 源代码（只读）
  interfaceHeader: string;    // 接口头文件（只读）
}, { testCases: TestCase[] }> {}  // 候选测试池 → EvalRunner 验证后固化进门禁

// CodeAgent：只读知识文档（DocGenAgent 产物）+ 接口，物理看不到源码
interface CodeAgent extends Agent<{
  doc: KnowledgeDoc;          // 唯一事实输入（DocGenAgent 产物）
  interfaceHeader: string;    // 只读接口，物理看不到源码
}, CodeArtifact> {}

interface CheckAgent extends Agent<{
  diff: string;               // 只给 diff，不给生成历史（CCR）
  criteria: string[];
}, { findings: string[] }> {} // 发现清单，非打分

// ReviewAgent：归因 + 修订指令，反馈给 DocGenAgent 优化知识文档
interface ReviewAgent extends Agent<{
  doc: KnowledgeDoc;
  report: EvalReport;         // 客观评测结果
}, AttributionReport> {}      // corrections → DocGenAgent

// ---------- 非 Agent 组件（确定性程序） ----------
interface EvalRunner {
  compile(code: CodeArtifact): { ok: boolean; errors: string[] };
  runTests(code: CodeArtifact, cases: TestCase[]): EvalReport;
}
interface Sandbox { assertReadAllowed(path: string): void; }
interface Protection { snapshot(paths: string[]): void; verify(paths: string[]): void; }
interface KnowledgeStore { save(doc: KnowledgeDoc): void; load(module: string): KnowledgeDoc; }
```

### 4.5.6 与 mvp-flywheel 现状对照（目标 vs 现状差距）

| 环节 | 目标架构（Agent） | mvp-flywheel 现状 | 差距 |
|---|---|---|---|
| 统筹 | OrchestratorAgent（只调度，决策归门禁） | 确定性编排层（代码） | 用户已定：主 Agent 只调度不执笔（README 决策点 2） |
| 文档生成 | DocGenAgent + DocWorkerAgent（分块并行 + 检索定位） | 单知识生成 agent（chunk 雏形） | 需补 DocWorkerAgent 并行（README 决策点 3） |
| 测试生成 | TestGenAgent（读源码 → 行为 oracle，期望输出经 EvalRunner 验证） | 无（评测集直接来自探针） | 需新增（README 决策点 5）；输入=源代码 |
| 代码生成 | CodeAgent | 单 Coder agent | 命名对齐 |
| 独立检查 | CheckAgent（CCR） | 无独立检查 agent，靠 Review | 需新增（README 决策点 4） |
| 归因修订 | ReviewAgent | Review 独立 session（已满足 CCR） | 命名对齐；跨模型二查为 P1 |
| 门禁 | EvalRunner 探针期望输出主判 + TDD 冒烟辅助 | 探针期望输出主判（已满足） | TDD 冒烟未接入 |
| 发布 | OrchestratorAgent 决策 + 门禁通过 | decide() 确定性决策（已满足） | 一致 |
| 语言 | TypeScript | Python | **全量迁移**（用户定） |

---

## 4.6 目标架构各环节设计依据（为什么这么设计 + 论文依据）

> 按 §4 的形式逐环节展开：每个环节为什么这么设计、参考了什么论文/工作、论文的优缺点、哪些值得借鉴、哪些需要规避。论文详情见 [02-编排模式调研.md](02-编排模式调研.md) 与 [03-开源编排框架.md](03-开源编排框架.md)，已有笔记见 2.wiki/研究/。

### 4.6.1 OrchestratorAgent（主 Agent，只负责调度）

**为什么这么设计**：主 Agent **只负责调度**（规划、拆解、委派、汇总、驱动重试），不执笔、不判断内容质量。决策（pass/iterate/rollback/stopped）由门禁 decide 状态机按规则给出（客观评测信号驱动），避免 LLM 主 Agent 的主观判断污染流程。两种实现路径：LLM orchestrator（动态规划，灵活）或确定性编排层（代码状态机，可控）。我们的判断是"外层确定性 + 内层 agent 自治"。

**参考论文/工作（2025+）**：
- Anthropic《Multi-Agent Research System》（2025.06）：orchestrator-worker 实证，多 agent 比单 agent 提升 90.2%，但 token 消耗 ≈ 15 倍；subagent 滥用教训（50 个 → 成本爆炸）
- 自进化代码 Agent 综述（arXiv:2608.03392，2026.08）：Agent 框架/记忆/技能/模型/工作流五类进化对象的分类框架
- Google ADK（2025-2026）：SequentialAgent/ParallelAgent/LoopAgent 等可组合工作流 agent 基元

**论文优缺点与借鉴点**：

| 来源 | 优点（值得借鉴） | 缺点（需要规避） | 我们的取舍 |
|---|---|---|---|
| Anthropic Research System | 查询分解、并行 subagent、结果综合的完整模式 | 早期教训：简单查询 spawn 50 个 subagent 成本爆炸；限制并行数（约 5 个）+ token 预算 | OrchestratorAgent 委派必须设并行上限与预算闸门 |
| 自进化综述 | 软件特有证据分类（结果/环境/轨迹） | 综述性质，无实现细节 | OrchestratorAgent 调度只用客观证据，决策归门禁规则，不依赖自我感觉 |
| Google ADK | 工作流 agent 基元（Sequential/Parallel/Loop） | 绑定 Google Cloud | 借鉴基元思想，用 TypeScript 自研实现 |

**结论**：OrchestratorAgent = 确定性调度层（规划/委派/汇总/重试），控制并行度（≤5）、设 token 预算；**决策（pass/iterate/rollback/stopped）由门禁 decide 状态机按规则给出，主 Agent 不参与内容判断**。

---

### 4.6.2 DocGenAgent + DocWorkerAgent（文档生成分块 + 检索定位）

**为什么这么设计**：30 万行/仓、总量上亿行的源码不可能一次塞进上下文。两个手段：① 生成阶段按依赖拓扑分块，每块一个独立 DocWorkerAgent 上下文；② 修订阶段按 knowledge_path 检索定位，只取命中段落，不重读全文。

**参考论文/工作（2025+）**：
- DocAgent（Facebook，arXiv:2504.08725，2025.04）：拓扑代码处理 + 增量上下文构建 + 验证-重写闭环
- Anthropic Research System（2025.06）：subagent 本质是"上下文压缩器"，各自窗口并行探索后压缩回传
- 上下文工程（Context Engineering）2025 共识：chunk 级检索 > 整文档注入

**论文优缺点与借鉴点**：

| 来源 | 优点（值得借鉴） | 缺点（需要规避） | 我们的取舍 |
|---|---|---|---|
| DocAgent | 拓扑排序天然适配 C/C++ include 依赖；增量上下文防爆炸；Verifier 保证 truthfulness | 5 角色偏多，编排有学习成本 | 采用拓扑排序 + 增量上下文；角色合并（Reader/Searcher→DocWorkerAgent，Writer→DocGenAgent 拼接，Verifier→EvalRunner/ReviewAgent） |
| Anthropic 压缩器思想 | DocWorkerAgent 独立上下文 = 防超长的核心手段 | 汇总环节信息有损 | 每块 DocWorkerAgent 只回传结构化摘要 + 溯源锚点 |
| 上下文工程 | chunk 级检索 > 整文档注入 | 检索质量依赖索引 | 修订时按 knowledge_path 精准定位，不重读全文 |

**结论**：分块粒度按"函数/模块级"（沿用现有 chunk 雏形），DocWorkerAgent 并行上限 5；修订时按修订指令的 knowledge_path 精准定位。

---

### 4.6.3 TestGenAgent（源代码 → 测试生成，行为 oracle）

**为什么这么设计**：**TestGenAgent 读源代码**（而非知识文档）提取行为 oracle。这样测试基准 = 真实源码行为，与 CodeAgent 的知识文档理解解耦，天然消除"测试与代码共享文档盲区"的问题。期望输出必须经 EvalRunner 跑真实源码验证，禁止 LLM 编造（同探针纪律）。测试定位从"冒烟/需求澄清"升级为**门禁主判的可验证 oracle**。

**参考论文/工作（2025+）**：
- MASTOR（arXiv:2606.10465，2026.06）：多 agent 从源码提取约束生成测试 oracle，提升 mutation score（与本设计最直接对应）
- TDD-Agent（arXiv:2608.16742，2026.08）：test-first reasoning，LiveCodeBench 上持续优于纯推理基线（GPT 70.04 vs 68.48）；dual-track 代码+测试共精化
- Spec-Driven Test Gen（Google，arXiv:2608.17177，2026.08）：先显式文档化前置/后置条件再生成测试，bug 检出 +9.8pp（p=0.0352）
- 2.wiki 研究笔记：TDD-Agent、Spec-Driven Test Gen、覆盖率引导测试生成、变异测试与测试集质量

**论文优缺点与借鉴点**：

| 来源 | 优点（值得借鉴） | 缺点（需要规避） | 我们的取舍 |
|---|---|---|---|
| MASTOR | 从源码/契约提取 oracle 是正解；多 agent 协作提取约束 | 面向 REST API 场景，需改造 | 直接采用"从源码提取行为 oracle"；改造为 C/C++ 头文件+实现输入 |
| TDD-Agent | test-first 是推理框架而非流程摆设；测试是"演化的推理工件" | 单 agent 双轨（测试+代码同一个 agent 写），盲区不消除 | 借鉴 test-first 推理价值；**拆成独立 TestGenAgent**，且读源码不读知识文档 |
| Spec-Driven Test Gen | 显式文档化 pre/post-condition 提升测试质量 9.8pp | 只解决测试生成，不解决代码生成 | 要求 TestGenAgent 先输出"前置/后置条件理解"再写用例（认知脚手架） |

**关键约束（防作弊与防编造）**：
- TestGenAgent 期望输出 = 真实源码行为 → **必须由 EvalRunner 跑真实源码验证**，与真实源码不一致的用例丢弃/修正，禁止 LLM 编造期望输出
- TestGenAgent 生成测试在 Sandbox 内完成，测试集对 CodeAgent 不可见（评测独立）
- 门禁主判 = 经验证的期望输出测试（客观）；CheckAgent 语义检查为补充

---

### 4.6.4 CodeAgent（知识文档 → 代码生成）

**为什么这么设计**：代码生成是"开放任务"（目标明确但实现路径未知），由独立 CodeAgent **从 DocGenAgent 产出的知识文档** + 接口头文件生成实现；物理隔离源码（Sandbox），防止抄源码作弊。**知识文档是 CodeAgent 的唯一事实输入**：知识文档若有错，测试（真实行为 oracle）必失败，触发迭代（ReviewAgent → DocGenAgent 修知识 → CodeAgent 重生成）。

**参考论文/工作（2025+）**：
- SDAD（arXiv:2608.20341，2026.05）：spec-driven agentic development，合成权与发布权分离
- spec-kit（GitHub，2025+，⭐130k）：规格驱动开发的工业实践
- Spec-Driven Test Gen（Google，arXiv:2608.17177，2026.08）：规格契约是"认知脚手架"
- Claude Agent SDK / Codex CLI（2025-2026，开源）：在真实仓库里做代码生成/评审/测试的终端 agent 执行层

**论文优缺点与借鉴点**：

| 来源 | 优点（值得借鉴） | 缺点（需要规避） | 我们的取舍 |
|---|---|---|---|
| SDAD | 合成与发布权分离；显式门禁 + 可审计溯源 | 报告性质，无开源实现细节 | 直接采用"谁生成谁可改，谁评测谁不改"原则（已落地） |
| spec-kit | 工业界规格驱动规模化验证 | 面向新项目，非存量仓库 | 借鉴"知识文档是唯一事实源"思想 |
| Spec-Driven Test Gen | 规格契约提升测试质量 | 面向测试生成，非代码生成 | CodeAgent 输入=知识文档+接口，输出实现 |
| Claude Agent SDK/Codex | 上下文隔离执行层，超大型仓库刚需 | 绑定特定模型/计费 | 作为 CodeAgent 的 LLM 后端接入（公司 GLM 5.1 经 codeagent CLI） |

**结论**：CodeAgent 只读知识+接口（Sandbox 强制），输出实现；不直接评测、不自我验证（生成与验证分离）；知识文档错误通过测试失败暴露，由 ReviewAgent → DocGenAgent 修复。

---

### 4.6.5 CheckAgent（独立检查，CCR 模式）

**为什么这么设计**：测试覆盖不到语义层（命名、边界设计、与知识文档的一致性、隐藏缺陷）。需要一个"不知道作者是谁"的独立审查者，用全新 session + 只读 + 判据清单做检查。

**参考论文/工作（2025+）**：
- Cross-Context Review（arXiv:2603.12123，2026.03）：跨上下文独立审查 F1 28.6% vs 同会话自审 24.6%；**同会话重复审两次无增益（p=0.11）**
- Adversarial Code Review（Augment Code，2026-07）：maker-checker 五维分离（上下文/prompt/模型/工具/输出）
- LLM-as-Judge 研究（CodeJudgeBench arXiv:2507.10535，2025.07）：位置偏差 14%、自我偏好
- 2.wiki 研究笔记：CodeJudgeBench-LLM裁判可靠性

**论文优缺点与借鉴点**：

| 来源 | 优点（值得借鉴） | 缺点（需要规避） | 我们的取舍 |
|---|---|---|---|
| CCR | 方法极简（新 session 而已），收益显著，任意模型可用 | F1 绝对值仍不高（28.6%），不能替代客观测试 | 直接采用：CheckAgent 全新 session + 只给 diff+判据 |
| Adversarial Review | 五维分离清单可操作；跨模型家族补盲区（libfuse 案例） | SWR-Bench 警告：架构本身不保证更强，prompt 决定效果 | 工具只读（Read/Grep）；跨模型二查留 P1 |
| LLM-as-Judge 研究 | 提示词设计要规避位置/详尽度偏差 | LLM 打分不可靠 | CheckAgent 输出"发现清单"而非"打分"；不进通过/失败判定 |

**结论**：CheckAgent 是"语义层补充检查"，输出结构化发现；门禁判定仍由客观测试决定。

---

### 4.6.6 ReviewAgent（归因 + 修订指令，反馈给 DocGenAgent）

**为什么这么设计**：评测失败后需要定位"知识文档哪段写错了"，产出修订指令（readlist 三字段：ID + 段落路径 + 可执行判据），**反馈给 DocGenAgent 优化知识文档**（版本 +1），再由 CodeAgent 基于新知识重新生成代码。评审对象是知识文档而非代码本身（代码是知识的下游产物，改代码是治标，修知识是治本）。ReviewAgent 独立上下文（CCR），只读，不知道生成者。

**参考论文/工作（2025+）**：
- CCR（arXiv:2603.12123，2026.03）：上下文分离是核心
- 自进化代码 Agent 综述（arXiv:2608.03392，2026.08）：软件特有证据分类（结果/环境/轨迹），反馈证据组合
- SDAD（arXiv:2608.20341，2026.05）：修订指令需可执行判据，纯 NL 建议不能驱动合并
- 2.wiki 研究笔记：反馈优先于流程拓扑（Feedback Over Form，2025 版）

**论文优缺点与借鉴点**：

| 来源 | 优点（值得借鉴） | 缺点（需要规避） | 我们的取舍 |
|---|---|---|---|
| 自进化综述 | 反馈证据分类（结果/环境/轨迹） | 综述性质，无实现细节 | ReviewAgent 输入 = 客观评测报告（结果证据），不掺主观 |
| SDAD | 修订需可执行判据 | 报告性质 | 修订指令三字段（ID+段落路径+可执行判据），纯 NL 不能驱动合并 |
| Feedback Over Form | 反馈质量优先于流程拓扑 | 无具体实现 | 反馈 = 结构化信号（失败用例/diff/通过率）+ NL 解读两层 |
| CCR | 上下文分离消除自我偏好 | F1 绝对值有限 | ReviewAgent 不给 CodeAgent 推理历史 |

**结论**：ReviewAgent 只读评测报告 + 工件，输出结构化归因（summary/weak_spots/corrections）；修订指令必须含可执行判据；**corrections 反馈给 DocGenAgent 优化知识文档，代码由新知识文档驱动重生成（不直接改代码）**。

---

### 4.6.7 EvalRunner（探针期望输出主判 + TestGenAgent 期望输出验证）

**为什么这么设计**：门禁主判必须是客观的、独立于任何 agent 理解的信号。期望输出来自"探针程序跑真实源码"，禁止 LLM 编造；编译必过 + 测试通过率主判 + 相似度仅归因。**新增职责：验证 TestGenAgent 产出的候选测试期望输出与真实源码一致**（一致才固化进门禁，不一致丢弃/修正），保证测试集 = 真实行为 oracle。

**参考论文/工作（2025+）**：
- Spec-Driven Test Gen（Google，arXiv:2608.17177，2026.08）：规格契约测试驱动，bug 检出 +9.8pp
- MASTOR（arXiv:2606.10465，2026.06）：从源码/契约提取语义 oracle，提升 mutation score
- 自进化代码 Agent 综述（arXiv:2608.03392，2026.08）：软件特有证据（结果/环境/轨迹）分类，评测六维（正确性/鲁棒性/成本/安全/泛化）
- 2.wiki 研究笔记：变异测试与测试集质量（2025 版）、覆盖率引导测试生成（2025 版）

**论文优缺点与借鉴点**：

| 来源 | 优点（值得借鉴） | 缺点（需要规避） | 我们的取舍 |
|---|---|---|---|
| Spec-Driven Test Gen | 契约测试提升检出率 9.8pp | 面向测试生成，非门禁体系 | 门禁主判 = 经验证期望输出测试；TestGenAgent 测试经 EvalRunner 验证后固化 |
| MASTOR | 语义 oracle 提升 fault detection | 面向 REST API，需改造 | P1 参考：从接口头文件提取约束 |
| 自进化综述 | 评测六维清单（正确性/鲁棒性/成本/安全/泛化） | 综述性质 | 作为验收检查清单，不只盯通过率 |
| 变异测试/覆盖率 | 量化评测集强度（注入 bug 抓不出 = 评测集太弱） | 变异执行成本高 | P1 引入，验证评测集本身合格 |

**结论**：EvalRunner 保持"编译 + 测试 + 相似度（仅归因）"三信号；重复评测 5 次均值±方差防随机；评测集独立受写保护；**TestGenAgent 候选测试的期望输出必须跑真实源码验证，禁止 LLM 编造**。

---

## 5. 推荐架构（最终定稿，TypeScript）

```text
┌─ OrchestratorAgent（确定性调度层，只调度不执笔）─────────────┐
│  规划 / 拆解 / 委派 / 汇总 / 驱动重试 / 审计 / 断点续跑      │
│  决策（pass/iterate/rollback/stopped）由门禁 decide 状态机   │
│  按客观评测信号给出（TypeScript 实现）                       │
├───────────────────────────────────────────────────────────┤
│ 文档生成阶段：                                              │
│   [单模块] DocGenAgent（读源码 → 知识文档）                   │
│   [超大库] DocGenAgent + DocWorkerAgent×N（每函数/模块独立    │
│            上下文，≤5 并行；修订按 knowledge_path 检索定位）   │
├───────────────────────────────────────────────────────────┤
│ 迭代阶段（每轮）：                                          │
│   TestGenAgent（读源代码 → 测试/冒烟，行为 oracle，          │
│                 期望输出由 EvalRunner 验证真实性）            │
│   CodeAgent（知识文档+接口 → 实现代码，Sandbox 隔离源码）     │
│   CheckAgent（CCR：全新 session + 只读 + 判据，语义层检查）   │
│   EvalRunner（编译 + 门禁测试 + 相似度）← 门禁主判            │
│   ReviewAgent（CCR：归因 + 修订指令三字段）                   │
│   知识修订（ReviewAgent → DocGenAgent 优化知识文档，版本 +1） │
│   → CodeAgent 基于新知识重新生成 → 重测                      │
├───────────────────────────────────────────────────────────┤
│ P1 可选项：                                                 │
│   pass@k 多候选（fan-out）· 跨模型检查 · 薄弱点地图           │
└───────────────────────────────────────────────────────────┘
```

### 引入多 Agent 的触发条件（成本闸门）

| 场景 | 动作 | 不做的代价 |
|---|---|---|
| 文档 > 单上下文可处理（如 >6000 字符后仍超） | DocGenAgent 分块 + DocWorkerAgent 并行 | 知识质量下降、截断丢信息 |
| 核心/高危模块 | CheckAgent（CCR）或跨模型检查 | 语义缺陷漏网 |
| 反复触发失败的薄弱点 | 薄弱点地图 + 优先重写（可加对抗检查） | 迭代不收敛 |
| 普通模块常规迭代 | 维持最小集（TestGenAgent + CodeAgent + ReviewAgent） | — |

---

## 6. 文献索引（2025+ 仅收录）

| 编号 | 文献 | 关键结论 |
|---|---|---|
| [1] | Anthropic: How we built our multi-agent research system (2025.06) | orchestrator-worker；多 agent ≈ 15× token；subagent 滥用成本爆炸 |
| [2] | Cross-Context Review (arXiv 2603.12123, 2026.03) | 上下文分离审查 F1 28.6% vs 自审 24.6%；重复审无增益 |
| [3] | Augment Code: Adversarial Code Review (2026-07) | maker-checker 5 维分离；跨家族补盲区；SWR-Bench 警告 |
| [4] | TDD-Agent (arXiv 2608.16742, 2026.08) | test-first reasoning + dual-track 代码/测试共精化 |
| [5] | Spec-Driven Test Gen, Google (arXiv 2608.17177, 2026.08) | spec 脚手架 bug 检出 +9.8pp |
| [6] | SDAD (arXiv 2608.20341, 2026.05) | 合成与发布权分离；独立多 agent 验证 + 人工签字 |
| [7] | CodeJudgeBench (arXiv 2507.10535, 2025.07) | LLM 裁判位置偏差 14%、自我偏好 |
| [8] | DocAgent (arXiv 2504.08725, 2025.04) | 拓扑代码处理 + 增量上下文 + 验证闭环（C/C++ 最相关） |
| [9] | MASTOR (arXiv 2606.10465, 2026.06) | 从源码/契约提取语义 oracle，提升 mutation score |
| [10] | 自进化代码 Agent 综述 (arXiv 2608.03392, 2026.08) | 软件特有证据分类；进化对象框架；评测六维 |
| [11] | Google ADK (2025-2026) | Sequential/Parallel/Loop 工作流 agent 基元 |
| [12] | Claude Agent SDK subagents / Codex CLI (2025-2026, 开源) | 进程级委派执行层，上下文隔离适合超大仓库（Claude Code 本体闭源黑盒不选） |

> 📎 相关已有笔记：研究/反馈闭环/自进化Agent脆弱性.md、研究/评测/CodeJudgeBench-LLM裁判可靠性.md（2025 版）

---

## 7. 待定问题（需 PoC 数据）

1. 分块阈值：多大文档该开 DocWorkerAgent 并行？（当前 4000 字符分块阈值是经验值）
2. 跨模型检查是否值得：公司内网若有 GLM 之外的第二模型（如 DeepSeek），用对比实验量化盲区补充收益
3. TestGenAgent 冒烟测试固化进评测集的比例：人工审过的测试进 holdout 还是 train？
4. pass@k 多候选（fan-out）的 k 值与聚合策略（P1）
5. OrchestratorAgent 的 LLM 动态规划 vs 纯确定性代码：以首个 PoC 的收敛数据决定
