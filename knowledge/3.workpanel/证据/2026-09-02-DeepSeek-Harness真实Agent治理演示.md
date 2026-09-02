# DeepSeek Harness 真实 Agent 治理 ohMyWorkPanel 演示

<details lang="en">
<summary>English summary</summary>

On 2026-09-02, the embedded LangGraph workflow governed the pinned ohMyWorkPanel commit with seven real Agent roles through DeepSeek Harness and OpenCode Go. The same run recovered from two implementation defects, turned a quality score of 65 into an automatic documentation iteration, produced a score-98 knowledge version, passed 295/295 deterministic checks, and published exactly one verified version. This is one successful engineering run, not yet a statistical model-quality or hostile-code isolation claim.

</details>

## 这次到底跑了什么

本次不是 Scenario fixture。`wpKnowledge` 通过进程型 `DeepSeekHarnessHeadlessAgent` 调用 DeepSeek Harness `0.1.2-alpha.4`，Provider 指向 OpenCode Go，模型为 `deepseek-v4-flash`。参考项目是本地只读检出的 ohMyWorkPanel，场景固定到 commit `3b2e6073e01b42e2a595fca4de3acaad44715ddd`，知识主题是 `src/chat/mentions.ts` 的 @ 提及解析。

运行时目录为本机忽略路径 `.workpanel/live-ohmyworkpanel-v2`。密钥只通过 `OPENCODE_GO_API_KEY` 注入进程环境；仓库、Agent 审计和本文均不保存密钥值。

最终 Run：

| 字段 | 值 |
|---|---|
| `runId` | `2d9d785d-9737-4bfd-bf0b-dac411efba3d` |
| Flywheel 状态 | `VERIFIED` |
| LangGraph 结果 | `COMPLETED / PASS` |
| 最终轮次 | `1` |
| 最终知识版本 | `kv_c700e868c87b221cd6437c95` |
| 知识质量 | `98/100` |
| 行为评测 | `295/295`，stability `1` |
| publication key | `ohmyworkpanel-mentions:kv_c700e868c87b221cd6437c95:local-v1` |

## 端到端时间线

第 0 轮由 Orchestrator 启动。DocWorker 与 TestGen 并行读取固定源码，Oracle 在仓库外快照中验证参考实现。DocGen 的第一次输出多带了一个 Schema 外字段，工作流停在 `doc_gen`。修正输出扫描和顶层键提示后，同一 `runId/thread_id` 从最近失败 Checkpoint 恢复，先前已完成的节点没有重新执行。

恢复后的候选知识可读性为 1，但没有 Markdown 二级标题，也没有可复现的验证命令。Quality Gate 给出 65 分，并返回两条具体 weak point：

- `structure: add explanation and explicit sections`
- `verifiability: add a reproducible command, metric, or evidence link`

工作流没有把低质量文档交给 CodeAgent。`candidate_knowledge → workflow_router → orchestrator` 自动进入第 1 轮，DocGen 收到上一版正文和质量反馈。第二版知识得到 98 分，随后 Code、Check、确定性 Evaluation、Review 和 Publication 依次完成。

| 轮次 | 节点 | Agent | 结果 | 约耗时 |
|---:|---|---|---|---:|
| 0 | orchestrator | Orchestrator | 完成 | 34 秒 |
| 0 | doc_worker | DocWorker | 完成 | 18 秒 |
| 0 | test_gen | TestGen | 完成 | 161 秒 |
| 0 | doc_gen | DocGen | 一次格式失败，恢复后完成 | 66 秒 + 249 秒 |
| 0 | candidate_knowledge | wpKnowledge Quality Gate | 65 分，进入知识迭代 | 立即判定 |
| 1 | orchestrator | Orchestrator | 完成 | 57 秒 |
| 1 | doc_worker | DocWorker | 完成 | 39 秒 |
| 1 | test_gen | TestGen | 完成 | 130 秒 |
| 1 | doc_gen | DocGen | 完成，质量 98 分 | 98 秒 |
| 1 | code | CodeAgent | 完成 | 245 秒 |
| 1 | check | CheckAgent | 完成 | 150 秒 |
| 1 | evaluation | TrustedProjectEvaluator | 295/295 | 223 秒 |
| 1 | review | ReviewAgent | 完成 | 116 秒 |
| 1 | publication | wpKnowledge | 原子发布 | 约 5 毫秒 |

节点审计共写入 72 个 Registry Event。前台读取的是 `WorkflowNodeProjection`，不直接读取 LangGraph checkpoint 表。

## 不可变证据索引

| 工件 | Artifact ID |
|---|---|
| 第 0 轮知识（质量 65） | `sha256:3b3626cb5462b9d8492d9f2ccf3fc75d86432e09e8d308adc456acb8c52d2675` |
| 第 1 轮 VERIFIED 知识（质量 98） | `sha256:c4887d767f03cbcfbeb8b79b2f1e839211221393f4a046a06c75628d455d4788` |
| 295/295 行为评测证据 | `sha256:c3b9f4d0906fe9d6ddc04a61e8b3690264b4cb34583c60e599f777f8307ea85e` |

这些对象保存在本机 CAS，不提交 Git。本文固定 ID、语义和结果，其他机器重跑会产生新的 Run、时间戳和评测 Artifact。

## 运行中撞到的问题

这次实跑很有价值，因为它没有一路绿灯。

1. DSH Headless 输出可能带诊断文本，也可能连续给出多个 JSON。适配器现在扫描完整的顶层 JSON 对象，选择最后一个符合 Schema 的对象；找不到合法对象时仍 fail closed。
2. 模型曾在合法对象中增加 `additionalProperties` 说明。提示现在明确列出允许的顶层键，Schema 校验没有被放宽。
3. 旧恢复入口看到 `FAILED` 就直接返回。现在会在 LangGraph 历史中找到最近带错误的 task checkpoint，从该分支续跑。CAS GenerationKey 和 publication key 继续保护业务副作用。
4. 候选知识只有正文，没有结构化质量反馈回路。现在质量不合格会跳过 CodeAgent，把 score、signals 和 weak points 交给下一轮 DocGen。
5. 候选正文是 Markdown Artifact，早期上下文装配器误按 JSON 解析。现在按 `mediaType` 解码。

这些问题和修复都属于 Demo 证据。删掉失败片段会让演示看起来干净，却无法说明系统为什么需要 Checkpoint、Schema 和确定性 Gate。

## 还不能据此宣称什么

- 只有一次完整 live Run，尚不足以证明模型成功率、成本和输出稳定性；后续要在同一固定 commit 上重复运行并统计分布。
- Headless 进程适配器把 Prompt 作为 argv 传入，宿主机同权限进程可能读取。生产版本应换成 DSH SDK 或 stdin/受保护 IPC。
- 当前 Agent 工作目录仍可见完整受信源码。特别是 CodeAgent 尚未达到 `KF-SYS-003` 要求的“只看知识和公开接口”；下一阶段要为每个角色构建隔离视图。
- `TrustedProjectEvaluator` 是受信项目执行器，不是敌对代码沙箱。
- 第 1 轮 TestGen 在源码和测试策略未变化时仍重复运行，浪费约 130 秒。可以用输入 Artifact 哈希复用，但不能只凭轮次跳过。
- 公网 DSH Web 目前是带连接 token 的临时 HTTP 演示。没有 TLS 和正式反向代理前，不应作为长期服务。

## 复现入口

部署参数见 `endlessWpKnowledgeRunner/deploy/deepseek-harness/README.md`。运行时至少需要设置：

```bash
export OPENCODE_GO_API_KEY='<runtime-secret>'
export WP_FLYWHEEL_AGENT_PROVIDER=deepseek-harness
export WP_DSH_MODEL=deepseek-v4-flash
export WP_DSH_ALLOWED_ROOTS='/path/to/wpKnowledge:/path/to/ohMyWorkPanel'
npm run knowledge -- workflow-run --repository /path/to/ohMyWorkPanel --workers 1 --max-iterations 3
```

不要把密钥写进 `.env` 示例、PPT、Issue 或命令历史。复验时应使用新的 runtime 目录，并保留失败率、Token、时延和最终 Gate 数据。
