# 2026-08-21 复评笔记

## WorkPanel 最新基线

- `f79fec9 refactor(ui): #7 第一步——goal bar 与 composer 草稿抽成独立 hooks`
- `d9ba142`：GitHub Actions 门禁 + 版本/文档 SSOT 校验（#10）
- `eeedac6`：HTTP+ACL 集成测试起步（#9）
- `aea9f0a`：正式版本化数据库迁移（#4）

## 实测命令

```text
pnpm test                         → 23 files / 81 passed
cd src-tauri && cargo test --no-default-features --lib → 131 passed
pnpm run build                    → passed
```

## 关键观察

- `db_migrations.rs` 已有 `PRAGMA user_version` 和升级测试。
- `workflow.rs` 仍有 `ALTER TABLE task_runs ADD COLUMN wave_id/version_id`。
- `scheduler.rs` 仍使用进程内 `scheduling_groups`，没有数据库 lease 字段。
- `web.rs` 的 ACL 测试直接调用 handler，不等于真实 HTTP/WS 集成测试。
- `run_events`、`run_phase_log` 并存，尚未统一为 append-only domain event。
- `App.tsx` 仍约 1840 行；新 hooks 是增量拆分而非 feature slice 完成。
