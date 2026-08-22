---
name: okf-knowledge-format
title: okf-knowledge-format
category: knowledge-format
tags: [okf, knowledge]
sources:
  - path: knowledge/wiki/research/knowledge-format/knowledge-catalog-okf.md
    pinned: true
schema_version: okf.v1
kind: concept
status: verified
verified: true
stale_after: ""
platforms: []
created_at: "2026-08-22T01:37:10+08:00"
updated_at: "2026-08-22T01:37:10+08:00"
version: 1
score: 87.9
confidence: 0.9
score_breakdown:
  provenance: 1.0
  structure: 0.829
  freshness: 1.0
  dedup: 1.0
  verifiability: 0.75
  usage: 0.5
---

# OKF 知识格式

## 概述

OKF（Open Knowledge Format）是 Google knowledge-catalog 提出的知识表示格式：Markdown + YAML frontmatter。

## 设计要点

- Bundle：目录树/git 仓库为单位的自包含知识集合；Concept = 一个 .md 文件。
- frontmatter：sources 溯源、status 状态、verified 信任层级、stale_after 新鲜度。
- 口号：能 cat 就能读 OKF，能 git clone 就能分发 OKF。

## 为什么

1. 知识天生可信、可 diff、可评审 —— 信任由消费方从信号推断。
2. 替代 RAG 的轻量沉淀：知识库就是文件树，无向量化依赖。

## 适用场景

团队知识库、代码文档反推、agent 技能库；不适合海量语义相似检索（那用向量检索补位）。

## 验证

官方仓库 https://github.com/GoogleCloudPlatform/knowledge-catalog 的 SPEC.md 与 samples/bundles
