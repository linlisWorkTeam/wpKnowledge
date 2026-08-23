---
name: omp-soul
title: omp 下一代 Soul 概念（ohMyAGI 第一类实体）
description: omp 下一代 soul 概念：第一类实体、双层级、壳壳分离、评测门禁（v2 经交叉评审修订）
category: architecture
tags: [omp, soul, ohmyagi, persona, clowder]
sources:
  - path: knowledge/3.workpanel/作者随笔/下一代OMP，或者说ohMyAGI/08-概念：soul在ohMyAGI中的位置.md
    pinned: true
schema_version: okf.v1
kind: concept
status: verified
verified: true
stale_after: ""
platforms: []
created_at: "2026-08-23T02:53:56+08:00"
updated_at: "2026-08-23T03:00:30+08:00"
version: 2
score: 93.0
confidence: 0.9
score_breakdown:
  provenance: 1.0
  structure: 0.971
  freshness: 1.0
  dedup: 1.0
  verifiability: 1.0
  usage: 0.5
---

## 概述

omp-soul 是 ohMyWorkPanel 下一代（ohMyAGI）的第一类实体：可携带、可加载、可演化、可卸载的稳定人格包。它绑定的不是进程而是身份（Connecter 的 Subject/GroupRef），活在群聊治理平面之内、任务状态机之外。市面正处人格格式竞争定义期（soulspec 当前最完整候补、仍是草案），omp 的策略是采用"抽象字段层 + soulspec 默认导出目标"，不发明私有格式。

## 设计要点

- 本体六件套：声明（soul.json）/人格（SOUL.md）/规则（AGENTS.md）/状态（state）/记忆通道（memory lanes）/活性（rhythm heartbeat）。
- 加载层级：Group 级 soul（团队气质）× Agent 级 soul（成员个性）两层绑定；注入优先级：平台安全策略 > 群气质 > 成员个性 > 默认；不碰任务状态机（壳不是电梯）。
- 身份与记忆分离：T0 身份不可变（人授权才改），记忆走 T1 常青/T2 工作记忆分层、衰减与晋升管道，防"记忆-身份悖论"。
- 一键卸载 = 解绑 + 停注入 + 资产保留/导出带走（clowder 教训：关系资产不可回收）。
- 制造：预制商店+建群推荐（P0）→ 对话归纳蒸馏（P1，人在环确认）→ SoulFactory 流水线预制群组（P2，采集/提炼/评审/发布四角色+五道门禁）。
- 与 clowder 的 cat-template.json v2 定义双向 import/export 协议：soul=breed 与 body=variant 分离、mentionPatterns 别名召唤、reviewPolicy 跨家族互审、restrictions 硬边界全部可映射。

## 为什么这样设计

1. 人格化能留人是 clowder 作者的主张（无公开留存数据），是**待验证的头号假设**——但人格产品的信任建立在一致性上，soul 必须有评测门禁（跨模型保真、对话内一致性、价值反馈）才能上架。
2. soul 定位为留存杠杆而非拉新杠杆：优先级排在 Connecter 生产化与 A2A/MCP 服务器面之后，但成本低、与任务逻辑基本隔离（P0 审计用本地事件表先行），可并行发布。
3. 兼容竞争中的格式而不是自造标准，避免生态内卷；soul 跟身份走不跟进程走，跨站 soul 由此成立（记忆同步为待设计新组件，不进入 Connecter 核心）。

## 适用场景

工程角色类（评审鹰/架构军师/文档工匠/测试鹰眼/安全卫士/PM 管家）对项目开发收益最高，适合写代码/复盘/调研/发布等群用途；建群时按"群用途 → 推荐组合"预制与推荐（全量货架 12 款、P0 首发子集 8 款，可全退回到默认）；MBTI 皮肤与导师类承载情绪价值（MBTI® 为注册商标，命名建议自创"军师队/创意队"）；SoulFactory 与对话蒸馏两条生产线用于规模化制造。

## 验证

- 一手取证：soulspec（commit 569cbd1）、OpenPersona（03b924f）、clowder-ai cat-template.json v2（f2b9c118）均 clone 通读；cat-template 的 breed/variant 分离、mentionPatterns、reviewPolicy、restrictions 为实际字段。
- 详细论证：knowledge/3.workpanel/作者随笔/下一代OMP，或者说ohMyAGI/08-概念：soul在ohMyAGI中的位置.md（概念）、09-设计（SKU）、10-兼容（clowder 映射）、12-评测（评测体系）。
- 待验证假设：① soul 提升留存（建议参照 knowledge/3.workpanel/调研/clowder-ai调研/05-joint-thinking.md 的"MBTI 群组人格实验群"思路做 omp 对照实验）；② CLI × 注入方式矩阵（P0 前勘定）；③ soulspec 兼容性命令级验收（clawsouls validate 通过）。已做独立交叉评审并修订（2026-08-23）。
