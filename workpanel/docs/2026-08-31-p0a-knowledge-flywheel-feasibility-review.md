# P0-A Knowledge Flywheel MR 可行性评审

## 元数据

- 日期：2026-08-31
- 研究对象：[linlisWorkTeam/wpKnowledge PR #11](https://github.com/linlisWorkTeam/wpKnowledge/pull/11)
- PR 基线：`6999099f2d7ffb1f37aca743674f325072fe39fd`
- PR 评审头：`aa7592a67ba913de717d419ea66efa8d43a3fafc`
- PR 规模：38 个新增文件，约 1,367 行，全部位于新目录 `specs/`
- 评审性质：规范、架构、实现现状和关键依赖的可行性评估；不包含合入操作

## 执行结论

这个 MR 准备把“知识飞轮”定义为一条可审计的多 Agent 软件再生成流水线：从参考实现生成候选知识和测试，用知识重新生成代码，再通过独立评测、确定性发布门禁和增量纠错，最终发布“经过真实执行验证的知识”。它还为首个版本选择了 TypeScript 六边形架构、LangGraph + SQLite 检查点、本地内容寻址存储、最多 5 个本地 Worker、C++ 语言插件，以及 DeepSeek Harness/GLM 的适配层。

产品思想可行，而且仓库中现有的 Python `mvp-flywheel/` 已经证明“知识 → 代码 → 编译测试 → 纠错/回滚”最小闭环可以成立。但当前 MR 只交付规范和 JSON Schema，没有实现 P0-B 技术尖峰，也没有解释如何继承现有两套飞轮代码。它不适合以 `Accepted`、新单一事实源的状态直接合入；建议先改为提案状态并解决下面四个 P0 阻塞项。

| 评估对象 | 判断 | 说明 |
| --- | --- | --- |
| 单机、单语言、单进程 PoC | 高可行 | 现有 Python MVP 已有真实循环；LangGraph SQLite 适合本地实验 |
| 单机 C++ V1 | 中等可行 | 编译、测试、CAS 和确定性门禁可做；不可信代码隔离与工具链复现仍未证明 |
| 生产级“Verified Knowledge”发布 | 中低可行 | 需要解决语义 oracle、原子发布、审计完整性、模型不稳定性和沙箱安全边界 |
| 当前 MR 直接作为 Accepted 架构合入 | 不建议 | 规范冲突、迁移缺失、关键技术尖峰未完成，且验证脚本不验证系统行为 |

## MR 准备做什么

### 1. 建立知识飞轮状态机

主流程在 `specs/05-workflows/knowledge-flywheel-workflow.md` 中定义为：

1. 固化参考源码、公开接口和测试输入快照。
2. DocGen/DocWorker 并行生成候选知识，TestGen 生成测试资产。
3. CodeAgent 只能读取候选知识和公开接口，不能读取参考源码或私有评测集。
4. Check/Eval 编译、运行、比较参考实现与再生成实现。
5. 确定性 Gate 根据固定指标决定通过、继续修订、回滚或停止。
6. Review/Correction 把失败归因到知识、代码、测试、基础设施或置信度。
7. 只增量修改知识，然后从干净工作区重新生成代码，直至发布或达到迭代上限。

这不是普通 RAG 或文档生成，而是在尝试把知识当作“能够重建并验证软件行为的中间表示”。

### 2. 用职责与权限隔离减少自证偏差

MR 把生成者、执行者、评测者和发布者拆开，并通过 `specs/09-security/data-boundaries.md` 约束 Agent 能读取哪些工件。核心意图是防止 CodeAgent 偷看参考实现、防止 TestGen 泄漏私有评测，以及防止 LLM 自己决定是否发布。

### 3. 引入持久化、幂等和可追溯性

MR 定义了不可变 `ArtifactRef`、事件、检查点、恢复协议、需求追踪矩阵和 JSON Schema。目标是让每一次生成、执行、评分和发布都可重放、可审计、可恢复。

### 4. 为后续扩展保留适配层

首版聚焦 C++，但使用 Language Plugin 隔离语言细节；用 AgentProvider 隔离 DeepSeek Harness/GLM；ADR-005 还预留 MCP、ACP、A2A 边界。方向上是避免核心领域依赖某个模型或 Agent 框架。

## 做得好的地方

1. **确定性门禁与 LLM 分离。** LLM 生成候选物和解释，最终发布由固定阈值、Core Gate、重复运行和结构化证据决定，这是系统可信度的基础。
2. **权限模型抓住了核心风险。** CodeAgent 不得读取参考源码和私有评测集，能显著降低“复制答案”和评测污染。
3. **不可变工件与 checkpoint 思路正确。** 对长链路、多 Agent、可重试任务，内容哈希、幂等键和阶段性提交比只保存对话记录更可靠。
4. **失败是显式状态。** `LOW_CONFIDENCE`、迭代上限、回滚和停止条件避免无限 Agent 循环。
5. **语言和 Agent 适配器方向正确。** DeepSeek Harness 当前仍处于 developer preview，官方明确警告兼容性破坏，因此适配层和版本锁定是必要的，而不是过度设计。

## P0 阻塞项

### P0-1：仓库出现两个“单一事实源”，且需求 ID 被复用

`specs/README.md` 声称新 `specs/` 是 Accepted P0-A 的单一事实源，并要求需求 ID 永不复用；但现有 `mvp-flywheel/docs/README.md` 已声明其 SDD 文档具有规范性，`mvp-flywheel/docs/01-需求规格.md` 也已使用 `SYS-001` 至 `SYS-006`，含义与新规范不同。

例如，现有 `SYS-003` 明确 P0 从已有知识开始、知识生成不应是必经路径；新 MR 的主流程却把 DocGen/TestGen 放在起点。合入后，相同 ID 会指向不同需求，追踪矩阵和审计将失去可信度。

建议：在合入前建立仓库级规范索引，选择一个权威源；新需求使用新命名空间（例如 `KF-SYS-*`），或者提供旧 ID 到新 ID 的正式迁移表。新文档在完成评审前应标为 `Proposed`，不能标为 `Accepted`。

### P0-2：规划了第三套平台，但没有迁移或复用策略

仓库已有：

- `mvp-flywheel/`：Python 实现的知识到代码、编译测试、holdout、修订和发布闭环；
- `endlessWpKnowledgeRunner/`：Python/JavaScript、DeepSeek Harness 集成、知识摄取/评分/检索/看板；
- 本 MR：新的 TypeScript + LangGraph + SQLite + C++ Plugin 平台。

ADR-001/002 已直接接受 TypeScript 和 LangGraph，但“LangGraph 与 Temporal 对比”“DSH 适配器”“本地 CAS”“C++ 沙箱”又被放在后续 P0-B 尖峰。这使 ADR 的证据顺序倒置，也无法回答现有 Python 代码是迁移、包装、复用还是废弃。

建议：先形成组件盘点和迁移 ADR。优先把现有 Python MVP 的确定性评测、决策逻辑和测试夹具抽成可调用内核；只有在尖峰证明维护成本或可靠性明显更优后，才批准重写。LangGraph/Temporal 选择应在故障注入数据出来后从 `Proposed` 升级为 `Accepted`。

### P0-3：当前“沙箱”不是运行不可信 C++ 的安全边界

现有 `mvp-flywheel/fw/sandbox.py` 只是对通过该 Python API 的路径访问做 allowlist/denylist 检查。生成的 C++ 二进制仍可能直接访问文件、网络、注册表、子进程或消耗系统资源，绕过应用层路径检查。

Windows Job Object 能管理进程树、CPU/内存/运行时间并统一终止，但 Microsoft 文档明确说明安全限制需要逐进程设置，因此 Job Object 本身不是完整安全沙箱。[Win32 App Isolation/AppContainer](https://learn.microsoft.com/en-us/windows/security/book/application-security-application-isolation) 提供更强应用边界；对于敌对代码，[Microsoft 的容器安全说明](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/container-security) 把 Hyper-V 隔离视为更强的安全边界，普通进程隔离不适合敌对多租户场景。

建议：把 V1 威胁模型写清。若代码只来自受信团队，可采用独立低权限账户/AppContainer + Job Object + 网络禁用 + 临时只读输入和一次性输出目录；若代码视为敌对输入，应使用 Hyper-V 隔离容器、专用 VM 或成熟的远程沙箱。沙箱尖峰必须包含逃逸、资源耗尽、子进程、符号链接/联接点、网络和残留进程测试。

### P0-4：参考行为与“正确行为”的语义没有定义

当前设计把参考实现的真实运行结果作为 oracle。这能验证行为等价，但会把参考实现中的 bug 也固化成“正确知识”。仓库现有 MVP 文档已经记录过：模型生成了更防御性的实现，而评测因未覆盖参考实现崩溃输入而接受它。

需要先选择并编码策略：

- **观测等价模式**：严格复制参考行为，包括已知缺陷；
- **契约正确模式**：以公开接口、需求和人工批准的修复为准，允许偏离参考实现；
- **双轨模式（推荐）**：默认观测等价；遇到差异时生成 `REFERENCE_BUG_CANDIDATE`，只有人工批准并增加回归契约后，才能升级 oracle。

否则门禁可能拒绝正确修复，也可能把未知缺陷发布为 Verified Knowledge。

## 其他高风险项

### 1. LangGraph 恢复不等于外部副作用 exactly-once

[LangGraph 的持久化文档](https://docs.langchain.com/oss/javascript/langgraph/persistence)证明它适合保存图状态、从成功的 super-step 恢复，也说明 SQLite checkpointer 适合实验和本地工作流。但[官方 Functional API 文档](https://docs.langchain.com/oss/javascript/langgraph/functional-api)明确要求把 API/文件等副作用放入 task，并设计为幂等，因为任务开始后崩溃仍可能重执行。

所以 `artifact write → event append → checkpoint → publish pointer` 不能仅依赖 LangGraph。建议用同一 SQLite 事务提交元数据、事件和发布指针，以内容哈希作为幂等键；CAS 文件先写临时名、校验哈希、原子 rename，再提交数据库引用，并配置孤儿对象 GC。

### 2. Temporal 更耐久，但本地 V1 不一定值得引入

[Temporal Event History](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/workflow/workflow-execution/event.mdx)提供持久事件历史和崩溃恢复，[Retry Policy](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/retry-policies.mdx)为 Activity 提供默认重试，并强制 Workflow 确定性。它在跨进程、长时间运行和运维可见性方面更成熟，但会引入服务端、Worker、版本化和运维成本。

对“本地单进程、最多 5 个 Worker”的 P0，LangGraph + 自有事务/outbox 足够；只有出现跨机器、长期任务、复杂补偿或高可用需求时，Temporal 才更有优势。ADR-002 应把这个边界写成可复验的升级条件。

### 3. DSH 可接入，但不能成为未经隔离的核心依赖

[DeepSeek Harness 官方仓库](https://github.com/deepseek-ai/deepseek-harness)说明当前是 developer preview，兼容性破坏是预期行为。本地源码 `D:\AI\deepseek-harness\deepseek-harness`（commit `b150a551b8d465e31e418e1b2eaf5e79bbb7d28e`）显示它已有：

- 一次性 headless Agent，持久化 Session 后输出最终答案；
- 每次运行启动完整子 Harness 的 JSON-RPC SDK Provider；
- 本地工具、工作流、子 Agent，以及 E2B 组合 PoC。

但其 `subagent-dsh-sdk` 文档也明确写着：父进程当前不能强制 `outputSchema`、工具过滤、persona 或深度限制；每个子 Agent 启动完整进程，且只支持本地 cwd。MR 的安全矩阵不能只靠提示词或子 Agent 自己的 `cordis.yml` 实现。

建议：AgentProvider 固定 DSH commit/RC 版本，做契约测试；权限在宿主进程和 OS 沙箱层强制执行；结构化输出由宿主用 Schema 验证，失败时拒绝提交工件。

### 4. Schema 验证仍只是规范一致性检查

MR 的 validator 能检查 7 个 Schema 的语法、元 Schema、交叉引用、角色 fixture、链接和 P0 追踪，运行结果为 `SPEC_VALIDATION_OK schemas=7 commands=7 results=8 p0=25`。这是好基础，但不能证明 LangGraph 恢复、CAS 原子性、DSH 适配器、C++ 隔离或门禁执行正确。

另外 `language-plugin.schema.json`、`event.schema.json` 的 payload 仍较开放，分数组件没有充分的跨字段不变量。建议增加 `additionalProperties: false`/判别联合、工件 ID 与内容哈希绑定、分数组件总和、attempt 唯一性、状态迁移合法性和发布指针单调性测试。

## 当前实现验证

在隔离的 Python 3.13 虚拟环境中执行现有 `mvp-flywheel/tests`：

- 68 项通过；
- 19 项失败；
- 19 项失败均由当前机器没有 `gcc/g++/clang/clang++/cl` 引起，执行结果为 `compiler unavailable: [WinError 2]`；
- 系统 Python 3.8 在收集阶段不支持 `Path | None`，说明实际最低版本至少是 Python 3.10，但仓库缺少足够明确、可自动检查的运行时约束。

这不能证明 19 项业务测试有代码缺陷，但证明文档中的 `87/87` 在当前环境不可复现，也证明工具链 preflight、跳过/阻塞语义和 CI 镜像需要成为正式交付物。

## `endlessWpKnowledgeRunner` 是否需要彻底重构

结论：如果它要成为新 MR 的编排核心，需要结构性重构；但不建议从零重写。它当前更准确的定位是“知识目录运营与检索子系统”，不是“知识到代码再生成并进行行为验证的飞轮”。

当前实现的主闭环是 `获取 → OKF 卡片 → 文档质量打分 → verified/draft → BM25 检索 → 使用反馈`。其评分主要验证溯源、结构、时效、去重、可验证锚点和使用反馈；文档也明确把“知识 → 代码还原”列为未来的强评测环。因此它不能直接承担新规范中的 CodeAgent、真实执行 oracle、Core Gate、行为等价、checkpoint 恢复和确定性发布语义。

### 应保留并迁移

- OKF 卡片、来源锚点和知识目录边界；
- 确定性文档质量信号，但降级为候选知识的 Quality Gate，而不是 Verified Knowledge Publication Gate；
- verified 版本保护、history、反馈 ledger 和 BM25/质量重排；
- source scan、CLI fixture 和当前 18 项通过的回归测试；
- Dashboard 的读模型和知识检索交互。

### 应重构

- `目录位置 + frontmatter` 状态机改为显式领域状态、事件和 ArtifactRef；
- 无事务/无锁文件写入改为 CAS + SQLite 元数据事务、幂等键和原子 publish pointer；
- DSH 插件通过 shell 启动 Python CLI 的方式改为有版本的 AgentProvider/KnowledgeService 契约；
- harvester timer 改为可恢复、可取消、可重试的 workflow job；
- Dashboard 直接加载并调用 Store/Scorer 改为只读 API/read model，写操作经过应用服务和权限校验；
- 文档质量门禁与代码行为门禁分离，禁止仅凭文档分数自动发布“Verified Knowledge”；
- JSON 配置增加版本化 Schema，状态迁移、评分解释和发布规则成为可测试契约。

### 应删除或退出主路径

- 自制 YAML 子集解析器，替换为受维护且严格校验的格式实现；
- 依赖人工 `cordis_define` 的动态插件源码复制流程；
- 把同一个确定性评分函数重复执行多次并将零方差解释为统计置信度；
- 未认证的内嵌 HTTP 写接口；
- 已提交的 `__pycache__`/`.pyc` 产物；
- 仅凭启发式文档评分写入 `verified` 的语义。

### 推荐迁移方式

采用 Strangler Pattern，而不是 big-bang rewrite：

1. 冻结当前 CLI、知识卡和检索行为，以 18 项现有测试加 golden fixtures 建立兼容基线。
2. 在旧实现外增加 `KnowledgeCatalog`、`ArtifactStore`、`QualityGate`、`Retriever` 等接口；先由旧模块实现。
3. 让新飞轮通过适配器调用这些接口，把代码行为评测和 Publication Gate 放在新核心中。
4. 逐步把存储迁到 CAS + SQLite，并做双读/双写结果比较；确认等价后再切换。
5. 最后移除 shell CLI 桥接和动态 DSH 插件；只有在回归、数据迁移、回滚演练都通过后，才删除旧实现。

建议同时把模块重命名为更准确的 `knowledge-catalog` 或 `knowledge-operations`，避免继续把它误认为整个 Knowledge Flywheel。

## 推荐实施路线

### Phase 0：先让规范可以合入

1. 把所有新 ADR 和 `specs/` 状态改为 `Proposed`。
2. 修复 SYS ID 冲突，建立旧规范、新规范和实现的迁移映射。
3. 明确选择“扩展现有 Python MVP”还是“TypeScript 重写”，列出复用/废弃成本。
4. 定义 oracle 的双轨语义和人工批准点。
5. 删除或延后没有需求和验收追踪的 MCP/ACP/A2A 扩展项。

### Phase 1：五个可执行尖峰

每个尖峰必须提交代码、故障注入测试和可复现记录：

1. DSH headless Provider：进程崩溃、超时、取消、非法结构化输出和版本变化。
2. LangGraph：节点完成前后崩溃、并行节点、重复恢复、幂等副作用。
3. CAS + SQLite：断电窗口、原子 publish、哈希冲突、孤儿清理。
4. C++ sandbox：进程树、CPU/内存/时间、文件/网络、残留进程和逃逸测试。
5. 端到端薄切片：一个固定 C++ fixture 完成两轮修订、恢复和发布。

### Phase 2：有限 V1

只支持本地、单语言、单租户、受信代码来源；最多 5 个 Worker；禁止远程 Agent 和多租户。发布门禁必须同时满足 Core Gate、重复执行稳定、权限审计清洁、无未处理的 reference bug candidate。

### Phase 3：有证据再扩展

当任务持续时间、跨机器调度、恢复频率或运维成本达到已定义阈值时，再评估 Temporal；当第二种语言真正进入路线图时，再固化通用 Language Plugin；当跨 Agent 协议有明确消费者时，再接受 MCP/ACP/A2A ADR。

## 合入建议

当前建议：**Request changes，不合入**。

允许转为可合入的最低条件：

1. 解决规范权威性和需求 ID 冲突；
2. 提交现有实现到新架构的迁移/复用 ADR；
3. 把未验证的技术决策降级为 `Proposed`；
4. 定义 reference bug/oracle 策略；
5. 至少完成 DSH、恢复幂等、CAS 原子发布和 C++ 隔离四个尖峰的可执行验收。

## 证据来源

### 本地源码

- `wpKnowledge` 基线仓库：`C:\Users\Windows11\Documents\Codex\2026-08-31\prior-conversation-with-codex-conversation-role\work\wpKnowledge-pr11`；基线 commit `6999099f2d7ffb1f37aca743674f325072fe39fd`，PR head tree 与远端 `aa7592a67ba913de717d419ea66efa8d43a3fafc` 一致。
- 新 MR：`specs/README.md`、`specs/01-requirements/`、`specs/02-architecture/`、`specs/05-workflows/`、`specs/08-evaluation/`、`specs/09-security/`、`specs/10-acceptance/`、`specs/adr/`、`specs/schemas/`。
- 现有 MVP：`mvp-flywheel/docs/`、`mvp-flywheel/fw/runner.py`、`mvp-flywheel/fw/config.py`、`mvp-flywheel/fw/sandbox.py`、`mvp-flywheel/tests/`。
- 现有 DSH Runner：`endlessWpKnowledgeRunner/`。
- DeepSeek Harness：`D:\AI\deepseek-harness\deepseek-harness`，commit `b150a551b8d465e31e418e1b2eaf5e79bbb7d28e`。

### 外部官方资料

- [LangGraph Persistence](https://docs.langchain.com/oss/javascript/langgraph/persistence)
- [LangGraph Functional API：idempotency 与 side effects](https://docs.langchain.com/oss/javascript/langgraph/functional-api)
- [Temporal Event History](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/workflow/workflow-execution/event.mdx)
- [Temporal Retry Policies](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/retry-policies.mdx)
- [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [Microsoft Windows Container Isolation Modes](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/hyperv-container)
- [Microsoft Secure Windows Containers](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/container-security)
- [DeepSeek Harness 官方仓库](https://github.com/deepseek-ai/deepseek-harness)

## 证据边界

- MR 本身没有平台实现，因此本评审不能验证实际吞吐、模型质量、成本或生产可靠性。
- 没有可用 C/C++ 编译器，19 项编译相关测试只能判断为环境阻塞，不能据此判定业务逻辑失败。
- 未使用真实 GLM/DeepSeek 凭据执行完整飞轮，Agent 质量与 token 成本仍未知。
- 没有完成恶意代码逃逸测试，C++ 沙箱结论是基于现有代码边界和操作系统官方安全模型的风险判断。
- 时间与可行性判断以“本地单租户、最多 5 Worker、单语言 C++”为边界，不外推到多机、多租户或高可用生产系统。

## 实施更新：结构性替换结果

用户随后批准按上述边界重构。PR 分支上的实现提交 `db20813` 已完成对 `endlessWpKnowledgeRunner/` 主路径的结构性替换，而不是保留第三套平行运行时：

- 删除旧 Python 目录状态机、自制 YAML 解析、shell DSH 桥、内嵌 Dashboard 写路径和已跟踪的 `.pyc`；
- 建立 TypeScript 六边形边界：纯领域、应用服务、端口、SQLite/CAS 与 DSH/legacy/source-scan Adapter；
- 把旧卡片全部迁移为 `CANDIDATE`，旧 `verified` 不继承发布权限；
- 只有非空不可变证据、至少一项由本地受信评测调用方申报的测试、匹配 run 的策略和确定性 PASS 才能原子发布为 `VERIFIED`；核心尚不负责亲自执行编译与测试；
- GenerationKey 对已提交操作直接重放结果，对并发重复执行 fail closed，失败检查点留事件并可受控重试；
- Dashboard 和 DSH 使用 `/api/v1`，HTTP 写操作无 token 时禁用，有 token 时使用常量时间 bearer 比较；
- LangGraph/Temporal、真实 Agent Provider、GLM、oracle 双轨和敌对 C++ 沙箱仍标为 Proposed/Planned，不伪装成已实现能力。

复验结果：TypeScript 类型检查通过；规范校验为 `schemas=7 commands=7 results=8 p0=25`；27 项领域、契约、集成和验收测试全部通过；npm 官方生产依赖审计为 0 vulnerability；空运行时迁移首次 `imported=6, rejected=1, errors=[]`，复跑 `replayed=6`；真实浏览器中 `/api/v1` 四个请求均为 200，页面正确显示 6 个候选、0 个 VERIFIED，控制台 0 错误/0 警告。

这次落地解决了原评审中的规范 ID 冲突、迁移缺失、文档分数自动发布、无事务知识状态、shell DSH 桥和未认证写接口。它没有解决独立 EvalRunner、C++ 敌对执行、真实 Agent/GLM、reference bug oracle 和进程崩溃后 RUNNING lease 回收，因此当前结论从“仅规格、Request changes”更新为“可信本地核心已具备，可继续评审；生产级完整飞轮仍不可宣称完成”。按照用户要求，本轮只更新 PR，不执行合入。

## 实施更新：固定 commit 真实源码闭环

2026-09-01 的后续实现把 `endlessWpKnowledgeRunner` 恢复为只委派给新 TypeScript CLI 的兼容门面，并增加 `ProjectEvaluator` 端口及受信本地实现。固定 commit `cfef082d7a9e5d434777374bd6b99ef8cd309cfc` 的 ohMyWorkPanel 验收实际完成“参考实现 1/1 → 首版 0/1 与 `ITERATE` → Correction → 增量知识修订 → fresh 代码生成 → 最终 279/279 与 `PASS` → 原子发布”；原源码工作树在验收前已包含另一 Agent 的改动，验收前后 HEAD 与 dirty 状态保持不变，未被读取、覆盖或纳入固定 commit 快照。命令、工具链、run ID 与 CAS 工件见 [`../notes/2026-09-01-ohmyworkpanel-real-source-e2e.md`](../notes/2026-09-01-ohmyworkpanel-real-source-e2e.md)。

因此“独立 EvalRunner 尚未实现”的旧结论更新为：受信项目的固定快照执行评测已实现并有真实证据；真实 Agent/GLM、敌对代码 OS 隔离、reference bug 双轨审批和 RUNNING lease 回收仍未实现。该验收不能被解释为生产级不可信 C++ 沙箱或模型质量证明。
