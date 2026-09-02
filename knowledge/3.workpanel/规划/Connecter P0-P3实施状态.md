# Connecter P0–P3 实施状态

| 项目 | 内容 |
|---|---|
| 日期 | 2026-08-22（更新） |
| 研究对象 | `linlisWorkTeam/workpanelConnecter` |
| 来源基线 | `main@e5b51eb9f89f9bcbb19480d58dc2de230d7e7591` |
| 工作分支 | `codex/connecter-p0-p3`（评审时尚未提交） |
| 完整计划 | 来源仓库中的 `docs/superpowers/plans/2026-08-21-connecter-p0-p3-evolution.md` |

## 已实现

- P0：12 个带校验和的版本化迁移，包含变更前备份和事务回滚；Runner 支持 claim、ack、renew、fencing、结果幂等、ack 前崩溃与运行中崩溃回收、死信，以及带 fencing 保护的人工重新入队和取消；Subject、Group 标识稳定，传输层和应用服务边界已经拆开。
- P1：Directory v2 的 Subject、Endpoint、Capability、Membership、Presence 模型；v1、v2 Runner 可以持久化、隔离共存；支持一次性注册、审批、凭据轮换与吊销，也可在生产模式下只允许设备凭据；路由采用可解释的本地优先策略，同名冲突会明确报错。
- P2：federation v1 信封带有 TTL、hop、correlation、causation 和 trace；Host 与 Site 都有持久化 inbox/outbox；支持投递租约、冲突检测和目录交换；WorkPet 命令可经 Host 到达 B 侧 Runner，持久化的 `run.event` 再返回 A 侧，更新 run projection，并尽力回写来源 WorkPanel。
- P3：消息签名密钥与业务凭据分离，支持 active、next、revoked 轮换和外部密钥来源；支持直接配置 mTLS 客户端材料；Site、Group、Subject、Operation、Direction、Capability、Data-classification ACL 默认拒绝；运行时策略生命周期和 Host 对端凭据轮换、吊销有审计记录；追加式审计会脱敏，并受归档保留策略控制；还包含结构化日志、运维 trace、修正后的健康指标、准确的受影响投递清单、按 Site 配额、磁盘背压、兼容矩阵、备份恢复与运维手册。

## 验证证据

一次 fail-fast 本地运行通过了 49 个发布 Gate，覆盖设备身份、TLS 配置、临时 CA 签发后的真实双向 TLS 握手与无证书拒绝、策略矩阵/API、配额、trace 和短时 soak。另有两个三进程 federation soak，时长分别为 600,000 ms 和 480,000 ms，结果均为 `FEDERATION_SOAK_OK`，耗时 602.4 秒与 482.6 秒。E2E 在同一台机器上启动相互独立的 A Site、Host、B Site 进程与数据库，通过原始 correlation ID 验证结果投影，并将结果回写来源 WorkPanel。Host 角色现在会直接拒绝 WorkPet、WorkPanel 和 Runner 的执行 API，而不是仅仅不配置这些 API。

恢复专项覆盖 Site A、Site B、Host、Runner 和 WorkPanel 的独立重启或中断，以及 Host ack 响应丢失、Runner 不可用时目标 inbox 重试、TTL 过期和迟到的冲突终态。Host 停机时，Site A 仍能访问本地 WorkPanel，Site B 的本地 Runner 任务也能完成。目标 Site 在确认 Host 后仍保留消息正文，因此无需 Host 重发正文即可继续本地投递；终态回调乱序时采用 first-terminal-wins。

灾难恢复 Gate 还模拟了 Host 接收消息后、目标投递前临时 SQLite 数据库被删除的情况。来源 Site 会定期对账未终结的 outbox 项，Host 重启后可重建队列并完成结果往返，且没有重复执行。

## 结论

代码已经实现预期拓扑：WorkPet 只与所属 Site Connecter 通信；本地流量留在本地；跨 Site 的命令和结果经过唯一、持久化的 Connecter Host；Runner 仍在目标 Site 执行。关键契约与服务边界可以替换，没有把 Agent 调用写成服务器之间的硬编码直连。

## 建议

进入生产环境前，还需要完成 72 小时 soak，在至少两个真实 Site 服务器和一个独立 Host 上部署 HTTPS/mTLS 与生产密钥库支持的签名密钥；指标应接入告警和值班体系，并使用接近生产的备份演练 Host 数据丢失和凭据泄露。

## 证据边界

这不是一次真实多服务器或生产 TLS 验证。历史的 `127.0.0.1:8081` fixture 当时离线，但当前 `127.0.0.1:8082` 上的 WorkPanel canary 已经通过健康检查、成员关系、无 `@` 的管理员路由和显式 `@Agent` 分发，结果为 `E2_AT_MENTION_OK`，Gate 输入可配置。72 小时 soak 和真实多服务器验收尚未执行。因此，当前实现只能称为经过本地验证的发布候选，不能称为已经生产就绪。

<details lang="en">
<summary>English summary</summary>

The reviewed Connecter candidate implements the planned P0–P3 local, federated, recovery, security, and operations capabilities. Local release gates and two multi-process federation soaks passed. Real multi-server deployment, production TLS, and the 72-hour soak remain unverified, so this evidence supports a locally verified release candidate—not a production-ready claim.

</details>
