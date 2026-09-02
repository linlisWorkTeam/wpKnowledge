# WorkPanel 综合分析报告

## 文档定位

本文件是 `knowledge/3.workpanel/调研/` 的长期维护入口，汇总会影响 WorkPanel 知识系统架构、实现边界和后续路线的正式结论。一次性命令、CAS 哈希和审查过程放在相邻的 `证据/`；特定阶段的完整论证保留为独立日期报告。

最后更新：2026-09-02。

## Connecter Remote Provider 验收更新

Windows 本机 Codex 已通过单一 Connecter Host 接入 ECS ohMyWorkPanel canary，完成群任务创建、跨站路由、runner 执行、签名结果回程和单条 Agent 回复闭环。正式结论见[本机 Codex 通过 Connecter Host 接入 ECS WorkPanel](2026-09-02-本机Codex-Connecter-Provider接入验收.md)，原始命令与 ID 见[联调证据](../证据/2026-09-02-本机Codex-Provider联调证据.md)。该结果不外推为多 Host HA 或生产发布完成。

## 当前结论

wpKnowledge 的 Knowledge Flywheel 已从“只有 P0-A 规格和多套旧实现”演进为一套可执行的 TypeScript 六边形核心，并通过 [PR #11](https://github.com/linlisWorkTeam/wpKnowledge/pull/11) 合入 main。

最终 merge commit 为 29612b078978fba7dd1681229a6931d97185c652，tree 为 5b512f8cf806d3889971b4424d38992bd7911fdf。

当前最准确的能力描述是：

> 系统已经能够在单机、单租户、受信源码边界内，把固定源码快照转化为候选知识和 fresh 生成代码，使用独立进程执行实际门禁，根据结构化失败增量修订知识，并只在不可变证据通过确定性 Gate 后原子发布 VERIFIED 知识。

它尚不能被描述为：

- 在线 GLM/DeepSeek 质量已经验证；
- 敌对生成代码可以安全运行；
- 支持多机、高可用或完整 LangGraph/Temporal 恢复；
- 能自动判断参考实现中的 bug 是否应该被知识继承。

## 架构状态

| 层 | 当前实现 | 维护边界 |
|---|---|---|
| Domain | Run 状态机、ArtifactRef、EvaluationReport、GateDecision、事件、确定性 Gate | 无数据库、SDK、模型或语言依赖 |
| Contracts | ArtifactStore、Repository、AgentProvider、ProjectEvaluator、Sandbox、LanguagePlugin | 只定义端口 |
| Application | ingest、quality、query、checkpoint、evaluate、publish、两轮 project flow | 只依赖 Domain 与 Contracts |
| Adapters | SQLite/CAS、Legacy OKF、Source Scan、DSH、Scenario Agent、Trusted Project Eval | 具体 I/O 和外部系统 |
| Entry points | CLI、HTTP、Dashboard、endlessWpKnowledgeRunner facade | 不拥有独立领域状态 |

核心不变量：

1. 文档质量不等于行为正确；
2. CANDIDATE 不能绕过 EvaluationReport 和确定性 Gate 成为 VERIFIED；
3. evidence、toolchain、run、version 和 decision 必须互相绑定；
4. 评测落库、Gate decision、REVIEWING 和事件必须原子提交；
5. 精确重试返回原结果，冲突重试失败；
6. 发布必须幂等；
7. 规划中或仅有端口的能力不得标记为 Implemented。

## endlessWpKnowledgeRunner 的最终定位

旧 runner 不再是第二套飞轮。它现在是兼容层：

- 继续服务历史 init、ingest、query、get、status、scan、feedback 调用；
- 委派给 `endlessWpKnowledgeRunner/src/interfaces/runner/cli.ts`；
- 使用同一个 WP_FLYWHEEL_HOME、SQLite Registry 和 CAS；
- 不再支持旧 score、synthetic eval 或 timer harvest；
- 不允许用 --root 选择另一套状态目录。

这实现了最初评审建议的 Strangler Pattern：先保留调用契约，再替换状态、存储、权限和发布语义，而不是维持平行系统或一次性删除所有兼容入口。

## 真实源码验收状态

固定 ohMyWorkPanel commit cfef082d7a9e5d434777374bd6b99ef8cd309cfc 已完成：

~~~text
参考实现 1/1
  → 第一版生成实现 0/1
  → Gate ITERATE
  → Correction
  → 只修订目标知识章节
  → fresh CodeGen
  → 5 次定向测试 + 123 项前端测试 + build + 150 项 Rust 测试
  → 279/279
  → Gate PASS
  → 原子发布 VERIFIED
~~~

正式结果见 [PR #11 Verified Knowledge Flywheel 交付与全项目测评报告](2026-09-01-PR11知识飞轮交付测评.md)，原始证据索引见 [ohMyWorkPanel 固定 commit 真实源码闭环验收](../证据/2026-09-01-ohMyWorkPanel真实源码验收.md)。

## 对早期可行性评审的更新

[P0-A Knowledge Flywheel MR 可行性评审](2026-08-31-P0-A知识飞轮可行性评审.md)最初给出 Request changes，核心理由是只有规格、规范冲突、迁移缺失、EvalRunner 未实现和沙箱边界不清。

截至 2026-09-01：

| 早期问题 | 更新 |
|---|---|
| 新旧需求 ID 冲突 | 已使用 KF-SYS-* 命名空间和追踪矩阵 |
| 第三套平台且无迁移策略 | 已结构性替换，legacy 只保留兼容门面 |
| 文档分数可自动 verified | 已禁止，必须 evidence-bound deterministic PASS |
| 无独立 EvalRunner | 固定 commit 的受信 ProjectEvaluator 已实现并完成真实验收 |
| 无事务发布/恢复 | SQLite 原子发布、checkpoint 和评测精确重放已实现 |
| 沙箱边界模糊 | 已明确本地 Adapter 不是敌对代码沙箱，未实现项继续 Planned |
| 在线模型质量未知 | 仍未知；Scenario Agent 不外推为真实模型 |
| reference bug 语义 | 仍待双轨 oracle 与人工批准流程 |

因此长期结论已从“当前 MR 不宜合入”更新为“受信本地核心和真实源码薄切片可合入；生产级模型与敌对执行能力仍不可宣称完成”。

## 测评摘要

- TypeScript：PASS；
- Spec validator：7 schemas、7 commands、8 results、28 个 P0 追踪项；
- 自动化测试：34/34 PASS；
- npm 生产依赖审计：0 vulnerabilities；
- ohMyWorkPanel：参考 1/1、首版 0/1、最终 279/279；
- Cursor 实际意见：6 条，全部修复并回复；
- 最终 PR：MERGED，main merge tree 与本地已测 tree 一致。

## 下一阶段优先级

### P0

- 敌对代码的 OS/VM 隔离与逃逸测试；
- 真实 GLM/DeepSeek Provider 的质量、成本和稳定性评测；
- reference bug 双轨 oracle。

### P1

- RUNNING checkpoint lease 与 crash reclaim；
- CAS orphan audit/GC；
- 细粒度身份授权和审计脱敏；
- 量化触发 LangGraph/Temporal 的升级条件。

### P2

- 第二种真实 LanguagePlugin；
- MCP/ACP/A2A 的真实消费者验证；
- 多项目固定 commit 验收 corpus。

## 维护规则

1. 新结论先更新对应日期报告，再更新本综合入口。
2. 所有 Implemented 状态必须同时指向源码和自动化测试。
3. 真实项目验收必须固定 commit、记录工具链和证据边界。
4. CAS Artifact ID 放在 notes/，不要提交本地运行数据库和工件。
5. 外部 review 因额度或服务失败时必须如实记录，不能当作通过。
6. 不修改或清理其他 Agent 的工作树；真实源码默认用 git archive 快照。

## 相关报告

- [本机 Codex 通过 Connecter Host 接入 ECS WorkPanel](2026-09-02-本机Codex-Connecter-Provider接入验收.md)
- [本机 Codex Provider 联调证据](../证据/2026-09-02-本机Codex-Provider联调证据.md)
- [PR #11 Verified Knowledge Flywheel 交付与全项目测评报告](2026-09-01-PR11知识飞轮交付测评.md)
- [P0-A Knowledge Flywheel MR 可行性评审](2026-08-31-P0-A知识飞轮可行性评审.md)
- [PR #11 开发、复验与审查记录](../证据/2026-09-01-PR11开发复验记录.md)
- [ohMyWorkPanel 固定 commit 真实源码闭环验收](../证据/2026-09-01-ohMyWorkPanel真实源码验收.md)
- [P0-A MR 评审证据与复现记录](../证据/2026-08-31-P0-A评审证据.md)
