# endlessWpKnowledgeRunner 飞轮实现分析

## 研究信息

- 日期：2026-08-22
- 研究对象：`D:\AI\wpKnowledge\endlessWpKnowledgeRunner`
- 源码基线：`c8f1d8d25b39edfeea0c9aa712f8b541159a6872`
- 研究方式：源码阅读、stdlib unittest、CLI 冒烟、隔离临时目录行为验证
- 结论性质：本地实现分析，不等同于生产部署验收

## 一句话结论

当前飞轮不是“Agent 自己修改知识库”的自治系统，而是一个由 Agent 提交候选、Python runner 负责确定性治理的知识生产管道：

`ingest / liveMode 获取 -> OKF 规范化 -> 多信号评分 -> gate 门禁 -> verified 或 draft -> BM25 检索 -> 使用反馈回流`。

MVP 的闭环骨架已经成立，且零第三方 Python 依赖、可审计、可 diff、可回滚；但“质量判断”目前主要是文档形态和证据锚点的启发式评分，尚未实现代码—知识语义一致性验证、自动归因修订、可靠并发存储或生产级调度。

## 1. 实际数据流

### 1.1 入口层

`fw.py` 提供 `init`、`ingest`、`score`、`eval`、`query`、`get`、`status`、`scan`、`harvest`、`feedback` 十个 CLI 命令（`endlessWpKnowledgeRunner/fw.py:49-193`）。每次命令都重新加载 JSON 配置，创建 `Store` 和 `Scorer`，然后调用对应模块。

DSH 插件只是薄适配层：通过 shell 服务执行 `python fw.py ...`，把 stdout JSON 转回工具结果；知识写入仍由 Python 核心完成（`endlessWpKnowledgeRunner/dsh/fw-plugin.js:33-68`）。

### 1.2 获取与沉淀

`Ingester.run` 的顺序是：

1. 读取文件、stdin 或文本；
2. 解析已有 frontmatter；
3. 补全 `name/title/description/sources/status/version` 等元数据；
4. 创建临时 draft 视图并评分；
5. `score >= threshold` 时写入 `store/concepts/`，否则写入 `store/drafts/`；
6. 更新 `log.md`、`index.md`、`ledger.json`，并登记内容 hash（`endlessWpKnowledgeRunner/fwrunner/ingest.py:54-225`）。

已 verified 的概念如果收到更差的新版本，不会被覆盖：旧版本保留在 `history/<name>/vN.md`，新内容退回 drafts（同文件 `:136-204`）。这是当前最重要的反污染保护。

### 1.3 Store 是文件系统 Bundle

Store 目录结构是：

- `concepts/`：通过门禁的知识卡；
- `drafts/`：未通过门禁的候选；
- `history/`：verified 版本升级前的快照；
- `index.md`：自动生成的可读索引；
- `log.md`：追加式操作日志；
- `ledger.json`：内容 hash、命中、评分、纠错反馈；
- `.livemode-state.json`：liveMode 的文件处理游标（`endlessWpKnowledgeRunner/fwrunner/store.py:49-71`、`:224-277`）。

因此它更像 Git 可审查的知识目录，而不是数据库或向量库。

## 2. OKF 格式层

每张知识卡是 Markdown 正文 + YAML-like frontmatter，核心字段包括 `schema_version`、`name`、`sources`、`status`、`verified`、`score`、`version`、`updated_at`。实现自己维护了一个无第三方依赖的 YAML 子集解析器和 emitter（`endlessWpKnowledgeRunner/fwrunner/okf.py:81-222`）。

支持：标量、内联列表、块列表、简单的列表映射、少量 block scalar，以及 `sources` 的字符串/映射归一化（同文件 `:225-245`）。

边界：它不是完整 YAML parser，也没有独立 schema 校验；复杂 YAML、转义、带逗号的复杂内联值等情况不应假定完全兼容。`ingest.py` 中定义的 `REQUIRED_META` 目前没有被用作硬性校验。

## 3. 评分与门禁

默认门禁为 70 分，默认权重来自 `config.json`：

| 信号 | 权重 | 当前实际判断 |
|---|---:|---|
| provenance | 0.25 | frontmatter、sources、锚点和路径/URL 是否可解析 |
| structure | 0.20 | name、description、`##`、代码块/列表、解释性词、长度、与 source 的相似度 |
| freshness | 0.10 | `updated_at` 和 `stale_after` 衰减 |
| dedup | 0.10 | 内容 hash 和正文重复 |
| verifiability | 0.05 | URL、代码围栏、命令、数字/指标等锚点 |
| jury | 0.20 | 可选的外部 JSON jury，多次运行均值/方差 |
| usage | 0.10 | 查询命中、rating、correct、最近使用时间 |

复合分是所有已启用信号的加权平均再乘 100；jury 未启用时，其权重会被剩余信号重新归一化（`endlessWpKnowledgeRunner/fwrunner/scorer.py:220-283`）。

当前 `jury.enabled=false`，所以实际 gate 主要由 provenance、structure、freshness、dedup、verifiability、usage 决定。所谓 confidence 在无 jury 时固定为 0.9，不是经过统计校准的置信度。

评分器的优点是可解释：每个信号都会产生 weak points，例如缺来源、缺验证锚点、正文过短、超过 stale_after。重复评测 `eval` 会报告 mean/std/min/max，但由于默认信号是纯确定性的，重复运行得到 `std=0` 只能说明当前实现稳定，不说明知识本身正确（`scorer.py:285-303`）。

## 4. 应用与反馈回流

### 4.1 检索

Retriever 为每张卡索引 `name/title/description/tags/body`，字段有不同 boost；查询时计算简化 BM25，再与知识卡质量分混排：

`rank = normalized_bm25 * (1 - quality_weight) + score/100 * quality_weight`

默认只检索 verified，draft 必须显式开启；支持 category/platform/status 过滤（`endlessWpKnowledgeRunner/fwrunner/retrieve.py:27-113`）。

### 4.2 反馈

搜索默认将返回结果全部记录为 `hit`；`get` 也记录 hit；用户可额外提交 `rate` 或 `correct`。usage signal 大致按命中次数上升、rating 修正、correct 扣分，并按 90 天衰减（`endlessWpKnowledgeRunner/fwrunner/store.py:148-189`）。

这使“被使用”可以影响下一次评分，但目前还不是完整的修订闭环：`correct` 只减少 usage 分，没有生成问题单、定位来源、启动修订或重新入库。

## 5. liveMode 与 DSH

Python 侧 `scan` 遍历 `source_dirs + watch_dirs`，只看 Markdown，跳过 `.git`、`__pycache__`、`node_modules` 等目录和 README/index/log 等文件；按 SHA-256 判断新增或变更，并按 mtime 升序返回候选（`endlessWpKnowledgeRunner/fwrunner/livemode.py:21-59`）。

DSH 侧定时器执行：

`scan -> harvester subagent 提炼结构化 JSON -> fw_ingest -> score/gate`。

如果 harvester 失败，则回退为直接 ingest 原始文件；`with_agent=false` 时也是确定性原文模式（`endlessWpKnowledgeRunner/dsh/fw-plugin.js:112-162`）。调度器是 DSH 进程内 timer，动态插件生命周期结束或宿主重启后不会继续运行；状态只保存文件游标，不保存可靠任务队列或重试记录。

当前 DSH HTTP 入口实际注册为 `/flywheel/query` 和 `/flywheel/status`（`dsh/fw-plugin.js:417-455`）；部分 README 仍写 `/fw/query`，文档与实现存在漂移。

## 6. 当前实测结果

在基线 commit 上运行：

- `python -m unittest discover -s tests -v`：15/15 通过；
- `python fw.py status --json`：4 张卡，3 verified，1 draft，平均分 76.3，5 条反馈事件；
- `python fw.py query --q connecter --no-feedback --json`：返回 3 张 verified 卡，`workpanel-connecter` 排名第一；
- `python fw.py eval --name workpanel-connecter --runs 5 --json`：mean 95.8、std 0、5 次均 pass。

这里还暴露一个重要现象：卡片当前保存的 score 是 93.0，但评测实时计算为 95.8。这是因为 usage ledger 已变化，而卡片 frontmatter 不会随反馈自动重算；必须显式执行 `score`。因此“卡片显示分”和“当前动态分”可能暂时不一致。

隔离临时目录验证还得到：

- `tokenize("alpha alpha alpha")` 只返回一个 `alpha`，所以 BM25 的词频实际上被文档内去重削弱为近似二值特征；
- CJK 名称的 `slugify` 使用 Python 内置 `hash()`，跨进程对同一名称会产生不同 ID；
- `force_draft` 产生的 draft 即使之后 `score` 报告 gate=pass，`score_one` 也只更新分数字段，不会把它迁移到 `concepts/`。

## 7. 主要风险与优先级

### P0：并发写入没有事务或锁

`ledger.json`、知识卡、日志和索引都是直接写文件；没有文件锁、临时文件 rename、版本检查或事务。DSH timer、外部 CLI、HTTP 请求同时执行时，可能出现 ledger 最后写入覆盖、重复入库或 index 与卡片不一致（`store.py:118-146`、`dsh/fw-plugin.js:33-68`）。

### P1：评分结果与状态迁移分离

`score`/`eval` 可以发现 pass，但只有 `ingest` 执行 gate 后才会迁移 draft/verified。这会造成“报告说 pass、卡片仍在 drafts”或动态分与保存分不一致。应统一一个带状态迁移策略的 rescore/review 命令，并记录审计事件。

### P1：检索质量和 ID 稳定性

Tokenizer 去重词频，削弱 BM25；CJK fallback 使用进程随机 hash，可能导致同一标题跨进程生成不同概念 ID。应保留 token frequency，并改用稳定 hash（如 SHA-256 截断）。

### P1：反馈信号容易被系统行为放大

一次查询会把所有返回结果都记为 hit，而不是只记录用户实际消费的结果；这会让“被排序出来”被误当成“被使用”。应区分 impression、open、use、rating、correction，并只让有明确消费证据的事件进入 usage。

### P1：来源可信度仍是声明式的

`pinned`、`lines`、`commit` 和 URL 主要由调用方提供；URL 被视为可解析，不会在评分时拉取或校验内容，文件来源也没有记录 source hash/commit 内容。provenance 分高不等于来源事实已被外部复核。

### P1：Jury 和“重复评测”尚未形成真正外部验证

Jury 只是读取 `store/jury/<name>.json`，默认关闭；`eval` 重复同一确定性函数。当前系统缺少独立评测集、代码/文档一致性测试、来源反向归因和基于失败反馈的自动修订。

### P2：DSH 适配层的运维与安全边界

- `RUNNER_ROOT` 硬编码为 `D:/AI/wpKnowledge/endlessWpKnowledgeRunner`；
- shell 命令通过字符串拼接构造，参数转义只处理空格和双引号，未覆盖完整 shell 元字符；
- HTTP 查询参数手工 split，未使用标准 URL parser；
- HTTP 入口没有认证、限流或审计身份；
- liveMode timer 不是持久调度器，宿主重启后需要重新启用。

## 8. 建议的后续路线

1. 先做存储可靠性：文件锁或单写入队列、原子写、ledger 版本检查、操作幂等键。
2. 修正确定性基础：token frequency、稳定 slug、完整 YAML/明确 schema 校验、统一 rescore/gate 迁移。
3. 把 feedback 改为事件模型：impression/open/use/rating/correction，建立真实消费证据和可追溯修订任务。
4. 增加代码—知识强评测：source hash/commit、代码符号/行号校验、测试命令执行结果、失败后归因修订。
5. 最后再扩展调度：持久任务队列、失败重试/退避、跨进程锁、状态面板和 HTTP 认证；不要把当前 DSH timer 当生产 scheduler。

## 证据边界

本报告证明了当前本地源码行为和本机 MVP 回归测试，不证明：多进程并发安全、真实 DSH 宿主加载、HTTP 对外暴露安全、跨机器 liveMode、LLM jury 质量、来源 URL 的真实性或生产长期运行稳定性。

