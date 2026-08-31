---
name: flywheel-livemode
title: flywheel-livemode（旧实现，已退出主路径）
category: flywheel
tags: [livemode, harvester, legacy]
sources:
  - path: packages/application/src/index.ts
    pinned: true
schema_version: okf.v1
kind: concept
status: superseded
verified: false
stale_after: ""
platforms: []
created_at: "2026-08-22T01:37:16+08:00"
updated_at: "2026-08-31T00:00:00+08:00"
version: 2
score: 84.8
confidence: 0.9
score_breakdown:
  provenance: 1.0
  structure: 0.829
  freshness: 1.0
  dedup: 1.0
  verifiability: 0.25
  usage: 0.5
---

# 可恢复的知识获取工作流

## 概述

旧 liveMode 使用 DSH 进程内 timer 扫描文件并调用 shell/Python ingest。该实现已退出主路径：新的飞轮通过 WorkflowPort、GenerationKey checkpoint 和版本化 Agent/API Adapter 承担调度，进程内 timer 不再被视为可靠工作流。

## 设计要点

```text
source event -> workflow claim -> Agent adapter -> CANDIDATE
             -> real evaluation -> deterministic gate -> VERIFIED
```

- Artifact 使用 SHA-256 内容寻址，GenerationKey 负责节点幂等。
- 调度、Agent、知识存储和发布分别通过端口隔离。
- 文档质量门禁只能接受候选，不能直接发布 VERIFIED。

## 为什么

1. DSH timer 随宿主进程消失，无法提供完整 checkpoint、取消和故障恢复语义。
2. shell/Python 桥接扩大权限边界，也无法把结构化契约稳定地绑定到版本。
3. 新方案仍允许手动和自动获取共存，但所有产物都必须走相同的候选、执行证据和发布门禁。

## 适用场景

用于新增来源扫描器、Agent harvester 或定时调度 Adapter。调度器可以替换，但不得绕过候选状态、Artifact 完整性、GenerationKey 和 Publication Gate。

## 验证

运行 `npm test`，检查 checkpoint 幂等、候选不自发布以及 PASS decision 的原子发布。
