# 🧭 候选论文池（引文滚雪球 + 定向检索）

> 更新时间：2026-08-20（第2轮扩充）
> 来源：Semantic Scholar 引文滚雪球（从 12 篇核心论文向前/向后追踪）+ 定向关键词检索（Semantic Scholar / arXiv 双通道）+ GitHub 高 star 仓库检索
> 用途：头脑风暴候选池——这些论文/仓库**尚未写详细单篇**，按主题列出，需要深入哪篇告诉我
> 检索方法见 [retrieval-method.md](retrieval-method.md)；脚本在 [scripts/](../scripts/)

## 📌 怎么用这个池子

1. 看主题分组 → 找感兴趣的标题
2. 点链接看摘要（arXiv 免费）
3. 需要我深读哪篇 → 说标题，我写详细单篇文档（含方法/实验/启发/置信度）

---

## 1️⃣ 评测与基准（门禁设计参考）

| 论文 | 年份 | 引用 | 链接 | 一句话 |
|------|------|------|------|--------|
| SWE-bench | 2023 | 3417 | [arXiv](https://arxiv.org/abs/2310.06770) | 仓库级真实 GitHub issue 修复基准（行业标准） |
| LiveCodeBench | 2024 | 1998 | [arXiv](https://arxiv.org/abs/2403.07974) | 防污染的代码生成评测基准（持续更新） |
| CRUXEval | 2024 | 338 | [arXiv](https://arxiv.org/abs/2401.03065) | 代码推理/执行理解基准 |
| RepoBench | 2023 | 412 | [arXiv](https://arxiv.org/abs/2306.03091) | 仓库级代码补全基准 |
| CodeSearchNet | 2019 | 1461 | [arXiv](https://arxiv.org/abs/1909.09436) | 语义代码检索经典基准 |
| EvoCodeBench | 2024 | 97 | [arXiv](https://arxiv.org/abs/2404.00599) | 演进式代码生成基准（对齐真实仓库） |
| CodeRAG-Bench | 2024 | 134 | [arXiv](https://arxiv.org/abs/2406.14497) | RAG 能否增强代码生成？系统性评测 |
| DevEval | 2024 | 117 | [arXiv](https://arxiv.org/abs/2405.19856) | 人工标注、对齐真实仓库的代码生成基准 |
| CrossCodeEval | 2023 | 286 | [arXiv](https://arxiv.org/abs/2310.11248) | 跨文件代码补全的多语言基准 |
| TheAgentCompany | 2024 | 279 | [arXiv](https://arxiv.org/abs/2412.14161) | agent 真实世界任务基准 |
| APPS | 2021 | 1244 | [arXiv](https://arxiv.org/abs/2105.09938) | 编程竞赛代码生成基准 |
| **Evo-Memory** | 2025 | 113 | [arXiv](https://arxiv.org/abs/2511.20857) | 🆕 自进化记忆的测试时学习基准（LLM Agent Test-time Learning） |
| **SWE-QA-Pro** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2603.16124) | 🆕 仓库级问答基准 + 可扩展训练配方 |
| **RepoProbe** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2608.04783) | 🆕 架构感知的仓库理解基准（checklist 式） |
| **DependEval** | 2025 | 新 | [arXiv](https://arxiv.org/abs/2503.06689) | 🆕 仓库依赖理解评测 |
| **Code2Doc** | 2025 | 新 | [arXiv](https://arxiv.org/abs/2512.18748) | 🆕 质量优先的代码文档数据集（文档质量评测用） |
| **LLM Code Doc + Multi-Judge** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2606.09852) | 🆕 文档生成 + 多裁判评测框架 |

## 2️⃣ 代码生成与 agent 框架（第二步参考）

| 论文 | 年份 | 引用 | 链接 | 一句话 |
|------|------|------|------|--------|
| CodeGen (Program Synthesis w/ LLM) | 2021 | 4295 | [arXiv](https://arxiv.org/abs/2108.07732) | 程序合成里程碑（CodeGen 系列） |
| Codex (Evaluating LLMs Trained on Code) | 2021 | 11087 | [arXiv](https://arxiv.org/abs/2107.03374) | Codex 论文，代码生成开山之作 |
| MetaGPT | 2023 | 2271 | [arXiv](https://arxiv.org/abs/2308.00352) | 多 agent 协作框架（SOP 驱动） |
| SWE-agent | 2024 | 1646 | [arXiv](https://arxiv.org/abs/2405.15793) | Agent-Computer Interface 修复真实 issue |
| Agentless | 2024 | 463 | [arXiv](https://arxiv.org/abs/2407.01489) | 无 agent 的两阶段修复，成本低效果好 |
| CodeAgent | 2024 | 366 | [arXiv](https://arxiv.org/abs/2401.07339) | 工具集成 agent 做仓库级编码 |
| MapCoder | 2024 | 262 | [arXiv](https://arxiv.org/abs/2405.11403) | 多 agent 竞争编程代码生成 |
| TaskWeaver | 2023 | 99 | [arXiv](https://arxiv.org/abs/2311.17541) | code-first agent 框架 |
| OpenHands | 2024 | 944 | [arXiv](https://arxiv.org/abs/2407.16741) | 🆕 开源通用软件 agent 平台 |
| RepairAgent | 2024 | 422 | [arXiv](https://arxiv.org/abs/2403.17134) | 🆕 自主程序修复 agent |
| SpecRover | 2024 | 123 | [arXiv](https://arxiv.org/abs/2408.02232) | 🆕 代码意图提取（LLM 反推规格） |
| **Self-Taught Optimizer (STOP)** | 2023 | 高 | [arXiv](https://arxiv.org/abs/2310.02304) | 🆕 递归自改进代码生成（经典） |
| **PRs as Training Signal** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2602.07457) | 🆕 用 Pull Request 做仓库级编辑训练信号 |
| **OctoLong** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2608.05141) | 🆕 跨仓库上下文长上下文建模 |

## 3️⃣ 自进化/自改进（反馈循环参考）

| 论文 | 年份 | 引用 | 链接 | 一句话 |
|------|------|------|------|--------|
| Promptbreeder | 2023 | 568 | [arXiv](https://arxiv.org/abs/2309.16797) | ⭐ 自我指涉提示词进化（已写单篇） |
| EvoAgent | 2024 | 115 | [arXiv](https://arxiv.org/abs/2406.14228) | 进化算法自动生成多 agent |
| Multi-Agent Design (MAD) | 2025 | 107 | [arXiv](https://arxiv.org/abs/2502.02533) | Google：同时优化 agent prompts + topologies |
| Symbolic Learning Self-Evolving | 2024 | 94 | [arXiv](https://arxiv.org/abs/2406.18532) | 符号学习实现自进化 agent |
| LLMs as Evolutionary Optimizers | 2023 | 242 | [arXiv](https://arxiv.org/abs/2310.19046) | LLM 当进化算子 |
| AlphaCode | 2022 | 2418 | [arXiv](https://arxiv.org/abs/2203.07814) | DeepMind 竞赛代码生成（采样+过滤） |
| **ReasoningBank** | 2025 | 174 | [arXiv](https://arxiv.org/abs/2509.25140) | 🆕 推理记忆扩展自进化 |
| **MemGen** | 2025 | 87 | [arXiv](https://arxiv.org/abs/2509.24704) | 🆕 生成式隐式记忆自进化 |
| **FLEX** | 2025 | 48 | [arXiv](https://arxiv.org/abs/2511.06449) | 🆕 前向学习经验连续进化 |
| **Remember Me, Refine Me** | 2025 | 47 | [arXiv](https://arxiv.org/abs/2512.10696) | 🆕 动态程序性记忆框架（ACL） |
| **ExpeRepair** | 2025 | 40 | [arXiv](https://arxiv.org/abs/2506.10484) | 🆕 双记忆仓库级程序修复 |
| **Self-Improving Code via Semantic Entropy** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2603.29292) | 🆕 语义熵 + 行为一致性自改进 |
| **Self-Evolving Software Agents** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2604.27264) | 🆕 自进化软件 agent |
| **ExeCRE** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2608.04439) | 🆕 执行一致性指导的自修正可靠性估计 |
| **SkillOS** | 2026 | 27 | [arXiv](https://arxiv.org/abs/2605.06614) | 🆕 Skill 策展自进化（skill 生命周期） |
| **Dual-Granularity Skill Bank** | 2026 | 25 | [arXiv](https://arxiv.org/abs/2603.28716) | 🆕 双粒度技能库 agentic RL |
| **Test-Time Self-Improving Agents** | 2025 | 23 | [arXiv](https://arxiv.org/abs/2510.07841) | 🆕 测试时自改进 |
| **Learning on the Job** | 2025 | 22 | [arXiv](https://arxiv.org/abs/2510.08002) | 🆕 经验驱动长时程任务自进化 |

## 4️⃣ 综述与评估方法

| 论文 | 年份 | 引用 | 链接 | 一句话 |
|------|------|------|------|--------|
| A Survey on LLMs for Code Generation | 2024 | 1109 | [arXiv](https://arxiv.org/abs/2406.00515) | 代码生成 LLM 全景综述 |
| MT-Bench / LLM-as-judge | 2023 | 10571 | [arXiv](https://arxiv.org/abs/2306.05685) | LLM 打分评测的开创工作 |
| ChatGPT Code Correctness Eval | 2023 | 2069 | [arXiv](https://arxiv.org/abs/2305.01210) | 严谨评估 LLM 生成代码正确性 |
| Arena-Hard / BenchBuilder | 2024 | 505 | [arXiv](https://arxiv.org/abs/2406.11939) | 众包数据 → 高质量基准 |
| **SoK: Agentic Skills** | 2026 | 98 | [arXiv](https://arxiv.org/abs/2602.20867) | 🆕 Agentic Skills 系统化综述（skill 定义/生命周期） |
| **RAG Code Gen Survey** | 2025 | 新 | [arXiv](https://arxiv.org/abs/2510.04905) | 🆕 仓库级 RAG 代码生成综述 |

## 5️⃣ 文档与代码交互（知识消费参考）

| 论文 | 年份 | 引用 | 链接 | 一句话 |
|------|------|------|------|--------|
| When LLMs Meet API Documentation | 2025 | 新 | [arXiv](https://arxiv.org/abs/2503.15231) | ⭐ 文档注入对 LLM 帮助有限（已写单篇） |
| Spec2RTL-Agent | 2025 | 38 | [arXiv](https://arxiv.org/abs/2506.13905) | ⭐ 规格→硬件代码（已写单篇） |
| Can Developers Prompt? | 2024 | 17 | [arXiv](https://arxiv.org/abs/2408.00686) | 开发者能否用 LLM 生成文档？受控实验 |
| Test Gen from Program Docs | 2025 | 新 | [arXiv](https://arxiv.org/abs/2504.21161) | ⭐ 从注释文档生成测试（已写单篇） |
| Structured CoT for Code | 2023 | 370 | [arXiv](https://arxiv.org/abs/2305.06599) | 结构化思维链提升代码生成 |
| **RepoDoc** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2604.26523) | 🆕 知识图谱驱动的自动文档生成（直接相关！） |
| **Spec-Driven Code Gen 实证** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2601.03878) | 🆕 规格驱动代码生成的实证研究 |
| **Doc vs Code Patterns** | 2026 | 新 | [arXiv](https://arxiv.org/abs/2608.00884) | 🆕 文档 vs 代码模式：异常 oracle 生成驱动因素 |
| **Doc-to-Code Traceability** | 2025 | 新 | [arXiv](https://arxiv.org/abs/2506.16440) | 🆕 文档-代码可追溯性评估 |
| **Lost in the Middle** | 2023 | 4708 | [arXiv](https://arxiv.org/abs/2307.03172) | 🆕 长上下文位置偏差（知识注入位置设计参考） |

## 6️⃣ 其他值得关注的

| 论文 | 年份 | 引用 | 链接 | 一句话 |
|------|------|------|------|--------|
| AutoCodeBench | 2025 | 26 | [arXiv](https://arxiv.org/abs/2508.09101) | LLM 自动生成代码基准 |
| SWE-QA | 2025 | 37 | [arXiv](https://arxiv.org/abs/2509.14635) | 仓库级代码问答评测 |
| FeatureBench | 2026 | 26 | [arXiv](https://arxiv.org/abs/2602.10975) | agent 复杂特性开发基准 |
| FlowBench | 2024 | 50 | [arXiv](https://arxiv.org/abs/2406.14884) | 工作流引导 agent 规划基准 |
| CodeScope | 2023 | 68 | [arXiv](https://arxiv.org/abs/2311.08588) | 执行式多语言多维评测 |
| **RAG Code Gen 安全** | 2025 | 新 | [arXiv](https://arxiv.org/abs/2502.03233) | 🆕 知识库投毒攻击（RAG 代码生成安全） |
| **RepoGraph** | 2024 | 新 | [arXiv](https://arxiv.org/abs/2410.14684) | 🆕 仓库级代码图谱增强 |

## 7️⃣ GitHub 高 star 仓库（⭐≥1000 且活跃维护，按准入标准）

### 规格驱动开发（知识=规格，对应飞轮第二步）
| 仓库 | ⭐ | 最近push | 一句话 |
|------|-----|---------|--------|
| [github/spec-kit](https://github.com/github/spec-kit) | 130k | 2026-08 | GitHub 官方 SDD 工具包（spec-driven development） |
| [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) | 65k | 2026-08 | Spec-driven development for AI coding assistants |
| [modu-ai/moai-adk](https://github.com/modu-ai/moai-adk) | 1177 | 2026-08 | SPEC-driven plan/run/sync + TRUST 5 质量门禁（门禁设计参考） |

### 代码文档与知识（对应飞轮第一步）
| 仓库 | ⭐ | 最近push | 一句话 |
|------|-----|---------|--------|
| [upstash/context7](https://github.com/upstash/context7) | 60k | 2026-08 | LLM/编辑器用的最新代码文档（文档质量 → LLM 表现） |
| [cyberagiinc/DevDocs](https://github.com/cyberagiinc/DevDocs) | 2105 | 2026-02 | 技术文档 MCP server（文档即服务） |
| [MicrosoftDocs/mcp](https://github.com/MicrosoftDocs/mcp) | 1845 | 2026-08 | MS Learn 官方文档 MCP（文档给 LLM 消费） |
| [SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent) | 3399 | 2026-08 | 自维护个人知识库（丢入资料自动建 wiki） |
| [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki) | 1950 | 2026-07 | Karpathy 式 LLM 知识 wiki（Agent Skills 兼容） |

### 自改进/记忆（对应飞轮第三四步）
| 仓库 | ⭐ | 最近push | 一句话 |
|------|-----|---------|--------|
| [letta-ai/letta](https://github.com/letta-ai/letta) | 24k | 2026-08 | 有状态 agent：记忆可学习、随时间自改进 |
| [PrimeIntellect-ai/prime-agent](https://github.com/PrimeIntellect-ai/prime-agent) | 17k | 2026-08 | Self-improving RLM coding agent |
| [facebookresearch/HyperAgents](https://github.com/facebookresearch/HyperAgents) | 2687 | 2026-07 | 自指自改进 agent（可优化任意可计算任务） |
| [jennyzzt/dgm](https://github.com/jennyzzt/dgm) | 2237 | 2025-08 | Darwin Gödel Machine：开放式自改进进化 |
| [hexo-ai/sia](https://github.com/hexo-ai/sia) | 2114 | 2026-07 | Self Improving AI 框架（自动提升任意 AI 系统） |
| [mex-memory/mex](https://github.com/mex-memory/mex) | 1498 | 2026-08 | 项目持久记忆 + **漂移检测 CLI**（差异对比参考） |
| [greyhaven-ai/autocontext](https://github.com/greyhaven-ai/autocontext) | 1281 | 2026-08 | 递归自改进 harness（agent 的 agent 迭代） |
| [metauto-ai/GPTSwarm](https://github.com/metauto-ai/GPTSwarm) | 1036 | 2026-02 | RL/提示优化的自改进 agents |

---

## 📌 观察（头脑风暴视角）

1. **评测基准最多**：代码生成评测是热点，但**文档/知识质量评测仍是空白**——我们的门禁是差异化机会（Code2Doc / Multi-Judge 2026 才刚出现）
2. **自进化方向 2025-2026 爆发**：ReasoningBank/MemGen/FLEX/Remember Me Refine Me/SkillOS 全是记忆与技能策展——**"记忆/技能库"正在成为自进化的标准答案**，与我们"知识库驱动"的思路吻合
3. **文档→代码的价值被低估**：API 文档那篇说"帮助有限"，但 Spec2RTL/RepoDoc 证明"严格规格/知识图谱"有效——**文档质量决定文档价值**，这正是我们做知识工程的立论
4. **Agentless 值得注意**：无 agent 的简单流程效果不输复杂 agent——支持"先简单后复杂"的飞轮策略
5. **规格驱动开发（SDD）2026 爆发**：spec-kit 130k star / OpenSpec 65k star——"知识=规格 → 代码"路线被工业界验证，与我们飞轮第二步直接对应
6. **安全新维度**：RAG 知识库投毒攻击研究出现——知识库可信性成为门禁考虑因素

> 需要深读池子里哪篇，直接告诉我标题就行。
