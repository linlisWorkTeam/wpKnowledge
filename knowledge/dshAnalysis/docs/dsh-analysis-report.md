# DeepSeek Harness（dsh）可借鉴性分析报告

| 项 | 内容 |
|---|---|
| 对象 | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)（`dsh`，开发者预览，分析时 npm `@deepseek-ai/dsh@0.1.0-rc.6`） |
| 对照 | LinlisWorkPanel（Rust 调度 + 外挂 CLI：Cursor / Codex / Claude / OpenCode / OpenClaw…） |
| 约束 | **不**整仓接入本机常驻；本机可用内存约 **1.8Gi**；任务要求避免大规模 `pnpm install` |
| 证据来源 | GitHub 文档（`docs/architecture*.md`、`capability-seams`、`subsystems/*`）、`apps/cli` README、npm 元数据；对照本机 `/AI/LinlisWorkPanel` 只读 |
| 日期 | 2026-08-14 |

---

## 0. 一句话结论

**不要把 dsh 当作与 Cursor/Codex 平级的常驻适配器。** 应把 dsh 当作「机制样本库」：优先抄 **Capability Seams / 仅追加 run 事件日志 / Compaction / Goal·Plan / Approval 预设**，落在 WorkPanel 现有 Rust 调度、epitaph/handoff、适配器契约上；可选远期用隔离机做一次 `dsh --profile headless` 冒烟，再决定是否加薄 CLI 适配器。

---

## 1. dsh 模块拆解

### 1.1 总体形态

- **Cordis 插件树**：产品几乎全部是插件（模型适配、工具、会话日志、agent loop 均可替换）。扩展方式是并排挂载插件，副作用在卸载时撤销——无「打补丁内核」。
- **Profile + Bundle 组装**：运行中的 `dsh` = 按序叠加的组合包 + `cordis.patch.yml`。发行模板含 `web` / `headless`；`dsh-base` 是几乎所有 profile 的第一层。
- **仓库规模**：pnpm monorepo，`packages/*/*` 约 **226** 个 `package.json`；根包引擎要求 **Node `^22.19 || >=24`**；`@deepseek-ai/dsh` 直接依赖约 **61** 个包（含大量 `@deepseek-ai/dsh-*`）。
- **入口**（产品 CLI）：
  - `dsh web` / `--profile web`：浏览器 UI（默认文档称 `127.0.0.1:3080`）
  - `dsh --profile headless "task"`：一次性会话，打印最终助手文本后退出，**不监听端口**

### 1.2 核心主干（每个可运行组合几乎都会碰到）

| 模块 | 职责 | 对 WorkPanel 的含义 |
|---|---|---|
| **core/session** | 仅追加 `SessionEvent` 日志；模型历史由日志 **派生**；「模型可见即已记录」 | 对应强化 `TaskRun` / 流式 parts / 可回放事件，而非只存最终字符串 |
| **core/system-prompt** | 提示词片段 + 工具 schema 组装注册表 | 对应群公告 / AGENTS / epitaph / Wiki 注入的 **有序 seam**，避免散装字符串拼接 |
| **core/tools** | 作用域工具注册 + `pre-execute → execute → post-execute` 把关流水线 | WorkPanel 侧多在外挂 CLI 内完成；平台层可借鉴 **审计与拒绝默认** |
| **core/agent + agent-loop** | Agent 句柄、inbox、turn/step、可替换 loop | WorkPanel 的「调度器 + AdapterKind」是另一层抽象：管群成员与 CLI 进程，不管模型循环 |
| **llm** | 消息/流式词汇 + 适配器 seam | 与平台无关；平台只消费 CLI stdout/stderr 契约 |

**轮次心智模型（可直接借鉴命名）**：

```text
turn/start → pre-step → step(start → llm stream → tool* → end)* → turn-stopping → turn/end
```

持久事实走会话事件；实时拦截走 `agent/*` / `tools/*` waterfall。

### 1.3 关键能力子系统（任务点名项）

| 子系统 | 要点 | 借鉴价值 |
|---|---|---|
| **goal** | 同会话目标领域，事件溯源 + 修订号 CAS；可驱动续跑 | 高：对齐 PM Wave/任务「未完成则续」 |
| **plan / plan-mode** | 计划协作状态（与执行模式分离） | 中高：与「先计划后改码」产品节奏一致 |
| **compaction** | 可选 seam：`compaction/start|summary|end` + 用 `user/message` + `surfaceOp: replace` 遮蔽旧区间；锁可检测崩溃 | **高**：长会话 / chatbot 窗口 / 滚动摘要的正规化 |
| **permission-presets + approval + sandbox** | 预设捆绑「沙箱模式 × 审批策略」；审批默认 fail-closed（`unavailable`≠放行）；headless 常用 `never` | **高**：群/成员级权限旋钮，而不是散落 env |
| **headless** | 无 Host/HTTP/浏览器；提交一条任务 → 等静默 → stdout 最终文本；失败写 stderr | 中：若未来做适配器，这是唯一合理进程契约面 |
| **MCP** | `dsh-mcp-client`：连 MCP server 并把工具挂到 `ctx.tools` | 低～中：WorkPanel 更宜「成员侧 CLI 自带 MCP」，平台少掺和 |
| **subagent / jobs / workflow / skill** | 子 agent、后台 job、workflow worker、技能文件系统 | 中：与群 @委派、扩展 Host 有概念重叠，勿整包搬 |
| **session-projection / session-query / telemetry** | 投影、检索、OTel | 中：Experience/Logs 面板可对齐事件模型 |
| **hooks（含 Codex/Claude 桥）** | 把外部 hook 协议记入会话 | 低：平台已有适配器边界 |

### 1.4 Capability Seams（架构核心理念）

一项可替换能力 = **Service Definition + Provider + Consumer** 三者一起设计。  
例：换 `ctx.fs` / `ctx.subprocess` 提供方到远程沙箱，则 Bash、PTY、LSP 一并搬迁，无需为每个工具写 fork。

这与 WorkPanel「换 AdapterKind = 换外挂 CLI」同构，但 dsh 的 seam 粒度更细（fs/shell/approval/compaction/llm…）。

---

## 2. 与 WorkPanel 能力对照

### 2.1 现状速写（WorkPanel）

- **编排层**：Rust `scheduler` + SQLite；群成员绑定 `AdapterKind`；同 Agent 串行；流式 parts；Cursor/OpenClaw session resume。
- **适配器层**：spawn CLI → 解析 JSONL/stdout → `resolve_adapter_final_text` 契约测（OpenClaw/Cursor/Codex/…）。
- **交接层**：`docs/epitaph/` + `version-pipeline.md`（人工/Agent 可读 handoff，非运行时事件日志）。
- **产品方向**：Workflow 时代（Wave、总结回写）、chatbot 窗口与滚动摘要、Experience/Logs、沙箱与内存门禁（v1.7）。

### 2.2 概念可借鉴（建议「抄语义，不抄仓」）

| dsh 概念 | WorkPanel 落点建议 | 不要做的事 |
|---|---|---|
| Capability Seams | 把「上下文注入 / 权限 / 摘要 / 运行日志」做成显式接口 + 可替换实现 | 引入 Cordis 运行时进 `src-tauri` |
| 仅追加 SessionEvent | `task_runs` / run phases 旁增加结构化事件流（turn/step/tool/approval/compact） | 用可变「当前 prompt 大字符串」当唯一真源 |
| 模型可见即已记录 | 凡注入群公告、epitaph、Wiki、短回复约束，都记一条带 `source` 的事件 | 静默改 system 前缀导致无法回放 |
| Compaction + surface replace | chatbot/长 run：摘要替换旧窗口，保留审计事件 | 静默 truncate 无记录 |
| Goal 续跑 | Wave/Task「未完成 → 自动或半自动再派发」 | 把 dsh goal 包嵌进进程 |
| Permission presets | 成员或群：`workspace-write` vs `danger-full-access` 一类命名旋钮 | 把 Node sandbox/landlock 整棵依赖拉进 1.8G 机 |
| Headless 进程契约 | 若适配：stdout=最终答复、stderr=错误、exit code、无端口 | 常驻 `dsh web` 与 Panel 抢内存 |
| System-prompt 注册表 | 有序 section：身份 / 群规则 / handoff / 工具说明 | 无序字符串加法 |

### 2.3 明确不要搬

1. **整仓 / `@deepseek-ai/dsh` 作为本机常驻依赖**（安装闭包巨大，Node 22+，Cordis 插件树，与 Tauri/Rust 运行时重叠）。
2. **Cordis 插件体系作为 WorkPanel 扩展模型**（已有 Extension Host / A2A / 外挂 CLI；再叠一层插件运行时成本过高）。
3. **把 agent-loop / tools 执行搬进平台内核**（与「外挂 CLI 拥有工具世界」的产品边界冲突；也会毁掉现有适配器契约测策略）。
4. **Web UI / Host / PTY / Landlock native 栈**（运维与内存面都与 1.8G 双槽位发布模型不兼容）。

---

## 3. 落地优先级与切片

### P0 — 高（机制借鉴，1～2 个小里程碑内可做）

| 切片 | 做什么 | 验收线索 |
|---|---|---|
| **A. Run 事件日志（SessionEvent 精简子集）** | 每次适配器 run 追加：`run/start`、`user/inject`（来源：群公告/epitaph/wiki/…）、`assistant/delta|final`、`run/end(reason)`；可选 `tool/*` 若 CLI 能解析 | Experience/Logs 能按 runId 回放；失败可区分「CLI 无输出」vs「解析失败」 |
| **B. Context Seams（注入注册表）** | 把今日散落注入收成有序 section 列表（name、priority、content、source_event_id）；调度拼 prompt 只读该表 | 与「模型可见即已记录」一致；单测不依赖真 CLI |
| **C. Handoff ↔ 运行时桥** | epitaph 仍为人读 SSOT；跑任务时把「active epitaph 摘要」经 Context Seam 注入并记事件 | 交接文档与实际 prompt 可对照，减少「读了没注入」 |

### P1 — 中

| 切片 | 做什么 |
|---|---|
| **D. Compaction 策略** | chatbot/长线程：显式 `compact` 事件 + 摘要替换窗口（对齐 dsh surface replace，实现可极简） |
| **E. Permission preset** | 群或成员级：`ask` / `never`（无人值守）与工作区写范围文案；先做策略字段与 UI，强制执行可仍交给 CLI |
| **F. Goal/Plan 轻量态** | Wave/Task 上记录 goal revision 与 plan 文档链接；调度「未完成可续跑」 |

### P2 — 低

| 切片 | 做什么 |
|---|---|
| **G. dsh headless 冒烟（隔离环境）** | 在 **≥8Gi / 独立机** 安装 `@deepseek-ai/dsh`，跑 `dsh --profile headless "…"`，记录 RSS、耗时、stdout 契约 |
| **H. 薄适配器原型** | 仅当 G 证明稳定：新增 `AdapterKind::Dsh`，镜像 Cursor 路径（build_args + final text 契约测）；**默认不在生产 1.8G 机启用** |
| **I. MCP 平台化** | 除非产品要求「平台统一 MCP」，否则保持 CLI 侧 |

### 建议实施顺序

```text
A 事件日志 → B Context Seams → C Handoff 注入桥 → D Compaction → E Permission 文案/字段
                                    ↘（可选并行调研）G headless 冒烟 →（门禁通过才）H 适配器
```

---

## 4. 性能与资源风险

| 风险 | 观察/依据 | 对 WorkPanel 的影响 |
|---|---|---|
| **安装内存峰值** | 任务记录：1.8G 机上 `npm i @deepseek-ai/dsh` 峰值约 **820MB 仍未完成**；本机 `free` 约 1.8Gi total | **禁止**在生产/灰度同机做全量安装或 `pnpm install` 整仓 |
| **依赖闭包** | CLI 包直接依赖 ~61；背后是整棵 `dsh-*` + Cordis + 可选 node-pty/koffi 等原生件 | 即使用 npx，冷启动与磁盘/ inode 压力大 |
| **Node 版本** | `engines`: Node 22.19+ / 24+ | 与常见 20.x 工具链不一致，运维成本↑ |
| **与现有 Agent 并行** | WorkPanel 已可能同时跑 Cursor/Codex 等；再叠加 dsh Node 树 | 易触发 OOM / swap 抖动；违反 v1.7「内存门禁」精神 |
| **开发者预览** | README 明示破坏性变更 | 平级适配器 = 持续跟版本的高维护税 |
| **Headless 相对友好点** | 无 HTTP/UI；stdout 最终文本 | 仅降低「端口与 UI」成本，**不**降低依赖与 RSS 主因 |
| **安全面** | `danger-full-access` + `approval/never` 是合法预设 | 若未来接 headless，默认必须 fail-closed / workspace 限定，并与群沙箱策略对齐 |

**本分析未在本机实测 RSS**：遵从任务约束，未跑完整安装。RSS 数字需在隔离机补测后回写本节。

---

## 5. 平级适配器可行性

### 5.1 判定

| 维度 | Cursor/Codex 现状 | dsh | 结论 |
|---|---|---|---|
| 进程模型 | 外挂 CLI，平台 spawn | `headless` 可 one-shot | 形态上 **可**做成 AdapterKind |
| 输出契约 | JSONL / 可测 final text | 文档：成功时 stdout=最后非空助手文本，stderr 空 | 契约 **简单**，甚至比 OpenClaw 更易测 |
| 资源 | 用户本机已装 CLI | 平台机需自备庞大 Node 树 | **生产机不可行** |
| 稳定性 | 相对产品化 CLI | 开发者预览 | **维护风险高** |
| 产品重叠 | 「另一个编码 agent」 | 自带 loop/tools/UI | 与「平台编排、CLI 干活」重复建设 |

**结论：不宜作为与 Cursor/Codex 平级的默认适配器。**  
**仅借鉴机制**是主路线；**隔离环境验证后的可选 AdapterKind** 是支线，且默认关闭。

### 5.2 推荐路线（机制优先）

1. **主线（WorkPanel 内生）**  
   实现 §3 的 A→E：事件日志、Context Seams、Handoff 注入、Compaction、Permission 字段——语义对齐 dsh，实现保持 Rust/SQLite/现有适配器。

2. **支线（可选）**  
   专用分析/金丝雀机安装 dsh → headless 契约与资源基线 → 若 RSS/冷启动可接受，再 PR `AdapterKind::Dsh` + 契约测；生产 unit **不**安装 dsh。

3. **明确不做**  
   整仓 submodule、Cordis 嵌入、常驻 `dsh web`、把工具执行迁入平台。

---

## 6. 需要其他角色协作时

- 若要在隔离机补测安装峰值 / RSS / headless 延迟：可 @运维 或另开有 ≥8Gi 内存的 runner。
- 若要将 A/B 切片排进 `version-pipeline`：需 WorkPanel 维护者在流水线占位后再改码（本报告 **未** 改 `/AI/LinlisWorkPanel`）。

---

## 7. 附录：关键参考路径（上游）

- 架构：`docs/architecture.md` / `architecture.zh.md`
- 能力图：`docs/capability-seams.md`
- 子系统：`docs/subsystems/{session,core,compaction,goal,approval,permission-presets,system-prompt,tools}.md`
- CLI：`apps/cli/README.md`；headless bundle：`packages/bundle/headless`
- 对照本机：`/AI/LinlisWorkPanel/AGENTS.md`、`docs/epitaph/README.md`、`docs/version-pipeline.md`、`src-tauri/src/adapters/mod.rs`
