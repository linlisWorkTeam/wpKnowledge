# 03 · Agent Platform 架构设计（现成框架之外的"自研部分"）

> 日期：2026-08-26
> 定位：**以框架选型图（用户版）为锚点**，说明哪些能力是现成框架已经给的（LangGraph 图、Codex / Claude / DeepSeek Agent 本体、MCP / ACP / A2A 协议），哪些必须平台自研（AgentProvider / ContextPolicy / ResourceClaim / AgentRun / AgentSession / 副作用幂等），以及自研部分怎么实现。选型图上每个"参考 XXX"具体参考它的哪些部分，见第 2 节参考清单。
> 关联：[01-多agent调研.md](01-多agent调研.md)（业务架构）｜ [02-技术选型与架构决策.md](02-技术选型与架构决策.md)（为什么这么选）｜ [04-LangGraph选型与多Agent图.md](04-LangGraph选型与多Agent图.md)（框架选型）

---

## 0. 标注版选型图（每个 Agent 需要什么自研能力）

这是框架选型图（用户暂定版），蓝色 Agent 框上标注**【平台必须自研的能力】**与**参考来源**：

```mermaid
flowchart TD
    LG["LangGraph 图编排层<br/>【现成：图结构 / 节点调度 / 状态保存】<br/>负责整个多 Agent 图怎么跑"]

    LG --> O["OrchestratorAgent<br/>【现成：Supervisor 模式 + Codex 协作原语】<br/>只调度；门禁状态机自研，跑在条件边"]

    O -->|委派文档生成| D1["DocGenAgent<br/>【自研：fork-all 上下文、写 knowledge/**<br/>参考 DSH：插件化 + Capability Seam】<br/>参考 DSH（DeepSeek Harness）"]
    O -->|委派测试生成| D2["TestGenAgent<br/>【自研：artifact-only 上下文（含源码）、只读 source/**】<br/>参考隔离设计（独立链路）"]
    O -->|分块并行（Send API）| DW["DocWorkerAgent × N<br/>【自研：fork-all 分块上下文、按模块读写<br/>参考 DSH scope + Codex fork_turns】<br/>参考 DSH + Codex"]

    DW -->|分块知识片段| D1
    D1 -->|知识文档（spec）| KS["KnowledgeStore<br/>【完全自研】<br/>候选区 + 版本 + ledger"]
    D2 -->|候选测试池| EV0["EvalRunner<br/>【完全自研】<br/>验证期望输出与真实源码一致"]

    KS -->|知识文档，唯一事实输入| CA["CodeAgent<br/>【自研：artifact-only（无源码！）、写 code/**、读 knowledge/**<br/>参考 OpenHands：资源锁 + workspace；走 ACP 接 Codex】<br/>重点参考 Codex / OpenHands"]
    EV0 -->|门禁测试集| EV["EvalRunner（确定性程序）<br/>【完全自研】<br/>编译必过 + 门禁测试 + 相似度（仅归因）"]
    CA -->|实现代码| CK["CheckAgent<br/>【自研：fresh 上下文（全新 session）、只读 diff + 判据】<br/>参考独立 Context 模式"]
    CK -->|检查报告| EV
    KS --> EV

    EV -->|评测报告| RV["ReviewAgent<br/>【自研：fresh 上下文、只读评测报告 + 工件】<br/>参考独立 Reviewer"]
    RV -->|归因 / 修订指令| O2["OrchestratorAgent 重新调度<br/>【自研规则，跑在 LangGraph 条件边】<br/>门禁状态机：pass / iterate / rollback / stopped"]
    O2 -->|iterate：修订指令 → DocGenAgent 优化知识（v+1）| D1
    O2 -->|pass| PUB["知识发布<br/>【完全自研】<br/>verified，SHA-256 快照"]

    classDef lg fill:#ede7f6,stroke:#5e35b1;
    classDef agent fill:#e1f5fe,stroke:#0288d1;
    classDef infra fill:#fff3e0,stroke:#f57c00;
    class LG lg;
    class O,O2,D1,D2,DW,CA,CK,RV agent;
    class KS,EV0,EV,PUB infra;
```

**一句话看懂**：
- **紫色 LangGraph** = 现成：图结构 / 节点调度 / 状态保存（checkpoint），不用我们写
- **蓝色 Agent** = 现成框架跑（LLM / Coding Agent），但"**用什么上下文跑（ContextPolicy）+ 能读写哪些资源（ResourceClaim）+ 用哪个 Provider 跑（AgentProvider）**"这 3 件事必须平台自研（防作弊隔离是硬约束，不能靠 prompt）
- **橙色框** = 完全自研（业务壁垒）

---

## 1. 现成 vs 自研 分工（先看这张表）

| 能力 | 现成（用谁的） | 自研（平台做） |
|---|---|---|
| 图编排（节点 / 边 / 并行 / 循环 / 状态保存） | LangGraph（checkpointer 存图状态） | 不写图运行时 |
| 调度模式 | LangGraph Supervisor（OrchestratorAgent 骨架） | 门禁状态机规则（条件边实现） |
| Agent 本体 | Codex / Claude / DeepSeek / GLM（走 ACP 或 Provider） | 不重造 Coding Agent |
| 上下文注入策略 | 无现成（prompt 约束是软约束） | **ContextPolicy**（artifact-only 禁源码等，物理不给） |
| 资源冲突判定 | 无现成（maxConcurrency 只限数量） | **ResourceClaim**（A∥B safe / A∥C conflict） |
| 运行句柄 / 血缘 / 审计 | 无现成 | **AgentRun / AgentSession**（Session Event Log） |
| 副作用幂等 | 无现成（Temporal 只保证执行可靠性） | **GenerationKey** 去重 |
| 确定性评测 / 知识库 | 编译器 g++ / Postgres / 对象存储 | **EvalRunner / KnowledgeStore**（知识飞轮） |
| 接外部 | MCP / ACP / A2A 标准协议 | 协议 Adapter |

**判定标准**：能现成（图、Agent 本体、协议、编译器）绝不重复造轮子；现成给不了的（上下文隔离、资源冲突、会话审计、评测门禁、知识版本）必须自研，这是防作弊与业务壁垒所在。

---

## 2. 参考清单：每个"参考"参考它的哪些部分（核心）

选型图上每个"参考 XXX"都不是泛泛而谈，下面是**参考对象 → 参考的具体机制 → 机制是什么 → 用在我们哪里**的完整映射。所有机制均来自官方源码 / 官方文档（2026 现状）。

### 2.1 OrchestratorAgent ← LangGraph Supervisor

| 参考它的什么 | 机制是什么（官方） | 用在我们哪里 |
|---|---|---|
| `create_supervisor` 模式 | supervisor 节点统一协调一组专用 agent，控制所有通信流与任务委派（README 原文） | OrchestratorAgent = supervisor 节点：规划 / 拆解 / 委派 / 汇总 |
| Tool-based handoff（工具型交接） | agent 之间通过工具调用完成交接，官方推荐的手动 supervisor 模式 | 委派 = 一次工具调用（带任务描述 + 资源声明），不搞自定义消息协议 |
| 消息历史管理（output_mode） | `full_history`（保留 worker 全部消息）或 `final_response`（只留最终回复） | DocWorkerAgent 并行后只汇总结构化摘要 + 溯源锚点，防上下文膨胀（对应 01 的"压缩器"思想） |

证据：https://github.com/langchain-ai/langgraph-supervisor （README，2026 官方说明建议用工具型手动 supervisor 模式，我们采用其模式而非库本身）

### 2.2 OrchestratorAgent / DocWorkerAgent ← Codex

| 参考它的什么 | 机制是什么（官方源码） | 用在我们哪里 |
|---|---|---|
| 协作原语六件套 | `spawn_agent`（创建子 agent）、`followup_task`（给已有 agent 新任务并触发一轮）、`send_message`（给运行中 agent 发消息不触发轮次）、`wait_agent`（等待结果）、`interrupt_agent`（打断）、`list_agents`（列出活跃 agent） | 委派 / 重试 / 汇总的调用面：LangGraph 节点内部按这些原语语义调 AgentProvider |
| `fork_turns` 参数 | 控制向子 agent 传播多少上下文：`all`（全量）/ `none`（不传）/ 正整数（最近 N 轮） | ContextPolicy 的 `fork-all` / `fork-last-n` 直接对应；`none` 对应 `fresh` |
| `max_concurrent_threads_per_session` | 会话级并发槽位上限（usage hint 原文："up to N agents can be active at once"） | DocWorkerAgent 并行上限（01 定 ≤5）+ ResourceClaim 并发判定 |
| 共享工作区语义 | "All agents share the same directory... edits made by one agent are immediately visible to all other agents" | **反着用**：我们刻意打破它，DocGenAgent 产物是 CodeAgent 唯一事实输入，CodeAgent 物理看不到源码（Sandbox 强制）。共享 = 交接文件，隔离 = 上下文物理裁剪 |

证据：https://github.com/openai/codex/blob/main/codex-rs/core/src/session/multi_agents.rs （源码 usage hint 常量，2026）

### 2.3 DocGenAgent / DocWorkerAgent / AgentProvider ← DSH（DeepSeek Harness）

| 参考它的什么 | 机制是什么（官方架构文档） | 用在我们哪里 |
|---|---|---|
| Everything is a Plugin | 基于 Cordis：模型适配器、工具注册表、会话日志、agent loop 本身全部是插件，无特权核心，任何部分可替换 | AgentProvider 可插拔：换模型 / 换 Coding Agent 只换 Provider，不动平台 |
| Capability Seam 三角色 | 可替换能力 = Service Definition（接口声明）+ Service Provider（实现）+ Consumer（使用方）；新增能力要设计全部三件套 | AgentProvider = Provider；AgentCapabilities = Service Definition 的一部分；LangGraph 节点 = Consumer |
| Session Event Log | append-only 会话事件日志；"Model-visible means logged"（模型看到的必须能从日志重建）；fork / resume / telemetry / persistence 都从日志派生 | AgentSession Event Log（第 4 节）：语义审计 / trace / eval 溯源 |
| `agent/pre-step` 事件 | 每轮模型请求前的事件，监听者可以重写模型将看到的消息或直接拒绝 | ContextPolicy 的注入时机：进模型前物理裁剪上下文（artifact-only 不给源码） |
| `ctx.sandbox` / `ctx.fs` provider | 沙箱后端与文件系统 provider 分离，换后端不换业务 | Sandbox 白名单（allowed_read_dirs 硬禁止 src_dir） |
| `agent.ctx`（scope） | per-agent 作用域注册：注册只对单个 agent 生效 | 每个 Agent 的上下文 / 权限作用域隔离 |

⚠️ 注意：DSH 官方标注 developer preview，"THERE WILL BE COMPATIBILITY-BREAKING CHANGES"。**只借鉴设计，不引入代码、不依赖其 API**。

证据：https://github.com/deepseek-ai/deepseek-harness （docs/architecture.md，2026）

### 2.4 CodeAgent / ResourceClaim ← OpenHands Software Agent SDK

| 参考它的什么 | 机制是什么（官方源码） | 用在我们哪里 |
|---|---|---|
| `ResourceLockManager` | per-resource FIFO 锁：按资源键（`file:/a.py` 等）加锁，同一资源串行、不同资源并发；**锁按排序顺序获取防死锁**；FIFOLock 保证公平不饥饿；按资源前缀区分超时（file/terminal/browser/mcp/tool） | ResourceClaim 判定（第 6 节）：DocWorker A∥B safe / A∥C conflict 的精确实现参考 |
| Conversation + workspace | Agent 绑定 workspace 运行，工具在 workspace 内生效 | AgentRun / AgentSession 的 workspace 字段；Sandbox 工作目录 |
| Ephemeral workspaces（Agent Server） | Agent 可在 Docker / K8s 临时工作区运行 | CodeAgent 的物理隔离沙箱（未来分布式 worker） |
| Tool 体系（FileEditor / Terminal / TaskTracker） | 工具与 Agent 解耦，按名称注册 | 我们的工具统一走 MCP（FileEditor→文件工具、Terminal→终端工具） |

证据：https://github.com/OpenHands/software-agent-sdk （README + openhands-sdk/openhands/sdk/conversation/resource_lock_manager.py，2026）

### 2.5 TestGenAgent / CheckAgent / ReviewAgent ← 隔离设计 / 独立 Context / 独立 Reviewer

这三个"参考"不是外部框架，是 **01 业务架构的设计依据**（论文 2025+ 实证）：

| 参考它的什么 | 机制是什么 | 用在我们哪里 |
|---|---|---|
| 隔离设计（TestGenAgent） | TestGenAgent 独立链路：读源码提取行为 oracle，**不读知识文档**（01 硬规则，消除"测试与代码共享文档盲区"） | 门禁测试集 = 真实源码行为，与 CodeAgent 的知识理解解耦 |
| 独立 Context 模式（CheckAgent） | CCR：全新 session，只读 diff + 判据清单，不知道作者 / 无生成历史 | CheckAgent 语义层审查（测试覆盖不到的边界 / 命名 / 设计） |
| 独立 Reviewer（ReviewAgent） | 独立评审者：评测失败归因 → 修订指令（readlist 三字段），反馈 DocGenAgent 优化知识文档 | 归因报告驱动知识版本 +1 |

证据（论文依据见 01 §4.5.3/§4.5.4 设计依据小节，2025+）：CheckAgent 采用 CCR 跨上下文独立审查（Cross-Context Review，arXiv:2603.12123，2026.03）：F1 28.6% vs 同会话自审 24.6%，同会话重复审两次无增益（p=0.11）→ https://arxiv.org/abs/2603.12123；ReviewAgent 修订指令三字段（ID + 段落路径 + 可执行判据）参考 SDAD（arXiv:2608.20341，2026.05），纯 NL 建议不能驱动合并 → https://arxiv.org/abs/2608.20341

---

## 3. 平台给每个 Agent 什么（先看这张表）

| 图上节点 | 用什么上下文（ContextPolicy） | 能读写什么（ResourceClaim） | 谁在跑 |
|---|---|---|---|
| DocGenAgent | fork-all（继承分块指令） | 读 source/，写 knowledge/ | AgentProvider（参考 DSH 插件化实现） |
| DocWorkerAgent×N | fork-all（每块独立上下文，Codex fork_turns 语义） | 各读 source/moduleX/，写 knowledge/moduleX/ | AgentProvider（LangGraph Send 并行） |
| TestGenAgent | artifact-only（源码+接口） | 读 source/（只读） | AgentProvider |
| CodeAgent | **artifact-only（知识文档+接口，无源码！）** | 读 knowledge/，写 code/ | AgentProvider / ACP（Codex / OpenHands） |
| CheckAgent | fresh（全新 session） | 读 diff+判据（只读） | AgentProvider |
| ReviewAgent | fresh（全新 session） | 读评测报告+工件（只读） | AgentProvider |

下面逐个能力解释"是什么、为什么、图上哪用"。这些都是**自研部分**。

---

## 4. AgentProvider：Agent 由谁运行（自研稳定接口）

### 4.1 图上位置

所有蓝色 Agent 框的"运行底座"。

### 4.2 为什么需要它

没有它，业务代码就会写 `if provider === "codex"` / `if provider === "deepseek"`，换模型就要改业务。Provider 把"跑哪个 Agent"变成可替换的（对应 DSH 的 Everything is a Plugin，见 2.3）。

### 4.3 与 LangGraph 的关系（节点 = 薄包装）

LangGraph 图上的每个蓝色节点 = **薄包装**：节点逻辑 = 调 `AgentProvider.start()` + 应用 ContextPolicy / ResourceClaim。图的结构（谁接谁、怎么循环）归 LangGraph，节点内部"跑哪个模型、注入什么上下文"归平台。

### 4.4 定义

```typescript
interface AgentProvider {
  readonly name: string;
  capabilities(): AgentCapabilities;       // 先问能力
  start(request: AgentStartRequest): Promise<AgentRun>;  // 再启动
}
```

- Provider 可以包装：本地 LLM API（DeepSeek / GLM）、Codex CLI、Claude Agent SDK、任意 NewAgent-X
- 设计参考：DSH 的 Capability Seam（Service Definition → Provider → Consumer，见 2.3）→ https://github.com/deepseek-ai/deepseek-harness ；Codex 的协作原语（见 2.2）→ https://github.com/openai/codex/blob/main/codex-rs/core/src/session/multi_agents.rs

### 4.5 能力声明（AgentCapabilities）：先问会不会，再派活

```typescript
interface AgentCapabilities {
  structuredOutput: boolean;   // 能输出结构化结果吗
  contextFork: boolean;        // 能显式 fork 上下文吗（Codex fork_turns）
  resume: boolean;             // 能恢复吗
  subagent: boolean;           // 能 spawn 子 agent 吗（Codex spawn_agent）
  toolFilter: boolean;         // 能限制工具白名单吗
  sandbox: boolean;            // 自带沙箱吗（OpenHands ephemeral workspace）
  streaming: boolean;          // 流式吗
}
```

**Fail loud（响亮失败，不静默降级）**：业务要求 `structuredOutput=true`，Provider 不支持 → 直接报 `UNSUPPORTED_CAPABILITY`，绝不偷偷降级成普通文本（否则 Eval / Artifact 契约会被破坏）。

---

## 5. AgentRun / AgentSession：Agent 不是一次函数调用

### 5.1 图上位置

所有蓝色 Agent 框的"运行时形态"。

### 5.2 为什么

旧接口 `run(input): Promise<output>` 太薄：Agent 可能跑几分钟、可能被取消、可能崩溃要恢复、可能有父子关系。要表达这些，需要运行句柄 + 会话。

### 5.3 AgentRun（执行句柄）

```typescript
interface AgentRun {
  id: AgentRunId;
  sessionId: SessionId;
  result: Promise<AgentResult>;       // 完成结果
  cancel(reason?: string): void;      // 取消（要级联子 agent）
  dispose(): Promise<void>;           // 释放
  status(): AgentStatus;              // created/running/completed/failed/aborted
}
```

### 5.4 AgentSession / Lineage（会话与血缘）

```typescript
interface AgentInstance {
  agentId: AgentId;
  sessionId: SessionId;
  parentSessionId?: SessionId;   // 父子血缘（DocGen → DocWorker 就是父子）
  role: string;                   // DocGen / TestGen / Code / Check / Review ...
  model: ModelId;
  permission: PermissionSet;
  workspace: WorkspaceRef;
  contextLineage: ContextPolicy;  // 上下文继承策略
  status: AgentStatus;
}
```

### 5.5 三套状态别混（LangGraph / Temporal / Agent Session）

| | LangGraph graph state | Temporal Event History | Agent Session Event Log |
|---|---|---|---|
| 语义 | 图走到哪了（节点执行顺序） | 执行真相（谁跑了、重试几次、崩溃点） | 交互真相（模型看到了什么、调了什么工具） |
| 记录 | checkpoint（superstep 边界） | Commands / Events / Activity 结果 | AgentStarted / ModelRequest / ToolCall / SubagentEnded... |
| 用途 | 断点续跑（图级） | 执行恢复 / 审计 | 语义审计 / trace / eval 溯源 |
| 参考来源 | LangGraph（现成） | Temporal（现成） | **DSH Session Event Log**（"Model-visible means logged"，见 2.3） |

图上：LangGraph 管"图结构"的状态，Temporal 管"流程箭头"的执行，Session Log 管"蓝色框"里 LLM 干了什么。

---

## 6. ContextPolicy：Agent 用什么上下文跑（自研，本项目最重要的能力）

### 6.1 图上位置

- **CodeAgent 必须看不到源码** → artifact-only（知识文档+接口，无源码）
- **TestGenAgent 读源码** → artifact-only（含源码）
- **CheckAgent / ReviewAgent 全新上下文** → fresh（不知道作者、无生成历史）
- **DocWorkerAgent 分块** → fork-all（继承分块指令）

### 6.2 定义

```typescript
interface ContextPolicy {
  mode:
    | "fresh"            // 全新上下文（Check/Review 默认，对应 Codex fork_turns=none）
    | "fork-all"         // 继承全部父上下文（DocWorker 子任务，对应 Codex fork_turns=all）
    | "fork-last-n"      // 只继承最近 N 轮（控制膨胀，对应 Codex fork_turns=N）
    | "artifact-only";   // 只注入指定 Artifact（CodeAgent：知识文档+接口）
}
```

### 6.3 为什么是"平台能力"而不是"prompt 约束"

- prompt 里写"不要看源码" = 软约束，Agent 可能违反
- **ContextPolicy = 硬约束**：平台在注入上下文时**物理上就不给**源码 → 配合 Sandbox 双重强制
- 注入时机参考 DSH `agent/pre-step`（进模型前最后一道裁剪，见 2.3）；模式语义参考 Codex `fork_turns`（见 2.2）

---

## 7. ResourceClaim：谁和谁可以并行（自研）

### 7.1 图上位置

- DocWorkerAgent×N 并行 → 需要判定 A/B/C 是否真独立
- 未来多 Agent 并行写产物 → 需要资源冲突判定

### 7.2 为什么不是 maxConcurrency = 5

OpenHands 的教训：并发不只是"限数量"，还要看**共享资源冲突**：

```
Agent A writes moduleA
Agent B writes moduleB   → A ∥ B safe（可以并行）
Agent C writes moduleA   → A ∥ C conflict（不能并行）
```

### 7.3 定义

```typescript
interface ResourceClaim {
  uri: string;              // 如 "knowledge/moduleA/**"
  mode: "read" | "write";
}
```

| Agent | read | write |
|---|---|---|
| DocWorker A | source/moduleA/** | knowledge/moduleA/** |
| DocWorker B | source/moduleB/** | knowledge/moduleB/** |
| CodeAgent | knowledge/moduleA/** | code/moduleA/** |

调度系统据此判定：无写冲突 → 可并行；有写冲突 → 串行。比 `maxConcurrency=5` 精确得多。

**实现参考 OpenHands `ResourceLockManager`（见 2.4）**：
- per-resource 锁（按 `uri` 键加锁），同一资源串行、不同资源并发
- 锁按排序顺序获取，防死锁（多 Agent 申请重叠资源集时）
- FIFO 公平，不饥饿；按资源前缀区分超时（文件写 vs 长任务）

---

## 8. 副作用幂等（自研，业务正确性，Temporal 不管这个）

### 8.1 图上位置

Agent 每次调 LLM / 写 Artifact / 发知识，都要防重复。

### 8.2 为什么需要

Temporal 重试时，可能存在"LLM 已返回但结果没提交 → 崩溃 → 重试 → 再调一次"的窗口。所以**业务副作用去重要平台自己做**：

- LLM 调用去重：`GenerationKey = workflowRunId + moduleId + iteration + agentType + promptHash + modelConfigHash`
- Artifact 写幂等：同 key 重复写不产生脏产物
- 知识发布幂等：按版本号幂等

---

## 9. 连接外部：ACP / A2A / MCP（现成协议，只做 Adapter）

```mermaid
flowchart LR
    PLAT["Knowledge Agent Platform"]
    PLAT --> ACP["ACP<br/>接 Coding Agent Runtime（Codex/Claude）"]
    PLAT --> A2A["A2A<br/>接远程 Agent Service"]
    PLAT --> MCP["MCP<br/>接工具/知识服务"]
```

| 协议 | 图上哪 | 什么场景 | 来源 |
|---|---|---|---|
| **ACP** | CodeAgent 接 Codex / Claude | 本地 / CLI Coding Agent | 现成 → https://github.com/agentclientprotocol/agent-client-protocol |
| **A2A** | 未来跨系统 | 远程独立 Agent Service | 现成 → https://github.com/a2aproject/A2A |
| **MCP** | Agent 调工具 / 检索 / 知识 | Tool / Knowledge Service | 现成 → https://modelcontextprotocol.io/ |

**结构（业务不直接碰协议）**：

```
Knowledge Agent Platform
   → AgentProvider（稳定 Contract）
      → ACP Adapter → Codex / Claude / Other
```

ACP v2/v3 升级 → 只改 Adapter。

---

## 10. V1 / V2 边界（对照图）

**V1**：
- LangGraph 定义 7 Agent 图：节点 = AgentProvider 薄包装、条件边 = 门禁状态机、Send = DocWorker 并行、Postgres checkpointer
- 图上所有蓝色框跑在 AgentProvider 上
- CodeAgent 的 ContextPolicy = artifact-only（看不到源码）
- DocWorker 并行用 ResourceClaim 判定（参考 OpenHands ResourceLockManager）
- 持久执行：Temporal（插件评估接入）
- 接 Codex / Claude 用 ACP PoC；工具 / 知识用 MCP
- 副作用幂等（GenerationKey）就位

**V2+**：
- Agent Teams（Task DAG / durable mailbox / writeScopes）
- rich A2A / 跨 repo 调度 / 分布式 Agent Provider / 智能 Resource Scheduler
- Temporal LangGraph 插件必上（长任务 / 多 worker）

## 11. 成功标准（怎么算设计对）

1. 新 Coding Agent（NewAgent-X）出现 → 只加 Provider 或 ACP 配置，**不动**飞轮 / 图 / EvalRunner / KnowledgeStore
2. LangGraph 被替换 → 只改图的定义（节点 / 边描述），**不重写**平台和业务
3. Temporal 被替换 → 只改持久执行 Adapter，**不重写**平台和业务
4. 模型 DeepSeek → GLM → OpenAI → private → 只改 Model / Agent Provider

**若做不到以上任意一条，说明 Agent Platform abstraction 设计失败。**
