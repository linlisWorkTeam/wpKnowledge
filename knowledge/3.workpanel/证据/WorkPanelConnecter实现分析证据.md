# WorkPanelConnecter 实现分析证据笔记

日期：2026-08-22

## 基线与命令

- 源码仓库：`D:\AI\workpanelConnecter`
- 源码 commit：`3cf0d68c9242a7fce322363940413345bbbac34f`
- 交接依据：`docs/epitaph/2026-08-22-documentation-audit.md`
- 验证命令：`npm run test:release-local`
- 验证结果：`RELEASE_LOCAL_GATE_OK gates=51`

## 关键证据

- 启动：`bin/connecter-relay.js` 调用 `listenRelay()`；`server.js` bootstrap 打开 SQLite、应用 migrations、同步 pets/runners、恢复 pending delivery 并启动 Host join。
- 认证：`authPet.js` 区分 pet/ops/runner/peer；`server.js` 对 host role 限制只允许 Host/federation/ops path。
- 站内 chat：`handlers.js` 做群成员与 mention/admin 解析，`messaging.js` 通过 messages.id 幂等，`delivery.js` 负责 Runner 优先及 WorkPanel retry。
- Runner：`runners.js` 的 poll 在事务中写 lease token hash、lease_until、attempt；ack/renew/result 检查 owner、token 和过期时间；result 使用 `(taskId,resultId)` 幂等。
- Directory：`identityService.js` 生成稳定 Subject/GroupRef/Trace；`directory.js` 投影 subjects/endpoints/capabilities/memberships/presence；`routeResolver.js` 做资格、TTL、能力和本地优先选择。
- Federation：`hostJoin.js` Site 出站 register/heartbeat/directory/outbox/inbox；`federationHost.js` Host 验证 schema、签名、peer/target、policy、quota、幂等并发放 delivery lease；`federationSite.js` 处理 chat.command/run.event 和结果投影。
- WorkPet：`connecterApi.js` 只访问本站 `/v1/*`；`main.js` 负责登录、群控制台、2 秒 transcript polling 和 run polling；Tauri `main.rs` 读写 `~/.workpet/config.json`。

## 未确认/边界

- 本地门禁使用临时多进程和模拟/本地 WorkPanel，不能证明真实两台 Site 服务器加独立 Host 的网络部署。
- `test:mtls-handshake` 是临时 CA 实验，真实证书轮换、外部 secret store、NAT/firewall 和反向代理仍需环境验收。
- `test:soak-smoke` 只运行 7 秒；生产 72 小时 soak 和外部告警尚未证明。
- 发现文档与实现方法名不一致：`docs/protocol/directory-v2.md` 写 `POST /v2/routes/explain`，但 `src/relay/server.js`、`docs/api-relay.md` 和测试使用 `GET`。
