# 4+1 架构视图

## 场景视图（+1）

`源码快照 → Doc/Test 两条独立链路 → 知识驱动 Code → Check → 确定性 Eval → Review → iterate/rollback/pass`。关键场景详见 `AC-FLOW-001`、`AC-SEC-001`、`AC-REC-001`。

## 逻辑视图

- **Domain**：Run、Module、Artifact、KnowledgeVersion、EvaluationReport、Correction、GateDecision。
- **Application**：工作流节点、权限策略、发布策略、幂等协调器。
- **Ports**：Agent、Workflow、Artifact、Knowledge、Sandbox、LanguagePlugin。
- **Adapters**：LangGraph/候选 Temporal、DSH/进程 Provider、GLM、SQLite/CAS、C++ 插件。

依赖方向为 `Adapters → Ports ← Application → Domain`；Domain 不导入 SDK 或语言专属类型。

## 进程视图

V1 为本地单控制进程，最多五个隔离 Agent worker；编译和测试在短生命周期沙箱进程树执行。Artifact 先写临时对象并校验摘要，再原子提交；checkpoint 只在节点输入输出已持久化后推进。取消从 Run 向 worker 和沙箱传播。

## 开发视图

计划实现单元：`packages/domain`、`packages/application`、`packages/contracts`、`packages/adapters/*`、`plugins/languages/*`、`apps/runner`、`tests/{contract,integration,acceptance}`。TypeScript 是平台基线；插件可调用外部工具链，但只能返回通用 Schema。

## 物理视图

V1 部署在个人电脑：runner + SQLite checkpoint/run registry + 本地文件 CAS + 受限沙箱。网络默认关闭，仅 Agent Provider 可经显式出口访问内部 GLM。生产扩展可替换远程 Artifact/Knowledge Store，但不改变端口。

## 约束验证

架构测试扫描 `packages/domain` 禁止 `dsh`、`langgraph`、`temporal`、编译器 AST 包依赖；语言插件契约测试使用非 C++ 假插件证明核心无语言假设。

