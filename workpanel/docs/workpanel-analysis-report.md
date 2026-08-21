# LinlisWorkPanel 综合架构分析

| 项 | 内容 |
|---|---|
| 对象 | [linlisWorkTeam/workPanel](https://github.com/linlisWorkTeam/workPanel) |
| 基线 | `master@c9cceff`，产品版本 `2.0.0` |
| 日期 | 2026-08-21 |
| 对照 | Claude Code、OpenCode、DeepSeek Harness、Clowder-ai |
| 验证 | Rust 123 项测试通过；前端 81 项测试通过；前端生产构建通过 |
| 日期快照 | [`2026-08-21-workpanel-architecture-review.md`](./2026-08-21-workpanel-architecture-review.md) |

## 一句话结论

LinlisWorkPanel 已经不是普通的多 Agent 聊天壳，而是一个以群聊为治理平面、以外部 Agent CLI 为执行平面、兼顾本地桌面和 Web 服务的协作平台。产品边界和发布治理做得很好，但代码结构仍保留早期单体形态，下一阶段应优先补 Application Service、持久事件日志、数据库 lease 调度和正式迁移体系。

## 做得好的地方

1. **治理平面完整**：群聊、Version/Wave、人类审批、灰度和生产晋升形成闭环。
2. **CLI 进程隔离正确**：Codex、Claude、OpenCode、Cursor、DSH 是可替换执行者，不污染平台内核。
3. **调度不变量清晰**：同 Agent 串行、跨 Agent 并行、取消、重试、心跳和重启恢复已有测试。
4. **扩展边界务实**：manifest、群级开关、健康检查、同源代理、路径净化和 A2A 媒体限制方向正确。
5. **发布纪律突出**：测试门禁、双槽位、drain、生产 DB 隔离和人工批准强于同体量项目。
6. **本地优先栈合适**：Rust、SQLite、Tauri 的部署和资源画像符合当前规模。

## 主要问题

1. `web.rs`、`db.rs`、`App.tsx`、`scheduler.rs` 等核心文件过大，职责边界模糊。
2. Tauri IPC 和 HTTP API 双入口重复业务编排，权限和事件触发容易漂移。
3. SQLite 依赖启动时 `ALTER TABLE`，缺少版本化迁移和升级校验。
4. Scheduler 的正确性仍依赖进程内锁，缺少数据库 lease、fencing 和幂等完成保护。
5. messages、runs、phase log、WS 事件尚未统一成可回放领域事件流。
6. Adapter 仍是中心枚举，新增适配器需要同时修改后端、前端和模型目录。
7. 前端 `App.tsx` 同时承担鉴权、聊天、运行、工作流、扩展和布局状态。
8. Secret、文件系统、安装和运维权限尚未收敛成统一 Capability Policy。
9. 单元测试较强，但 HTTP/WS/代理/故障恢复等系统集成测试不足。
10. version pipeline、epitaph、spec、runbook 等多套状态文档存在漂移风险。

## 对比结论

| 对象 | 最值得借鉴 | WorkPanel 不应照搬 |
|---|---|---|
| Claude Code | hooks、MCP、skills、权限拦截和 subagent 生命周期 | 单会话、单用户产品模型 |
| OpenCode | client/server 分离、provider 抽象、统一模型生态 | 退化为模型选择器或单 Agent IDE |
| DeepSeek Harness | durable session event、capability seam、可逆 effect、ACP | 把庞大的 Cordis 内核直接并入平台 |
| [Clowder-ai](https://github.com/zts212653/clowder-ai) | 身份、A2A、共享记忆、SOP 和平台三层原则 | Node/Redis 多服务复杂度全部照搬 |

WorkPanel 最有价值的差异不是“更会调用模型”，而是把人类决策、Agent 执行和发布治理放进同一闭环。

## TOP 10 修改建议

1. 建立统一 Application Service 层，让 Tauri 和 HTTP 只做传输适配。
2. 引入 append-only Run Event Log，并以投影产生当前 run 状态。
3. 将 Scheduler 改为数据库 lease + fencing + idempotency 驱动。
4. 引入带版本号、事务和升级测试的正式数据库迁移系统。
5. 将 `AdapterKind` 演进为能力描述符和适配器注册表。
6. 建立统一 Policy/Capability 安全层，并引入可插拔 SecretStore。
7. 按 auth/groups/chat/runs/workflow/extensions 拆分前端 feature slices。
8. 用 OpenAPI/JSON Schema 或 Rust DTO 生成前端与 WS 契约类型。
9. 补齐 HTTP+ACL、WS 重放、CLI 故障、SQLite 竞争和扩展代理集成测试。
10. 统一 trace ID、结构化观测，并在 CI 校验版本和文档 SSOT 一致性。

## 推荐演进顺序

```text
Application Service
  → Run Event Log
  → DB Lease Scheduler
  → Versioned Migrations
  → Adapter Capability Registry
```

## 证据边界

- WorkPanel 结论来自 `c9cceff` 源码、项目文档和本机测试。
- DeepSeek Harness 结合本机源码检出及其架构文档。
- Clowder-ai 依据公开 README 和仓库结构。
- Claude Code、OpenCode 的比较以公开产品和架构资料为主，不代表对其闭源内部实现的逐行审计。
