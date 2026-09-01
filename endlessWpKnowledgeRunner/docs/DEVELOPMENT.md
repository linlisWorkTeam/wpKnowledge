# 开发指南

## 开发基线

从仓库根目录开始：

```bash
npm ci
npm run typecheck
npm test
```

要求 Node.js 24+。运行数据默认写入 `.workpanel/`；开发和测试不得把该目录、SQLite 文件或 CAS 工件提交到 Git。

## 依赖方向

```text
CLI / HTTP / DSH / Web projection
                 │
                 ▼
           Application services
                 │
        ┌────────┴────────┐
        ▼                 ▼
      Domain            Ports
                          ▲
              SQLite / CAS / Agent / Evaluator adapters
```

- `packages/domain`：领域实体、状态和纯规则；不能导入 Adapter、数据库或工作流 SDK。
- `packages/application`：用例编排和 Port；不能直接依赖具体 SQLite、HTTP、模型或编译器。
- `packages/adapters`：实现 Registry、CAS、Agent、DSH、项目评测等外部边界。
- `apps/runner/src`：组合根、CLI、HTTP Server 和 Console read model。
- `web`：浏览器界面；不能复制状态机或发布判断。

架构契约由自动化测试保护，详细语义见[架构说明](ARCHITECTURE.md)。

## 修改流程

### 修改产品行为

1. 在 [`../specs/`](../specs/README.md) 定位需求 ID 和用例。
2. 补充或调整可验收行为、异常路径与权限边界。
3. 更新追踪矩阵中的实现和测试映射。
4. 从 Domain/Application 边界实现，再接入 Adapter 和入口。
5. 增加最窄且足够的测试，最后同步上手或运维文档。

### 增加 HTTP 或 CLI 能力

- 优先调用现有 Application Service；入口层只做解析、鉴权和结果映射。
- 版本化 API 使用 `/api/v1`；`/health` 只用于进程探针。
- 写 API 必须在未配置 token 时 fail closed。
- 不在 Console 中用一串原始 transition 请求模拟 Orchestrator。

### 增加 Agent 或 Evaluator

- 输入输出遵循 `specs/schemas/` JSON Schema；大对象通过 ArtifactRef 传递。
- Agent 输出必须先做 schema validation，再进入领域流程。
- 独立评测器不能复用被评代码的自报结果作为通过证据。
- 外部命令避免 shell，限制工具、环境、路径、超时和输出；这些限制仍不能替代 OS 沙箱。

### 修改前台

- 先对齐[前台产品设计](../specs/04-product/frontend-product-design.md)和[用户用例](../specs/05-workflows/user-use-cases.md)。
- Console read model 位于 `apps/runner/src/console-read-model.ts`，写操作必须经过共享应用服务。
- 未实现的自动化能力应呈现真实状态，不制作会绕过权限边界的假按钮。

## 配置与调试

常用环境变量：

| 变量 | 用途 |
| --- | --- |
| `WP_FLYWHEEL_HOME` | 覆盖 SQLite/CAS 运行目录 |
| `WP_KNOWLEDGE_HOST` | 覆盖 HTTP 监听地址 |
| `WP_KNOWLEDGE_PORT` | 覆盖 HTTP 端口 |
| `WP_KNOWLEDGE_WRITE_TOKEN` | 启用受保护写 API |

为每个实验使用独立 `WP_FLYWHEEL_HOME`，可以避免开发数据互相污染。配置默认值见 [`../runner.config.json`](../runner.config.json)。

## 完成定义

一次行为变更只有在以下内容一致时才完成：

- Spec 和追踪矩阵；
- Domain/Application/Adapter 实现；
- 正常、失败、重试或权限边界测试；
- 用户、开发或运维文档；
- PR 中可复现的实际验证结果。

提交规则和评审标准见根目录[贡献指南](../../CONTRIBUTING.md)。
