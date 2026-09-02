# 追踪矩阵

实现状态按当前代码和可执行测试记录。`Implemented` 表示已有对应代码与自动化验证，`Partial` 表示只实现安全子集，`Planned` 表示规范仍保留但不得宣称为当前能力。实现和测试路径默认相对 `endlessWpKnowledgeRunner/`；以 `../knowledge/` 开头的路径指向仓库知识域中的人工审计证据。

| 需求 ID | 验收 | 状态 | 实现 | 测试 |
|---|---|---|---|---|
| KF-SYS-001 | AC-FLOW-001 | Partial | src/application/services/index.ts | tests/acceptance/publication-flow.test.ts |
| KF-SYS-002 | AC-AGENT-001 | Planned | src/application/ports/index.ts | tests/contract/agent-schema.test.ts |
| KF-SYS-003 | AC-SEC-001 | Partial | src/infrastructure/agents/workspace + src/infrastructure/agents/deepseek-harness/isolation-launcher.mjs | tests/security/agent-workspace.test.ts + tests/integration/deepseek-harness-agent.test.ts |
| KF-SYS-004 | AC-EVAL-001 | Planned | src/application/services/oracle-verifier | tests/acceptance/oracle-verification.test.ts |
| KF-SYS-005 | AC-EVAL-002 | Implemented | src/infrastructure/evaluation/project + evidence-bound deterministic gate | tests/acceptance/real-source-flow.test.ts + ../knowledge/3.workpanel/证据/2026-09-01-ohMyWorkPanel真实源码验收.md |
| KF-SYS-006 | AC-OBS-001 | Implemented | src/infrastructure/persistence/sqlite-cas/index.ts | tests/integration/sqlite-cas.test.ts |
| KF-SYS-007 | AC-FLOW-002 | Implemented | src/application/services/project-flow.ts | tests/acceptance/real-source-flow.test.ts |
| KF-SYS-008 | AC-FLOW-003 | Partial | src/domain/index.ts | tests/unit/domain.test.ts |
| KF-SYS-009 | AC-PUB-001 | Implemented | src/application/services/index.ts + sqlite-cas adapter | tests/acceptance/publication-flow.test.ts |
| KF-SYS-010 | AC-REC-001 | Partial | src/application/services/index.ts + checkpoints table | tests/integration/sqlite-cas.test.ts |
| KF-SYS-011 | AC-SCHEMA-001 | Partial | specs/schemas + src/application/ports | specs/13-verification/validate-specs.ts |
| KF-SYS-012 | AC-LANG-001 | Implemented | src/application/ports/index.ts LanguagePlugin port | tests/contract/architecture.test.ts |
| KF-SYS-013 | AC-SEC-002 | Partial | authenticated HTTP mutation boundary | tests/integration/server.test.ts |
| KF-SYS-014 | AC-LANG-002 | Planned | plugins/languages/cpp | tests/integration/cpp-sandbox.test.ts |
| KF-SYS-015 | AC-AGENT-002 | Partial | deterministic decideGate | tests/unit/domain.test.ts |
| KF-SYS-016 | AC-COMPAT-001 | Implemented | endlessWpKnowledgeRunner compatibility facade | tests/integration/legacy-runner-compat.test.ts |
| KF-SYS-017 | AC-E2E-001 | Implemented | src/application/services/project-flow + project EvalRunner | tests/acceptance/real-source-flow.test.ts + ../knowledge/3.workpanel/证据/2026-09-01-ohMyWorkPanel真实源码验收.md |
| KF-SYS-018 | AC-DOC-001 | Implemented | src/application/services/knowledge-writing-guide.ts + quality-policy.ts + project-flow.ts | tests/unit/quality-policy.test.ts + tests/acceptance/real-source-flow.test.ts |
| KF-SYS-019 | AC-ARCH-002 | Implemented | src/infrastructure/workflow/langgraph + src/interfaces/runner/composition.ts | tests/contract/architecture.test.ts + tests/integration/langgraph-infrastructure.test.ts |
| KF-SYS-020 | AC-OBS-002 | Implemented | src/application/services/workflow-control.ts + src/interfaces/runner/console-read-model.ts | tests/integration/langgraph-infrastructure.test.ts + tests/acceptance/automated-langgraph-flow.test.ts |
| KF-SYS-021 | AC-AGENT-003 | Implemented | src/infrastructure/workflow/langgraph/agent-definitions.ts + src/application/services/workflow-control.ts + web/app.js | tests/integration/server.test.ts + tests/contract/site.test.ts |
| KF-SYS-022 | AC-E2E-002 | Implemented | src/application/services/automated-project-workflow.ts + src/infrastructure/workflow/langgraph/graph.ts | tests/acceptance/automated-langgraph-flow.test.ts |
| KF-SYS-023 | AC-DOC-002 | Implemented | web + site + docs + specs + docs/DEVELOPMENT.md completion rule | tests/contract/site.test.ts + tests/contract/component-layout.test.ts |
| KF-SYS-024 | AC-DOC-003 | Implemented | docs/DOCUMENTATION-I18N.md + repository documentation | tests/contract/component-layout.test.ts + tests/contract/site.test.ts |
| KF-SYS-025 | AC-E2E-003 | Implemented | src/infrastructure/agents/deepseek-harness + src/application/services/automated-project-workflow.ts + deploy/deepseek-harness | tests/integration/deepseek-harness-agent.test.ts + ../knowledge/3.workpanel/证据/2026-09-02-DeepSeek-Harness真实Agent治理演示.md |
| KF-SYS-026 | AC-FLOW-005 | Implemented | src/application/services/automated-project-workflow.ts + src/infrastructure/workflow/langgraph/graph.ts | tests/integration/langgraph-infrastructure.test.ts + ../knowledge/3.workpanel/证据/2026-09-02-DeepSeek-Harness真实Agent治理演示.md |
| KF-SYS-027 | AC-OBS-003 | Implemented | src/interfaces/runner/demo-report.ts + src/interfaces/runner/cli.ts | tests/integration/demo-report.test.ts |
| KF-SYS-028 | AC-DOC-004 | Implemented | site/index.html + site/app.js + web/index.html + web/app.js | tests/contract/site.test.ts |
| KF-SYS-029 | AC-SEC-004 | Implemented | .env.example + package.json + web/app.js | tests/contract/site.test.ts + tests/integration/server.test.ts |
| NFR-001 | AC-SEC-002 | Partial | src/interfaces/runner/server.ts | tests/integration/server.test.ts |
| NFR-002 | AC-REC-001 | Partial | checkpoints + publication transaction | tests/integration/sqlite-cas.test.ts |
| NFR-003 | AC-REC-002 | Implemented | GenerationKey and publication key | tests/integration/sqlite-cas.test.ts + tests/acceptance/publication-flow.test.ts |
| NFR-004 | AC-OBS-001 | Partial | SQLite events | tests/acceptance/publication-flow.test.ts |
| NFR-005 | AC-ARCH-001 | Implemented | src/domain + src/application/ports | tests/contract/architecture.test.ts |
| NFR-006 | AC-SCHEMA-001 | Partial | specs/schemas + schema migration table | specs/13-verification/validate-specs.ts |
| NFR-007 | AC-LANG-002 | Planned | Sandbox port only; hostile execution fails closed | tests/security/resource-limits.test.ts |
| NFR-008 | AC-EVAL-003 | Implemented | deterministic gate + immutable process evidence + toolchain fingerprint | tests/acceptance/real-source-flow.test.ts + ../knowledge/3.workpanel/证据/2026-09-01-ohMyWorkPanel真实源码验收.md |
| NFR-009 | AC-SEC-003 | Partial | src/infrastructure/agents/deepseek-harness + src/interfaces/runner/demo-report.ts | tests/integration/deepseek-harness-agent.test.ts + tests/integration/demo-report.test.ts |
| NFR-010 | AC-FLOW-004 | Planned | src/application/services/scheduler | tests/acceptance/resource-claims.test.ts |
| NFR-011 | AC-E2E-001 | Implemented | project acceptance report + CAS evidence | tests/acceptance/real-source-flow.test.ts + ../knowledge/3.workpanel/证据/2026-09-01-ohMyWorkPanel真实源码验收.md |

`SPK-001` 的官方 SDK 接缝、stdin JSON-RPC、超时关闭和 Bubblewrap 角色工作区已有自动化验证；端到端 SDK Run `5503b6bc-0350-4b53-98cc-6fbf3a13aaa9` 已归档，`KF-SYS-025` 的接线验收完成。`SPK-002` 的 LangGraph 选型结果已由 ADR-006 和自动化测试固化；失败 task checkpoint 恢复已有自动化用例，四个崩溃注入点仍是恢复加固项。单次 live Run 不能替代稳定性试验，Agent 源码隔离也不能证明敌对代码执行安全。
