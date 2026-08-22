# WorkPanelConnecter 文档与代码一致性审查

日期：2026-08-22  
研究对象：`linlisWorkTeam/workpanelConnecter` v0.2.3，commit `8b176cb`
源码证据：`src/relay/server.js`、handlers、协议模块、`config/relay.schema.json`、根/WorkPet package 与构建脚本。

## 结论

仓库原有文档存在明显时间层叠：2026-08-04 的纯 CLI/协调 Agent 设计、E1/E2/E3 计划、后续 Directory/federation 实现和 v0.2.2 Windows 交付混在同一层级，导致旧文档可能被误认为当前规范。此次逐一审查全部 Markdown 后，当前架构已统一为“每站一台 Connecter、全网唯一 Connecter Host；WorkPet、WorkPanel、User 与 Runner 连接本站；跨站消息经过 Host”。

当前规范按代码重写或修正；历史计划、canary、release 与交接材料保留事实但加状态边界；第三方 Live2D license/notice 不改正文。新建权威索引与逐文件审查表，并增加 `npm run test:docs`，检查内部链接、npm 命令、实现路由覆盖、版本一致性、门禁数和每份 Markdown 是否进入审查表。

## 主要修正

- `docs/architecture.md`、`scheduling-boundaries.md`：从早期 CLI 架构切换到 Site/Host/Runner 控制面与数据面。
- `api-relay.md`、`protocol/*`：补全 Runner lease/fencing、Directory v2 enrollment/credential、federation 与 ops 接口。
- `relay-config.md`、`workpet-config-sample.md`：覆盖 schema 与 UI 实际读取的全部关键字段，明确匿名登录换取会话 token 和本地 Connecter 优先策略。
- `ROADMAP.md`、`NEXT-DEV-PATH.md`、`CONNECTER-EVOLUTION.md`：P0–P3 改为已完成；下一阶段优先真实部署验收、adapter 和按规模触发的 HA。
- Windows 交付文档改为发布流程已生成 NSIS 安装 EXE、Connecter SEA 便携包和 SHA-256，不再把桌面打包留给用户。

## 建议

1. 将 `test:docs` 永久保留在 release gate；API、配置或版本变更必须同步权威文档。
2. 设计/计划完成后立即标记为“已实现记录”或“历史快照”，不得继续充当 backlog。
3. 环境地址、在线状态、凭证和群 ID 只能进入 dated evidence，不应进入当前规范。
4. “代码已实现”“本地门禁通过”“Windows 产物可启动”“桌面可见”“生产部署通过”必须继续分开陈述。

## 证据边界

本审查证明文档与当前仓库代码/schema/命令的结构和语义已对齐，并由自动门禁防止一部分回归。它不证明真实外部 Site/Host、WorkPanel 实例、生产证书、外部告警或 72 小时运行状态。透明无边框 WorkPet 的最终可见渲染仍需目标桌面人工确认。
