# ADR-002：LangGraph V1 编排与可替换端口

- 状态：Accepted
- 日期：2026-08-31

## 决策

V1 采用 LangGraph StateGraph、条件边、Send 和 SQLite Checkpointer；业务只依赖 WorkflowPort，门禁状态机自研且确定性。P0-B 与 Temporal 做崩溃恢复和运维对照。

## 后果

避免自研图运行时并匹配本地单进程；节点副作用必须幂等。若 Spike 否定选择，以新 ADR 替代，不改变领域契约。

