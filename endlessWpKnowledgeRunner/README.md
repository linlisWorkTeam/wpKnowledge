# endlessWpKnowledgeRunner — 知识飞轮 MVP

打造「简易但功能够强」的知识飞轮：**获取 → 沉淀（OKF）→ 评测（打分）→ 应用（检索）** 的循环。
设计依据与实现说明见 [docs/FLYWHEEL-DESIGN.md](docs/FLYWHEEL-DESIGN.md)（汇总自 wpKnowledge 仓库全部调研）。

- **触发式**：`fw_ingest`（或 CLI `python fw.py ingest` / 向 `sources/` 投递文件）→ 收到知识即运行。
- **自动化**：`fw_livemode on`（或 CLI `python fw.py harvest`）→ harvester agent 自行扫描、提炼、入库。
- **沉淀不用 RAG，用 OKF**：知识卡 = Markdown + YAML frontmatter（sources/status/verified/score），Bundle 目录树即知识库，可 `cat`、可 diff、可 git 评审。
- **评测 = 多信号打分**：溯源 / 结构 / 时效 / 去重 / 可验证性 / 使用反馈（+可选 LLM 陪审团），重复评测报均值±方差，门禁决定 verified 或 draft，防污染自动回滚保护。
- **应用 = 外部检索**：`fw_query` 工具 / CLI `python fw.py query` / HTTP `GET /fw/query?q=...`（DSH 插件加载后）。

## 快速开始（Standalone，零第三方依赖）

```bash
python fw.py init                          # 初始化 store/
python fw.py ingest --file <知识.md> --name <id> --source <溯源路径> --pinned
python fw.py query --q "connecter 适配层"
python fw.py status
python fw.py eval --name <id> --runs 5     # 重复评测：均值±方差
python fw.py feedback --name <id> --action rate --rating 4.5
python fw.py scan                          # liveMode 候选
python fw.py harvest                       # 确定性 liveMode 一轮（无 agent）
```

要求：Python ≥ 3.8（无第三方包）。Windows 下建议 `set PYTHONIOENCODING=utf-8`。

## 加载到 DSH

MVP 以 DSH 动态 Cordis 插件方式加载，注册 `fw_*` 工具与 HTTP 检索端点：

1. 打开 [dsh/fw-plugin.js](dsh/fw-plugin.js) 查看 `code.host`（插件源码与 cordis_define 使用的完全一致）。
2. 在当前 DSH 会话：`cordis_define`（plugin: new, idPrefix: fwrun）→ `cordis_run`。
3. 然后让任意 agent 调用：`fw_ingest`（触发）/ `fw_query`（检索）/ `fw_livemode on`（自动化）。
4. 外部检索：`curl "http://127.0.0.1:3080/fw/query?q=connecter"` 与 `http://127.0.0.1:3080/fw/status`。

> 动态插件随进程生命周期存在；需要永久挂载时，把 plugin 代码放进 agent preset（见 [dsh/plugin-agent-preset.md](dsh/plugin-agent-preset.md)），或在宿主 composition 中注册该插件行。

## 目录

```
fw.py                CLI 入口（python fw.py <cmd>）
fwrunner/            Python 核心：okf / store / ingest / scorer / retrieve / livemode
config.json          门禁阈值 / 信号权重 / 来源目录 / 陪审团开关（可执行级定义）
sources/             投放目录（往里丢 .md 即被 liveMode 拾取）
store/               OKF Bundle 知识库：index.md / log.md / ledger.json（使用反馈）
  drafts/            未过门禁的知识卡
  concepts/          已过门禁的合格知识卡（verified）
  history/           版本升级前的旧版快照（防污染回滚）
  jury/              外部模型写入的陪审团打分 JSON（可选）
dsh/                 DSH 集成：插件源码 + 挂载说明
tests/               python -m unittest discover -s tests
docs/                飞轮设计总结（读完仓库全部调研后的收敛）
```

## 打分与门禁（一句话）

`score = 100 * Σ(权重 × 信号分) / Σ(启用权重)`；`score ≥ 70`（config.json 可配）→ `verified` 合并入库，否则退回 `drafts/` 并给出薄弱点清单；已 verified 概念被更差版本覆盖时自动保留旧版 + 新版退回 drafts（防污染）。