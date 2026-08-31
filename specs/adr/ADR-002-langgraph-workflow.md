# ADR-002：LangGraph V1 编排与可替换端口

- 状态：Proposed（需要 Workflow Spike）
- 日期：2026-08-31

## 决策

V1 领域和应用只依赖 WorkflowPort，门禁状态机自研且确定性。当前本地实现使用 SQLite Registry 与 GenerationKey checkpoint 协调器验证提交协议；LangGraph StateGraph/SQLite Checkpointer 是候选 Adapter，必须通过崩溃注入和与 Temporal 的对照 Spike 后才能转为 Accepted。

## 后果

领域契约不绑定工作流 SDK；节点副作用必须幂等。Spike 可以选择 LangGraph、Temporal 或保留本地协调器，但不得改变 Artifact 完整性、事件审计、GenerationKey 去重和原子发布约束。

