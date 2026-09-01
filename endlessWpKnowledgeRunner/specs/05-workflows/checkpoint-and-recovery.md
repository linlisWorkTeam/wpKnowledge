# Checkpoint 与恢复

## 提交协议

每个节点执行 `读取 checkpoint → 认领 GenerationKey → 执行 → 临时写 Artifact → 摘要校验/原子提交 → 追加事件 → 提交节点 checkpoint`。checkpoint 不得引用未提交 Artifact。

## 恢复语义

- 启动时 Run Registry 扫描非终态 Run，以 `threadId/runId` 从最后完整 checkpoint 恢复。
- 节点中途崩溃视为“结果未知”；允许重放，但同 GenerationKey 返回已提交结果或重新执行后 CAS 去重。
- 模型流式半成品、沙箱临时目录和未提交对象不进入领域状态，恢复时清理。
- 发布采用 `publicationKey=moduleId+versionId+policyId` 的比较交换；重复发布返回原 receipt。
- checkpoint 损坏或 Artifact 摘要不符时禁止继续，Run 转 `FAILED` 并记录 `INTEGRITY_FAILURE`。
- 进程不会在关机期间继续；取消恢复后维持 `CANCELLED`，不会自动重启。

## 失败分类

`TRANSIENT` 可按策略退避重试；`AGENT_OUTPUT_INVALID` 允许同节点有限重试；`POLICY_DENIED`、`INTEGRITY_FAILURE`、`UNSUPPORTED_CAPABILITY` 不重试；`RESOURCE_EXHAUSTED` 是否重试由已固化策略决定。所有重试计数进入 checkpoint。

## 崩溃注入点

验收必须覆盖：模型返回后/Artifact 提交前、Artifact 提交后/事件前、事件后/checkpoint 前、发布 CAS 前后。每个点均验证无悬空引用、无重复发布、状态单调。

