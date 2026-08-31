# ADR-004：确定性评测和发布权分离

- 状态：Accepted
- 日期：2026-08-31

## 决策

Agent 生成和归因，EvalRunner/GatePolicy 以客观证据决策，Knowledge Publisher 独占发布权。LLM 自评和相似度均不能通过门禁。

## 后果

门禁可复现且避免 maker 自审；必须维护真实 oracle、稳定测试集和版本化策略。

