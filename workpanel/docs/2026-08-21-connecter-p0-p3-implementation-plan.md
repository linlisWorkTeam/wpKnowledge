# Connecter P0–P3 修改计划

| 项 | 内容 |
|---|---|
| 日期 | 2026-08-21 |
| 研究对象 | `linlisWorkTeam/workpanelConnecter` |
| 源码基线 | `main@e5b51eb9f89f9bcbb19480d58dc2de230d7e7591` |
| 完整执行计划 | `workpanelConnecter/docs/superpowers/plans/2026-08-21-connecter-p0-p3-evolution.md` |

## 目标

将现有站点内中继与 Host peer 注册骨架，分四阶段演进为可靠、可扩展、可审计的多站 Connecter 网络。本站流量继续由本站 Connecter 处理；跨站流量才经中心 Connecter Host。WorkPanel 继续作为群聊正文事实源。

## 阶段摘要

| 阶段 | 核心交付 | 退出条件 |
|---|---|---|
| P0 | migration、Runner lease/ack/fencing、故障恢复、应用服务拆分、稳定 ID | Runner/Connecter 崩溃不再造成永久 stuck 或重复有效终态 |
| P1 | Subject/Endpoint/Capability/Membership/Presence 目录、enrollment、凭证生命周期、策略路由 | 可回答谁在哪个站点、属于哪个群、具备什么能力、为什么被调度 |
| P2 | Federation envelope、Host/Site durable inbox/outbox、出站长轮询、跨站结果回流 | 两 Site + 一 Host 在断网/重启/重复/乱序下完成真实双向闭环 |
| P3 | 设备身份、签名/mTLS、ACL、观测、配额、兼容升级、备份恢复 | 安全和运维门禁通过，可灰度进入生产 |

## 关键顺序

1. 先完成 P0 的任务租约和 migration，避免把永久卡死问题扩散到跨站网络。
2. P1 先固化 `siteId + subjectId + groupRef`，不允许 P2 继续依赖显示名跨站寻址。
3. P2 首版采用 Site 主动出站 HTTP 长轮询，复用现有 NAT 友好模式；协议稳定后再评估 WebSocket/gRPC。
4. P3 的安全设计可提前开发，但 P2 真实故障矩阵未通过前不能宣称生产可用。

## 推荐里程碑

- M1：Runner 取任务后被强杀，lease 到期可重领且只有一个有效终态。
- M2：v1/v2 Runner 并存；同名跨站 Agent 不冲突；凭证可吊销。
- M3：A User → A Connecter → Host → B Connecter → B Runner → 原路结果回 A。
- M4：mTLS/签名、ACL、trace、配额、滚动升级和灾备演练全部通过。

## 证据与边界

- 计划基于 `e5b51eb` 的 `runners.js`、`hostJoin.js`、`hostPeers.js`、`schema.sql`、`db.js`、`handlers.js` 和既有门禁制定。
- 这是实施计划，不代表 P0–P3 已实现或已完成真实多服务器验收。
- 详细文件清单、API 契约、schema 字段、任务顺序、feature flag、回滚方式和 Definition of Done 以源码仓完整执行计划为准。
