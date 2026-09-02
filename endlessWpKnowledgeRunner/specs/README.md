# Knowledge Flywheel 规范集

**状态：Accepted（P0-A）+ P0-B 实现中｜版本：1.3.0｜基线日期：2026-09-01**

本目录是 `endlessWpKnowledgeRunner` 的唯一规范性事实源。`KF-SYS-*` 使用独立命名空间，避免与历史 `mvp-flywheel/docs/` 中的 `SYS-*` 需求发生冲突。本文档定义需求、产品、架构、领域、工作流、Agent 契约、评测、安全与验收；实现进度由追踪矩阵明确标记。关键词“必须 / 不得 / 应当 / 可以”分别表示强制、禁止、推荐和可选。

## 阅读顺序与目录

1. [术语表](glossary.md)
2. [系统需求](01-requirements/system-requirements.md)与[非功能需求](01-requirements/non-functional-requirements.md)
3. [系统上下文](02-architecture/system-context.md)与[4+1 视图](02-architecture/4plus1-views.md)
4. [领域模型](03-domain/domain-model.md)
5. [前台产品设计](04-product/frontend-product-design.md)
6. [知识飞轮工作流](05-workflows/knowledge-flywheel-workflow.md)、[用户用例与交互时序](05-workflows/user-use-cases.md)、[断点恢复](05-workflows/checkpoint-and-recovery.md)与[真实源码验收](05-workflows/real-source-acceptance.md)
7. [Agent 规范](06-agents/README.md)、[知识写作风格](06-agents/knowledge-writing-style.md)、[语言插件](07-language-plugins/language-plugin-contract.md)、[评测与发布门禁](08-evaluation/evaluation-model.md)
8. [数据边界](09-security/data-boundaries.md)、[验收计划](13-verification/acceptance-plan.md)和[追踪矩阵](13-verification/traceability-matrix.md)
9. [ADR](adr/README.md)与可机器校验的 [JSON Schema](schemas/README.md)

## 规范规则

- 需求 ID 永不复用；废弃需求保留 ID 并标为 `Retired`。
- 所有 P0 需求必须映射至少一个 `AC-*` 验收场景、一个计划实现单元和一个测试。
- Agent 交接只使用 `schemas/` 中的 JSON Schema；Markdown、源码等大对象通过不可变 Artifact 引用传递。
- 领域核心只认识 `LanguageId`、Artifact 与端口，不包含 C/C++ AST、编译器选项或 DSH SDK 类型。
- `Accepted` 文档不得含阻塞性占位标记；待实验项必须有明确默认行为，并记录为 P0-B Spike 假设。
- Spec、实现、验收 fixture、测试与运维文档必须位于同一组件根目录；仓库根目录只保留工作区入口和跨域知识库。

## 阶段门

P0-A Spec 已进入实现验证。当前 P0-B 已落地纯领域边界、Artifact CAS、SQLite Registry、幂等业务副作用、确定性 Gate、原子发布、旧 OKF 迁移、产品控制台和无 shell 的 DSH API 适配器。LangGraph 已按 ADR-006 以内嵌 `domain-knowledge` infrastructure 接入：它执行 Agent 节点、并行、循环与 checkpoint，wpKnowledge 继续持有 Run、KnowledgeVersion、评测、发布和审计事实。固定 ohMyWorkPanel 自动场景已经覆盖失败、纠错、fresh 再生成、独立执行评测、节点投影和发布闭环；当前 Provider 仍是 deterministic fixture。内部 GLM、敌对 C++ 沙箱和完整崩溃注入仍待完成，受信真实项目验收不得被外推为 live 模型质量或敌对代码隔离证明。
