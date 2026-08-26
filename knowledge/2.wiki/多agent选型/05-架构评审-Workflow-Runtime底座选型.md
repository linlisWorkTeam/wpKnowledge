# 05 · 架构评审：Workflow Runtime 底座选型（Temporal vs 自研）

> 日期：2026-08-20
> 性质：架构评审委员会答辩记录。**推翻了此前"零框架自研编排"的结论**（该结论仅适用于 PoC 语境）。
> 背景：知识飞轮是企业级长期底座（单仓 30 万行+、多仓库并行、数小时任务、分布式 worker、故障恢复），原则是"V1 功能可以少，但架构底座必须可靠"，避免 workflow runtime 层技术债。
> 相关：[01-多agent调研.md](01-多agent调研.md)、[03-开源编排框架.md](03-开源编排框架.md)

---

## 〇、评审结论（TL;DR）

**方案 C：Temporal 做 L1 Workflow Runtime 底座；L2 Agent Platform / L3 Domain 自研（核心资产）。预留 adapter，V2+ 出现动态 agent 图时可选 D（局部 LangGraph 作 L2 图 DSL）。**

| 方案 | 判定 |
|---|---|
| A. 零框架自研 | ❌ 推翻（仅适用 PoC 语境） |
| B. LangGraph 底座 | ❌ 不成立（单进程，checkpoint 保存数据不保存执行） |
| **C. Temporal 底座** | ✅ **采纳** |
| D. Temporal + 局部 LangGraph | ⚠️ V2+ 演进路径（V1 不引入） |
| E. 其他 | 不考虑 |

---

## 一、关键证据（非感觉，均官方来源）

### 1.1 Temporal 官方：Workflow replay / Event History

来源：https://docs.temporal.io/workflows

- Workflow 是"由代码定义的步骤序列"，执行时产生 Commands 与 Events，记录在 **Event History**（完整有序日志，工作流全生命周期的 source of truth）
- 恢复时不从快照恢复内存，而是**从头重放 Event History**，用记录的事件把代码引导回崩溃前的精确状态
- **Activity 结果记入 Event History，重放时复用、不重算**（"Activities aren't executed again during replay"）
- 官方明确把 **LLM invocations** 列为 Activity 场景（与 API calls / DB queries / file I/O 并列）
- Workflow 可运行数年，基础设施故障后自动重建崩溃前状态

### 1.2 Temporal 官方：Activity retry / heartbeat

来源：https://docs.temporal.io/activities

- Activity = 执行单个明确定义动作的函数（短或长），**官方建议幂等**
- 官方将 **"a read that should be memoized, like an LLM call"** 明确列为 Activity 用例
- Activity 失败 → 按 retry policy 重试；可用 **Heartbeat + details payload** 把检查点状态存到服务端，恢复后从检查点继续

### 1.3 Temporal 官方博客：LangGraph checkpoint 的局限（2026-07-16）

来源：https://temporal.io/blog/temporal-langgraph-plugin-durable-execution

> "A LangGraph run lives in a single process, so if that process dies then the run dies with it. The checkpoint preserves your data, not your execution: something has to detect the failure, decide where to re-enter the graph, and restart it."

**一句话击穿"文件/SHA/status = 持久化"的幻觉：保存数据 ≠ 保存执行。**

### 1.4 生产案例

来源：https://temporal.io/news/temporal-io-raises-usd100-million-series-b-company-valuation-passes-usd1-5 、 https://temporal.io/news/temporal-investors-expand-funding-with-usd75m-round

- Netflix / Stripe / Coinbase / DoorDash / Snap / Box / HashiCorp / Instacart / Datadog / Comcast 等大规模使用
- Netflix：部署故障率 4% → ~0.0001%（https://byteiota.com/temporal-workflow-engine-netflixs-10x-speed-secret-2026/ ）
- 峰值 300K executions/sec；单月 10 亿+ workflow 执行（https://automationatlas.io/tools/temporal-workflows/ ）

### 1.5 LangGraph checkpoint 官方 API

来源：https://langchain-ai.github.io/langgraphjs/reference/modules/langgraph-checkpoint.html

- Checkpointer 在**每个 superstep 边界**保存 graph state（channel values）：即保存"数据快照"，非"执行恢复"

---

## 二、逐条回应质疑

### 质疑 1：文件持久化 ≠ Workflow 持久化（**成立**）

文件 + SHA + status JSON 只解决 **Artifact durability（产物持久）**，不解决 **Execution durability（执行持久）**：

| 问题 | 文件方案能否回答 |
|---|---|
| 子任务到底执行完没有？ | ❌（无法区分 未开始 / LLM 已响应未落盘 / 落盘一半 / status 写入前崩溃） |
| LLM 完成但文件未落盘？ | ❌（写入非事务，需自造 write-ahead + commit 两阶段） |
| 是否重试（不重复烧 token）？ | ⚠️ 部分（无幂等保证） |
| A/B/D 是否重跑？ | ⚠️ 部分（依赖人工判断依赖图，无确定性重放） |
| fan-in 何时继续？ | ❌（无原子完成判定，并发读 status 有竞态） |
| retry 后状态 merge？ | ❌（无事务性协调） |
| 同一任务重复执行？ | ❌（无 task leasing / idempotency key） |
| orchestrator 崩溃后恢复？ | ❌（无 event history 重放） |
| 多进程同时恢复同一 task？ | ❌（无锁/租约） |

**结论**：补齐上述 9 项 = 重新实现简化版 workflow engine（无事件模型、无确定性重放、无版本化、无分布式调度、bug 自修、只有内部团队用）。而 Temporal 已实现且生产验证 8+ 年。

### 质疑 2：自研 Orchestrator 会演化成残缺版 LangGraph/Temporal（**成立**）

需求清单（conditional branch / loop / dynamic fan-out / fan-in / retry / timeout / interrupt / resume / parallel / checkpoint / versioning / partial failure / HITL / cross-repo）**每一项都是成熟 workflow runtime 的领域模型**。自研层每加一项需求就长出对应概念（Node/Edge/State/RetryPolicy/Checkpoint...），这是必然，因为这是分布式状态机的基本词汇表。

核心风险不是"写不出来"，而是：**Temporal 已用 8+ 年、300K exec/s 验证过的能力，我们每个 failure mode 都是第一次遇到。**

### 质疑 3：框架绑定 vs 内部 runtime 绑定（**成立，内部绑定更严重**）

| 维度 | A: 成熟 runtime + adapter | B: 自研内部 runtime |
|---|---|---|
| bus factor | 数百贡献者 | 1~2 人，离职即停摆 |
| 文档 | 官方完整文档 | 维护者记忆 |
| 测试 | 分布式系统级测试套件 | 自写 happy path |
| 故障场景覆盖 | 崩溃/重放/网络分区/时钟漂移全验证 | 每次都是第一次 |
| 社区 | 活跃 | 无 |
| 可观测性 | Web UI + CLI + tracing + Event History | 自造日志 |
| 维护成本 | 社区承担 | 全内部分摊 |
| 新员工理解成本 | 业界通用知识 | 公司私有知识 |
| 版本升级 | 官方语义版本 + LTS | 自己改自己 |
| 长期技术债 | 低 | 高（独有代码 + 独有 bug） |

**核心反驳**：引入内部 abstraction（`interface WorkflowRuntime { run/resume/cancel }`）后，框架绑定可控可替换；**内部 runtime 绑定不可替换**（自己写的，无人维护，未来再痛也只能继续用）。"避免框架绑定"的正确方案是 abstraction + adapter，不是自己重写 engine。

### 质疑 4：为什么不用 Temporal（**成立**）

Temporal 不是 agent 框架，是 durable execution 引擎。拿"不需要自由 agent orchestration"反驳它打错了靶子。22 项未来需求（child workflow / retry / timeout / heartbeat / cancel / signal / crash recovery / event history / 分布式 worker / long-running）**逐项都是 Temporal 原生能力**。唯一新增成本 = 部署 Temporal Server（自托管 Docker/Helm 或 Cloud），是业界通用运维件。

**"现在流程简单"不构成理由**：现在正是引入成熟底座成本最低的时刻；等流程复杂再迁移是最高成本路径。V1 功能可以少，架构底座必须可靠：引入 Temporal 正是贯彻该原则。

### 质疑 5：LangGraph 和 Temporal 分层（**不 PK，分层采用**）

- LangGraph：agent graph（state / conditional routing / loop / fan-out / HITL / checkpoint）。解决"图怎么走"。
- Temporal：durable execution（failure recovery / retry / timeout / long-running / distributed / event history）。解决"走到一半挂了怎么办"。
- LangGraph checkpoint 保存**数据**（superstep 边界 channel values），非**执行**（官方博客原话）。
- 我们的主干是确定性固定流水线，不需要自由 agent 图 → L1 用 Temporal；若未来出现动态 agent 图，在 L2 用 LangGraph 定义图、调度到 Temporal 执行（V2+ 可选）。

### 质疑 6：哪些值得自研（**L2/L3 自研，L1 用成熟件**）

| 层 | 内容 | 决策 | 理由 |
|---|---|---|---|
| L3 Domain | 知识飞轮、EvalRunner、KnowledgeStore、Test Oracle、Dependency Graph、Knowledge Feedback | ✅ 核心自研资产 | 业务差异化，无现成方案 |
| L2 Agent Platform | Agent Contract、Artifact Contract、Agent Registry、Model Adapter、Sandbox、Permission、Context Engineering、Trace Context | ✅ 核心自研资产 | 公司级复用面，需深度定制（沙箱/防作弊/知识隔离） |
| L1 Workflow Runtime | Workflow、State、Retry、Checkpoint、Fan-out、Fan-in、Resume、Cancel、Timeout、Execution History | ❌ 不自研，用 Temporal | 成熟基础设施，重造 = 长期技术债 |
| L0 Infrastructure | DB、对象存储、消息、部署、监控 | ❌ 用现成 | Postgres/S3/K8s 标准件 |

判断标准：**是否构成差异化壁垒 + 是否属于成熟基础设施**。L1 是成熟基础设施；L2/L3 是知识工程差异化。自研预算投在 L2/L3。

---

## 三、最终决定

**方案 C：Temporal 做 L1 底座；L2/L3 自研；推翻"零框架"结论。**

### 1. 为什么
证据链完整（见第一节）：文件持久化 ≠ 执行持久化；自研必然演化成残缺 runtime；内部 runtime 绑定比框架绑定更严重；Temporal 正是"数小时 + 分布式 + 崩溃恢复 + LLM 调用"场景的成熟答案；LangGraph 定位是 L2 图 DSL；L1 属成熟基础设施。

### 2. 核心收益
- 22 项需求能力全拿到（retry/timeout/heartbeat/cancel/resume/child workflow/event history/分布式 worker/HITL/审计），无需自研
- LLM 调用不重复计费（Activity 结果重放复用）
- 全链路可观测（Event History = 审计日志 + Web UI）
- 业界通用技能，新员工上手成本低
- 长期技术债最小化

### 3. 核心代价
- 新增 Temporal Server 运维件（自托管或 Cloud）
- Workflow 代码需遵循确定性约束（非 Activity 代码不能直接调外部 IO/随机/系统时间）
- 团队需掌握 Workflow/Activity/retry policy 模型

### 4. 3 年后最大的风险
- Temporal 商业路线风险（商业公司 + 开源双轨）：但它是 2026 年 durable execution 事实标准，替代风险远小于自研 runtime 停摆风险
- 若自研：代码库长成残缺版 Temporal，1~2 个维护者，无人敢改，业务被自己的 runtime 锁死

### 5. V1 应该实现什么
- L1：Temporal 部署 + Workflow/Activity 骨架（OrchestratorAgent → DocGen/TestGen/Code/Eval/Review 各为 Activity 或 Child Workflow）
- L2：Agent Contract、Artifact Contract、Model Adapter（GLM 5.1/DeepSeek）、Sandbox、Permission、Trace Context
- L3：知识飞轮核心闭环（DocGen→Code→Eval→Review→修订）；文件交接保留（作为 Artifact 层，不承担 execution 语义）

### 6. 哪些能力坚决不要自己实现
execution history、checkpoint、retry policy、idempotency、task leasing、concurrency control、heartbeat、resume、failure recovery、workflow versioning、分布式 worker 调度、HITL 信号机制 ： 全部用 Temporal 原生能力。

### 7. 若仍坚持零框架，自研 runtime 至少必须补齐
（不建议；若决策层坚持，这是最低门槛）
execution history（事件日志+重放）、确定性重放、retry policy、idempotency key、task leasing、heartbeat、分布式锁、resume、failure recovery、workflow versioning、fan-in 原子聚合、并发控制、HITL 信号、审计日志、Web UI 可观测性：**约等于重写 Temporal 的 60%，且无生产验证。**

---

## 四、最关键问题的回答

> 如果这个框架未来会成为整个知识工程长期使用的基础设施，那么"自己写比较简单"究竟是优势，还是早期看起来便宜、后期昂贵的技术债？

**是早期看起来便宜、后期昂贵的技术债，而且是最贵的那种。**

- **"简单"是幻觉**：现在简单，是因为需求还没来。22 项能力一旦开始增长，自研层必然长出 Node/Edge/State/RetryPolicy/Checkpoint：每一项都是成熟 runtime 已验证的领域模型，我们是在重新发明并承担其全部 bug。
- **成本曲线不对**：自研显性成本（开发）前期低，隐性成本（维护/故障/文档/人员流动/不可观测性/升级恐惧）随时间线性到超线性增长；Temporal 显性成本（部署+学习）前期一次性，隐性成本被社区摊薄。
- **判断标准**：自研的唯一正当理由是"差异化"。Workflow runtime 不是我们的差异化：知识飞轮、防作弊评测、沙箱隔离、知识文档体系才是。把预算投在 L1 上是给竞争对手送时间。

---

## 五、权威来源汇总

- Temporal Workflows（execution semantics / replay）: https://docs.temporal.io/workflows
- Temporal Activities（retry / heartbeat / LLM call 用例）: https://docs.temporal.io/activities
- Temporal LangGraph Plugin 博客（checkpoint vs durable execution）: https://temporal.io/blog/temporal-langgraph-plugin-durable-execution
- LangGraph.js Checkpoint API: https://langchain-ai.github.io/langgraphjs/reference/modules/langgraph-checkpoint.html
- Temporal 融资与生产客户（Netflix/Stripe/Coinbase 等）: https://temporal.io/news/temporal-io-raises-usd100-million-series-b-company-valuation-passes-usd1-5
- Temporal 规模化（300K exec/s、10 亿+/月）: https://automationatlas.io/tools/temporal-workflows/ 、 https://byteiota.com/temporal-workflow-engine-netflixs-10x-speed-secret-2026/
