# endlessWpKnowledgeRunner

`endlessWpKnowledgeRunner` 是 wpKnowledge 当前 Knowledge Flywheel 的完整组件根目录。运行代码、产品控制台、Spec、验收 fixture、测试和运行文档在这里共同演进；仓库根目录只保留工作区入口和跨项目协作文件。

<details lang="en">
<summary>English summary</summary>

This directory is the complete Knowledge Flywheel component. It contains the TypeScript runtime, embedded LangGraph infrastructure, Console, specs, acceptance fixtures and tests. wpKnowledge owns governance and publication; `domain-knowledge` owns workflow execution. The repeatable acceptance path uses deterministic fixtures, while the optional live path uses the official DeepSeek Harness SDK with role-scoped Linux process isolation. Neither a fixture nor a single live run proves general model quality.

</details>

## 它负责什么

- 把 Markdown 或项目经验摄取为带来源的 `CANDIDATE`；
- 用 CAS 保存不可变工件，用 SQLite 保存 Run、Event 和发布状态；
- 编排生成、独立评测、失败归因、Correction 和增量知识修订；
- 用确定性 Gate 给出 `PASS`、`ITERATE`、`ROLLBACK` 或 `STOPPED`；
- 只在证据完整且通过 Gate 时原子发布 `VERIFIED` 知识；
- 通过 CLI、HTTP API、Web Console 和 DSH Adapter 暴露同一个应用核心。

内嵌的 `domain-knowledge` LangGraph runtime 负责 Agent 节点、并行、循环和恢复；wpKnowledge 仍负责 Run、KnowledgeVersion、评测、发布和审计。Console 会展示七类 Agent 角色与每个节点的实时投影，受信操作者只能追加提示词，不能改节点职责、输入输出、拓扑或工具权限。固定 ohMyWorkPanel 场景既有可重复的 deterministic fixture，也能切换到 DeepSeek Harness 官方 SDK。Linux live 模式会为每个角色建立文件白名单工作区并用 Bubblewrap 隔离参考源码；独立评测器仍只用于受信项目。图中的 `code` 是由当前 Provider 执行的代码生成角色，不是另行接入的 CodeAgent CLI。

## 从哪里开始

| 目标 | 文档 |
| --- | --- |
| 首次安装并看到 Console | [快速上手](docs/GETTING_STARTED.md) |
| 查找所有工程文档 | [文档中心](docs/README.md) |
| 理解核心架构 | [架构说明](docs/ARCHITECTURE.md) |
| 查看真实 DeepSeek Harness 闭环 | [三次运行记录](../knowledge/3.workpanel/证据/2026-09-02-DeepSeek-Harness真实Agent治理演示.md)与[方案 PPT](../knowledge/2.wiki/设计/当前wpKnowledge知识飞轮方案.pptx) |
| 修改实现 | [开发指南](docs/DEVELOPMENT.md) |
| 定制某个 Agent 角色 | [Agent 角色定制指南](docs/AGENT-CUSTOMIZATION.md) |
| 运行测试和准备 PR 证据 | [测试策略](docs/TESTING.md) |
| 判断文件归属 | [仓库目录规则](docs/REPOSITORY-GUIDE.md) |
| 操作 CLI、评测、发布与部署 | [运维手册](docs/OPERATIONS.md) |
| 修改产品行为 | [Spec 总入口](specs/README.md) |

## 目录

```text
endlessWpKnowledgeRunner/
├── acceptance/ohmyworkpanel/ # 固定 commit 的真实源码验收 fixture
├── apps/runner/src/          # CLI、HTTP Server、Console read model、composition
├── docs/                     # 上手、架构、开发、测试、运维与迁移
├── infrastructure/           # 相对独立的 domain-knowledge LangGraph runtime
├── packages/                 # domain、contracts、application、adapters
├── specs/                    # 唯一规范性事实源
├── site/                     # GitHub Pages 项目官网
├── tests/                    # unit、contract、integration、acceptance
├── web/                      # Console 静态前端
├── fw.mjs                    # 旧调用方兼容入口
└── runner.config.json        # 默认本地配置
```

`packages/domain` 不依赖数据库、工作流 SDK、模型提供方、编译器或具体语言类型；`packages/application` 只依赖领域和 Port。Adapter、CLI、HTTP 和 Web 都不能拥有第二套状态机、Registry、评分或发布权威。

## 最短运行路径

在仓库根目录执行：

```bash
npm ci
npm run knowledge -- init
npm run knowledge -- status
npm run knowledge:serve
```

打开 <http://127.0.0.1:4174>。详细步骤和预期结果见[快速上手](docs/GETTING_STARTED.md)。

要启动固定 ohMyWorkPanel 自动工作流，并在 Console 查看 LangGraph 节点：

```bash
npm run knowledge -- workflow-run --repository /path/to/ohMyWorkPanel
```

源仓库必须包含验收场景固定的 commit；该命令会等待工作流到达终态。Agent 清单和受限提示词配置可通过 `agents`、`set-agent-prompt` 命令或 Console 的 Agents 页面查看。

项目官网与本地 Console 分开维护。运行 `npm run site:serve` 可以在 <http://127.0.0.1:4175> 预览静态官网；它不会连接 Registry 或暴露治理能力。

兼容门面 `fw.mjs` 支持 `init`、`ingest`、`query`、`get`、`status`、`scan` 和 `feedback`，并委派给同一个 TypeScript CLI、SQLite Registry 与 CAS。旧 `score`、`eval` 和 `harvest` 会返回迁移说明并失败，避免恢复“文档分数即 verified”的旧语义。

## 规范和信任边界

[规范总入口](specs/README.md)、[用户用例](specs/05-workflows/user-use-cases.md)、[前台产品设计](specs/04-product/frontend-product-design.md)、[评测模型](specs/08-evaluation/evaluation-model.md)和[数据边界](specs/09-security/data-boundaries.md)共同定义行为。

固定项目 EvalRunner 只面向受信源码和生成代码。它使用临时 `git archive` 工作区、工具白名单、环境净化、超时和输出限制，但不是敌对代码沙箱；不得用它执行陌生代码，也不得把 deterministic fixture 或单次 live Run 的通过结果表述为普遍模型质量。Agent 源码可见性隔离与生成代码执行隔离是两件事，前者已落地，后者仍需专用 Sandbox Adapter。
