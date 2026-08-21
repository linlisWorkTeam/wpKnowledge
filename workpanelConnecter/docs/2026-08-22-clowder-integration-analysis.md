# WorkPanelConnecter × Clowder AI 集成分析

日期：2026-08-22
Clowder 研究 commit：`8fd4824cb7db9124a0d863ba1b085a59b865c722`（2026-08-21）
Connecter 研究 commits：`b133877`, `12ebb66`, `d73e5c6` / v0.2.3 候选；本轮文档审查未改变 adapter 结论
Clowder 仓库：[zts212653/clowder-ai](https://github.com/zts212653/clowder-ai)

## 结论

Connecter 可以同时连接 WorkPanel 与 Clowder AI，而且这种“双宿主”比二选一更符合 Connecter 的中间件定位。必要性是条件性的：若只在单机使用 Clowder 的多 Agent 协作，不需要 Connecter；若需要把 Clowder 的 Agent 团队与不同服务器上的 WorkPanel User/群组/Runner 联通、统一跨站策略和审计，Connecter 有明确价值。

推荐做法是 adapter，不是 fork 或内嵌：

```text
WorkPanelAdapter ----\
                     Site Connecter -> Connecter Host -> other Sites
ClowderA2AAdapter ---/
RunnerAdapter -------/
```

## Clowder 当前代码事实

1. [`A2AAgentService.ts`](https://github.com/zts212653/clowder-ai/blob/8fd4824cb7db9124a0d863ba1b085a59b865c722/packages/api/src/domains/cats/services/agents/providers/A2AAgentService.ts) 已作为 A2A client，通过 HTTPS JSON-RPC `tasks/send` 调远端 Agent，支持 bearer、timeout/cancel，并把结果映射为 `AgentMessage`；当前注释明确 streaming 属于后续阶段。
2. [F050 External Agent Onboarding](https://github.com/zts212653/clowder-ai/blob/8fd4824cb7db9124a0d863ba1b085a59b865c722/docs/features/F050-a2a-external-agent-onboarding.md) 已关闭 L1 CLI contract；L2 A2A 设计和 client 代码存在，但真实远程验收仍被拆为后续工作。文档强调“协议互通不等于协作语义互通”。
3. [F143 Hostable Agent Runtime](https://github.com/zts212653/clowder-ai/blob/8fd4824cb7db9124a0d863ba1b085a59b865c722/docs/features/F143-hostable-agent-runtime.md) 仍是 spec，目标是 Transport × Binding × RuntimeContract × EventAdapter 的配置式接入；全部主要 AC 尚未勾选。
4. [`ExternalRuntimeSessionRegistration.ts`](https://github.com/zts212653/clowder-ai/blob/8fd4824cb7db9124a0d863ba1b085a59b865c722/packages/api/src/domains/cats/services/runtime-session/ExternalRuntimeSessionRegistration.ts) 已有外部 runtime session 注册、agent-key principal、cat/user/thread 不可变绑定和并发锁，但 runtime allowlist 当前只含 `antigravity-desktop`，不能直接当通用 Connecter 注册接口。
5. [F178 Persistent Agent-Key](https://github.com/zts212653/clowder-ai/blob/8fd4824cb7db9124a0d863ba1b085a59b865c722/docs/features/F178-persistent-mcp-agent-key-auth.md) 已完成 principal/registry/核心 allowlist，具备 hash、TTL、rotation、revocation 和 0600 sidecar 思路；审计/失败率闭环仍有 backlog。
6. [F261 Durable Execution](https://github.com/zts212653/clowder-ai/blob/8fd4824cb7db9124a0d863ba1b085a59b865c722/docs/features/F261-agy-durable-execution-recovery.md) 仍是 spec。Clowder 对长任务跨重启的 Managed Job 真相源尚未完成，不能把它当作 Connecter Runner lease/fencing 的现成替代。

## 三种集成方案

### A. Connecter 暴露 A2A server façade（推荐首期）

Clowder 保持现有 `A2AAgentService`，把 Connecter 注册成 remote Agent。Connecter 新增 `/.well-known/agent.json` 和 `tasks/send`，内部翻译为本地或 federation envelope，并等待/查询终态。

优点：Clowder 改动最小，边界标准化，WorkPanel 与 Clowder 解耦。缺点：Clowder 当前 client 偏同步，需定义超时后 task 查询、取消与流式语义。

### B. Clowder 作为 Connecter Runner

实现 `clowder-runner`，向 Site Connecter register/heartbeat/poll/ack/result，再调用 Clowder thread/invocation API。

优点：直接复用 Connecter v2 lease/fencing 和跨站结果链。缺点：Clowder 当前没有稳定的通用“外部启动任意 Cat task 并返回 durable result”公共契约，需要插件或专用 endpoint；身份/thread 绑定更复杂。

### C. Connecter 作为 Clowder channel connector

复用 Clowder `infrastructure/connectors` 模式，把 WorkPanel 消息当外部渠道消息。

优点：适合纯聊天。缺点：该层主要面向 IM gateway，不拥有跨站 Agent 任务、lease/fencing 或全局目录，无法单独满足 Connecter 愿景。只适合作为 UI/channel 补充。

## 推荐分阶段成本

| 阶段 | 范围 | 估算（单名熟悉双方 TypeScript 工程师） |
|---|---|---:|
| Spike | Agent Card、`tasks/send`、文本结果映射、固定身份 | 3-5 人日 |
| MVP | 鉴权、Subject↔Cat、GroupRef↔Thread、幂等、超时、错误映射、契约测试 | 10-15 人日 |
| 双向可靠版 | 异步 task 状态、回调/轮询、取消、流式事件、附件、断线恢复、审计/trace | 20-35 人日 |
| 生产验收 | mTLS/secret rotation、配额、跨机 chaos、升级兼容、SLO/告警 | 10-20 人日 + 环境等待 |

合计：可演示单轮约 1 周；可用 MVP 约 2-3 周；生产级双向连接约 6-10 周。若要求同时修改 Clowder F143/F261 内核或上游合并，排期会进一步增加。

## 身份与语义映射

| Connecter | Clowder | 规则 |
|---|---|---|
| Subject ID | `catId + userId` principal | 显式映射表，不用显示名猜测 |
| GroupRef | thread ID | 一个映射可版本化；禁止默认 thread 静默兜底 |
| Runner task ID | A2A task/invocation ID | 保留 causation/correlation/trace |
| capability | Agent descriptor / provider capability | 取交集并进入 policy decision |
| lease/cancel | invocation/task cancel | 两侧终态需 first-terminal-wins，未知状态不自动重放副作用 |

## 必要性判断

- **必要**：跨服务器 WorkPanel 用户要调用 Clowder Cats；Clowder 结果要回写 WorkPanel 群；需要统一 Site ACL、审计、NAT 出站接入和故障隔离。
- **非必要**：所有用户和 Agents 都在同一 Clowder 实例，且没有 WorkPanel/跨站需求。
- **不应做**：把 Clowder 的记忆、SOP、prompt hooks 或 UI 搬进 Connecter；把 Connecter 的 Host 当 Clowder 的执行 supervisor；绕过两边的 principal 和 policy。

## 首个可执行 PoC

1. 在 Connecter 新建隔离的 `adapters/a2a` façade，不修改 federation v1 envelope。
2. 固定一个 Clowder Cat/Thread 与一个 Connecter Subject/GroupRef 的显式映射。
3. Clowder `A2AAgentService` 调 `tasks/send`；Connecter 投递到本地 mock Runner 和远端 Site Runner各一次。
4. 验证成功、超时、重复 request ID、取消、Host 重启和旧 token 失效。
5. 只有 PoC 数据证明需求后，再决定 Clowder Runner path 或 streaming。

## 证据边界

本次 Git clone 因 `github.com:443` 间歇不可达未完成；源码通过 GitHub API 按 commit `8fd4824` 读取，关键文件和文档均使用固定 commit 链接。没有构建或运行 Clowder，也没有验证其未公开 API。因此成本是架构级估算，进入实现前应完成本地 clone、依赖构建和双方真实契约探针。
