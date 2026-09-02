# DeepSeek Harness 治理 ohMyWorkPanel：三次真实运行记录

<details lang="en">
<summary>English summary</summary>

On 2026-09-02, wpKnowledge ran three live governance exercises against the pinned ohMyWorkPanel commit. The legacy headless path completed a two-iteration quality loop (65 to 98) and passed 295/295 checks. The official DSH SDK path then exposed and preserved a fail-closed path violation. A clean isolated SDK run resumed after one malformed DocGen response and finished `VERIFIED / PASS`, with 1/1 deterministic behavior check, one publication, and 12/12 referenced artifacts verified. “Code role” means a fixed LangGraph responsibility executed by the configured provider; it is not a separately installed CodeAgent product or company CodeAgent CLI.

</details>

## 先说结论

这次打通的不是一条只在测试里成立的绿色路径。`wpKnowledge` 已经能够用内嵌 LangGraph 编排七类角色，通过 DeepSeek Harness 官方 SDK 调用 OpenCode Go / `deepseek-v4-flash`，把候选知识、代码生成、确定性评测、Review、Gate 和发布串成完整闭环。

这里容易混淆一个名字：图上的 `code` 是“代码生成角色”，不是另行安装的 CodeAgent 产品。它和 DocGen、TestGen、Check、Review 一样，由同一个 `DeepSeekHarnessSdkAgent` 执行，只是收到的基础提示词、可见文件和输出 Schema 不同。本次没有调用原 `domain-knowledge` 中面向公司环境的 `CompanyCodeAgentCliRunner`。

参考项目固定为 ohMyWorkPanel commit `3b2e6073e01b42e2a595fca4de3acaad44715ddd`，治理对象是 `src/chat/mentions.ts` 的 `@` 提及解析。密钥只在运行进程环境里出现，没有写入仓库、Prompt 审计或导出的 Demo 报告。

## 三次运行各自证明了什么

| 运行 | Provider 路径 | 结果 | 这次留下的证据 |
|---|---|---|---|
| Headless 兼容性样例 | 旧 `DeepSeekHarnessHeadlessAgent` | `VERIFIED / PASS` | 质量 65→98，第二轮通过 295/295 行为检查并发布 |
| SDK 隔离与失败样例 | 官方 stdio JSON-RPC SDK + 角色工作区 + Bubblewrap | Fail closed | 进入第 2 轮后，代码生成角色尝试输出未授权的 `src/chat/mentions.test.ts`，系统在评测前拒绝；0 次发布 |
| SDK 完整样例 | 官方 stdio JSON-RPC SDK + 角色工作区 + Bubblewrap | `VERIFIED / PASS` | DocGen 首次返回非 JSON，同一 Run 恢复；1/1 行为检查通过；唯一发布；12/12 工件完整 |

三次结果不能相互替代。Headless 样例证明了两轮质量反馈；失败样例证明路径白名单会真的拒绝越界输出；最后一次 SDK 样例证明官方传输、角色隔离、失败恢复、评测和发布可以在同一条真实路径上闭合。

## Demo A：Headless 两轮知识迭代

Run `2d9d785d-9737-4bfd-bf0b-dac411efba3d` 使用旧 Headless 兼容入口。第 0 轮候选知识只有正文，没有足够的结构和复现命令，Quality Gate 给出 65 分，并产生两条明确反馈：

- `structure: add explanation and explicit sections`
- `verifiability: add a reproducible command, metric, or evidence link`

图没有让低质量知识继续进入代码生成，而是自动回到下一轮 DocGen。第 1 轮知识得到 98 分，随后通过 295/295 行为检查并原子发布。

| 字段 | 值 |
|---|---|
| 最终状态 | `VERIFIED / PASS` |
| 最终轮次 | `1`（从 0 开始计数，共两轮） |
| 最终知识版本 | `kv_c700e868c87b221cd6437c95` |
| 最终知识质量 | `98/100` |
| 行为评测 | `295/295`，stability `1` |
| Registry Event | `72` |
| publication key | `ohmyworkpanel-mentions:kv_c700e868c87b221cd6437c95:local-v1` |

关键工件：

| 工件 | Artifact ID |
|---|---|
| 第 0 轮知识（质量 65） | `sha256:3b3626cb5462b9d8492d9f2ccf3fc75d86432e09e8d308adc456acb8c52d2675` |
| 第 1 轮知识（质量 98） | `sha256:c4887d767f03cbcfbeb8b79b2f1e839211221393f4a046a06c75628d455d4788` |
| 295/295 行为评测证据 | `sha256:c3b9f4d0906fe9d6ddc04a61e8b3690264b4cb34583c60e599f777f8307ea85e` |

这个样例仍保留，是为了兼容性和两轮质量反馈演示；它不再代表推荐的生产接法。

## Demo B：SDK 隔离路径的失败与拒绝

Run `4ffa31d0-3e91-4bfa-82a3-c221e5771481` 首次把官方 SDK、独立角色工作区和 Bubblewrap 放到一起。它经历了多次 JSON Schema 错误恢复，也跑到了第 2 轮，但最终停在 `evaluation`：代码生成角色除了允许的实现文件，还返回了 `src/chat/mentions.test.ts`。

系统没有删掉违规文件后继续，也没有绕过 Gate。动态输出 Schema 与应用层路径校验将其拒绝为 `PROJECT_PATH_DENIED`，所以本次运行没有 publication。

| 字段 | 值 |
|---|---|
| 最终业务状态 | `GENERATING`（保留失败现场） |
| 最后节点 | `evaluation`，`FAILED` |
| 最终轮次 | `2` |
| Agent 调用 | `28` |
| 节点投影 | `45` |
| Registry Event | `134` |
| 已生成知识版本 | `3`，均未发布 |
| 评测记录 | `2` |
| publication | `0` |
| 工件完整性 | `31/31` |

完整的脱敏快照在 [`演示素材/03-SDK失败恢复-脱敏报告.json`](演示素材/03-SDK失败恢复-脱敏报告.json)。报告只保留角色、状态、耗时、错误码、摘要和业务证据，不保存 Prompt 正文、模型输出日志、会话内容或凭据。

## Demo C：官方 SDK 完整闭环

Run `5503b6bc-0350-4b53-98cc-6fbf3a13aaa9` 从一个新的运行目录启动。DocGen 第一次调用返回了不能解析的内容，节点记录为 `FAILED / DSH_AGENT_OUTPUT_NOT_JSON`。随后用同一个 `runId` 恢复，已提交的 Orchestrator、DocWorker、TestGen 和 Oracle 副作用没有重复落库；DocGen 第二次成功，图继续完成代码生成、Check、Evaluation、Review 和 Publication。

| 字段 | 值 |
|---|---|
| Flywheel 状态 | `VERIFIED` |
| LangGraph 结果 | `COMPLETED / PASS` |
| 知识版本 | `kv_1355064c2116a4e2d072c93f` |
| 知识质量 | `96/100` |
| 行为评测 | `1/1`，stability `1`，critical failures `0` |
| Agent 调用 | `8`：7 次成功，1 次格式失败 |
| 节点投影 | `14` |
| Checkpoint | `10`，全部 `COMMITTED` |
| Registry Event | `46` |
| publication | `1` |
| 工件完整性 | `12/12` |

真实 Agent 调用耗时如下。这里的角色都由同一个 DSH SDK Provider 执行，并不是七个不同的 Agent 产品。

| 角色 | 结果 | 耗时 |
|---|---|---:|
| orchestrator | 成功 | 35.761 秒 |
| doc-worker | 成功 | 22.251 秒 |
| test-gen | 成功 | 284.832 秒 |
| doc-gen（首次） | `DSH_AGENT_OUTPUT_NOT_JSON` | 64.550 秒 |
| doc-gen（恢复） | 成功 | 490.783 秒 |
| code（代码生成角色） | 成功 | 164.774 秒 |
| check | 成功 | 277.169 秒 |
| review | 成功 | 189.179 秒 |

关键业务证据：

| 工件 | ID |
|---|---|
| 知识正文 | `sha256:b1890c02ee8f4a26a159144f31fd2d2b575c03ee37c2867ebf2749de7de69551` |
| 代码生成角色输出 | `sha256:9adcd29a4dc9e05c1a217e933481faa3dc6ac49fbc6ef170c91294a771c38953` |
| 评测证据 | `sha256:a4f7456b9a5682610f25c5de017357eacfff1086aabad399560fc69668099b9e` |
| Gate decision | `41be5fc5-e438-40fd-bd3d-657043d48d9e` |
| publication key | `ohmyworkpanel-mentions:kv_1355064c2116a4e2d072c93f:local-v1` |

可视化和完整脱敏报告：

- [`演示素材/01-真实SDK运行-VERIFIED-深色.png`](演示素材/01-真实SDK运行-VERIFIED-深色.png)
- [`演示素材/02-Agent有限定制-浅色.png`](演示素材/02-Agent有限定制-浅色.png)
- [`演示素材/04-SDK成功运行-脱敏报告.json`](演示素材/04-SDK成功运行-脱敏报告.json)
- [`演示素材/05-项目官网-深色首页.png`](演示素材/05-项目官网-深色首页.png)
- [`演示素材/06-项目官网-真实演示区.png`](演示素材/06-项目官网-真实演示区.png)

## 端到端数据怎么走

```text
固定 commit 的 ohMyWorkPanel
  → SourceSnapshot + provenance
  → Orchestrator 形成当前轮计划
  → DocWorker 与 TestGen 并行
  → DocGen 生成候选知识
  → wpKnowledge Quality Gate
      ├─ 不合格：携带 weak points 进入下一轮，跳过代码生成
      └─ 合格：进入 code 角色节点
  → DSH 启动新的受限模型会话，只给候选知识和公开接口
  → 生成文件写入 CAS
  → Check 只读检查
  → TrustedProjectEvaluator 在独立副本中执行确定性命令
  → Review 根据 Eval + Check 给出 PASS 或可验证 Correction
  → wpKnowledge 确定性 Gate
      ├─ ITERATE：修知识后重新生成、重新评测
      └─ PASS：原子写 Publication，KnowledgeVersion 变为 VERIFIED
```

“重新生成”强调输入隔离和不沿用上一轮实现，不代表有一个名叫 Fresh 或 CodeAgent 的外部服务。

## 运行中遇到的问题，以及代码如何收口

1. **包管理器定位失败。** 隔离环境最初只看见 PATH 中的 `pnpm` 链接，执行器找不到真实脚本。现在先解析工具路径，再把必要运行文件带入受信评测环境。
2. **并行失败覆盖状态。** 一个并行分支失败后，较晚完成的兄弟节点曾把图状态写回 RUNNING。runtime 现在对并行结果做失败归一化，并有恢复测试。
3. **复用 DSH session 得到空结果。** 每次 Provider 尝试改用独立 session，Schema 重试也单独审计。
4. **模型输出不是合法 JSON。** Provider 对闭合 JSON Schema 做严格校验，只对 `DSH_AGENT_OUTPUT_NOT_JSON` 和 `AGENT_OUTPUT_INVALID` 执行有上限的重试；超时、取消、权限和路径错误不重试。
5. **代码角色越界生成测试文件。** `allowedGeneratedPaths` 现在直接进入动态 JSON Schema，应用层仍保留第二道重复路径和白名单校验。
6. **Check/Review 误把工作区里没有生成代码当成缺陷。** 生成文件实际存于 CAS，并以内联受信上下文提供。基础提示词已明确这一点，评测事实仍以 `EvaluationReport` 为准。
7. **角色隔离不等于敌对代码沙箱。** Bubblewrap 证明 code 角色的模型会话看不到参考源码；`TrustedProjectEvaluator` 仍只允许执行受信项目，不能据此运行任意不可信代码。

这些失败没有从报告中抹掉。它们解释了为什么系统需要 Checkpoint、幂等 GenerationKey、Schema、路径白名单和确定性 Gate。

## 公网 DSH 页面边界

本机当前将 DSH Web 临时绑定到公网 `43.156.129.189:80`，未携带连接 token 的本机和公网请求均返回 `401`。为避免长期进程持有模型凭据，这次恢复的 Web 进程没有注入 OpenCode Go 密钥，只承担 Harness 调试壳；真实模型调用能力由上面的 SDK Run 证据证明。这个入口没有 TLS、正式域名、反向代理、速率限制或生产级密钥轮换，因此不应作为长期服务。知识飞轮 Console 与 DSH 调试页面是两个产品面，前者读取 wpKnowledge Registry，后者只负责 Harness 运行时调试。

## 现在仍不能宣称什么

- 三次工程运行只能证明接线、边界和代表性恢复路径，不能证明模型质量、成本或时延已经稳定。
- SDK 成功样例只有一个行为命令（1/1）；Headless 样例的 295/295 可以补充覆盖证据，但不能代替在 SDK 隔离路径上的重复统计。
- 角色工作区和 Bubblewrap 已阻断参考源码读取，但完整 `AccessDenied` 业务事件还没有覆盖所有 Harness 工具调用。
- `TrustedProjectEvaluator` 不是敌对代码执行沙箱。没有资源限制和系统调用策略之前，只能运行明确受信的仓库与命令。
- 当前 DocWorker 只有一个分块；面向大仓库的语义分块、动态 fan-out 和合并冲突处理仍是后续能力。

## 复现入口

部署参数见 [`endlessWpKnowledgeRunner/deploy/deepseek-harness/README.md`](../../../endlessWpKnowledgeRunner/deploy/deepseek-harness/README.md)。推荐入口：

```bash
export OPENCODE_GO_API_KEY='<runtime-secret>'
export WP_FLYWHEEL_AGENT_PROVIDER=deepseek-harness
export WP_DSH_MODEL=deepseek-v4-flash
export WP_DSH_PROCESS_ISOLATION=bubblewrap
export WP_DSH_ALLOWED_ROOTS='/path/to/wpKnowledge:/path/to/ohMyWorkPanel'
npm run knowledge -- workflow-run \
  --repository /path/to/ohMyWorkPanel \
  --workers 1 \
  --max-iterations 3
```

导出脱敏证据：

```bash
npm run knowledge -- workflow-report --run '<run-id>' --output './demo-report.json'
```

密钥不要写进 `.env` 示例、PPT、Issue 或命令历史。复验时使用新的 runtime 目录，并记录失败率、Token、耗时、评测覆盖和最终 Gate 数据。
