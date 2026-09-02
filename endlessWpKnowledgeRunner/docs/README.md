# Knowledge Flywheel 文档中心

本目录存放 `endlessWpKnowledgeRunner` 的非规范性工程指南。产品行为、权限、状态机和验收条件以 [`../specs/`](../specs/README.md) 为规范性事实源；工程文档负责说明如何理解、运行、修改和维护当前实现。

## 按任务查找

| 任务 | 文档 | 适合谁 |
| --- | --- | --- |
| 第一次安装、初始化和打开 Console；或把完整配置 Prompt 交给 Agent | [GETTING_STARTED.md](GETTING_STARTED.md) | 使用者、Agent、评审者 |
| 理解治理上层、domain-knowledge/LangGraph 基础设施和知识生命周期 | [ARCHITECTURE.md](ARCHITECTURE.md) | 开发者、架构师 |
| 搭建开发环境和实现变更 | [DEVELOPMENT.md](DEVELOPMENT.md) | 贡献者、Agent |
| 选择测试层级和提交证据 | [TESTING.md](TESTING.md) | 贡献者、评审者 |
| 确定目录和文件归属 | [REPOSITORY-GUIDE.md](REPOSITORY-GUIDE.md) | 所有贡献者 |
| 摄取、评测、发布、验收和部署 | [OPERATIONS.md](OPERATIONS.md) | 操作员、维护者 |
| 从旧 Runner 迁移 | [MIGRATION.md](MIGRATION.md) | 旧版本使用者 |
| 本地预览或发布项目官网 | [site/README.md](../site/README.md) | 维护者 |

## 按角色阅读

- **使用者**：快速上手 → 用户用例 → 运维手册的 Dashboard/API 部分。
- **贡献者**：根目录贡献指南 → 开发指南 → 测试策略 → 对应 Spec。
- **架构评审者**：Spec 总入口 → 架构说明 → ADR → 追踪矩阵。
- **操作员**：安全策略 → 运维手册 → 数据边界 Spec。

相关入口：

- [仓库首页](../../README.md)
- [贡献指南](../../CONTRIBUTING.md)
- [安全策略](../../SECURITY.md)
- [组件首页](../README.md)
- [Spec 总入口](../specs/README.md)

## 文档维护规则

1. 文档只描述当前可证明行为；路线或假设必须明确标记。
2. 行为变化先更新 Spec，再同步本目录的操作说明。
3. 命令必须从仓库根目录可执行，并注明额外前提。
4. 相对链接必须通过 `component-layout` 契约测试。
5. 不在仓库根目录创建第二个 `docs/`；组件相关文档全部留在本目录。
