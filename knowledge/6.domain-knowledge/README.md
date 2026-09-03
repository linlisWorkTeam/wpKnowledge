# 6.domain-knowledge · 可信知识治理系统分析

> 对象：[linlisWorkTeam/domain-knowledge](https://github.com/linlisWorkTeam/domain-knowledge)  
> 建档日期：2026-09-03  
> 适用阶段：DEV-006 开始实施，最终七页 UI/UX 已冻结

本目录保存 domain-knowledge 的产品能力、治理效果、性能预期、企业化差距和演进判断。运行代码、Spec、SQLite、CAS、Checkpoint 和完整日志仍只在 domain-knowledge 或其运行环境维护；这里保存适合人阅读和评审的分析，不构成运行时事实源。

## 调研

- [知识生成速度、治理效果与企业级差距评估](调研/知识生成速度、治理效果与企业级差距评估.md)：分析当前工作流的时间尺度、治理强弱项、合理目标指标，以及与完整企业知识治理平台之间的差距。

## 证据边界

- “已具备”只指 domain-knowledge 当前代码或 Accepted Spec 中可以定位的机制。
- 时间、成功率、误报率和人工介入比例均为规划估计，必须由真实 Pi Agent 批次的 P50/P95 数据校准。
- 企业能力对比用于确定产品边界，不表示本项目需要立即演化成通用企业 Wiki 或数据治理套件。
