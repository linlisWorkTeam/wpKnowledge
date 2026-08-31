# 追踪矩阵

实现状态按当前代码和可执行测试记录。`Implemented` 表示已有对应代码与自动化验证，`Partial` 表示只实现安全子集，`Planned` 表示规范仍保留但不得宣称为当前能力。

| 需求 ID | 验收 | 状态 | 实现 | 测试 |
|---|---|---|---|---|
| KF-SYS-001 | AC-FLOW-001 | Partial | packages/application/src/index.ts | tests/acceptance/publication-flow.test.ts |
| KF-SYS-002 | AC-AGENT-001 | Planned | packages/contracts/src/index.ts | tests/contract/agent-schema.test.ts |
| KF-SYS-003 | AC-SEC-001 | Planned | packages/contracts/src/index.ts Sandbox port | tests/security/code-isolation.test.ts |
| KF-SYS-004 | AC-EVAL-001 | Planned | packages/application/oracle-verifier | tests/acceptance/oracle-verification.test.ts |
| KF-SYS-005 | AC-EVAL-002 | Partial | Evidence-bound deterministic gate exists; independent compiler/test EvalRunner is not implemented | tests/acceptance/publication-flow.test.ts |
| KF-SYS-006 | AC-OBS-001 | Implemented | packages/adapters/sqlite-cas/src/index.ts | tests/integration/sqlite-cas.test.ts |
| KF-SYS-007 | AC-FLOW-002 | Planned | packages/application/revision | tests/acceptance/incremental-revision.test.ts |
| KF-SYS-008 | AC-FLOW-003 | Partial | packages/domain/src/index.ts | tests/unit/domain.test.ts |
| KF-SYS-009 | AC-PUB-001 | Implemented | packages/application/src/index.ts + sqlite-cas adapter | tests/acceptance/publication-flow.test.ts |
| KF-SYS-010 | AC-REC-001 | Partial | packages/application/src/index.ts + checkpoints table | tests/integration/sqlite-cas.test.ts |
| KF-SYS-011 | AC-SCHEMA-001 | Partial | specs/schemas + packages/contracts | specs/13-verification/validate-specs.ts |
| KF-SYS-012 | AC-LANG-001 | Implemented | packages/contracts/src/index.ts LanguagePlugin port | tests/contract/architecture.test.ts |
| KF-SYS-013 | AC-SEC-002 | Partial | authenticated HTTP mutation boundary | tests/integration/server.test.ts |
| KF-SYS-014 | AC-LANG-002 | Planned | plugins/languages/cpp | tests/integration/cpp-sandbox.test.ts |
| KF-SYS-015 | AC-AGENT-002 | Partial | deterministic decideGate | tests/unit/domain.test.ts |
| NFR-001 | AC-SEC-002 | Partial | apps/runner/src/server.ts | tests/integration/server.test.ts |
| NFR-002 | AC-REC-001 | Partial | checkpoints + publication transaction | tests/integration/sqlite-cas.test.ts |
| NFR-003 | AC-REC-002 | Implemented | GenerationKey and publication key | tests/integration/sqlite-cas.test.ts + tests/acceptance/publication-flow.test.ts |
| NFR-004 | AC-OBS-001 | Partial | SQLite events | tests/acceptance/publication-flow.test.ts |
| NFR-005 | AC-ARCH-001 | Implemented | packages/domain + packages/contracts | tests/contract/architecture.test.ts |
| NFR-006 | AC-SCHEMA-001 | Partial | specs/schemas + schema migration table | specs/13-verification/validate-specs.ts |
| NFR-007 | AC-LANG-002 | Planned | Sandbox port only; hostile execution fails closed | tests/security/resource-limits.test.ts |
| NFR-008 | AC-EVAL-003 | Partial | deterministic gate + immutable evidence | tests/acceptance/publication-flow.test.ts |
| NFR-009 | AC-SEC-003 | Planned | packages/application/audit-redaction | tests/security/redaction.test.ts |
| NFR-010 | AC-FLOW-004 | Planned | packages/application/scheduler | tests/acceptance/resource-claims.test.ts |

Spike `SPK-001..005` 分别计划落在 `spikes/{dsh-provider,workflow-engine,glm-provider,artifact-store,cpp-sandbox}/`，各自用 `spikes/*/report.md` 与可重复脚本验收；它们不计为本 P0-A Spec 提交的实现。

