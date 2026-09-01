# endlessWpKnowledgeRunner

本目录是 Knowledge Flywheel 的组件根目录。运行代码、规范、验收场景、测试、产品控制台和运维文档必须在这里共同演进；仓库根目录只保留 npm/TypeScript 工作区入口和跨项目知识库。

## 目录

```text
endlessWpKnowledgeRunner/
├── acceptance/ohmyworkpanel/ # 固定 commit 验收 fixture
├── apps/runner/src/          # CLI、HTTP Console、composition
├── docs/                     # 架构、运维与迁移
├── packages/                 # domain、contracts、application、adapters
├── specs/                    # 唯一规范事实源
├── tests/                    # unit、contract、integration、acceptance
├── web/                      # Console 前端
├── fw.mjs                    # 旧调用方兼容入口
└── runner.config.json        # 默认本地配置
```

`packages/domain` 和 `packages/application` 继续保持六边形边界；Console 的 Run/Evidence 查询由 `apps/runner/src/console-read-model.ts` 提供只读投影。所有状态变更仍通过共享 Application Service、Registry 和确定性 Gate，不存在第二套发布权威。

```powershell
node endlessWpKnowledgeRunner/fw.mjs init
node endlessWpKnowledgeRunner/fw.mjs ingest --file knowledge/inbox/example.md --name example --source knowledge/inbox/example.md --pinned
node endlessWpKnowledgeRunner/fw.mjs query --q "example"
node endlessWpKnowledgeRunner/fw.mjs status
```

`init`、`ingest`、`query`、`get`、`status`、`scan` 和 `feedback` 映射到组件内的 TypeScript CLI。旧 `verified` 映射到 `VERIFIED`，旧 `draft` 映射到 `CANDIDATE`；`--force-draft` 是冗余参数，因为摄取只能创建候选。

`score`、`eval` 和 `harvest` 会返回迁移指引并失败。它们原先把文档质量当成发布权威，或依赖不可恢复的定时器状态。行为验证必须使用真实源码工作流和独立 EvalRunner。通过 `WP_FLYWHEEL_HOME` 选择 SQLite/CAS 运行目录；已移除的 `--root` 不会被重新解释。

## Specifications

[规范总入口](specs/README.md)、[前台产品设计](specs/04-product/frontend-product-design.md)、用例、参与者边界、Gate、安全和验收契约均位于本目录，不再维护仓库根级平行 Spec。
