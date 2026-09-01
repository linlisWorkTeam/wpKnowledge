# 数据边界与权限矩阵

动作缩写：`R` 读、`W` 创建新 Artifact、`X` 隔离执行、`P` 发布、`-` 拒绝。表中未出现的主体、资源或动作一律拒绝。

| 主体 | 参考源码 | 候选知识 | 公开接口 | 候选测试/oracle | 门禁测试 | Code 工作区 | 评测报告 | 发布知识 | Checkpoint/事件 |
|---|---|---|---|---|---|---|---|---|---|
| OrchestratorAgent | - | 元数据R | 元数据R | 元数据R | - | - | R | - | 仅命令W |
| DocGen/Worker | R(授权范围) | W / base R | R | - | - | - | R(仅Correction证据) | - | - |
| TestGenAgent | R | - | R | W | - | - | - | - | - |
| CodeAgent | - | R | R | - | - | W | - | - | - |
| CheckAgent | - | R | R | - | - | R(diff) | - | - | - |
| ReviewAgent | - | R | R | - | - | - | R | - | - |
| EvalRunner | R(oracle验证) | R | R | R | R | R/X | W | - | 事件W |
| Workflow Service | 元数据R | 元数据R | 元数据R | 元数据R | 元数据R | 元数据R | 元数据R | - | R/W |
| Knowledge Publisher | - | R | - | - | - | - | R | P | 事件W |
| Human Governor | 按仓库ACL R | R/W新版本 | R | R | 仅受控R | - | R | 通过门禁后请求P | 审计R |

## 数据级别

`SOURCE_RESTRICTED`（源码/门禁测试）、`CANDIDATE`, `INTERNAL`, `PUBLISHED`, `SECRET`。密钥仅由 Provider/Sandbox Adapter 在调用瞬间取得，不成为 Artifact。日志只记摘要和引用；stdout/stderr 先脱敏并受大小限制。授权令牌绑定 runId、主体、资源摘要、动作、过期时间，不可跨 Agent/session 转移。

