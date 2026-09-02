# 仓库目录规则

目录结构用于表达所有权和依赖边界，不只是文件收纳方式。

## 顶层结构

```text
wpKnowledge/
├── endlessWpKnowledgeRunner/ # 当前可运行产品组件
├── knowledge/                # 跨项目研究与 Git 来源知识
├── mvp-flywheel/             # 历史 Python MVP
├── .github/                  # CI 和协作模板
├── README.md                 # 使用者入口
├── CONTRIBUTING.md           # 贡献规则
└── SECURITY.md               # 安全报告入口
```

### `endlessWpKnowledgeRunner/`

当前 TypeScript Flywheel 的唯一组件根。以下内容必须共同留在这里：

- `apps/`：可执行入口和 composition root；
- `packages/`：领域、应用、契约和 Adapter；
- `infrastructure/`：可独立演进的工作流基础设施；当前只包含内嵌的 `domain-knowledge` LangGraph runtime；
- `web/`：产品控制台；
- `site/`：GitHub Pages 项目官网和本地静态预览工具；
- `specs/`：规范性事实源、ADR 和 Schema；
- `tests/`：unit、contract、integration 和 acceptance；
- `acceptance/`：固定项目场景和 fixture；
- `docs/`：上手、架构、开发、测试、迁移与运维指南。

### `knowledge/`

Git 可评审的研究来源，不是运行时数据库。新增材料先选择稳定来源域，目录编号表示来源身份而非优先级。详细分类和插入规则见[`knowledge/知识库目录.md`](../../knowledge/知识库目录.md)。

ohMyWorkPanel 相关研究、PR 评审和证据统一放在 `knowledge/3.workpanel/`；不得恢复根目录 `workpanel/`。

### `mvp-flywheel/`

历史 Python MVP，只用于设计演进和迁移对照。新的生产行为不在这里实现；确需修改时，PR 必须解释为何属于历史兼容而不是当前组件。

### 根目录和 `.github/`

根目录只接收工作区配置和跨组件协作入口，例如 `package.json`、`tsconfig.json`、首页、贡献与安全策略。CI、PR 模板等 GitHub 协作配置放在 `.github/`。

## 新文件决策表

| 如果新增的是…… | 放到…… |
| --- | --- |
| 领域实体、Gate 或状态规则 | `endlessWpKnowledgeRunner/packages/domain/` |
| 用例编排或 Port | `endlessWpKnowledgeRunner/packages/application/` 或 `packages/contracts/` |
| SQLite、CAS、DSH、Agent、Evaluator 实现 | `endlessWpKnowledgeRunner/packages/adapters/` |
| LangGraph 图、运行时、AgentRunner 与 graph checkpoint | `endlessWpKnowledgeRunner/infrastructure/domain-knowledge/` |
| CLI、HTTP、Console read model | `endlessWpKnowledgeRunner/apps/runner/src/` |
| 浏览器资产 | `endlessWpKnowledgeRunner/web/` |
| 项目介绍、公开快速入门和 GitHub Pages 资产 | `endlessWpKnowledgeRunner/site/` |
| 需求、用例、工作流、ADR、Schema | `endlessWpKnowledgeRunner/specs/` |
| 自动化验证 | `endlessWpKnowledgeRunner/tests/` 对应层级 |
| 使用或维护当前组件的说明 | `endlessWpKnowledgeRunner/docs/` |
| 外部项目调研、证据或知识卡片 | `knowledge/` 对应来源域 |

禁止创建含义不明确的 `misc/`、`common/`、`helpers/` 或 `temp/` 收容目录。共享代码应按它负责的领域或 Port 命名。

## 一致性规则

1. Spec 定义预期行为，实现和测试提供证据；发现不一致时显式修复并更新追踪矩阵。
2. 用户入口不复制完整参考手册。根 README 负责导航，细节进入组件文档或 Spec。
3. 移动文件必须同时更新 import、npm script、tsconfig、Spec、测试和 Markdown 相对链接。
4. 运行数据、外部检出、生成产物和临时报告不进入受版本控制的产品目录。
5. `component-layout` 契约测试负责阻止已收敛目录再次散落到根级。
6. 文档解释性文字以中文为主；关键入口使用相邻 English summary，不建立无人校验的全文镜像。具体格式见[文档语言与 I18n 约定](DOCUMENTATION-I18N.md)。

## 命名

- 稳定规范 ID 使用既有 `KF-SYS-*`、`UC-*`、`AC-*` 命名空间，不复用已废弃 ID。
- 工程入口文档使用稳定主题名，不把容易过期的日期放进文件名。
- 调研证据可保留日期或固定 commit，以便说明取证时间和边界。
- 相对链接优先，外部源码证据优先使用固定 commit URL。
