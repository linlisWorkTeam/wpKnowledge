# 知识飞轮技术细节补充

> 来源：对 [operator-flywheel-case.md](operator-flywheel-case.md) §13「待澄清问题」的逐条回答（别的团队提供，2026-08-21）。
> 定位：补充《知识飞轮案例》中未展开的实现细节，包括轨迹格式、评测机制、审查实现、哈希算法、写保护范围等。正文按脱敏口径改写，与案例文档一致。

---

## 1. 轨迹 JSONL 的字段结构

角色轨迹 JSONL 由 run_role.py 生成，每行一条 JSON 记录，共有三种类型。

### 1.1 Attempt Start 记录

| 字段 | 含义 |
|------|------|
| type | 固定为 knowledge_e2e_role_attempt |
| event | start |
| attempt_id | UUID，唯一标识本次角色会话 |
| role | 角色名：base-developer / knowledge-code-comparator / knowledge-evolver / knowledge-verifier / knowledge-landing-reviewer |
| platform | 规范化平台 |
| model | 固定模型标识 |
| reasoning_effort | 固定推理强度 |
| knowledge_commit | 固定知识库 commit |
| prompt_sha256 | 渲染后 prompt 的 SHA-256 |
| started_at | ISO-8601 时间戳 |

### 1.2 Attempt End 记录

| 字段 | 含义 |
|------|------|
| type | 固定为 knowledge_e2e_role_attempt |
| event | end |
| attempt_id | 与 start 对应 |
| role | 同上 |
| codex_return_code | 编码 CLI 会话原始退出码 |
| return_code | 最终退出码（有越权写入时为 3） |
| boundary_changes | 被越权修改的受保护路径列表 |
| finished_at | ISO-8601 时间戳 |

### 1.3 中间行

编码 CLI 的 --json 输出原样追加（stdout 逐行转发到 JSONL 文件）。这些是 CLI 自身的会话事件格式，由 CLI 控制，不是飞轮脚本定义的。

**与 session.py 的对齐**：飞轮不使用 session.py，也不定义 CLI 内部会话格式。attempt_id + started_at/finished_at + prompt_sha256 是飞轮层面的会话标识，可以用来与 CLI 的 session 记录做外键关联。

**Evolver 读的 Verifier 轨迹**：Evolver 的 B1 阶段读的是上一轮 verifier 的完整 JSONL（路径在 input.json 的 input_trace 字段中），包含上述所有记录类型。B1 从中提取构建/精度/性能/纠偏等事实，方式是 LLM 直接阅读 JSONL 中的会话事件，而非脚本预处理。

## 2. 评测集来源与规模

### 2.1 Cases 来源

由评测框架提供，存放在 task/cases.csv 或 task/cases.yaml 中，与评测任务绑定。每个算子的 cases 数量不同，由评测框架按算子语义（dtype/shape/layout 组合）自动生成。

### 2.2 "正确率 100%" 的含义

从 canonical_eval.py 的校验逻辑看，评测报告中有 correctness.passed 和 correctness.total 两个字段，正确率 100% = passed == total。

日志中出现的实际数据：transpose 算子 20/20 cases。

### 2.3 Golden 期望输出

task/golden.py 是精度评测参考，它计算每个 case 的期望结果，与待测实现的实际输出对比。golden.py 本身不属于"官方实现源码"（这是飞轮的术语边界：官方实现源码专指 Comparator 对比的官方实现仓源码）。Golden 的生成方式由评测框架决定，通常是 PyTorch 参考实现。

### 2.4 规模

没有一个统一数量，取决于算子。从日志中看到的实际运行数据是 20 个 cases。复杂算子（多模板/多 dtype）可能有更多。

## 3. Landing Review 的实现机制

判断"知识是否正确落地"靠 LLM，不是规则。

### 3.1 靠规则的部分（确定性关卡在 R 之前已检查）

| 检查项 | 实现方式 |
|--------|---------|
| readlist 每条 K<n> 在 checklist 恰有一行 | prepare_loop.py 的 readlist 解析器检查 |
| 终态只能是四种之一 | review_loop.py 的 TERMINAL 集合校验 |
| 已实现必须精度 100% | canonical_eval.py 校验 passed == total |
| 评测数字来自 canonical 报告 | 脚本验证 canonical 路径和 hash |

### 3.2 靠 LLM 的部分（R 的核心价值）

- 实现是否收敛到知识指定的语义（不是代码是否一致，是语义方向对不对）
- 已实现/部分实现是否朝官方实现路线收敛（可以走不同路径，但不能走偏）
- 路由条件是否来自语义而非硬编码 case ID
- 是否存在 harness debt / 无脑复制官方源码
- direct-launch unlocker 是否真的建立了桥接能力

### 3.3 偏离点提取

R 读取 02-code-comparison.md（A 的官方路线证据）、04/07（B 的决策和 readlist）、verifier 的设计/progress/checklist、当前代码 diff。偏离点是 LLM 通过交叉比对这些材料自行判定的，没有预定义的偏离模式列表。

如果发现偏离，R 写入 13-correction-packet.md，格式固定（偏离点 + 纠偏依据 + 最小 retry 范围 + 成功判据 + 不允许事项），然后触发 fresh verifier retry。

## 4. 知识树 hash 算法

按文件内容计算，不是按目录结构。从 validate_evolved_knowledge.py 的实现看：

| 步骤 | 说明 |
|------|------|
| 文件集合校验 | 比较 source_manifest.json 登记的相对路径集合与 knowledge_worktree/ 下实际存在的文件集合，必须完全一致（不能新增也不能删除） |
| 逐文件 SHA-256 | 对 knowledge_worktree/ 下每个文件计算 SHA-256，结果存入 08-knowledge-validation.json 的 validated_tree_sha256 字段（key 是相对路径，value 是 SHA-256） |
| 校验关卡用法 | review_loop.py 在收口时重新计算知识树的 hash 并与 Evolver 校验时固定的 hash 比对。这里的"hash"是整个 validated_tree_sha256 字典的完整性，每个文件的 SHA-256 都被记录并比对，任何一个文件内容变化都会被检测到 |
| 特殊点 | _digest_path（run_role.py 中的写保护快照）对目录类型的路径递归计算所有子文件的 SHA-256，并且把相对路径名也纳入哈希输入（先 update 路径字符串，再 update 文件内容字节），所以文件重命名也会被检测到 |

总结：SHA-256，逐文件计算，路径名 + 文件内容字节共同输入哈希，排除 __pycache__/.pytest_cache/.pyc 等临时文件。

## 5. 写保护快照范围

受保护路径的具体清单（按角色分组，来自 run_role.py 的 _protected_paths 函数）：

### 5.1 所有角色共同保护

- task/（评测任务目录）
- run_meta.json
- 00-input-facts.md
- access_policy.json
- progress.md

### 5.2 除 Base 外额外保护

- base/（Base 全部产物）

### 5.3 Comparator / Evolver / Landing Reviewer 额外保护

- csrc/（目标代码，这三个角色不能改代码）

### 5.4 Loop 级别保护

| 角色 | 额外保护的路径 |
|------|---------------|
| 所有循环角色 | input.json、source_manifest.json、source_manifest.md、11-loop-decision.json |
| Evolver / Verifier / Landing Reviewer | 02-code-comparison.md |
| Verifier（不能碰 B 产物） | 03/04/06/07/08/12/13/updated-knowledge/ |
| Landing Reviewer（不能碰 A/B/C 产物） | 00-STATE.md/03/04/05/06/07/08/09/10/updated-knowledge//evals//csrc/ |
| Evolver（不能碰上一轮轨迹） | input_trace 指向的文件 |
| Comparator / Verifier / Landing Reviewer | knowledge_worktree/（不能碰知识副本） |

### 5.5 源码和原始 wiki 保护

- 所有 golden.sources[].operator_dir（官方源码 checkout）
- 所有 wiki_files[].path（原始 wiki 文件）

### 5.6 知识库根保护（可检索角色）

- 知识库根下的 kernels/、runbooks/、reference/、graph/、schemas/
- .agents/skills/knowledge-query

### 5.7 "构建输入"指什么

指 csrc/ 目录下参与目标构建的所有源文件。source_hash.py 的计算方式：递归遍历工作目录下所有文件（排除 .git/build/dist/__pycache__/.pytest_cache/*.egg-info/*.so/*.whl/*.pyc 等，排除 docs/ 目录），对每个文件的相对路径 POSIX 字符串和原始字节内容一起喂入 SHA-256。Comparator 和 Evolver 运行前后各算一次，不一致则视为越权修改。

## 6. 非抄代码证明

靠 LLM 自己写，不是自动化验证。

从 Verifier 角色契约看，每个"已实现"候选必须写出两份证明：

| 证明 | 内容 |
|------|------|
| 融合路径证明 | 优化 case 的命中条件（dtype/shape/k/layout/tiling/resource 等语义条件）、host launch 函数名、device kernel 符号名、关键 file:line、softmax/top-k/sort/reduce 等核心计算位于该 kernel 内的说明 |
| 非抄代码证明 | 说明候选是基于 readlist/知识检索的局部自定义 kernel 实现 |

### 6.1 为什么不是自动化的

没有脚本去 diff 生成的代码和官方源码然后判断"相似度"。原因有两层：

1. 概念上：飞轮允许实现路径与官方不同，只要语义方向收敛。相似度低不代表抄了，相似度高也不一定抄了（必要 API/模板形态可能一致）
2. 实践上：如果 Verifier 的 diff 呈现官方源码大段原样搬运且不能解释为必要 API/模板形态，它不能进入"已实现"，这个判断需要语义理解，是 LLM 做的

### 6.2 自动化部分

Landing Reviewer 和 review_loop.py 会检查 canonical 报告中的 file:line 证据链、source_hash 与 build_hash 一致性、source_commit 可验证等，但这些验证的是"评测证据是否真实"，不是"代码是否抄了"。

## 7. 实际收敛数据

本仓库中没有完整的收敛统计。能从日志中提取到的有限数据：

### 7.1 已知实际运行

| 算子 | 实验 | 结果 |
|------|------|------|
| transpose | 0717 实验 | 20/20 正确率、score 62.66、avg_speedup 0.42，未达到 1.0 目标 |
| 8 算子 | 本地飞轮实验（07-18 日志提及） | 没有性能结果记录 |
| 某 MoE 门控算子 | Wiki 卡中有 avg_speedup 字段 | 具体数值未在日志中披露 |

### 7.2 关于收敛轮次

- 日志中提到 max_loops 曾从 10 提升到 20，暗示 10 轮不够收敛
- transpose 的 avg_speedup=0.42 远低于 1.0 目标，说明该算子在已有轮次内未收敛
- 目前没有"平均几轮收敛"的数据，从日志看，可能大部分算子在常用轮次内未达到 1.0 目标

### 7.3 单轮耗时与成本

日志中没有记录。但可以推算：

- 每轮 5 个角色（A/B/C/R + 主调度），每个角色是一个完整编码 CLI 会话
- Verifier 是最耗时的角色（需要实际加速硬件构建+评测，每条 readlist 项都要 build-eval）
- 平台C 算子涉及寄存器 API 审查，Verifier 更慢
- 远程模式还有 SSH 延迟和远程构建时间

结论：本仓库没有公开的系统化收敛数据，只有零散的单算子实验记录。要获得系统数据需要实际跑多个算子的完整飞轮实验。

## 8. Comparator 的 150 行限制与大算子对比策略

150 行是建议值，不是硬限制。从 Comparator 角色契约的原文："每次只读符号附近或切片给出的行段，单次读取建议不超过 150 行。"

### 8.1 大算子的分块策略（三层渐进披露）

**第一层：源码切片计划（comparator-input/source-slices/）**

这是 Evolver 的 B2 为下一轮 A 准备的导航信息，内容包括：

- 按模板/实现组织的最小读取计划
- 每个模板需要读的文件、符号、行段
- 必要注意点

A 先读切片计划，然后按计划逐个模板定位，不需要全文件展开。

**第二层：符号搜索 + 小范围读取**

切片缺失时，A 用符号搜索（如函数名/类名）从官方源码中定位入口，然后只读取入口附近小范围行段。每次读取控制在建议范围内。

**第三层：多模板分解**

如果官方实现呈现多 tiling key / 多模板类 / 多 kernel 入口 / 多分发路径，A 必须按模板/实现维度拆分，每个差异单独一条候选，每条候选只覆盖一个模板/实现。这意味着大算子的对比本身就是拆成多个小对比完成的。

### 8.2 大算子的实际处理

- 官方源码的 _source_index/<name>.md 提供按模板组织的源码导航（只有 Comparator 可以读），每个模板小节只列关键符号和行段
- 禁止 cat / 完整展开大文件 / 把完整官方实现灌入上下文
- 确需扩大读取范围时，A 必须先写明缺口并拆成多个小范围

总结：大算子对比按模板分块、按切片导航、按符号定位、每次只读必要行段。150 行是控制单次读取量的软约束，实际策略的核心是"渐进披露"，先读导航信息，再定向小范围读取，避免上下文爆炸。

---

## 附录：与主文档的对应关系

> 主文档指该团队完整版《知识飞轮》设计文档（本文档为对其内容的补充说明）。

| 本文档章节 | 对应主文档章节 |
|-----------|---------------|
| 1. 轨迹 JSONL 字段结构 | 第 19 章（产物清单）、第 12 章（检索审计） |
| 2. 评测集来源与规模 | 第 17 章（评测体系） |
| 3. Landing Review 实现机制 | 第 9 章（阶段 R） |
| 4. 知识树 hash 算法 | 第 13 章（增量知识校验） |
| 5. 写保护快照范围 | 第 11 章（写保护机制） |
| 6. 非抄代码证明 | 第 8.5 节（融合路径验收不变量） |
| 7. 实际收敛数据 | 无对应（补充数据） |
| 8. Comparator 150 行限制 | 第 6.4 节（硬边界） |

---

## 对本项目的启示（2026-08-21 分析）

> 项目边界澄清：本项目范围 = **飞轮演进知识副本**（知识库输入，首版生成由上游负责，不在本项目范围）；项目背景 = **业务代码仓库**（每仓几十万行），文档滞后失真，需从代码回推解释型文档。以下启示基于此定位。

### 1. 轨迹 JSONL 直接可借鉴（对齐 session.py）

attempt_id + started_at/finished_at + prompt_sha256 作为飞轮层会话标识，外键关联编码 CLI 内部会话。对应到我们的 session.py：

- 每次角色调用记录：attempt_id、prompt_sha256、时间戳、退出码
- 增加 boundary_changes 字段：越权修改的受保护路径名单，对应它们的 return_code=3 机制（有越权写即失败）

### 2. Landing Review 是纯 LLM 判断，规则只做确定性关卡

确定性部分（readlist 完整性、终态枚举、精度 100%、canonical 校验）在 R 之前由脚本检查；R 的 LLM 部分判断：语义方向对不对、是否朝官方路线收敛、路由条件是否来自语义、是否有 harness debt / 无脑复制。

对我们：印证 §12.1 第 6 条（Review Agent 增加"知识是否正确落地"审查维度），且拿到具体输入清单：02-code-comparison.md（A 证据）+ 04/07（B 决策与 readlist）+ verifier 设计/progress/checklist + 当前代码 diff，交叉比对后 LLM 自行判定偏离点。

### 3. hash 算法与写保护细节可抄

- 逐文件 SHA-256，**路径字符串也入哈希**（先 update 路径再 update 内容，重命名可检测）
- 排除 __pycache__/.pytest_cache/.pyc 等临时文件
- 写保护清单分三层：角色级（按角色分组）、loop 级（input.json/source_manifest/loop-decision）、知识库根（kernels/、runbooks/、reference/、graph/、schemas/）
- 对应我们的 gate/hashcheck.py 设想，比现有粒度细得多

### 4. 收敛数据警示：正确率与相似度是两条线

transpose 实测 20/20 正确率但 avg_speedup 0.42 远未达标（目标 1.0），max_loops 从 10 提到 20 暗示收敛慢。对照我们的门禁：

- 测试通过率（正确率）和相似度是独立信号，测试全过不代表相似度达标
- PoC 阶段必须分开记录两条曲线，避免"正确率提升"误判为"知识合格"
- 收敛慢是常态：该团队无"平均几轮收敛"的系统数据，我们 PoC 的 5 轮上限可能偏紧，需预留扩展

---

## 案例实现的不足（论文视角审视，2026-08-21）

> 用检索论文的结论审视案例实现，列出不足与论文依据。这些不足同时是 PoC 设计要规避的坑。

### 1. 收敛性未被证明（最致命）

- **表现**：transpose 20/20 正确率但 avg_speedup 0.42（目标 1.0）；max_loops 从 10 提到 20，暗示收敛慢或未收敛；7.2 自认无系统化收敛数据。它跑通了工程骨架，但可能是在"跑轮子"而非"收敛"，靠轮次上限硬停
- **论文依据**：[On the Fragility of Self-Improving Agents](https://arxiv.org/abs/2608.18066)（2608.18066）：记忆型自改进 agent 同配置重复方差巨大、规格模糊时"自信地改进到错误方向"；[A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046)（2507.21046）：演进机制有效性缺乏系统验证是领域通病
- **对我们**：PoC 收敛曲线报告是第一验证目标，优先级高于任何模块优化

### 2. 自我评估偏见在关键环节未防住

- **表现**："非抄代码证明"由 LLM 自证、无自动化验证；"Evolver 声明本轮无待实现知识"作为完美达标条件之一，是 LLM 自我声明；Landing Review 判断"语义方向对不对"同样纯靠 LLM 交叉比对。写保护防篡改防得很细，但"合法范围内的坏知识更新"恰是它最依赖 LLM 判断的地方
- **论文依据**：[Teaching LLMs to Self-Debug](https://arxiv.org/abs/2304.05128)（2304.05128）：执行反馈最有效，但依赖外部信号；[ConSelf](https://arxiv.org/abs/2603.29292)（2603.29292）：内部信号只能作辅助，不能替代外部锚点；[ReVeal](https://arxiv.org/abs/2506.11442)（2506.11442）：可靠自验证是自演进 agent 的公认难点
- **对我们**：外部锚点（独立评测集、私有/变换代码）不可省；退出条件不依赖 LLM 自我声明

### 3. 单次评测不可信

- **表现**："执行且仅一次完整评测"，continue/stop 决策建立在单次数值上
- **论文依据**：[On the Fragility of Self-Improving Agents](https://arxiv.org/abs/2608.18066)（2608.18066）：同配置重复实验方差巨大，单次结论不可信
- **对我们**：保持 ≥5 次重复评测取均值±方差（flywheel §9.1）

### 4. 退出条件可能永远达不到

- **表现**：正确率100% + speedup≥1.0 双维度；transpose 正确但性能远不达标，只能靠 max_loops 硬停。性能优化是 LLM 生成最不稳定的部分
- **论文依据**：规格模糊导致改进跑偏（[Fragility](https://arxiv.org/abs/2608.18066) 2608.18066）
- **对我们**：门禁定义到可执行级；预留"部分达标"中间态，避免二值化卡死

### 5. 工程成本高

- **表现**：每轮 5 个完整 CLI 会话；信息隔离彻底但每轮全量重载材料；Verifier 需真实构建+评测（每条 readlist 项都要 build-eval）
- **对我们**：控制 max_rounds、单模块起步、产物落盘可断点续跑（我们的 JSONL 会话存储正好支持）

### 6. 知识质量无独立信号

- **表现**：知识好坏只看最终代码正确率/速度，知识本身没有连续的质量度量
- **论文依据**：[Code-QA-Bench](https://arxiv.org/abs/2605.29277)（2605.29277）：仓库级 QA 需区分"代码推理"与"文档记忆"，防作弊归因
- **对我们**：相似度分数作为知识的连续信号 + 溯源归因定位薄弱段（flywheel §4.3）

### 7. 写保护防不了"合法范围内的坏知识"

- **表现**：写保护/哈希只防越权篡改；知识更新由 Evolver（LLM）决策，决策错时只能靠下一轮 C/R 事后发现
- **论文依据**：[On the Fragility of Self-Improving Agents](https://arxiv.org/abs/2608.18066)（2608.18066）：记忆型自改进的污染风险
- **对我们**：防污染回滚（门禁分数下降自动回退）+ 版本控制（flywheel §9.5）
