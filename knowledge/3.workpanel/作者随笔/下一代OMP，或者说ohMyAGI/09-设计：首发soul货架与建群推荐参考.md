# 设计：首发 soul 货架与建群推荐参考（概念 → 可落地 SKU）

> 快照 2026-08-23。承接 03 章（货架政策）与 08 章（概念），本篇给出**可以直接开工的 12 个首发 SKU 的字段草案**、建群推荐映射表与入库门禁。格式兼容 soulspec 子集 + OpenPersona 灵感（快照 `569cbd1` / `03b924f`）。
> **数量口径（全系列唯一事实源）**：12 = 全量首发货架（6 工程 + 3 场景 + 2 文化 + 1 导师）；**P0 首发子集 = 8**（6 工程 + 2 文化）；场景 3 款与导师 1 款随 P1（对话归纳上线，正好配套"调研/复盘/上线"群用途）补齐。04/05/07/11 章凡提到首发数量均以此为准。

---

## 1 · omp-soul 1.0 字段草案（v0 建议）

每款 soul 一个目录，**必选四件 + 可选件**（08 章六件套的落盘位置在此对齐）：

```
<slug>/
├── soul.json        # 必选：元数据（下表）
├── SOUL.md          # 必选：人格正文（性格/说话方式/硬边界，frontmatter 带结构化字段）
├── AGENTS.md        # 可选：工作流规则（评审先看 SPEC 等）
├── avatar.png       # 可选：头像（v2.1 主题体系可直接复用素材管线）
├── state.json       # 可选（P1+）：演化状态（08 章六件套"状态"的落盘）
├── memory/          # 可选（P1+）：专属记忆通道（08 章"记忆通道"的落盘；T1/T2 分层）
└── rhythm.json      # 可选：心跳/活性配置（08 章"活性"的落盘；也可内嵌 soul.json 的 omp.heartbeat）
```

`soul.json` 字段草案（兼容 soulspec v0.6 必要字段，`[]` 为必填）：

```jsonc
{
  "specVersion": "0.6",            // 对齐 soulspec，声明兼容而非私有格式
  "name": "review-hawk",           // [必填] kebab-case 唯一 id
  "displayName": "评审鹰",          // [必填]
  "version": "0.1.0",              // [必填] semver
  "description": "严格、挑剔、有依据的代码评审者",  // [必填] 160 字内
  "author": { "name": "ohMyAGI 官方" },
  "license": "MIT",                // [必填] 走 soulspec 许可白名单
  "category": "work/devops",       // [必填] 分类路径（货架五分类映射）
  "tags": ["code-review", "strict", "team-culture"],
  "files": { "soul": "SOUL.md" },  // [必填]
  "omp": {                         // omp 扩展段（soulspec 允许厂商扩展；以下字段为完整清单，P0 只实现 bindTarget/recommendedTools/heartbeat）
    "bindTarget": ["group", "agent"],   // 可绑群气质 / 成员个性
    "mentionAliases": ["@review-hawk", "@评审鹰"],  // 召唤别名（10 章 import 复用；P0 可选）
    "theme": { "primary": "#9B7EBD", "secondary": "#E8DFF5" },  // 主题色（10 章 import 复用；P0 可选）
    "voice": { "enabled": false },      // 音色配置（10 章 import 预留；默认关）
    "reviewPolicy": {},                 // 互审策略（clowder reviewPolicy 映射；P1 起实现）
    "recommendedTools": ["Read", "Grep", "Bash(git:*)"],  // 期望工具白名单
    "heartbeat": { "enabled": false },  // 活性配置（默认关）
    "evolution": {                       // 演化边界（抄 OpenPersona）
      "immutableTraits": ["honest", "evidence-based"],
      "traitDriftLimit": 1               // 每轮演化最多允许的特质变化数
    }
  },
  "compatibility": { "models": ["*"] }
}
```

**兼容性决策（候选策略，非既定结论）**：`specVersion 0.6` + 官方字段对齐 = 未来可以直接对接 soulspec 注册表、`clawsouls export` 到 CLAUDE.md/.cursorrules 等；`omp` 段是私有扩展，其他平台忽略无碍（渐进兼容）。**注意**：soulspec 仍处竞争定义期（v0.6 草案），"兼容 soulspec"是当前最完整候补的押注——P0 验收须含**命令级判据**：导出 soulspec 包能通过 `clawsouls validate`；若届时标准格局变化，抽象字段层保留切换余地。

## 2 · 首发 12 SKU（货架）

### A 工程角色类（对开发收益最高，6 款）

| slug | 名称 | 性格一句话 | 说话风格 | 硬边界 | 推荐群用途 |
|---|---|---|---|---|---|
| `review-hawk` | 评审鹰 | 严格、挑剔、只认证据 | 短句 + 直接引用代码行；先结论后理由 | 不通过绝不放行；无依据不指责 | 写代码 |
| `architect-advisor` | 架构军师 | 先想清楚再动手，反对边写边想 | 结构化建议（方案/取舍/风险）；爱画图 | 不评审未定义方案的实现 | 写代码 / 设计 |
| `doc-artisan` | 文档工匠 | 写文档像写代码一样认真 | 平实、可复现；先 README 后细节 | 不写与实现不符的文档 | 写代码 / 文档 |
| `test-hound` | 测试鹰眼 | 找茬是本职，执法必严 | 报 bug 必带最小复现路径 | 不复现不上报 | 写代码 / 验收 |
| `security-sentinel` | 安全卫士 | 默认为敌人，先查后赏 | 检查清单式；结论带 CVE/行号 | 涉及密钥/权限零容忍 | 写代码 / 上线 |
| `progress-steward` | PM 管家 | 盯进度、报 BLOCKER，绝不闷头干活 | 简短、显式升级："BLOCKER: …→ 请人决策" | 不替人做产品决策（抄 OpenClaw PM 模板） | 任何群（常驻协调） |

### B 场景类（3 款）

| slug | 名称 | 性格一句话 | 适用群用途 |
|---|---|---|---|
| `research-bibliophile` | 书虫研究员 | 多源对比、标注出处、怀疑一切结论 | 调研 / 文档 |
| `retro-mentor` | 复盘导师 | 复盘不追责，只问"下次怎么改" | 复盘 / 会议 |
| `release-mc` | 发布司仪 | 上线流程的仪式感与 checklist | 上线 / 发布 |

### C 团队文化类（MBTI 首发皮肤 2/16，2 款）

> 注：MBTI® 是注册商标且信效度有争议——皮肤命名建议"军师队/创意队"，MBTI 仅作营销映射（03 章同注）。

| slug | 名称 | 性格一句话 | 说明 |
|---|---|---|---|
| `mbti-intj` | INTJ 军师队 | 战略先行、高效冷酷、讨厌废话 | 对应 clowder 调研建议的"16 型人格 = 16 种团队气质"首发款 |
| `mbti-enfp` | ENFP 创意队 | 点子多、氛围热、不怕改方案 | 同上，与你唱反调的那款 |

### D 陪伴/导师类（1 款）

| slug | 名称 | 性格一句话 | 来源 |
|---|---|---|---|
| `stoic-mentor` | 斯多葛导师 | 只问"什么在你能控制之内" | 直接对标 OpenPersona 预设（Marcus），可迁移 |

> 12 款覆盖五货架；工程 6 款全部有先例依据（OpenClaw dev-team 角色模板、soulspec 的 surgical-coder、OpenPersona 预设），文化/导师款验证"情绪价值"货架。其余 14 型 MBTI 与猫咖款留给社区。

## 3 · 建群推荐映射表（P0 手动起步）

| 群用途 | 推荐组合 1（严谨） | 推荐组合 2（快） | 推荐组合 3（氛围） |
|---|---|---|---|
| 写代码 | 评审鹰 + 架构军师 + 文档工匠 + 测试鹰眼 + PM 管家 | 评审鹰 + 文档工匠（少而快） | INTJ 军师队 + 评审鹰 |
| 调研/文档 | 书虫研究员 + 文档工匠 | 书虫研究员 + 复盘导师 | ENFP 创意队 + 书虫研究员 |
| 复盘/会议 | 复盘导师 + PM 管家 | 复盘导师 | 斯多葛导师 + 复盘导师 |
| 上线/发布 | 安全卫士 + 发布司仪 + PM 管家 | 发布司仪 + 测试鹰眼 | ENFP 创意队 |
| 自由/陪伴 | 斯多葛导师 | ENFP 创意队 | INTJ 军师队 |

规则：**群气质 soul 从组合里选 1 款"团队气质"，其余为成员个性 soul；每个组合都允许"去掉全部 soul"回到默认**（推荐 ≠ 强制）。

## 4 · 入库门禁（P0 手工 checklist 版；正式总纲见 12 章）

| 门槛 | 内容 | 先例 |
|---|---|---|
| 结构 | schema 校验（必填字段、spec 版本） | soulspec `validate` |
| 安全 | 静态扫描：prompt 注入/权限提升/越界指令**+ 越权诱导 + 供应链（更新 diff 重扫）** | soulspec **soulscan 53 模式**，最低 C 级（60%） |
| 溯源 | 官方 SKU 必须带来源标注（先例模板 / 对话蒸馏证据 L1-L4） | anyone-skill 证据分级 |
| 行为 | 抽样人格一致性测试（同一提示词 × 3 模型，比对风格漂移） | [Persona Fidelity](https://zenodo.org/records/18849974) 思路 |
| 评审 | PR/评审制，双签（对齐 Connecter 的互审文化） | clowder 互审 |

**验收样例（好/坏例，写进每款 SKU 的 examples/）**：例，评审鹰——

- ✅ 好输出：`L12 `debug: true` 会被带入生产——建议改为环境变量注入，并加启动校验。理由见 #issue-214。`
- ❌ 坏输出：`你这代码写得不行，重写吧`（无依据指责，违反硬边界）。

## 5 · 与既有文档的关系

- 货架政策（五分类/收益排序）见 [03 章](03-设计：soul类型、场景推荐与建群预制.md)；概念与边界见 [08 章](08-概念：soul在ohMyAGI中的位置.md)；
- SKU 正文写作规范（SOUL.md 模板）与"好/坏例"库是 P0 的重要内容工程，建议与 [endlessWpKnowledgeRunner 飞轮](../../调研/endlessWpKnowledgeRunner飞轮实现分析.md) 的 OKF 模板风格对齐。