---
name: flywheel-livemode
title: flywheel-livemode
category: flywheel
tags: [livemode, harvester]
sources:
  - path: endlessWpKnowledgeRunner/fwrunner/livemode.py
    pinned: true
schema_version: okf.v1
kind: concept
status: verified
verified: true
stale_after: ""
platforms: []
created_at: "2026-08-22T01:37:16+08:00"
updated_at: "2026-08-22T01:37:16+08:00"
version: 1
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

# 知识飞轮

## liveMode

li
## 概述

当 liveMode 开启时，harvester agent 会扫描 sources 目录与 watch_dirs，找出新增或变更的 markdown 文件，提炼为结构化知识并调用 ingest 入库。

## 设计要点

`	ext
scan -> candidates -> harvester 提炼 -> fw_ingest -> 打分 -> 门禁 -> verified/draft
`

- scan 基于内容哈希与 livemode state 判重，已入库内容不再重复处理。
- 每周期候选上限 max_per_cycle，防止一次消费过多。

## 为什么

1. 触发式 ingest 覆盖'有人推知识'的场景，liveMode 覆盖'没人推但来源在变'的场景。
2. 自动化与手动可以共存：harvester 产出与人工投递走同一条打分门禁，无特权通道。

## 验证

python fw.py scan 检查候选输出；python fw.py status 确认 counts。
