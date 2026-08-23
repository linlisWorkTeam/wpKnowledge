# 兼容：clowder 猫咖的猫如何一键入伙（问 1 的延伸取证）

> 快照 2026-08-23。本轮对 clowder-ai 做一手取证：clone `zts212653/clowder-ai` @ `f2b9c118`，通读 `cat-template.json`（935 行）与调用链 `cat-config-loader.ts` / `cat-catalog-store.ts`。结论：**cat-template v2 就是"灵魂与身体分离"的成熟实现，omp-soul 可以直接定义一键迁移协议，让猫咖的猫入伙 ohMyAGI。**

---

## 1 · cat-template.json v2 结构解析（一手事实）

| 段 | 内容 | 对应 omp-soul 概念 |
|---|---|---|
| `roleTemplates[]` | 6 只猫的简版：id/name/nickname/avatar/color(primary+secondary)/roleDescription/personality/teamStrengths | soul 声明（简版） |
| `breeds[]` | 完整"品种"定义：id/catId/name/nickname/avatar/color/**mentionPatterns**（@别名集合，如 `@opus`/`@布偶猫`/`@宪宪`）/roleDescription/teamStrengths/**caution**/**restrictions**（如暹罗猫"禁止写代码！幻觉多"）/**features**/variants[] | **soul = breed（人格层）**；mentionPatterns = 被召唤方式；restrictions/caution = 硬边界 |
| `breeds[].variants[]` | 每个变体：id/clientId/defaultModel/cli(command/outputFormat/defaultArgs/effort)/mcpSupport/personality/strengths/**voiceConfig**（音色+语气指令+温度） | **body = variant（身体层）**：同一只布偶猫可有 opus/sonnet/fable 三个身体 |
| `roster{}` | 实际实例表：family(属于哪个品种)/roles/lead/available/evaluation/关系 | 实例注册：谁在岗、干什么、是否可召唤 |
| `clientDefaults{}` | 各客户端默认模型清单 | 模型路由表 |
| `reviewPolicy{}` | `requireDifferentFamily: true` 等——**跨家族互审，禁止家族内自审** | 治理：soul 的"家族"属性参与审批策略 |
| `coCreator{}` | 人类"大当家"身份（别名/头像/时区/@ 模式） | 用户的身份卡（soul 的镜像） |

**三个关键发现（比旧笔记更硬的事实）：**

1. **soul 与 body 分离是 clowder 的原生设计**：布偶猫=宪宪，但有 opus（主）、sonnet（轻快）、fable-5（新猫）三个变体；同一灵魂，多个身体。这就是"soul 是壳，不是电梯"的成品级证据——换身体（模型/CLI），猫还是那只猫。
2. **soul 携带"被召唤方式"**：mentionPatterns 是人格与路由的接缝——omp 的 @ 路由可以直接对接"@布偶猫 = 布偶家族当前 lead 实例"。
3. **soul 参与治理**：reviewPolicy 定义"谁能审谁"（跨家族、优选 lead、排除 unavailable）——人格不只是显示层，还是互审纪律的载体（对应 clowder"纪律化能可信"）。

## 2 · 迁移映射表（cat-template v2 → omp-soul 1.0）

| clowder 字段 | omp-soul 1.0 | 转换规则 |
|---|---|---|
| breed.id / name / nickname | `name`(slug) / `displayName` / tags | id：`cat-<breed.id>`（保留可逆性）；nickname 进 tags 与 SOUL.md |
| breed.avatar / color | avatar.png / `omp.theme` | 资产直拷；color 映射为主题色（v2.1 主题管线） |
| breed.roleDescription | `description` | 直拷，160 字内 |
| breed.personality | SOUL.md 性格段 | 直拷 + 展开成"价值观/说话方式"两小节 |
| breed.teamStrengths | tags + SOUL.md 分工段 | 转 tags（`role:architect` 等） |
| breed.restrictions / caution | SOUL.md "硬边界" + `omp.evolution.immutableTraits` 补充 | **restrictions 必须进硬边界**（"禁止写代码"是安全属性，不是性格） |
| breed.mentionPatterns | `omp.mentionAliases` | 直拷，omp @ 路由直接可用 |
| breed.reviewPolicy（全局） | 群级配置 `omp.reviewPolicy`（群气质 soul 可携带） | 默认继承"跨家族互审"；omp 不做则忽略 |
| variants[].clientId/defaultModel/cli | （不迁移） | **body 层是 clowder 私有的 CLI 配置；omp 用 adapter 抽象，不搬** |
| variants[].voiceConfig | `omp.voice`（可选） | 保留：omp 若做语音是现成资产 |
| roster 实例 | agent 绑定 | **N:1**：roster 里多个实例（opus/sonnet）→ 同一群内按需绑定其一；`lead/available` 保留为绑定默认 |
| coCreator | 用户的默认身份卡 | 可选导入（大当家 → 用户画像） |

**双向协议建议**：
- **import**：`clowder-import <path/to/cat-template.json>` → 一键生成 6 个 `cat-*` soul 包（**首批迁 `roleTemplates` 的 6 只**，即布偶/缅因/暹罗/狸花/孟加拉/金渐层 + 对应 roster 实例映射）+ 一个"猫咖群"预制群组（群气质 = 猫咖文化，成员 = 6 猫）——**建群即入伙**，用户在 ohMyAGI 里直接 @宪宪 干活；
  - **其余 breeds 待评估**：gpt-pro（云端 Pro 席位）、gemini35、moonshot（梵花猫）、opus-47（试用分身）等条目依赖特殊模型/CLI/订阅，一期不迁，标记"缺身体"（见下）；
  - **"缺身体"降级**：import 向导按用户已配置的 adapter（claude/codex/gemini/opencode…）过滤可入伙的猫；没有对应 CLI 的猫标记"缺身体"，给绑定引导，不硬迁。
- **export**：`omp-soul export clowder <my-soul>` → 生成 `breeds[]` 条目 + roster 项，让 omp 造的 soul 能回猫咖上岗——实现 05 章"灵魂牌与猫咖互通"的实物通道。

## 3 · 迁移示例：布偶猫 → omp-soul（完整示例）

```jsonc
// cat-ragdoll/soul.json（由 clowder-import 生成）
{
  "specVersion": "0.6",
  "name": "cat-ragdoll",
  "displayName": "布偶猫",
  "version": "0.1.0",
  "description": "主架构师和核心开发者，擅长深度思考和系统设计",
  "author": { "name": "clowder-ai import" },
  "license": "MIT",
  "category": "work/devops",
  "tags": ["cat", "architect", "ragdoll", "宪宪", "imported:clowder"],
  "files": { "soul": "SOUL.md" },
  "omp": {
    "bindTarget": ["agent"],
    "mentionAliases": ["@opus", "@布偶猫", "@布偶", "@ragdoll", "@宪宪"],
    "theme": { "primary": "#9B7EBD", "secondary": "#E8DFF5" },
    "voice": { "voiceId": "zm_yunjian", "langCode": "zh", "instruct": "用一个调皮狡黠的少年语气说话…" },
    "evolution": { "immutableTraits": ["温柔但有主见", "注重质量"] },
    "reviewPolicy": { "requireDifferentFamily": true }
  },
  "compatibility": { "models": ["claude-*", "gpt-5.3-codex", "gemini-*"] }  // 由 variants 的可用模型推导
}
```

```markdown
<!-- cat-ragdoll/SOUL.md（节选） -->
# 你是布偶猫（宪宪）
- 身份：主架构师和核心开发者；来自 clowder 猫咖（imported）。
- 性格：温柔但有主见，喜欢深入分析问题，写代码快但注重质量。
- 硬边界：无（breed 无 restrictions）；如检出模型能力短板，按 caution 声明。
- 协作：遵循群 reviewPolicy：跨家族互审，家族内不自审。
```

## 4 · 收益与边界

**收益**：① 兼容性从"纸上声明"变成"可验证协议"（import/export 都有样例）；② 猫咖群的预制群组直接叩开 clowder 用户迁移；③ soul 的"家族 + 变体""互审策略""召唤别名"三个概念被一手证据钉死，08 章概念得到实现级背书。

**边界（提醒）**：① 不要把 variant 的 CLI 绑定搬进 omp-soul（那是 clowder 的私有执行配置，omp 有自己的 adapter 层）；② 猫咖的"纪律"（SOP/互审）是平台行为不是 soul 属性，omp 侧只迁移"策略意图"，执行归 omp 的治理平面；③ 导入的猫人格有版权/归属问题（官方猫 vs 用户自建猫），商店里对 `imported:clowder` 打标。

## 5 · 一句话

> 猫咖的猫已经证明了**灵魂（breed）与身体（variant）分离、人格携带召唤方式与互审策略**的完整形态；omp-soul 不需要发明，只需要定义 import/export 协议——**clowder-import 一键入伙`，就是 ohMyAGI 生态的第一条双向通路。**