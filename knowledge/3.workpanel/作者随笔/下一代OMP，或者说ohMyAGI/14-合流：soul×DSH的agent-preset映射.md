# 合流：soul × DSH agent preset（人格交换格式）

> 快照 2026-08-23。战略文件（06-strategy-thinking 命题 5）已有"把 ohMyWorkPanel 变成 dsh 宿主/面板"的路线；本篇论证一个推论：**omp-soul 可以兼作 DSH 与 omp 之间的"通用人格交换格式"——soul 一写，两边都能上岗。**
> 取证：本机真实预设 `linlis-super-harness`（`~/.dsh/.agent-presets/linlis-super-harness/`，`agent.cordis.yml` 282 行 + `preset.yml`）通读。

---

## 1 · DSH 预设的人格注入点（一手事实）

DSH agent preset = 一个 `cordis.yml` 组合 + 一个 `preset.yml` 元数据。与本主题直接相关的行：

| cordis.yml 行 | 内容 | 与 soul 的对应 |
|---|---|---|
| `persona` 行（`@deepseek-ai/dsh-persona`，`config.text`） | **人格/系统提示词唯一注入点**（含 `{{model}}`/`{{cwd}}` 模板变量；可内嵌"协作铁律"、生态知识、边界声明） | **SOUL.md 的宿主**：人格正文直接落在这里 |
| `agent-instructions` 行 | 指令上限（maxBytes 65536） | soul 大小约束（SOUL.md 精简原则） |
| 工具行（`tool-bash`/`tool-pwsh`/`tool-fs`…） | 注册进宿主 tools 注册表；`disabled` 条件可平台化 | `omp.recommendedTools` 的宿主侧表现（DSH 靠工具行，omp 靠 adapter） |
| 技能行 / prompt 段 | 领域规则与行为（如"先加载 X 技能再动手"） | AGENTS.md 规则的宿主侧表现 |
| `isolate` realm / hooks / timer | 服务隔离、事件钩子、定时 | 记忆通道、heartbeat 的宿主侧表现（DSH 侧用插件实现） |
| `preset.yml` | name/description 元数据 | soul.json 元数据（name/description/version） |

**关键事实：DSH 已具备人格注入的载体（persona 行），但没有 soul 生命周期**（无商店/无切换 UX/无评测）——这正是人格交换格式的切入点，而非"DSH 已有一个 soul 机制"。

## 2 · 双向往来：把 soul 变成交换格式

### omp-soul → DSH preset（`soul2dsh` 导出器）

```
cat-ragdoll/（omp-soul 包）
  → 生成 ~/.dsh/.agent-presets/cat-ragdoll/
      ├── preset.yml          ← soul.json 的 name/description
      └── agent.cordis.yml    ← SOUL.md 全文 → persona 行 config.text
                                  AGENTS.md 规则 → prompt 段/技能行
                                  recommendedTools → 工具行注册
```

- 用户导出自己喜欢的 soul → 在 DSH 里获得完全一致的"人格化编码 agent"；
- 注意项目规则：**导出生成的是新预设目录，绝不覆盖 shipped preset**（deployment 原始 preset 只读）。

### DSH preset → omp-soul（`dsh2soul` 导入器）

- 把现成的 cordis 预设（如 linlis-super-harness 的"canary 优先"协作铁律、知识预载）提炼成 AGENTS.md 段 → 生成 soul 包 → 进 omp 商店（12 章门禁）；
- 效果：**DSH 里被验证有效的"工程文化"能变成 omp 群里可复用的团队气质 soul**——人格文化的跨平台移植。

## 3 · 为什么这值得做（三个收益）

1. **生态牌落地**：05-joint-thinking 的"集成 dsh"从"接口适配"升级为"人格互认"——soul 是两边都认识的文件格式，比 API 对接更浅、更快、更有传播性；
2. **弓单发供给**：DSH 用户群即 soul 生产群（06 章蒸馏的活数据源）；omp 商店的社区层直接多一个"从 DSH 预设导入"的入口；
3. **反哺兼容**：soulspec 已能 `export claude-md/.cursorrules`；再加 DSH 一档，omp-soul 成为"全平台人格交换格式"的事实节点（soulspec 兼容 + clowder 兼容 + DSH 兼容）。

## 4 · 边界声明

- 不把 DSH 的 cordis 机制搬进 omp（执行面不同：DSH 的插件是"能力"，omp 的 adapter 是"协议"）；soul 只是**交换层的载荷格式**；
- 不承诺"人格完全一致"：跨平台注入点不同（系统提示 vs 上下文前缀），保真差异正是 12 章跨模型/跨平台评测要测的——soul2dsh 导出的预设建议打"跨平台保真待评"标；
- 记忆不随交换带走：DSH 侧记忆由宿主机制负责，omp 侧走 Connecter/飞轮；交换只带"我是谁、怎么干活"，不带"我记得什么"。

## 5 · 一句话

> soul × DSH 合流 = **把 omp-soul 定义为 DSH 与 omp 之间的人格交换格式**：`soul2dsh` 让"喜欢的性格"进城打工，`dsh2soul` 让"实战打磨的工程文化"变成群气质——两个生态互相喂供给，而 soul 是中间那张能识别对方的名字卡。