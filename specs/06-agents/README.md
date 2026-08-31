# Agent 规范

五类规范覆盖七个运行角色：

1. [编排类](orchestration-agents.md)：OrchestratorAgent
2. [知识生产类](documentation-agents.md)：DocGenAgent、可选 DocWorkerAgent
3. [测试生产类](test-generation-agent.md)：TestGenAgent
4. [代码与检查类](code-and-check-agents.md)：CodeAgent、CheckAgent
5. [评审类](review-agent.md)：ReviewAgent

统一信封、角色枚举和 payload 字段由 `agent-command.schema.json` 与 `agent-result.schema.json` 定义，Correction 另由 `correction.schema.json` 约束。所有输入 Artifact 在调用前授权，所有输出先 Schema 校验再提交。Agent 不能直接改变 Run 状态、发布知识或授予权限。
