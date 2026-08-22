# 知识飞轮实现方案（Implementation Plan）

> 最后更新：2026-08-21
> 用途：给 GLM 5.1 照着搭建的工程实现方案。目标 = 跑通飞轮 MVP，先在小规模（单个模块/仓库）上验证闭环收敛，再扩展。
> 前置设计：本方案严格对齐 [flywheel.md](flywheel.md)（角色分工/溯源归因/反馈结构）、[gate.md](gate.md)（门禁/评测闭环）、[knowledge-format.md](knowledge-format.md)（知识形态/溯源要求）。

---

## 0. 一句话目标

**搭一个能跑的飞轮 MVP**：源码 → 知识 → 代码 → 评测 → 归因 → 知识修改 → 再生成，直到基于知识生成的代码与源码相似度 ≥ 80%（或达迭代上限）。

## 1. 技术栈与约束

| 项 | 选择 | 说明 |
|----|------|------|
| 语言 | Python 3.11+ | 全项目统一 |
| 模型 | 公司本地 GLM 5.1 | 唯一可用模型，所有 LLM 调用走同一 client |
| 模型接口 | OpenAI 兼容 API（假设） | 若公司端点不兼容 OpenAI 格式，按实际 SDK 封装，client 层隔离 |
| 存储 | 本地文件系统 + JSONL | 会话/记录用 JSONL，知识文档是 Markdown 文件 |
| 版本控制 | git | 知识文档变更走 git，支撑防污染回滚 |
| 相似度 | difflib（文本）+ tree-sitter（AST，Phase 3 加） | 先文本 diff，后续 AST 结构比对 |
| 测试 | pytest | 每个模块 TDD |

**核心约束（设计硬规则，实现时必须遵守）**：

1. 三角色分离：Coder 不验证自己输出；Review 只读；知识生成 Agent 是唯一执笔者；知识飞轮只决策不执笔
2. 溯源链接：每段知识带 sources（文件:行/函数），是归因的锚
3. 反馈两层：结构化信号（diff/相似度/测试结果）+ Review 自然语言归因
4. 防污染：未过门禁的知识变更不合并，门禁分数下降自动回滚
5. 门禁可靠性：重复评测 ≥5 次报告均值±方差；评测集独立；防背源码

---

## 2. 目录结构

```
flywheel/                          # 项目根（新建，独立于 wiki 仓库）
├── README.md
├── pyproject.toml
├── config.yaml                    # 模型端点、门禁阈值、路径
├── flywheel/
│   ├── __init__.py
│   ├── cli.py                     # 命令行入口（见 §4）
│   ├── config.py                  # 配置加载
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py              # GLM 5.1 客户端封装（唯一 LLM 入口）
│   │   └── prompts.py             # 各角色 prompt 模板（知识生成/Coder/Review）
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── format.py              # OKF frontmatter 读写（sources/status/verified）
│   │   ├── generator.py           # 知识生成 Agent：源码 → 知识文档
│   │   └── loader.py              # 知识文档加载与索引（按 sources 反查）
│   ├── coder/
│   │   ├── __init__.py
│   │   └── coder.py               # Coder Agent：知识 → 临时代码
│   ├── review/
│   │   ├── __init__.py
│   │   ├── differ.py              # 代码 diff 定位（文件:行级）
│   │   ├── attributor.py          # 溯源归因：diff 位置 → 文档段落
│   │   └── feedback.py            # 反馈生成：结构化 + NL 归因
│   ├── gate/
│   │   ├── __init__.py
│   │   ├── evaluator.py           # 评测闭环：用例集驱动
│   │   ├── similarity.py          # 相似度计算（文本 → AST）
│   │   └── confidence.py          # 置信度 = f(通过用例数)
│   ├── flywheel/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # 编排层：读置信度+归因 → 决策改哪段
│   │   └── state.py               # 迭代状态（轮次/门禁分数/历史）
│   └── storage/
│       ├── __init__.py
│       ├── session.py             # JSONL 会话/记录存储
│       └── repo.py                # 知识文档 git 版本控制（提交/回滚）
├── tests/                         # pytest 单元测试（镜像 flywheel/ 结构）
│   ├── test_format.py
│   ├── test_similarity.py
│   ├── test_attributor.py
│   └── ...
└── workdir/                       # 运行产物（不入 git）
    ├── source/                    # 目标源码快照（PoC 阶段小模块）
    ├── knowledge/                 # 生成的知识文档
    ├── generated/                 # Coder 生成的临时代码
    ├── reports/                   # 评测报告（JSONL）
    └── sessions/                  # 会话记录
```

---

## 3. 模块设计与接口

### 3.1 llm/client.py — GLM 5.1 唯一入口

```python
class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str): ...

    def chat(self, messages: list[dict], temperature: float = 0.2,
             max_tokens: int = 8192) -> str:
        """单次对话，返回文本。messages = OpenAI 格式。"""

    def chat_json(self, messages: list[dict], schema: dict) -> dict:
        """要求 JSON 输出（结构化信号用），解析失败重试 N 次。"""
```

- 所有角色（知识生成/Coder/Review/编排）都通过这一个 client 调模型，不各自直连
- `chat_json` 用于需要结构化输出的环节（frontmatter 生成、归因结果、决策输出）

### 3.2 knowledge/format.py — OKF frontmatter

知识文档 = Markdown + YAML frontmatter（对齐 OKF）：

```yaml
---
name: parser-boundary-handling
description: parser 空输入边界处理逻辑
sources:                       # 溯源链接（必须，归因锚点）
  - file: src/utils/parser.py
    lines: 120-135
    function: parse_input
status: draft                  # draft | verified
verified: false
version: 1
---
# 边界处理

## 伪代码
if input is empty: return default

## 为什么
兼容空输入是历史需求 #452
```

接口：

```python
def parse_frontmatter(text: str) -> tuple[dict, str]: ...
def build_frontmatter(meta: dict) -> str: ...
def extract_sources(doc: dict) -> list[SourceRef]: ...   # 解析 sources 字段
def find_paragraph_by_source(doc: dict, source: SourceRef) -> str:
    """按溯源定位文档段落（归因用）"""
```

### 3.3 knowledge/generator.py — 知识生成 Agent

```python
class KnowledgeGenerator:
    def __init__(self, llm: LLMClient, skill_path: str): ...

    def generate(self, source_file: str, source_code: str,
                 context: list[SourceRef] | None = None) -> KnowledgeDoc:
        """源码 → 知识文档。加载知识生成 skill 的 prompt，输出带 frontmatter 的 Markdown。"""

    def revise(self, doc: KnowledgeDoc, feedback: Feedback) -> KnowledgeDoc:
        """按反馈修改文档（只改归因定位的段落）。"""
```

- prompt 要点（放在 prompts.py）：保留逻辑"魂"（边界/数据结构/调用关系），丢命名/格式/样板；每段标注 sources；伪代码 + 为什么
- `revise` 只改反馈指向的段落，不动其他内容（溯源反向映射）

### 3.4 coder/coder.py — Coder Agent

```python
class Coder:
    def __init__(self, llm: LLMClient): ...

    def generate(self, knowledge: KnowledgeDoc,
                 requirement: str) -> GeneratedCode:
        """只基于知识文档写代码。不接触源码。返回代码 + 输出文件路径。"""
```

- 约束：不验证自己输出、不修改知识、不迭代（编排层管迭代）

### 3.5 gate/ — 评测闭环

```python
class Evaluator:
    def __init__(self, similarity: Similarity, confidence: Confidence): ...

    def evaluate(self, generated: GeneratedCode, golden: GoldenCode,
                 tests: list[TestCase] | None) -> EvalReport:
        """多信号评测：相似度（必）+ 编译检查（必）+ 测试（有则用）。"""

class Similarity:
    def text_similarity(self, a: str, b: str) -> float: ...   # difflib，Phase 3 加 AST
    def ast_similarity(self, a: str, b: str) -> float: ...    # tree-sitter 结构比对

class Confidence:
    def compute(self, report: EvalReport) -> float:
        """置信度 = 通过用例数 / 总用例数（TDD 转正后主信号）。"""
```

EvalReport（JSON 结构，落 reports/）：

```json
{
  "run_id": "uuid",
  "similarity": {"text": 0.72, "ast": null},
  "compiles": true,
  "tests": {"passed": 5, "total": 8},
  "confidence": 0.625,
  "diff_locations": [{"file": "src/utils/parser.py", "line": 120, "kind": "missing_branch"}]
}
```

### 3.6 review/ — 差异对比与归因

```python
class Differ:
    def diff(self, generated: str, golden: str) -> list[DiffHunk]:
        """文件:行级 diff 定位，输出差异块。"""

class Attributor:
    def attribute(self, hunks: list[DiffHunk], knowledge: KnowledgeDoc) -> Attribution:
        """diff 位置 → 溯源反查 → 定位到知识文档段落。"""

class FeedbackGenerator:
    def generate(self, attribution: Attribution, report: EvalReport) -> Feedback:
        """两层反馈：
           结构化：diff 位置 + 相似度 + 测试结果
           NL：差异原因 + 建议改文档哪部分（例：'§3.2 缺边界处理说明'）"""
```

### 3.7 flywheel/orchestrator.py — 编排层（只决策）

```python
class Orchestrator:
    def __init__(self, generator, coder, evaluator, feedback, repo, config): ...

    def run(self, module: ModuleTarget, max_rounds: int = 5) -> RunResult:
        for round in range(max_rounds):
            doc = generator.generate(module.source)          # 首轮；后续轮 = revise
            code = coder.generate(doc, module.requirement)
            report = evaluator.evaluate(code, module.golden, module.tests)
            if report.confidence >= self.threshold:          # 通过门禁
                repo.commit(doc, "verified")                 # 合并
                return RunResult(converged=True, report=report)
            if report.confidence < self.last_confidence:     # 倒退 → 回滚
                repo.rollback()
            attribution = attributor.attribute(report.diff_locations, doc)
            feedback = feedback_gen.generate(attribution, report)
            doc = generator.revise(doc, feedback)            # 知识生成 Agent 执笔
            self.state.record(round, report)                 # 记录轮次
        return RunResult(converged=False, report=last_report)
```

决策规则（编排层只做这些）：
1. 置信度 ≥ 门限 → 通过，提交知识（git commit + status=verified）
2. 置信度 < 门限 → 生成反馈，让知识生成 Agent 改
3. 置信度低于上一轮 → 回滚到上一版知识再改（防污染）
4. 达迭代上限 → 停止，报告未收敛

### 3.8 storage/session.py — 会话记录

每次运行写一条 JSONL 记录（追加）：

```json
{"ts": "...", "run_id": "...", "round": 1, "action": "generate|revise|evaluate",
 "confidence": 0.62, "diff_hunks": 5, "files": ["src/utils/parser.py"]}
```

用途：复盘每轮变化、支持 §9 可靠性要求（多轮均值±方差统计）。

---

## 4. CLI 入口（cli.py）

```bash
flywheel init                     # 初始化 workdir/config
flywheel gen <source_file>        # 单步：知识生成（调试用）
flywheel code <doc> <req>         # 单步：Coder 生成
flywheel eval <gen> <golden>      # 单步：评测
flywheel run <module>             # 整轮飞轮（主入口）
flywheel status                   # 查看当前迭代状态/历史
```

每个子命令可独立跑，便于分阶段调试；`run` 串起全流程。

---

## 5. 分阶段实施（每个阶段有验收标准）

### Phase 0：骨架与配置（0.5 天）
- 建目录结构、pyproject.toml、config.yaml、cli.py 骨架
- 实现 `config.py` + `llm/client.py`（chat/chat_json）
- 验收：`flywheel init` 成功；`LLMClient.chat("hi")` 能调通 GLM 5.1 并返回

### Phase 1：知识格式与生成（1 天）
- 实现 `knowledge/format.py`（frontmatter 读写、sources 解析）
- 实现 `knowledge/generator.py` 的 `generate()` + prompts.py 知识生成 prompt
- 验收：对一个真实小模块（如 200 行以内的单文件），生成的知识文档带完整 frontmatter + 每段 sources，人读能还原逻辑

### Phase 2：Coder + 评测（1 天）
- 实现 `coder/coder.py`、`gate/similarity.py`（文本）、`gate/evaluator.py`（相似度 + 编译）、`gate/confidence.py`
- 验收：知识文档 → 生成代码 → 与源码算出相似度分数，分数合理（同样代码 = 1.0，不同代码 < 0.5）

### Phase 3：归因与反馈（1 天）
- 实现 `review/differ.py`、`review/attributor.py`、`review/feedback.py`
- 相似度加 AST 比对（tree-sitter）
- 验收：人为删掉知识文档某段 → 生成的代码出现对应差异 → 归因能定位回该段

### Phase 4：编排闭环（1 天）
- 实现 `flywheel/orchestrator.py`、`flywheel/state.py`、`storage/session.py`、`storage/repo.py`（git 提交/回滚）
- 验收：`flywheel run` 完整跑 3 轮，日志显示置信度变化曲线；手动制造知识缺陷能观察到"归因 → 修订 → 分数回升"

### Phase 5：PoC 验证（1-2 天）
- 选 1 个真实小模块（≤500 行、有边界逻辑的纯函数模块最好）
- 跑 5 轮迭代，记录每轮置信度
- 按 §9 要求重复 ≥5 次，报告均值 ± 方差
- 验收标准：
  1. 收敛：多数模块置信度从初始值提升到 ≥80% 或明显上升趋势
  2. 可归因：每轮反馈都能定位到具体文档段落
  3. 无污染：未过门禁的版本未合并，倒退轮次正确回滚
- 产出：PoC 报告（每轮数据 + 收敛曲线 + 结论）

---

## 6. 与设计文档的对应关系

| 设计要点 | 设计文档 | 本方案实现位置 |
|---------|---------|---------------|
| 三角色分离 + 只读原则 | flywheel.md §3, gate.md §3.6 | coder/ review/ 各自独立，编排层只决策 |
| 知识生成 Agent 唯一执笔 | flywheel.md §3.1 | generator.py 的 generate/revise |
| 溯源链接反向映射 | flywheel.md §4 | knowledge/format.py + review/attributor.py |
| 两层反馈 | flywheel.md §5 | review/feedback.py |
| 门禁 80% + 多信号 | gate.md §2/§3.5 | gate/evaluator.py（相似度+编译+测试） |
| 用例集驱动 | gate.md §3.6 | gate/evaluator.py + confidence.py |
| 防污染回滚 | flywheel.md §9.5 | storage/repo.py + orchestrator 决策规则 3 |
| 重复评测 ≥5 次 | flywheel.md §9.1 | storage/session.py 记录 + Phase 5 统计 |
| TDD 方案（探讨中） | gate.md §7 | confidence.py 预留"通过用例数/总数"，UT 有则用 |

---

## 7. 待确认事项（实现前/中需要用户拍板）

| # | 事项 | 影响 | 当前默认 |
|---|------|------|---------|
| 1 | GLM 5.1 调用方式 | Phase 0 能否开始 | 假设 OpenAI 兼容；若不是，改 client 层 |
| 2 | 相似度指标 | Phase 2 | 文本 diff 先行，AST 后续 |
| 3 | 用例集来源 | Phase 2/5 | PoC 阶段用手工 3-5 个用例 + 源码自带测试 |
| 4 | 门禁阈值 | Phase 4 | 0.80（可配置） |
| 5 | 迭代上限 | Phase 4 | 5 轮 |
| 6 | 切分策略（上亿行） | 扩展期 | PoC 只做单模块，不涉及 |

---

## 8. 风险与注意

1. **GLM 5.1 能力未知**：知识生成质量和归因准确度没验证过 → PoC 优先测这两环
2. **相似度误判**：功能等价但写法不同会被文本 diff 误杀 → 多信号组合 + AST 补位
3. **飞轮跑偏**（Fragility）：规格模糊会"自信地改进到错误方向" → 门禁定义到可执行级别、重复评测
4. **防作弊**：公开源码模型可能"背"过 → PoC 用私有/变换代码，评测集独立
5. **成本**：每轮多次 LLM 调用（生成/生成代码/归因/修订）→ 控制 max_rounds + 单模块起步
