# WorkPanel 修改建议复评

| 项 | 内容 |
|---|---|
| 日期 | 2026-08-21 |
| 仓库 | [linlisWorkTeam/workPanel](https://github.com/linlisWorkTeam/workPanel) |
| 基线 | `master@f79fec9`，`origin/master` 同步 |
| 复评对象 | 上一份综合报告的 TOP 10 修改建议 |
| 验证 | Vitest 81 项通过；Rust 131 项通过；`pnpm run build` 通过 |

## 总结

建议已经开始被执行，而且最近四个提交正好对应第 4、7、9、10 项。但执行面最关键的事件溯源、数据库 lease、Application Service、适配器能力注册和统一权限层仍未完成。

结论：**TOP 10 中 2 项基本完成，3 项部分完成，5 项未完成。** 项目质量在上升，但运行时可靠性风险仍未解决。

## 逐项核验

| # | 建议 | 状态 | 证据与判断 |
|---:|---|---|---|
| 1 | Application Service 层 | 未完成 | 未发现统一 application service；`web.rs` 约 2910 行、`commands.rs` 约 1121 行，HTTP/IPC 仍各自编排业务。 |
| 2 | Append-only Run Event Log | 部分完成 | 已有 `run_events` 与 `run_phase_log`，且 `set_run_phase` 统一记录阶段；但没有统一 seq、事件版本、delta/tool/review 的单一事件源，也没有 replay API。 |
| 3 | DB lease + fencing + idempotency | 未完成 | `scheduler.rs` 仍以 `Mutex<HashSet>` 防重复调度，run 表未见 lease owner、expiry、attempt 或 fencing token；双实例安全性未解决。 |
| 4 | 版本化数据库迁移 | 基本完成，但有尾债 | 新增 `db_migrations.rs`，使用 `PRAGMA user_version`、升级测试和幂等迁移；但 `workflow.rs` 仍保留启动期 `ALTER TABLE task_runs`，且 v1 内部仍用忽略错误的逐列 ALTER。 |
| 5 | Adapter Capability Registry | 未完成 | 仍是 `AdapterKind` 中心枚举；适配器、模型目录、前端 union 仍需同步修改，没有 capability descriptor/registry。 |
| 6 | 统一 Policy/Capability + SecretStore | 未完成 | 仍可从 `agent_profiles.api_key` 读取密钥；权限主要散落在 handler/DB 守卫，没有统一 policy engine 或 OS keychain 抽象。 |
| 7 | 前端 feature slices | 部分完成 | 新增 `useGoalBar`、`useComposerDraft`，`App.tsx` 约 1840 行；但仍是跨域状态容器，尚未按 chat/runs/workflow 等 feature 切片。 |
| 8 | 契约驱动 API/WS 类型 | 未完成 | 未发现 OpenAPI/JSON Schema 生成链；前端仍维护 `types.ts`，HTTP/Tauri/WS 契约仍主要手工同步。 |
| 9 | 系统级故障与集成测试 | 部分完成 | 新增 `web::acl_tests`，覆盖用户越权、成员作用域、管理员代发和 slash command；但仍是 handler 直接调用的模块测试，尚无真实 HTTP/WS、CLI 崩溃、重复 claim、代理上游失败测试。 |
| 10 | 统一 trace/观测与 SSOT CI | 部分完成 | 新增 GitHub Actions、`check-ssot.sh`、三处版本一致性和文档/tag 检查；仍没有贯穿 message→run→adapter→A2A 的 trace ID，且部分文档检查仍是 warning。 |

## 新增优点

- 数据库迁移已经从 `db.rs` 拆出独立模块，并增加 legacy upgrade 与二次启动测试。
- Web ACL 测试开始覆盖真实 schema、用户作用域和成员身份冒用。
- CI 已将前端、Rust、扩展纯度和 SSOT 检查纳入 GitHub Actions。
- `goal bar` 和 composer draft 已抽成 hooks，说明前端开始沿 feature 边界拆分。

## 新增风险/尾债

1. `workflow.rs` 的遗留 `ALTER TABLE` 说明迁移职责还没有完全收口。
2. Rust 测试虽增至 131 项，但构建仍有约 15 条 warning。
3. `run_events` 和 `run_phase_log` 是两套事件记录，继续增加功能会放大多个事实源问题。
4. `web.rs` 和 `db.rs` 继续变大，最近改动尚未逆转单体化趋势。

## 下一阶段排序

1. 先完成 Run Event Log 的统一 envelope、seq、replay 和 projection。
2. 立即为 `task_runs` 增加数据库 claim/lease/fencing，补双实例竞态测试。
3. 将 HTTP 与 Tauri 的共同逻辑下沉到 Application Service。
4. 清理 `workflow.rs` 遗留 ALTER，并把所有 schema 变更纳入 migration 编号。
5. 再推进 Adapter Capability Registry 和统一 Policy/SecretStore。

## 证据边界

- 结论基于 `f79fec9` 源码、提交历史、项目文档和本机测试；没有部署双实例生产环境做压力验证。
- “未完成”表示在当前仓库中未发现对应架构机制，不表示未来分支或未公开设计不存在。
