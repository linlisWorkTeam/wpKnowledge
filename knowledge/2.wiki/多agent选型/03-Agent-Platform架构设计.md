# 03 · Agent Platform 架构设计（现成框架之外的"自研部分"）

> 日期：2026-08-26
> 定位：**以框架选型图（用户版）为锚点**，说明哪些能力是现成框架已经给的（LangGraph 图、Codex / Claude / DeepSeek Agent 本体、MCP / ACP / A2A 协议），哪些必须平台自研（AgentProvider / ContextPolicy / ResourceClaim / AgentRun / AgentSession / 副作用幂等），以及自研部分怎么实现。
> 关联：[01-多agent调研.md](01-多agent调研.md)（业务架构）｜ [02-技术选型与架构决策.md](02-技术选型与架构决策.md)（为什么这么选）｜ [04-LangGraph选型与多Agent图.md](04-LangGraph选型与多Agent图.md)（框架选型）

---

## 0. 标注版选型图（每个 Agent 需要什么自研能力）

这是框架选型图（用户暂定版），蓝色 Agent 框上标注**【平台必须自研的能力】**：

```mermaid
flowchart TD
    LG["LangGraph 图编排层<br/>【现成：图结构 / 节点调度 / 状态保存】<br/>负责整个多 Agent 图怎么跑"]

    LG --> O["OrchestratorAgent<br/>【现成：Supervisor 模式】<br/>参考：LangGraph Supervisor + Codex<br/>只调度；门禁状态机自研，跑在条件边"]

    O -->|委派文档生成| D1["DocGenAgent<br/>【自研：fork-all 上下文、写 knowledge/**】<br/>参考 DSH（DeepSeek Harness）"]
    O -->|委派测试生成| D2["TestGenAgent<br/>【自研：artifact-only 上下文（含源码）、只读 source/**】<br/>参考隔离设计（独立链路）"]
    O -->|分块并行（Send API）| DW["DocWorkerAgent × N<br/>【自研：fork-all 分块上下文、按模块读写】<br/>参考 DSH + Codex"]

    DW -->|分块知识片段| D1
    D1 -->|知识文档（spec）| KS["KnowledgeStore<br/>【完全自研】<br/>候选区 + 版本 + ledger"]
    D2 -->|候选测试池| EV0["EvalRunner<br/>【完全自研】<br/>验证期望输出与真实源码一致"]

    KS -->|知识文档，唯一事实输入| CA["CodeAgent<br/>【自研：artifact-only（无源码！）、写 code/**、读 knowledge/**<br/>现成：走 ACP 接 Codex / OpenHands】<br/>重点参考 Codex / OpenHands"]
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

## 2. 平台给每个 Agent 什么（先看这张表）

| 图上节点 | 用什么上下文（ContextPolicy） | 能读写什么（ResourceClaim） | 谁在跑 |
|---|---|---|---|
| DocGenAgent | fork-all（继承分块指令） | 读 source/，写 knowledge/ | AgentProvider（可接 DSH 参考实现） |
| DocWorkerAgent×N | fork-all（每块独立上下文） | 各读 source/moduleX/，写 knowledge/moduleX/ | AgentProvider（LangGraph Send 并行） |
| TestGenAgent | artifact-only（源码+接口） | 读 source/（只读） | AgentProvider |
| CodeAgent | **artifact-only（知识文档+接口，无源码！）** | 读 knowledge/，写 code/ | AgentProvider / ACP（Codex / OpenHands） |
| CheckAgent | fresh（全新 session） | 读 diff+判据（只读） | AgentProvider |
| ReviewAgent | fresh（全新 session） | 读评测报告+工件（只读） | AgentProvider |

下面逐个能力解释"是什么、为什么、图上哪用"。这些都是**自研部分**。

---

## 3. AgentProvider：Agent 由谁运行（自研稳定接口）

### 3.1 图上位置

所有蓝色 Agent 框的"运行底座"。

### 3.2 为什么需要它

没有它，业务代码就会写 `if provider === "codex"` / `if provider === "deepseek"`，换模型就要改业务。Provider 把"跑哪个 Agent"变成可替换的。

### 3.3 与 LangGraph 的关系（节点 = 薄包装）

LangGraph 图上的每个蓝色节点 = **薄包装**：节点逻辑 = 调 `AgentProvider.start()` + 应用 ContextPolicy / ResourceClaim。图的结构（谁接谁、怎么循环）归 LangGraph，节点内部"跑哪个模型、注入什么上下文"归平台。

### 3.4 定义

```typescript
interface AgentProvider {
  readonly name: string;
  capabilities(): AgentCapabilities;       // 先问能力
  start(request: AgentStartRequest): Promise<AgentRun>;  // 再启动
}
```

- Provider 可以包装：本地 LLM API（DeepSeek / GLM）、Codex CLI、Claude Agent SDK、任意 NewAgent-X
- 设计参考：DSH 的 Capability Seam（Service Definition → Provider → Consumer）→ https://github.com/deepseek-ai/deepseek-harness ；Codex 的 multi-agent 源码 → https://github.com/openai/codex/blob/main/codex-rs/core/src/session/multi_agents.rs

### 3.5 能力声明（AgentCapabilities）：先问会不会，再派活

```typescript
interface AgentCapabilities {
  structuredOutput: boolean;   // 能输出结构化结果吗
  contextFork: boolean;        // 能显式 fork 上下文吗
  resume: boolean;             // 能恢复吗
  subagent: boolean;           // 能 spawn 子 agent 吗
  toolFilter: boolean;         // 能限制工具白名单吗
  sandbox: boolean;            // 自带沙箱吗
  streaming: boolean;          // 流式吗
}
```

**Fail loud（响亮失败，不静默降级）**：业务要求 `structuredOutput=true`，Provider 不支持 → 直接报 `UNSUPPORTED_CAPABILITY`，绝不偷偷降级成普通文本（否则 Eval / Artifact 契约会被破坏）。

---

## 4. AgentRun / AgentSession：Agent 不是一次函数调用

### 4.1 图上位置

所有蓝色 Agent 框的"运行时形态"。

### 4.2 为什么

旧接口 `run(input): Promise<output>` 太薄：Agent 可能跑几分钟、可能被取消、可能崩溃要恢复、可能有父子关系。要表达这些，需要运行句柄 + 会话。

### 4.3 AgentRun（执行句柄）

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

### 4.4 AgentSession / Lineage（会话与血缘）

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

### 4.5 三套状态别混（LangGraph / Temporal / Agent Session）

| | LangGraph graph state | Temporal Event History | Agent Session Event Log |
|---|---|---|---|
| 语义 | 图走到哪了（节点执行顺序） | 执行真相（谁跑了、重试几次、崩溃点） | 交互真相（模型看到了什么、调了什么工具） |
| 记录 | checkpoint（superstep 边界） | Commands / Events / Activity 结果 | AgentStarted / ModelRequest / ToolCall / SubagentEnded... |
| 用途 | 断点续跑（图级） | 执行恢复 / 审计 | 语义审计 / trace / eval 溯源 |

图上：LangGraph 管"图结构"的状态，Temporal 管"流程箭头"的执行，Session Log 管"蓝色框"里 LLM 干了什么。

---

## 5. ContextPolicy：Agent 用什么上下文跑（自研，本项目最重要的能力）

### 5.1 图上位置

- **CodeAgent 必须看不到源码** → artifact-only（知识文档+接口，无源码）
- **TestGenAgent 读源码** → artifact-only（含源码）
- **CheckAgent / ReviewAgent 全新上下文** → fresh（不知道作者、无生成历史）
- **DocWorkerAgent 分块** → fork-all（继承分块指令）

### 5.2 定义

```typescript
interface ContextPolicy {
  mode:
    | "fresh"            // 全新上下文（Check/Review 默认）
    | "fork-all"         // 继承全部父上下文（DocWorker 子任务）
    | "fork-last-n"      // 只继承最近 N 轮（控制膨胀）
    | "artifact-only";   // 只注入指定 Artifact（CodeAgent：知识文档+接口）
}
```

### 5.3 为什么是"平台能力"而不是"prompt 约束"

- prompt 里写"不要看源码" = 软约束，Agent 可能违反
- **ContextPolicy = 硬约束**：平台在注入上下文时**物理上就不给**源码 → 配合 Sandbox 双重强制
- 参考：Codex 的显式上下文 fork（`fork_turns = all / N / none`）

---

## 6. ResourceClaim：谁和谁可以并行（自研）

### 6.1 图上位置

- DocWorkerAgent×N 并行 → 需要判定 A/B/C 是否真独立
- 未来多 Agent 并行写产物 → 需要资源冲突判定

### 6.2 为什么不是 maxConcurrency = 5

OpenHands 的教训：并发不只是"限数量"，还要看**共享资源冲突**：

```
Agent A writes moduleA
Agent B writes moduleB   → A ∥ B safe（可以并行）
Agent C writes moduleA   → A ∥ C conflict（不能并行）
```

### 6.3 定义

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

调度系统据此判定：无写冲突 → 可并行；有写冲突 → 串行。比 `maxConcurrency=5` 精确得多。参考：OpenHands `ResourceLockManager` / `DeclaredResources` → https://github.com/OpenHands/software-agent-sdk

---

## 7. 副作用幂等（自研，业务正确性，Temporal 不管这个）

### 7.1 图上位置

Agent 每次调 LLM / 写 Artifact / 发知识，都要防重复。

### 7.2 为什么需要

Temporal 重试时，可能存在"LLM 已返回但结果没提交 → 崩溃 → 重试 → 再调一次"的窗口。所以**业务副作用去重要平台自己做**：

- LLM 调用去重：`GenerationKey = workflowRunId + moduleId + iteration + agentType + promptHash + modelConfigHash`
- Artifact 写幂等：同 key 重复写不产生脏产物
- 知识发布幂等：按版本号幂等

---

## 8. 连接外部：ACP / A2A / MCP（现成协议，只做 Adapter）

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

## 9. V1 / V2 边界（对照图）

**V1**：
- LangGraph 定义 7 Agent 图：节点 = AgentProvider 薄包装、条件边 = 门禁状态机、Send = DocWorker 并行、Postgres checkpointer
- 图上所有蓝色框跑在 AgentProvider 上
- CodeAgent 的 ContextPolicy = artifact-only（看不到源码）
- DocWorker 并行用 ResourceClaim 判定
- 持久执行：Temporal（插件评估接入）
- 接 Codex / Claude 用 ACP PoC；工具 / 知识用 MCP
- 副作用幂等（GenerationKey）就位

**V2+**：
- Agent Teams（Task DAG / durable mailbox / writeScopes）
- rich A2A / 跨 repo 调度 / 分布式 Agent Provider / 智能 Resource Scheduler
- Temporal LangGraph 插件必上（长任务 / 多 worker）

## 10. 成功标准（怎么算设计对）

1. 新 Coding Agent（NewAgent-X）出现 → 只加 Provider 或 ACP 配置，**不动**飞轮 / 图 / EvalRunner / KnowledgeStore
2. LangGraph 被替换 → 只改图的定义（节点 / 边描述），**不重写**平台和业务
3. Temporal 被替换 → 只改持久执行 Adapter，**不重写**平台和业务
4. 模型 DeepSeek → GLM → OpenAI → private → 只改 Model / Agent Provider

**若做不到以上任意一条，说明 Agent Platform abstraction 设计失败。**
