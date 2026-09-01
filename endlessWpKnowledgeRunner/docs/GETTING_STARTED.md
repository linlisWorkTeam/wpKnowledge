# 快速上手

本指南带你从空环境完成依赖验证、初始化本地运行时、导入候选知识并打开只读 Console。它不会伪造评测证据或自动发布 `VERIFIED` 知识。

## 1. 准备环境

需要：

- Git；
- Node.js 24 或更高版本；
- npm。

确认版本并安装锁定依赖：

```bash
node --version
npm --version
npm ci
```

Node.js 24 是硬性要求，因为 SQLite Adapter 使用内置 `node:sqlite`。

## 2. 验证检出内容

```bash
npm run typecheck
npm run validate:specs
npm test
```

三个命令都应退出 0。Node 可能打印 `node:sqlite` 的 ExperimentalWarning；警告本身不代表测试失败。

## 3. 初始化本地 Registry 和 CAS

```bash
npm run knowledge -- init
npm run knowledge -- status
```

默认运行目录是仓库根目录的 `.workpanel/`，已被 Git 忽略。若需要隔离多个实验，可以显式指定：

```bash
WP_FLYWHEEL_HOME=/tmp/wpknowledge-demo npm run knowledge -- init
```

同一次实验的后续命令必须使用相同的 `WP_FLYWHEEL_HOME`。

## 4. 导入或添加候选知识

导入仓库中的旧 OKF 卡片：

```bash
npm run knowledge -- migrate-legacy --root knowledge
npm run knowledge -- list --status CANDIDATE
```

导入只创建 `CANDIDATE`。旧卡片即使标记为 `verified`，也必须重新经过行为评测和 Publication Gate。

摄取单个 Markdown 文件时使用：

```bash
npm run knowledge -- ingest \
  --module example-module \
  --file path/to/example.md \
  --source path/to/example.md \
  --source-commit <commit> \
  --pinned \
  --title "Example knowledge" \
  --description "Why this knowledge is reusable"
```

## 5. 查询知识

```bash
npm run knowledge -- query --q "workpanel"
```

默认查询只返回已通过行为门禁并发布的 `VERIFIED` 版本。全新运行目录没有结果是预期行为，不应通过降低 Gate 或手工改库来“修复”。候选检查可以使用 `list --status CANDIDATE`。

## 6. 打开 Console

```bash
npm run knowledge:serve
```

浏览器打开 <http://127.0.0.1:4174>。Console 提供 Overview、Runs、Knowledge、Governance、Evidence 和 Settings 视图，默认只读。

若仅在受信本机测试 feedback 写入：

```bash
WP_KNOWLEDGE_WRITE_TOKEN='<local-secret>' npm run knowledge:serve
```

不要把 token 提交到仓库，也不要在公网明文 HTTP 上启用写操作。公网只读部署和 TLS 要求见[运维手册](OPERATIONS.md#dashboard-and-api)。

## 7. 下一步

- 想理解用户完整使用路径：阅读[用户用例与交互时序](../specs/05-workflows/user-use-cases.md)。
- 想完成真实评测与发布：阅读[行为评测与发布](OPERATIONS.md#behavioral-evaluation-and-publication)。
- 想修改实现：阅读[开发指南](DEVELOPMENT.md)。
- 想理解为什么 Agent 不能自行发布：阅读[评测模型](../specs/08-evaluation/evaluation-model.md)和[发布门禁](../specs/08-evaluation/knowledge-publication-gate.md)。
