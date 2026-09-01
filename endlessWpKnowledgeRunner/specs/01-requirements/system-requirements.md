# 系统需求

状态：Accepted。优先级 `P0` 是 V1 发布阻塞项。

| ID | 优先级 | 需求 | 验收场景 |
|---|---|---|---|
| KF-SYS-001 | P0 | 系统必须以确定性工作流编排源码分析、知识生成、测试生成、代码生成、检查、评测、归因、修订与发布。 | AC-FLOW-001 |
| KF-SYS-002 | P0 | DocGenAgent 必须是知识正文的唯一自动执笔者；评测者不得修改知识或实现。 | AC-AGENT-001 |
| KF-SYS-003 | P0 | CodeAgent 必须只读取知识、公开接口和自己的工作区，不能读取参考源码或门禁测试。 | AC-SEC-001 |
| KF-SYS-004 | P0 | TestGenAgent 的候选 oracle 必须由参考源码真实执行验证后才能进入门禁集。 | AC-EVAL-001 |
| KF-SYS-005 | P0 | EvalRunner 必须执行编译、稳定测试和关键行为门禁；相似度只能用于归因。 | AC-EVAL-002 |
| KF-SYS-006 | P0 | 每轮必须产出不可变 Artifact、血缘、事件和评测证据，并能按 `runId` 审计。 | AC-OBS-001 |
| KF-SYS-007 | P0 | 门禁失败时 ReviewAgent 必须输出可定位、可验证、有证据的 Correction，随后只增量修订受影响知识。 | AC-FLOW-002 |
| KF-SYS-008 | P0 | 系统必须保留 historical best；关键回归立即回滚，停滞或预算耗尽转 `LOW_CONFIDENCE`。 | AC-FLOW-003 |
| KF-SYS-009 | P0 | 仅满足知识发布门禁的版本可成为 `VERIFIED`；人工修改也必须重新生成代码并走完整门禁。 | AC-PUB-001 |
| KF-SYS-010 | P0 | 工作流必须支持进程退出后的 checkpoint 恢复，所有外部副作用必须按幂等键去重。 | AC-REC-001 |
| KF-SYS-011 | P0 | Agent 输入输出必须逐一匹配版本化 JSON Schema；Schema 校验失败不得调度下游。 | AC-SCHEMA-001 |
| KF-SYS-012 | P0 | 核心必须通过语言插件端口支持语言能力；语言专属结构不得进入核心领域或通用 Agent 契约。 | AC-LANG-001 |
| KF-SYS-013 | P0 | 系统必须执行完整的主体×资源×动作权限矩阵，未列出的访问默认拒绝并留审计事件。 | AC-SEC-002 |
| KF-SYS-014 | P0 | V1 必须提供 C++ 插件，完成发现、构建、测试执行、超时和资源限制结果的标准化。 | AC-LANG-002 |
| KF-SYS-015 | P0 | OrchestratorAgent 只负责计划、委派和汇总；`pass/iterate/rollback/stopped` 必须由确定性门禁规则决定。 | AC-AGENT-002 |
| KF-SYS-016 | P0 | `endlessWpKnowledgeRunner` 的旧入口必须作为新 TypeScript 核心的兼容层保留；兼容层不得维护第二套知识状态、评分权威或写入路径。 | AC-COMPAT-001 |
| KF-SYS-017 | P0 | 发布前必须以固定 commit 的真实可运行源码完成一次可复验闭环：参考门禁通过、首轮生成失败、Review 产生 Correction、DocGen 增量修订、CodeAgent fresh 再生成、独立 EvalRunner 全门禁通过、确定性发布并可按 runId 审计。 | AC-E2E-001 |
| KF-SYS-018 | P1 | DocGenAgent 生成中文知识时必须遵循面向工程师的自然写作约束：直接说明结论和适用条件，用具体证据代替宣传或模糊归因，并保留术语、限定条件与不确定性；Quality Gate 应报告模板腔和超长段落，但文风不得覆盖事实、Schema 或行为门禁。 | AC-DOC-001 |

## P0-B Spike（P0-A 后独立开展）

| ID | 假设 | Spike 出口证据 | 未通过时默认方案 |
|---|---|---|---|
| SPK-001 | DSH SDK 可通过 Adapter 满足 AgentProvider 契约。 | 类型映射、取消/超时、流式输出、错误分类实验。 | 使用进程型 Provider；核心不依赖 DSH。 |
| SPK-002 | LangGraph Checkpointer 足以支撑 V1，本地条件下优于 Temporal。 | 崩溃注入、重放、操作复杂度对照。 | 保留 WorkflowPort，采用通过实验的一方。 |
| SPK-003 | 内部 GLM 满足结构化输出、工具调用、上下文和稳定性要求。 | 固定语料重复试验和错误分布。 | Provider 降级/重试并阻止发布，不更换契约。 |
| SPK-004 | Artifact Store 可提供内容寻址、原子发布和校验。 | 并发写、损坏检测、去重、恢复实验。 | V1 本地文件 CAS + SQLite 元数据。 |
| SPK-005 | C++ 沙箱可证明源码/测试隔离并限制资源。 | 路径穿越、符号链接、进程树、网络、CPU/内存测试。 | 阻止 C++ 生产运行，不弱化隔离。 |
