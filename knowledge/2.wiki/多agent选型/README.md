# 多 Agent 选型（架构决策索引）

> 更新：2026-08-26 ｜ 读完本文 1～3 分钟，即可掌握当前架构真相。
> 原则：成熟问题用成熟基础设施；知识工程壁垒自研；所有第三方通过稳定内部接口隔离。

## 当前最终决策

| 能力 | 决策 | 方案 | WHY（一句话） |
|---|---|---|---|
| Workflow Runtime | **Adopt** | **Temporal** | durable execution 是成熟非差异化基础设施，不重造 workflow engine |
| Multi-Agent Graph Orchestration | **Adopt** | **LangGraph**（图编排层）+ Temporal 官方插件（持久执行） | 01 的架构本来就长成一张图；图怎么走 = LangGraph，挂了怎么办 = Temporal，不重造编排 |
| Agent Platform | **Build（稳定内部 Contract）** | 参考 Codex / DSH / OpenHands | 公司级 Agent abstraction，需要控制长期 API，不绑定任何厂商 |
| Coding Agent Interop | **Adopt（PoC）** | **ACP** | 避免为 Codex / Claude / Gemini 各造私有协议 |
| Remote Agent Interop | **Adopt（按需）** | **A2A** | 远程独立 Agent Service 互操作标准 |
| Tool / Knowledge Service | **Adopt** | **MCP** | Agent ↔ 工具/知识服务的标准协议 |
| Knowledge Engineering Domain | **Build（完全自研）** | 知识飞轮 / EvalRunner / KnowledgeStore | 真正的业务壁垒，无现成方案 |

## 四层架构

```mermaid
flowchart TD
    subgraph DOMAIN["Knowledge Engineering Domain ★ 核心自研：业务竞争力"]
        D1["Knowledge Flywheel<br/>DocGen / TestGen / Code / Review"]
        D2["EvalRunner / KnowledgeStore<br/>Artifact / Oracle / Feedback"]
        D3["Dependency Graph / 防作弊信息隔离"]
    end

    subgraph PLATFORM["Knowledge Agent Platform ★ 自研稳定接口，不重造 Runtime"]
        P1["AgentProvider / AgentRun / AgentSession"]
        P2["ContextPolicy / ResourceClaim / Capability"]
        P3["Permission / Sandbox / Trace / Session Event Log"]
        P4["ACP Adapter ｜ A2A Adapter ｜ MCP"]
    end

    subgraph RUNTIME["Workflow Runtime ★ 直接使用成熟基础设施"]
        R1["Temporal<br/>Retry / Timeout / Resume / Signal"]
        R2["Child Workflow / Crash Recovery / Versioning"]
        R3["Distributed Worker / Execution History"]
    end

    subgraph INFRA["Infrastructure"]
        I1["Postgres / Object Store / K8s / Sandbox / OTEL"]
    end

    DOMAIN --> PLATFORM --> RUNTIME --> INFRA
```

## 架构核心判断

1. **主干本质**：deterministic engineering workflow + uncertain intelligent steps。业务主流程由 **Workflow Runtime（Temporal）** 驱动；**LLM Agent 只是 Workflow 中的智能执行节点**。
2. **Temporal 解决 execution reliability，不解决 domain correctness**：LLM 去重、Artifact 幂等、知识发布幂等、权限/沙箱/上下文隔离、Eval 正确性，全部由 Agent Platform / Domain 负责。
3. **所有 Agent 运行时差异通过 Adapter 隔离**：业务层绝不出现 `if provider === "codex"`。未来新增 NewAgent-X = 新增 Provider 或 ACP 配置，不动 Flywheel / Workflow / EvalRunner / KnowledgeStore。
4. **不重复造协议**：MCP（Agent↔工具）、ACP（Platform↔Coding Agent）、A2A（Agent Service↔Agent Service），除非标准协议被证明不满足，否则不建私有协议。
5. **LangGraph 与 Temporal 分层（04 定案）**：LangGraph = 多 Agent 图编排层（图怎么走：节点 / 边 / 并行 / 状态 / 循环）；Temporal = 持久执行层（挂了怎么办：retry / recovery / 分布式 worker）；官方 LangGraph 插件桥接两层。DSH 仅作 Agent 运行层参考（03）。

## 看哪篇文档

| 文档 | 内容 | 什么时候看 |
|---|---|---|
| [01-多agent调研.md](01-多agent调研.md) | **业务架构**：Agent 角色、Eval / Artifact / 隔离、知识飞轮主循环 | 想了解业务怎么跑 |
| [02-技术选型与架构决策.md](02-技术选型与架构决策.md) | **为什么这么选**：ADR / 技术选型与架构决策（Temporal / ACP / A2A / MCP / DSH / Codex / OpenHands） | 想了解每个决策的 WHY |
| [03-Agent-Platform架构设计.md](03-Agent-Platform架构设计.md) | **Agent Platform 怎么实现**：AgentProvider / AgentRun / Session / ContextPolicy / ResourceClaim / Capability / ACP | 要开始实现 Agent Platform |
| [04-LangGraph选型与多Agent图.md](04-LangGraph选型与多Agent图.md) | **框架选型**：选型图 × 01 合并 mermaid；为什么选 LangGraph / 不选竞品；与 Temporal 分层 | 想确认"为什么用 LangGraph 不用 XX" |
| [05-知识回写与知识治理.md](05-知识回写与知识治理.md) | **知识治理规则**：增量回写、版本治理、Verification Score、迭代预算、Early Stop + Rollback、人工治理、稳定测试集 | 想知道知识怎么回写 / 怎么算 verified / 怎么转人工 |
