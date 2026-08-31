# PR #11 Verified Knowledge Flywheel 交付与全项目测评报告

## 元数据

- 日期：2026-09-01（Asia/Hong_Kong）
- 研究对象：[linlisWorkTeam/wpKnowledge PR #11](https://github.com/linlisWorkTeam/wpKnowledge/pull/11)
- PR 标题：refactor(flywheel): replace endless runner with verified core
- 合并状态：MERGED
- 基线 commit：6999099f2d7ffb1f37aca743674f325072fe39fd
- 最终 PR head：c80d1fc1de57757d9515e2045a9654f30111f9ff
- merge commit：29612b078978fba7dd1681229a6931d97185c652
- 最终 tree：5b512f8cf806d3889971b4424d38992bd7911fdf
- 规模：128 个文件，新增 7,250 行，删除 3,570 行，11 个 PR 提交
- 本地源码证据：D:/AI/wpKnowledge-pr11，最终已验证 tree 与远端 main 的 merge tree 完全一致
- 真实验收源码：D:/AI/LinlisWorkPanel 中的 ohMyWorkPanel 固定 commit cfef082d7a9e5d434777374bd6b99ef8cd309cfc

## 执行结论

PR #11 已把原先互相重叠的规格、Python runner、目录状态和启发式评分路径，收敛为一个 Spec 驱动、证据绑定、可恢复且可审计的 TypeScript Knowledge Flywheel 核心。endlessWpKnowledgeRunner 不再维护第二套知识库或发布语义，而是保留为同一 CLI、SQLite Registry 与 CAS 的兼容门面。

本轮不只验证了“代码能编译”或“测试进程退出 0”。最终验收从 ohMyWorkPanel 的固定 Git commit 建立只读快照，实际经历参考实现通过、第一版生成代码失败、确定性 Gate 要求 ITERATE、Review 生成 Correction、知识局部修订、fresh 代码再生成、279/279 真实门禁通过、PASS 和原子发布。该链路证明受信源码的薄切片可以完成一次完整的失败—学习—再生成—独立执行—发布闭环。

结论分级如下：

| 能力 | 最终判断 | 证据 |
|---|---|---|
| 单一本地知识 Registry/CAS | 已实现 | SQLite/CAS Adapter、迁移和集成测试 |
| endlessWpKnowledgeRunner 兼容 | 已实现 | Node 门面、真实 CLI 集成测试 |
| 候选知识与 Verified 发布隔离 | 已实现 | Quality Gate、EvaluationReport、Publication Gate |
| 固定 commit 真实源码 EvalRunner | 已实现，限受信源码 | ohMyWorkPanel 279/279 闭环 |
| 失败归因与增量知识修订 | 已实现于确定性场景 | Correction Schema、章节级字节约束、fresh CodeGen |
| 事务与幂等恢复 | 核心路径已实现 | checkpoint、原子评测、原子发布、精确重放 |
| 在线 GLM/DeepSeek 生成质量 | 未验证 | 当前 Agent Provider 为 Schema 校验的场景重放 |
| 敌对 C++ 安全执行 | 未实现 | 只有 Sandbox port；本地进程 Adapter 不是 OS 沙箱 |
| 多机调度、HA、完整 LangGraph | 未实现 | 仍为 Planned/Proposed |

## 从评审到合并的开发过程

### 阶段一：先修正规范，而不是直接重写

初始 PR 只有 P0-A Spec。可行性评审识别出四个 P0 风险：需求 ID 与旧规范冲突、缺少旧实现迁移策略、把应用层路径约束误当敌对代码沙箱、reference behavior 与正确行为的语义未定义。

后续把新需求改为 KF-SYS-* 命名空间，建立实现追踪矩阵，并明确：

- 文档质量合格只允许进入行为评测，不能自动成为 VERIFIED；
- Agent 输出必须通过 JSON Schema；
- 发布只能由确定性 Gate 决定；
- 未完成的真实模型、C++ 沙箱和调度能力继续标为 Planned 或 Partial；
- 所有“已实现”结论必须有代码和可执行测试共同支撑。

### 阶段二：以 Strangler 方式替换旧 runner

提交 af7e718 建立 TypeScript 六边形核心，并删除旧 Python 目录状态机、自制 YAML 子集解析、shell DSH 桥、未认证写路径和“文档分数即 verified”语义。旧 OKF 数据只能迁移为 CANDIDATE，不能继承历史 verified 权限。

endlessWpKnowledgeRunner 最终没有被彻底删除，而是重构成兼容门面：

- init、ingest、query、get、status、scan、feedback 委派给 apps/runner/src/cli.ts；
- 共用 WP_FLYWHEEL_HOME、SQLite 和 CAS；
- get --name 使用精确 module lookup，不退化为 BM25 top-1；
- --json、--force-draft、--no-feedback 等不影响新语义的旧参数被安全忽略；
- --root 被拒绝，避免调用方创建第二套 Registry；
- score、eval、harvest 明确返回 retired，避免旧的启发式评分或 timer 重新成为主路径。

### 阶段三：把独立执行从“申报结果”升级为真实 EvalRunner

提交 dc71ac7 增加 ProjectEvaluator 端口、TrustedProjectEvaluator、SchemaValidatedScenarioAgent 和固定场景的两轮应用流。执行器：

- 只接受完整 40 位固定 commit；
- 使用 git archive 解出一次性快照，不 checkout 或覆盖源码仓库；
- 生成文件只能落在允许目标，拒绝路径逃逸和符号链接目标；
- 只允许运行 node、pnpm、cargo；
- shell=false，使用清理后的环境；
- 记录工具版本、argv、退出码、耗时、超时、输出上限和脱敏输出；
- 取消或超时时终止进程树；
- 将 manifest、命令结果和完整报告写入 CAS。

应用流为：

~~~text
固定 commit 参考门
        │ 1/1
        ▼
DocGen v1 ──> CodeGen v1 ──> EvalRunner 0/1
                                  │
                                  ▼
                         Gate = ITERATE
                                  │
                                  ▼
Review Correction ──> 只改指定知识章节
                                  │
                                  ▼
                         fresh CodeGen v2
                                  │
                                  ▼
                 EvalRunner 279/279 ──> PASS
                                  │
                                  ▼
                     REVIEWING ──> PUBLISHING
                                  │
                                  ▼
                    原子发布 VERIFIED + receipt
~~~

### 阶段四：依据 Cursor 意见补齐边界失败

Cursor Bugbot 两轮共提出 6 个可执行问题，全部修复并在原讨论中回复：

| 问题 | 严重度 | 修复 |
|---|---:|---|
| PASS 后发布跳过 REVIEWING，合法状态机路径会失败 | High | recordEvaluation 负责进入 REVIEWING，publish 再进入 PUBLISHING |
| legacy get --name 返回搜索命中而不是命名卡正文 | Medium | CLI 增加精确 module lookup，兼容门面直接映射 |
| legacy query 的 --no-feedback 被错误拒绝 | Medium | 作为无副作用兼容参数安全忽略 |
| Unix HOME 被清理，pnpm 等工具可能找不到用户目录 | Medium | 同时保留 HOME 与 USERPROFILE，仍清理敏感变量 |
| Evaluation、Gate decision 与 REVIEWING 分两个事务 | Medium | 合并为一个 SQLite 事务并增加回滚测试 |
| git show 继承 GIT_DIR 等变量，可能与 commit 解析指向不同仓库 | Medium | 所有 Git probe 统一使用清理环境 |

第二轮“响应丢失后调用方拿不到 decisionId”的剩余风险又在 c80d1fc 中补齐：

- 若 run 已在 REVIEWING，完全相同的 EvaluationInput 返回原 report 与原 decisionId；
- 不追加 GateDecided 或 RunStateChanged 事件；
- 任一输入字段变化都以 evaluation replay input collision 失败；
- 自动化测试同时验证稳定 decisionId、事件列表不变和冲突拒绝。

最终 Cursor 重跑没有产生新代码意见。Bugbot、Approval 和 Security 检查因为 Cursor 账户 usage/hard limit 跳过；其中 Approval/Security 明确要求距离 hard limit 至少保留 2 美元。这个外部额度限制不能解释为代码通过，但此前实际产生的 6 条意见均已有对应代码、测试和回复。

## 最终代码架构

### 依赖方向

~~~text
CLI / HTTP / Dashboard / DSH / legacy facade
                    │
                    ▼
            Application services
        ingest / query / evaluate / publish
        checkpoint / real-source project flow
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       Domain                Ports
 state machine / Gate    ArtifactStore
 ArtifactRef / events    Repository
                         AgentProvider
                         ProjectEvaluator
                         Sandbox / LanguagePlugin
                              ▲
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        SQLite + CAS    Scenario Agent    Trusted Project Eval
        Legacy OKF      JSON Schema       git archive + processes
        Source Scan
~~~

packages/domain 不导入数据库、SDK、编译器或语言类型；packages/application 只依赖 domain 和 contracts；具体实现位于 packages/adapters。tests/contract/architecture.test.ts 自动约束这一方向。

### 领域和持久化语义

1. Markdown 正文先进入内容寻址存储，Artifact ID 必须等于 sha256 digest。
2. Registry 创建 CANDIDATE，记录 provenance、parent version 和 Quality Gate。
3. Run 按单调状态机推进；非法跳转失败。
4. EvaluationReport 绑定输入工件、执行证据、工具链指纹和测试计数。
5. Evaluation、GateDecision、REVIEWING 状态和两个事件在同一事务提交。
6. Gate 只输出 PASS、ITERATE、ROLLBACK 或 STOPPED。
7. 发布再次校验证据和正文完整性，并在一个 SQLite 事务内 supersede 旧版本、验证新版本、更新 run、追加事件和写 publication receipt。
8. GenerationKey 和 publication key 支持安全重放；并发重复 side effect fail closed。

SQLite 使用 WAL 和 synchronous=FULL。CAS 采用临时文件、flush、原子 rename 和提交后校验。事件顺序由 event_seq 保证，不依赖可能相同的时间戳。

### 接口和信任边界

- HTTP GET 与 Dashboard 为只读路径。
- 未配置 WP_KNOWLEDGE_WRITE_TOKEN 时写 API 返回 503；配置后要求 Bearer token。
- DSH Adapter 只调用版本化 /api/v1，不启动 Python 或 shell，也不能发布知识。
- source scan 根目录由配置固定，调用方不能请求任意路径。
- TrustedProjectEvaluator 只用于同组织受信源码。它减少误操作风险，但子进程仍共享宿主内核。
- 未通过 OS 级逃逸、网络、文件系统和资源测试前，不可信 C++ 必须 fail closed。

## 全项目测评

### 自动化门禁

| 门禁 | 最终结果 | 含义 |
|---|---:|---|
| npm run typecheck | PASS | TypeScript 7 无类型错误 |
| npm run validate:specs | PASS | schemas=7，commands=7，results=8，P0=28 |
| npm test | 34/34 PASS | unit、contract、integration、acceptance 全部通过 |
| git diff --check | PASS | 无空白错误 |
| npm audit --omit=dev --audit-level=high | 0 vulnerabilities | 使用 npm 官方 registry 复验 |

34 项自动化测试覆盖：

- 状态机、确定性 Gate、ArtifactRef 哈希绑定；
- CAS 去重与损坏检测；
- SQLite 事务、事件顺序、checkpoint claim/commit/fail/retry；
- 评测写入失败时 report、decision、状态和事件整体回滚；
- 响应丢失后的评测精确重放；
- 发布幂等和失败 Gate 禁止发布；
- legacy migration、compat facade、source scan；
- HTTP 写权限、DSH 无 shell 边界；
- Scenario Agent Schema 拒绝；
- 生成路径逃逸拒绝和敏感 argv 脱敏；
- 最小真实源码 fixture 的两轮闭环。

### ohMyWorkPanel 固定 commit 真实验收

最终 fresh 运行：

- runId：fad0b5ff-cfb7-4943-8f97-9b552099ab93
- 固定 commit：cfef082d7a9e5d434777374bd6b99ef8cd309cfc
- 当前 checkout HEAD：b1af2659aea5068643729ee995bb944bf27b7a37
- 当前 checkout dirty：true，属于另一 Agent 的用户改动，验收前后未改变
- 参考实现：1/1
- 第一版生成实现：0/1，Gate=ITERATE
- 最终生成实现：279/279，Gate=PASS，status=VERIFIED
- 最终知识版本：kv_08b9f7eec15a280cf70f3bf4
- Gate decision：205647bd-8838-4656-8e25-1bcafdf1123d
- publication key：ohmyworkpanel-mentions:kv_08b9f7eec15a280cf70f3bf4:local-v1

279 个门禁计数由以下结果聚合：

- 定向 Vitest 连续 5 次；
- 完整前端测试 123 项；
- 生产构建 1 次；
- Rust library 测试 150 项。

关键工具版本：

| 工具 | 版本 |
|---|---|
| Node.js | v24.11.1 |
| Git | 2.47.1.windows.2 |
| tar | bsdtar 3.5.2 |
| pnpm | 11.7.0 |
| cargo | 1.94.1 |
| rustc | 1.94.1 |

完整 CAS 索引、命令输出摘要和证据边界见 [ohMyWorkPanel 固定 commit 真实源码闭环验收](../notes/2026-09-01-ohmyworkpanel-real-source-e2e.md)。

## Spec 可维护性评估

本轮采用“规范先定义可声称能力，再用实现和测试提升状态”的方式，而不是在报告中把规划当成完成：

- KF-SYS-016 / AC-COMPAT-001 明确 legacy facade 的唯一 Registry 语义；
- KF-SYS-017 / AC-E2E-001 明确固定 commit 两轮真实源码验收；
- NFR-011 要求记录来源 checkout 与固定 commit、证据工件及“不修改原仓库”；
- 追踪矩阵逐项标注 Implemented、Partial、Planned；
- 7 个 JSON Schema 约束 ArtifactRef、Agent command/result、Correction、EvaluationReport、event 和 language plugin；
- 架构、运维命令、测试与正式证据报告互相链接。

维护性上的主要收益是：新贡献者可以从 requirement → acceptance → implementation → automated test → real evidence 逐层定位，不需要依靠聊天记录推断系统到底承诺了什么。

## 未完成能力与后续建议

### P0：安全和真实性

1. 为敌对生成代码实现真正的 OS/VM 隔离，并加入文件、网络、子进程、资源耗尽和逃逸测试。
2. 接入真实 GLM/DeepSeek AgentProvider，记录模型版本、prompt、Schema 失败率、成本和多次运行稳定性。
3. 定义 reference bug 双轨：观测等价默认路径与人工批准的契约修复路径。

### P1：恢复和运营

1. 为长时间 RUNNING checkpoint 增加 lease、owner、heartbeat 和 crash reclaim。
2. 增加 CAS 孤儿对象审计与 GC。
3. 将 HTTP token 边界升级为主体/资源/动作授权，并补全审计脱敏。
4. 只有在跨机器、长任务或高可用需求达到量化阈值时，再引入 LangGraph/Temporal 调度复杂度。

### P2：扩展

1. 真实实现第二种 LanguagePlugin 后再固化通用插件协议。
2. 对实际消费者验证 MCP/ACP/A2A，而不是先扩展核心。
3. 为真实项目场景建立可更新但必须显式 review 的固定 commit corpus。

## 证据来源

### 仓库与 PR

- [PR #11](https://github.com/linlisWorkTeam/wpKnowledge/pull/11)
- [merge commit 29612b0](https://github.com/linlisWorkTeam/wpKnowledge/commit/29612b078978fba7dd1681229a6931d97185c652)
- 本地最终源码：D:/AI/wpKnowledge-pr11，tree 5b512f8cf806d3889971b4424d38992bd7911fdf
- 规范：specs/
- 架构：docs/ARCHITECTURE.md
- 运维：docs/OPERATIONS.md
- 真实场景：acceptance/ohmyworkpanel/
- 自动化测试：tests/

### Cursor 审查

- [Publish path skips required REVIEWING](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590745)
- [Legacy get returns search hits](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590763)
- [Legacy query rejects no-feedback](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590774)
- [HOME environment compatibility](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896590789)
- [Evaluation save and transition split](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896735524)
- [Inspect Git env is inconsistent](https://github.com/linlisWorkTeam/wpKnowledge/pull/11#discussion_r3896735530)

## 证据边界

- 279/279 是多条门禁命令的聚合计数，生产构建按一次成功计数，不代表 279 个互不重叠测试。
- Scenario Agent 是确定性、Schema 校验的场景重放，只证明契约和编排，不证明在线模型质量。
- TrustedProjectEvaluator 不是敌对代码沙箱；本报告不能证明不可信 C++ 安全。
- ohMyWorkPanel 当前 checkout 的未提交改动没有进入固定 commit 快照，也不属于本交付。
- CAS 证据保存在本机忽略目录；其他机器复验会产生新 runId、时间戳和报告哈希。
- Cursor 最终检查因外部额度限制跳过，因此只能确认“所有实际产生的意见均已修复”，不能声称最后一个 head 得到了新的 Cursor Approval/Security 结论。
- Git Smart HTTP 在最终同步期间发生连接 reset；远端提交通过 GitHub Git Data API 创建，并在更新分支和合并后逐次验证 tree SHA 与本地已测 tree 完全一致。
