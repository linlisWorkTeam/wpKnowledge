# WorkPanel 2.0.0 架构评审

| 项 | 内容 |
|---|---|
| 日期 | 2026-08-21 |
| 仓库 | [linlisWorkTeam/workPanel](https://github.com/linlisWorkTeam/workPanel) |
| Commit | `c9cceff` |
| 版本 | `2.0.0` |
| 对比 | Claude Code、OpenCode、DeepSeek Harness、Clowder-ai |

## 评审摘要

WorkPanel 的强项是“平台治理”而非“Agent 内核”：它将群聊意图、成员路由、执行队列、审批、Version/Wave 和灰度发布组合成了完整产品。其外部 CLI 进程隔离和本地优先技术栈也符合实际部署约束。

当前首要架构风险来自成长速度超过模块边界：HTTP、IPC、DB、调度和前端状态继续集中在少数大文件中。若继续直接增加功能，双入口规则漂移、恢复不幂等和 schema 演进风险会显著增加。

## 关键源码观察

- `src-tauri/src/web.rs`：约 2700 行，涵盖认证、群、消息、运行、扩展、运维和工作流路由。
- `src-tauri/src/db.rs`：约 2600 行，兼具 schema、迁移、映射、ACL 和多领域 CRUD。
- `src/App.tsx`：约 1900 行，承载大量跨领域 UI 状态。
- `src-tauri/src/scheduler.rs`：约 1350 行，同时负责 claim、上下文组装、进程执行、心跳、委派和终态。
- `src-tauri/src/adapters/mod.rs`：适配器输出契约已有较好测试，但扩展仍依赖中心枚举。

## 验证记录

```text
cargo test --no-default-features --lib  → 123 passed
pnpm test                              → 81 passed
pnpm run build                         → passed
```

Rust 构建仍输出 15 条 warning，包含未使用 import、死代码、私有接口可见性和恒真模式。

## 判断

WorkPanel 适合继续保持模块化单体，不需要仓促微服务化。重构目标应是明确控制面、执行面、持久化和传输层，而不是更换数据库或基础技术栈。

具体建议与长期结论见 [`workpanel-analysis-report.md`](./workpanel-analysis-report.md)。
