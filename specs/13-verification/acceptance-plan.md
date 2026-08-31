# P0 验收计划

所有场景使用 Given/When/Then，可自动化场景为发布阻塞项。

| ID | 场景 |
|---|---|
| AC-SPEC-001 | Given 本规范集，When 执行 spec lint，Then 每个 SYS/NFR P0 ID 在追踪矩阵中恰有一行且实现、测试、场景非空。 |
| AC-SCHEMA-001 | Given 每类 Agent 的合法/非法 fixture，When Draft 2020-12 校验，Then 合法输入输出通过，未知字段、缺字段和错误版本失败且不调度下游。 |
| AC-FLOW-001 | Given 一个受支持模块，When 执行 Run，Then 状态按定义顺序完成两条独立生成链并以确定性 Gate 到达终态。 |
| AC-FLOW-002 | Given 一个可归因失败，When Review 完成，Then Correction 含路径、判据、证据，DocGen 仅改影响范围且 Code fresh 重生成。 |
| AC-FLOW-003 | Given critical regression 或预算耗尽，When Gate 决策，Then 分别回滚 historical best 或产生 LOW_CONFIDENCE 治理包。 |
| AC-FLOW-004 | Given 冲突写声明和六个并行 worker，When 规划，Then 冲突在执行前拒绝且同时运行数不超过五。 |
| AC-AGENT-001 | Given 全角色能力令牌，When 尝试写知识，Then 只有 DocGen 可创建候选，任何评测/评审写入均拒绝。 |
| AC-AGENT-002 | Given Orchestrator 输出主观 PASS，When 处理结果，Then 该字段因 Schema/权限失败，状态只接受 GateDecision。 |
| AC-SEC-001 | Given CodeAgent 会话，When 读取源码、门禁测试、旧实现、路径穿越或符号链接，Then 全部拒绝并产生 AccessDenied。 |
| AC-SEC-002 | Given 矩阵内外访问组合，When 执行权限参数化测试，Then 所有列明动作符合矩阵，未定义组合默认拒绝。 |
| AC-SEC-003 | Given 含源码、密钥和超长输出的任务，When 导出日志，Then 仅保留脱敏摘要/ArtifactRef 且输出受限。 |
| AC-EVAL-001 | Given LLM 猜测的错误 expected，When oracle 验证，Then 用例不能进入 Gate Test Set。 |
| AC-EVAL-002 | Given critical 失败、高相似度或五次中一次波动，When Gate，Then 均不能 PASS；报告保留全部重复结果。 |
| AC-EVAL-003 | Given 同一报告，When 审计，Then 能重建输入、测试集、策略、插件、工具链、prompt/model 配置摘要。 |
| AC-PUB-001 | Given Agent 或人工修改的候选，When 请求发布，Then 只有完整 fresh generation + Gate PASS 能原子生成唯一 receipt。 |
| AC-REC-001 | Given 四个崩溃注入点，When 重启恢复，Then 无悬空 Artifact、丢失状态或重复发布。 |
| AC-REC-002 | Given 相同 GenerationKey/发布键并发重试，When 完成，Then 只有一个逻辑生成结果和一个 receipt。 |
| AC-OBS-001 | Given 任一 Run，When 按 runId 导出，Then 状态、模型调用摘要、访问拒绝、Artifact 血缘和 Gate 证据完整。 |
| AC-ARCH-001 | Given 替代假 Provider/Store/Workflow Adapter，When 跑契约套件，Then Domain/Application 不变且测试通过。 |
| AC-LANG-001 | Given 非 C++ 假插件，When 运行发现与标准化契约测试，Then 核心成功且通用消息无 C/C++ 专属字段。 |
| AC-LANG-002 | Given C++ 示例及 CPU/内存/超时/进程树攻击，When 沙箱执行，Then正常结果标准化、超限终止并审计。 |

## P0-A Review 清单

`AC-SPEC-001` 还检查：accepted 文件无阻塞性占位标记；Schema 可解析且 `$id` 唯一；权限矩阵无空单元格；状态全集与转换目标一致；Domain 禁止 SDK/语言类型；全部 P0 有场景。P0-A 通过是创建独立 P0-B Spike 的前置条件，不代表 Spike 已通过或生产可用。
