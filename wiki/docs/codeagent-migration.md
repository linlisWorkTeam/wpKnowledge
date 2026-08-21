# 知识飞轮 CodeAgent 迁移方案

> 来源：codeagent（公司内部）基于案例团队复现文档生成的完整迁移设计（2026-08-21 用户提供），忠实记录原文，仅做脱敏处理。
> 定位：**架构落地主文档**。目标运行平台 = CodeAgent 主会话 + Agent tool 子角色。本文档描述"如何把案例飞轮架构迁移到 CodeAgent 平台"；与项目自身设计（4 角色）的适配见文末「与项目设计的适配」。

---

## 1. 迁移目标与范围

### 1.1 为什么要迁移

当前飞轮通过 Python 编排脚本调用外部 CLI 工具启动独立角色会话。这种架构存在三个结构性限制：

- 外部进程依赖：角色执行依赖特定 CLI 的安装、认证和版本兼容，部署成本高
- 编排逻辑分裂：Python 脚本承担编排+校验双重职责，逻辑分散在脚本文件和 Skill 文档中
- 权限控制粗糙：CLI 的绕过沙箱选项是全有或全无，无法按角色精细化限制

迁移到 CodeAgent 后，编排逻辑提升到 Skill 文档的自然语言指令层，角色执行切换到 Agent tool 的进程内子 agent，权限控制从"prompt 约束"升级到"工具级硬禁用"。

### 1.2 迁移范围

| 类别 | 迁移策略 |
|------|---------|
| 角色契约（agents/ 目录五个 .md 文件） | 不变，直接复用 |
| 准备/循环/校验脚本 | 不变，编排层通过 Bash 调用 |
| 角色执行方式 | 替换：外部 CLI 进程 → Agent tool 子 agent |
| 编排逻辑（run_role.py） | 拆分：编排职责归 Skill 文档，验证职责归独立脚本 |
| 角色定义（openai.yaml） | 删除：Agent tool 的 prompt 参数替代 |
| 轨迹追踪 | 重建：角色自记录 + 编排层聚合 |

### 1.3 不变量

迁移必须保证以下机制行为等价：

- 角色上下文完全隔离（fresh context）
- 写保护：受保护路径不可被越权修改
- STATE 责任制：各角色只维护自己的小节
- 知识检索审计：固定 commit、记录 doc-id、写入 JSONL
- 增量知识校验：文件集合边界、resource 不可变、版本差分
- 循环决策：continue / stop / infrastructure-blocked 三种语义
- 评测体系：canonical 报告选择、性能目标判定
- 循环输入继承：最近 verifier 轨迹优先，无则回退 Base

## 2. 架构总览

### 2.1 编排模型

迁移后的飞轮采用 Skill 主编排 + Agent tool 角色执行 的两层架构：

- 编排层：CodeAgent 主会话按 Skill 文档的步骤指令顺序执行，在角色执行前后插入验证脚本调用
- 执行层：每个角色通过 Agent tool 启动独立子 agent，子 agent 拥有隔离的上下文和受限的工具集

编排层不参与角色内部的推理和决策，只负责：调用准备脚本 → 启动角色 → 调用验证脚本 → 注入违规信息 → 决策循环走向。

### 2.2 执行流全图

```text
准备阶段
  ├─ Bash: prepare_e2e.py → 创建工作目录、固定官方源码、生成 run_meta.json
  ├─ Bash: 写保护快照（Base 角色）
  └─ Agent tool: Base 角色执行
       ├─ Bash: 审计 wrapper 知识检索（discover → preflight → get）
       ├─ Read/Write/Edit: 设计规格、源码开发
       ├─ Bash: 本地/远程评测
       └─ Write: STATE 基线节
  └─ Bash: 写保护校验 + STATE 验证

飞轮循环（第 N 轮）
  ├─ Bash: prepare_loop.py → 创建 loop-N 目录、解析 readlist、校验知识包
  │
  ├─ Agent tool: Comparator (A)
  │    ├─ Read: 官方源码、Base/前轮实现
  │    ├─ Edit: STATE A 节
  │    └─ 输出: 候选列表 + 映射表
  ├─ Bash: STATE A 节验证
  │
  ├─ Agent tool: Evolver (B)
  │    ├─ Bash: 审计 wrapper 知识检索（preflight → get）
  │    ├─ Read/Write/Edit: 源码修改、知识 wiki 更新
  │    ├─ Edit: STATE B 节
  │    └─ 输出: 实现变更摘要 + readlist
  ├─ Bash: 写保护校验 + STATE B 节验证
  │
  ├─ Agent tool: Verifier (C)
  │    ├─ Bash: 本地/远程评测
  │    ├─ Read: 知识 wiki、STATE A/B 节
  │    ├─ Edit: STATE C 节
  │    └─ 输出: 四种终态之一 + 融合路径证明
  ├─ Bash: STATE C 节验证 + 知识树 hash 校验
  │
  ├─ Agent tool: Landing Reviewer (R)
  │    ├─ Read: 全部 STATE 节 + 产物
  │    └─ 输出: 纠偏包或通过
  │
  └─ Bash: review_loop.py decide → continue / stop / infrastructure-blocked

收口
  └─ Bash: review_loop.py finalize → canonical 闭合校验 + 写保护终态校验
```

### 2.3 与现有架构的对照

| 现有（外部 CLI） | 迁移后（CodeAgent） | 变化说明 |
|-----------------|--------------------|---------|
| run_role.py 编排循环 | Skill SKILL.md 自然语言编排指令 | 编排逻辑从 Python 提升到文档 |
| subprocess.Popen 外部 CLI | Agent tool 调用 | 进程外 → 进程内子 agent |
| CLI 的绕过沙箱选项 | Agent tool 的 mode: auto | 全局绕过 → 按角色精细控制 |
| CLI 的输出取最后消息 | Agent tool 返回值 | 机制等价 |
| CLI 的 trace 文件 | 角色自记录 + 编排层聚合 | 详见第 7 章 |
| 角色权限靠 prompt 约束 | disallowedTools 硬禁用 + prompt 约束 | 双层防线 |
| 角色定义文件 | Agent tool prompt 参数 | 角色契约 .md 直接注入 |

## 3. 角色执行：Agent tool 配置

### 3.1 五角色配置矩阵

| 角色 | Agent 类型 | 执行模式 | 允许的工具 | 禁用的工具 | 隔离说明 |
|------|-----------|---------|-----------|-----------|---------|
| Base Developer | general-purpose | auto | Bash, Read, Write, Edit, Glob, Grep | Agent | 需完整开发能力；禁 Agent 防止递归 |
| Comparator (A) | general-purpose | auto | Bash, Read, Edit, Glob, Grep | Write, Agent | 只 Edit STATE A 节；禁 Write 防止创建文件 |
| Evolver (B) | general-purpose | auto | Bash, Read, Write, Edit, Glob, Grep | Agent | 需修改源码和知识卡；禁 Agent 防止递归 |
| Verifier (C) | general-purpose | auto | Bash, Read, Edit, Glob, Grep | Write, Agent | 只 Edit STATE C 节；Bash 跑评测 |
| Landing Reviewer (R) | general-purpose | auto | Read, Glob, Grep | Write, Edit, Bash, Agent | 纯审阅角色，最严格限制 |

### 3.2 权限设计原则

最小权限：每个角色只获得完成其职责所需的最少工具。相比外部 CLI 方案的"全局绕过"，这是质的变化：

- Comparator 禁 Write：CLI 方案只能靠 prompt 说"不要写文件"，CodeAgent 硬性禁止 Write 工具调用
- Landing Reviewer 禁 Write/Edit/Bash：CLI 方案无法阻止 Reviewer 执行命令，CodeAgent 直接移除所有修改能力
- 所有角色统一禁 Agent：防止角色嵌套调子 agent，导致上下文嵌套和不可控行为

双重防线：工具级禁用是第一层，SHA-256 写保护快照是第二层。即使 Edit 工具允许修改某些文件，写保护脚本仍会检测越权修改并注入违规信息到下一角色。

### 3.3 上下文注入

每个角色的 Agent tool 调用的 prompt 由以下部分拼接：

1. 角色契约：agents/ 目录下对应的 .md 文件全文
2. 上下文变量：工作目录路径、目标平台、当前循环号、性能目标、已验证性能、剩余轮次
3. 前置产物：上一角色的 STATE 小节内容、readlist、映射表、纠偏包等
4. 违规信息：写保护校验或 STATE 验证发现的越权行为（如有）
5. 知识检索结果：Base 和 Evolver 的审计 wrapper 输出

这与现有 run_role.py 的 prompt 拼接逻辑等价，只是执行者从 Python 字符串拼接变成主会话的自然语言注入。

## 4. 写保护机制迁移

### 4.1 双层防线架构

| 防线层级 | 外部 CLI 方案 | CodeAgent 方案 | 机制 |
|---------|-------------|---------------|------|
| 第一层：粗粒度预防 | 无（全局绕过沙箱） | disallowedTools 工具级禁用 | Comparator 禁 Write、Reviewer 禁 Write+Edit+Bash |
| 第二层：细粒度校验 | 前后 SHA-256 快照比对 | 同样脚本，编排层 Bash 调用 | 角色执行前后各跑快照，比对受保护路径 |

### 4.2 脚本提取

从 run_role.py 提取写保护相关逻辑为独立脚本 write_protection.py，提供两个子命令：

- snapshot：对工作目录中受保护路径计算 SHA-256 快照，保存到快照文件
- verify：重新计算快照并与前次比对，输出违规列表（路径、旧哈希、新哈希）

受保护路径的分层规则保持不变：全局公共项 + 角色专属项 + 官方源码 + 原始 wiki + 知识库根目录 + Skill 目录。

### 4.3 编排层集成

每个需要写保护的角色执行前后，编排层各插入一次 Bash 调用：

1. 角色执行前：运行 snapshot 生成基线快照
2. Agent tool 执行角色
3. 角色执行后：运行 verify 比对，输出违规列表
4. 如果存在违规：将违规信息注入下一角色的 prompt（与现有行为一致）

### 4.4 构建输入保护

"构建输入"（csrc/ 下所有源文件，排除 docs/ 和临时目录）的哈希保护机制保持不变。source_hash.py 不需要修改，编排层在评测前后调用即可。

## 5. STATE 责任制迁移

### 5.1 脚本提取

从 run_role.py 提取 STATE 小节边界检查逻辑为独立脚本 state_validator.py，提供两个子命令：

- check：验证指定角色只修改了自己负责的 STATE 小节，未触碰其他角色的内容
- extract：提取指定小节内容，供编排层注入下一角色的 prompt

STATE 模板的四节责任制（A/B/C/D）和 Base 的三节结构保持不变。

### 5.2 编排层集成

每个修改 STATE 的角色执行后，编排层调用 check 验证。下方的 Agent tool 调用前，编排层调用 extract 获取前置角色的小节内容并注入 prompt。

### 5.3 与写保护的协同

STATE 验证检查内容边界，写保护检查路径边界。两者互补：

- STATE 验证能发现"Comparator 修改了 Evolver 的 STATE 小节"
- 写保护能发现"Comparator 修改了 csrc/ 下的源码文件"
- 两者都发现不了"Comparator 用 Edit 修改了 STATE A 节中的无关内容"，这由角色契约的 prompt 约束覆盖

## 6. 知识检索审计迁移

### 6.1 审计 wrapper 保持不变

knowledge_query_audit.py 的核心逻辑（固定 commit、只允许确定性子命令、记录 command/doc_id/output_sha256 到 JSONL）不需要修改。

### 6.2 调用方式变化

在外部 CLI 方案中，角色的 prompt 中被告知调用审计 wrapper 的命令格式。迁移后不变，角色仍然通过 Bash 工具调用审计 wrapper，只是执行环境从 CLI 会话变成了 Agent tool 子 agent。

### 6.3 权限保障

Base 和 Evolver 的 allowedTools 包含 Bash，所以可以调用审计 wrapper。Comparator 和 Verifier 的 allowedTools 也包含 Bash（Comparator 需要读文件、Verifier 需要跑评测），但角色契约明确禁止其进行知识检索，这由 prompt 约束覆盖，与现有方案一致。

## 7. 可观测性与轨迹追踪

### 7.1 差异分析

| 维度 | 外部 CLI 方案 | CodeAgent 方案 |
|------|-------------|---------------|
| 追踪生成方式 | CLI 的 --json 模式实时写入 JSONL，包含每个工具调用 | Agent tool 只返回最终消息，中间过程不可见 |
| 追踪完整性 | 高（自动化、无遗漏） | 中（关键校验由脚本捕获，角色自记录依赖 prompt 遵从性） |
| 追溯能力 | 可回放每个工具调用的参数和输出 | 可回放验证脚本的输出，角色内部操作依赖自记录 |

### 7.2 替代方案：角色自记录 + 编排层聚合

角色自记录：角色契约 prompt 中要求，每次关键操作（读文件、写文件、调评测、查知识）后，用 Bash 追加一行 JSONL 到指定轨迹文件。格式与现有 JSONL 兼容。

编排层记录：主会话在每个角色执行前后，用 Bash 调用 trace_logger.py 写入 start/end 事件，格式与现有 run_role.py 的记录兼容：

- start 事件包含：attempt_id、角色名、平台、模型、prompt 哈希、开始时间
- end 事件包含：attempt_id、角色名、返回码、boundary_changes、结束时间

聚合：trace_logger.py 的 aggregate 子命令将角色自记录与编排层记录合并为统一 JSONL 文件，放在工作目录的 traces/ 下。

### 7.3 审计完整性保障

关键审计点不依赖角色自记录，而是由编排层的验证脚本独立捕获：

| 审计点 | 捕获方式 | 是否依赖角色自记录 |
|--------|---------|-------------------|
| 写保护违规 | write_protection.py verify 输出 | 否 |
| STATE 越权修改 | state_validator.py check 输出 | 否 |
| 知识检索记录 | knowledge_query_audit.py JSONL | 否 |
| 知识树 hash 变化 | validate_evolved_knowledge.py 输出 | 否 |
| 评测结果 | canonical_eval.py + 评测报告文件 | 否 |
| 循环决策 | review_loop.py 输出 | 否 |
| 角色内部操作细节 | 角色自记录 JSONL | 是 |

角色自记录只是增强可观测性（方便回放调试），不是审计的必要条件。即使角色完全不自记录，所有关键校验点仍然有完整证据。

## 8. 循环决策与收口

### 8.1 决策流程不变

review_loop.py 的三种决策语义（continue / stop / infrastructure-blocked）和判定逻辑完全保留。编排层通过 Bash 调用 review_loop.py decide，读取输出决定循环走向。

### 8.2 收口流程不变

review_loop.py finalize 的收口校验（canonical 闭合、写保护终态、知识树 hash）完全保留。编排层在循环结束后调用。

### 8.3 性能目标与退出语义

性能目标（正确率 100% 且 avg_speedup >= 1.0）和退出语义（达标只是允许退出而非必须退出，未达标不得早停，最多 10 轮）保持不变。这些逻辑都在 review_loop.py 和 performance_target.py 中实现，不需要迁移。

### 8.4 循环输入继承

prepare_loop.py 的循环输入继承逻辑（最近 verifier 轨迹优先，无则回退 Base）不需要修改。编排层在每轮循环开始时调用 prepare_loop.py 即可。

## 9. Resume 机制

### 9.1 不变部分

resume_e2e.py 的核心逻辑（保留 Base、历史 loop、知识副本和 commit，从下一轮继续）不需要修改。编排层通过 Bash 调用 resume_e2e.py 初始化续跑工作目录。

### 9.2 编排层适配

续跑时的编排起点是 resume_e2e.py 指定的循环号，从该轮次直接进入飞轮循环。Skill 文档需要描述两种入口：

- 全新运行：准备 → Base → 飞轮循环
- 续跑：resume → 飞轮循环（从指定轮次开始）

## 10. Skill 文档结构

### 10.1 SKILL.md 编排指令

Skill 文档的执行章节按步骤描述编排流程，主会话按步骤顺序执行。每个步骤包含：

- 操作类型：Bash（调用脚本）或 Agent tool（启动角色）
- 输入：命令参数或角色 prompt 内容
- 输出：预期产物和校验条件
- 失败处理：异常情况下的回退策略

### 10.2 步骤概览

| 步骤 | 类型 | 描述 |
|------|------|------|
| 1 | Bash | prepare_e2e.py — 创建工作目录、固定官方源码 |
| 2 | Bash | write_protection.py snapshot — Base 写保护基线 |
| 3 | Agent tool | Base 角色执行 |
| 4 | Bash | write_protection.py verify + state_validator.py — Base 校验 |
| 5 | Bash | 评测确认 Base 通过 |
| 6-N | Bash + Agent tool | 飞轮循环（每轮 5 个子步骤 × 角色数） |
| N+1 | Bash | review_loop.py finalize — 收口 |

### 10.3 角色执行步骤模板

每个角色的执行步骤遵循统一模板：

1. 运行写保护快照（如该角色需要写保护）
2. 用 Agent tool 启动角色，注入角色契约 + 上下文 + 前置产物 + 违规信息
3. 运行写保护校验（如该角色需要写保护）
4. 运行 STATE 验证（如该角色修改 STATE）
5. 运行知识树 hash 校验（如该角色可能修改知识 wiki）
6. 收集角色输出中的结构化摘要，供下一角色使用

## 11. 不变清单

以下文件/机制在迁移中不需要任何修改，直接复用：

| 类别 | 文件/机制 | 说明 |
|------|----------|------|
| 角色契约 | agents/base-developer.md | Base 角色完整契约 |
| 角色契约 | agents/knowledge-code-comparator.md | Comparator 角色完整契约 |
| 角色契约 | agents/knowledge-evolve-from-trace.md | Evolver 角色完整契约 |
| 角色契约 | agents/knowledge-verifier.md | Verifier 角色完整契约 |
| 角色契约 | agents/knowledge-landing-reviewer.md | Landing Reviewer 角色完整契约 |
| 模板 | references/base-state-template.md | Base STATE 模板 |
| 模板 | references/loop-state-template.md | 循环 STATE 模板 |
| 模板 | references/common-failure-modes.md | 常见失败模式 |
| 准备脚本 | scripts/prepare_e2e.py | 准备阶段入口 |
| 循环脚本 | scripts/prepare_loop.py | 循环目录创建与校验 |
| 决策脚本 | scripts/review_loop.py | 循环决策与收口 |
| 评测脚本 | scripts/canonical_eval.py | Canonical 评测报告选择 |
| 评测脚本 | scripts/local_bench.py | 本地评测 helper |
| 评测脚本 | scripts/remote_bench.py | 远程评测 helper |
| 性能脚本 | scripts/performance_target.py | 性能目标与退出判定 |
| 源码脚本 | scripts/golden_source.py | 官方源码固定 |
| 源码脚本 | scripts/source_hash.py | 构建输入 hash 计算 |
| 校验脚本 | scripts/validate_evolved_knowledge.py | 增量知识校验 |
| 审计脚本 | scripts/knowledge_query_audit.py | 知识检索审计 wrapper |
| 续跑脚本 | scripts/resume_e2e.py | 原地续跑 |
| 版本脚本 | scripts/knowledge_versions.py | 知识版本差分校验 |
| 解锁脚本 | scripts/unlocker.py | 阻断恢复 |

## 12. 需要提取或新建的脚本

### 12.1 write_protection.py

来源：从 run_role.py 的受保护路径定义和 SHA-256 快照逻辑提取

职责：

- snapshot 子命令：计算受保护路径的哈希快照，保存到快照文件
- verify 子命令：重新计算快照并与前次比对，输出违规列表

受保护路径规则（与现有完全一致）：

- 全局公共项：run_meta.json、STATE 文件、评测报告目录、知识库根五目录、Skill 目录
- 角色专属项：非 Base 角色的 base/ 目录、A/B/R 的 csrc/ 目录、各角色的 loop 内专属产物
- 固定资源：官方源码检出目录、原始 wiki 文件

### 12.2 state_validator.py

来源：从 run_role.py 的 STATE 小节分割和边界检查逻辑提取

职责：

- check 子命令：验证指定角色只修改了自己负责的 STATE 小节
- extract 子命令：提取指定小节内容

小节映射：

- Base：规格设计 / 实现正确性 / 唯一基线
- 循环 A：Comparator 候选与映射
- 循环 B：Evolver 实现变更与 readlist
- 循环 C：Verifier 终态与融合路径证明
- 循环 D：编排元数据（系统维护，非角色写入）

### 12.3 trace_logger.py

来源：新建

职责：

- start 子命令：记录角色开始事件（attempt_id、角色名、模型、prompt 哈希、开始时间）
- end 子命令：记录角色结束事件（attempt_id、角色名、返回码、boundary_changes、结束时间）
- aggregate 子命令：合并角色自记录与编排层记录为统一 JSONL

## 13. 需要删除的文件

| 文件 | 删除原因 |
|------|---------|
| scripts/run_role.py | 编排职责归 Skill 文档，验证职责归提取出的独立脚本，角色执行归 Agent tool |
| agents/openai.yaml | Agent tool 的 prompt 参数和配置矩阵替代角色定义文件 |

## 14. 关键差异与风险缓解

### 14.1 角色内无法实时追踪工具调用

风险：审计粒度低于外部 CLI 的 --json 模式

缓解：关键校验（写保护、STATE 边界、知识 hash、评测结果）由编排层验证脚本独立捕获，不依赖角色内部追踪。角色自记录只是增强可观测性的可选层。

### 14.2 Agent tool 无硬性超时

风险：角色可能长时间挂起

缓解：在角色契约 prompt 中明确时间预算和最大操作数约束；编排层可在 Agent tool 调用前通过 Bash 设置外部超时监控。

### 14.3 主会话上下文随循环增长

风险：后期循环可能因上下文过长导致截断

缓解：每轮循环结束后，编排层用 Bash 将关键状态（决策结果、评测分数、违规列表）序列化到文件。主会话只保留最近一轮的摘要，需要详情时从文件读取。

### 14.4 disallowedTools 是粗粒度的

风险：Comparator 理论上可以 Edit 非 STATE 文件（Edit 不区分目标路径）

缓解：SHA-256 写保护快照作为第二层防线，检测越权修改并注入违规信息到下一角色。双层防线（工具禁用 + 哈希校验）的联合覆盖度高于现有单层 prompt 约束。

### 14.5 Agent tool 返回文本摘要

风险：丢失角色执行过程中的结构化输出

缓解：角色契约 prompt 要求在最终消息中包含结构化摘要块（JSON 格式），编排层解析该块提取关键字段。摘要块的内容覆盖现有 run_role.py 从最后消息解析的全部字段。

## 15. 实现优先级与路线图

### 15.1 P0：单循环端到端跑通

目标：用最简用例验证 Base → A → B → C → R → decision 的完整流程

范围：

- SKILL.md 编排指令（单循环版本）
- Agent tool 五角色配置矩阵
- prepare_e2e.py / prepare_loop.py Bash 调用
- review_loop.py decide Bash 调用

不包含：写保护快照、STATE 验证、轨迹记录、多循环、resume

验收标准：Base 通过评测 → A 输出候选 → B 修改源码 → C 验证 → R 审阅 → decision 输出合理决策

### 15.2 P0.5：写保护 + STATE 验证

目标：提取并集成 write_protection.py 和 state_validator.py

范围：

- 从 run_role.py 提取写保护逻辑
- 从 run_role.py 提取 STATE 验证逻辑
- 编排层在角色执行前后插入脚本调用
- 违规信息注入下一角色 prompt

验收标准：角色越权修改被检测到，违规信息正确注入

### 15.3 P1：多循环 + 收口 + Resume

目标：实现完整的多循环飞轮

范围：

- 循环输入继承
- 收口校验
- resume_e2e.py 集成
- 性能目标判定

验收标准：多轮循环正确继承、达标后正确收口、续跑从指定轮次继续

### 15.4 P2：可观测性

目标：实现轨迹记录和聚合

范围：

- trace_logger.py 实现
- 角色自记录 prompt 指令
- 聚合脚本

验收标准：统一 JSONL 文件包含所有角色的 start/end 事件和关键操作记录

## 16. 与现有复现文档的关系

本文档是复现文档（描述飞轮的机制和规则，与实现平台无关）的架构迁移补充，描述如何将这些机制映射到 CodeAgent 平台。交叉引用：

| 复现文档章节 | 本文档对应章节 | 说明 |
|-------------|---------------|------|
| 架构概览 | 第 2 章 架构总览 | 执行模型从 CLI 切换到 Agent tool |
| 写保护与哈希校验 | 第 4 章 写保护机制迁移 | 双层防线架构 |
| 知识检索审计 | 第 6 章 知识检索审计迁移 | 审计 wrapper 不变 |
| 增量知识校验 | 不变 | 脚本直接复用 |
| Resume 续跑 | 第 9 章 Resume 机制 | 逻辑不变，编排入口适配 |
| 轨迹 JSONL | 第 7 章 可观测性 | 追踪方式变化 |
| 环境变量与配置 | 不变 | 环境变量和配置文件复用 |

---

## 附录 A：术语对照

| 外部 CLI 术语 | CodeAgent 对等术语 |
|--------------|-------------------|
| 外部 CLI 执行 | Agent tool 调用 |
| fresh session | Agent tool 无状态调用 |
| 绕过沙箱选项 | mode: auto |
| 输出取最后消息 | Agent tool 返回值 |
| trace 文件 | 角色自记录 + trace_logger.py |
| allowed-tools (YAML) | allowedTools (参数) |
| agent definition (YAML) | Agent tool prompt + 配置参数 |
| subprocess.Popen | Agent tool (进程内子 agent) |

## 附录 B：角色 prompt 拼接模板

每个角色的 Agent tool 调用的 prompt 遵循以下拼接模板：

```text
[角色契约 .md 全文]

---

## 当前上下文

- 工作目录: {work_dir}
- 目标平台: {platform}
- 当前循环: 第 {loop_num} 轮（共 {max_loops} 轮）
- 性能目标: 正确率 100%, avg_speedup >= {target_speedup}
- 已验证性能: {current_performance}

## 前置产物

{前置角色的 STATE 小节内容}
{readlist / 映射表 / 纠偏包}

## 违规信息

{写保护或 STATE 验证发现的越权行为，如无则省略}

## 知识检索结果

{审计 wrapper 的检索输出，仅 Base 和 Evolver 包含此节}
```

## 附录 C：验证脚本调用时序

| 角色 | 执行前 | 执行后 |
|------|--------|--------|
| Base | write_protection.py snapshot | write_protection.py verify |
| Comparator (A) | 无 | state_validator.py check A |
| Evolver (B) | write_protection.py snapshot | write_protection.py verify + state_validator.py check B + validate_evolved_knowledge.py |
| Verifier (C) | 无 | state_validator.py check C + source_hash.py（构建输入保护） |
| Landing Reviewer (R) | 无 | 无（纯审阅角色） |

---

## 与项目设计的适配（2026-08-21 分析）

> 以上方案迁移的是**案例团队的 5 角色飞轮**。本项目采用时需按自身 4 角色设计做映射，框架选型结论与注意事项如下。

### 框架选型结论（印证自研编排，不引入重型框架）

1. 本项目流程是固定循环，CodeAgent 方案的 SKILL.md 步骤化编排 + review_loop.py 确定性决策正是自研轻量编排的落地形态
2. 唯一模型，框架的模型无关性卖点无关紧要；Agent tool 已提供角色执行能力，无需 LangGraph/CrewAI
3. 核心机制（写保护、STATE 分节、检索审计、知识树 hash）框架给不了，方案中全部由脚本实现
4. 内网环境，云观测不可用；方案以文件/JSONL 落盘代替

### 角色映射（案例 5 角色 → 本项目 4 角色）

| 案例角色 | 本项目对应 | 权限配置沿用 |
|---------|-----------|-------------|
| Base Developer + Evolver (B) | 知识生成 Agent（唯一执笔） | 允许 Write/Edit + Bash（审计检索） |
| Verifier (C) | Coder Agent | 禁 Write，只 Edit 代码产物，Bash 跑评测 |
| Comparator (A) + Landing Reviewer (R) | Review Agent（只读） | 禁 Write/Edit（Reviewer 最严格） |
| 主调度 | 编排层（只决策不执笔） | SKILL.md 步骤 + review_loop.py 决策脚本 |

### 本项目落地时的关键调整

1. **角色契约按 4 角色重写**（agents/ 目录 4 个 .md，替代案例 5 个）：知识生成（首版修订一体）、Coder、Review、编排
2. **编排层 LLM 化的边界**：确定性决策（门禁、继续/停止/回滚、校验）全部脚本化；主会话只按 SKILL.md 步骤执行，不参与内容判断
3. **跨轮状态落文件**：失败机制总账、薄弱点地图等跨轮积累信息每轮结束写盘，不依赖主会话记忆（防 14.3 截断）
4. **写保护第二层必须保留**：disallowedTools 是粗粒度（Edit 不分路径），SHA-256 快照是唯一能抓"合法工具越权改文件"的手段
5. **可观测性降级可接受**：关键审计点由脚本独立捕获（7.3），角色自记录仅作调试增强
6. **PoC 第一验证目标不变**：收敛曲线报告；正确率与相似度两条线分开记录

### 常见坑（实现时注意）

1. SKILL.md 步骤必须写死成确定性流程，主会话无分支自由度
2. prompt 拼接模板（附录 B）作为硬规范，防止主会话漏注入
3. 退出条件不依赖 LLM 自我声明（"无待实现知识"需客观信号佐证）
4. 评测多次而非一次（单次 canonical 不可信，方差大）
5. 防背源码：评测用私有/变换代码，评测集独立
6. 待确认：codeagent 是否支持 Python SDK/HTTP API（支持则可脚本化编排，主会话 LLM 化可最小化）
