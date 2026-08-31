# 追踪矩阵

计划路径是 P0-B 之后的实现落点；本提交不创建这些业务模块。

| 需求 ID | 验收 | 计划实现 | 计划测试 |
|---|---|---|---|
| SYS-001 | AC-FLOW-001 | packages/application/workflow | tests/acceptance/flywheel-flow.test.ts |
| SYS-002 | AC-AGENT-001 | packages/application/authorization | tests/acceptance/agent-authority.test.ts |
| SYS-003 | AC-SEC-001 | packages/adapters/sandbox | tests/security/code-isolation.test.ts |
| SYS-004 | AC-EVAL-001 | packages/application/oracle-verifier | tests/acceptance/oracle-verification.test.ts |
| SYS-005 | AC-EVAL-002 | packages/application/evaluation | tests/acceptance/gate.test.ts |
| SYS-006 | AC-OBS-001 | packages/application/audit | tests/acceptance/audit-export.test.ts |
| SYS-007 | AC-FLOW-002 | packages/application/revision | tests/acceptance/incremental-revision.test.ts |
| SYS-008 | AC-FLOW-003 | packages/application/gate-policy | tests/acceptance/rollback-stop.test.ts |
| SYS-009 | AC-PUB-001 | packages/application/publication | tests/acceptance/publication.test.ts |
| SYS-010 | AC-REC-001 | packages/adapters/workflow | tests/acceptance/crash-recovery.test.ts |
| SYS-011 | AC-SCHEMA-001 | packages/contracts | tests/contract/agent-schema.test.ts |
| SYS-012 | AC-LANG-001 | packages/application/language-port | tests/contract/language-neutrality.test.ts |
| SYS-013 | AC-SEC-002 | packages/application/authorization | tests/security/permission-matrix.test.ts |
| SYS-014 | AC-LANG-002 | plugins/languages/cpp | tests/integration/cpp-sandbox.test.ts |
| SYS-015 | AC-AGENT-002 | packages/application/orchestration | tests/acceptance/deterministic-decision.test.ts |
| NFR-001 | AC-SEC-002 | packages/application/authorization | tests/security/default-deny.test.ts |
| NFR-002 | AC-REC-001 | packages/adapters/workflow | tests/acceptance/crash-recovery.test.ts |
| NFR-003 | AC-REC-002 | packages/application/idempotency | tests/integration/idempotency.test.ts |
| NFR-004 | AC-OBS-001 | packages/application/audit | tests/acceptance/audit-export.test.ts |
| NFR-005 | AC-ARCH-001 | packages/domain + packages/contracts | tests/architecture/adapter-boundary.test.ts |
| NFR-006 | AC-SCHEMA-001 | packages/contracts/migrations | tests/contract/schema-compatibility.test.ts |
| NFR-007 | AC-LANG-002 | packages/adapters/sandbox | tests/security/resource-limits.test.ts |
| NFR-008 | AC-EVAL-003 | packages/application/evaluation | tests/acceptance/reproducibility.test.ts |
| NFR-009 | AC-SEC-003 | packages/application/audit | tests/security/redaction.test.ts |
| NFR-010 | AC-FLOW-004 | packages/application/scheduler | tests/acceptance/resource-claims.test.ts |

Spike `SPK-001..005` 分别计划落在 `spikes/{dsh-provider,workflow-engine,glm-provider,artifact-store,cpp-sandbox}/`，各自用 `spikes/*/report.md` 与可重复脚本验收；它们不计为本 P0-A Spec 提交的实现。

