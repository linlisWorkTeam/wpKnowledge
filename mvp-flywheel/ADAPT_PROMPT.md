# 任务：将知识飞轮 MVP（mvp-flywheel）适配到本地环境，接入 codeagent

## 背景

你正在参与"知识飞轮"项目：对超大 C/C++ 业务代码仓库（文档滞后），从源码回推解释型知识文档，并闭环"知识→代码→反馈"迭代。

参考实现位于 `mvp-flywheel/`，已验证流程正确性（知识生成→Coder→评测→Review→修订→重测）。你的任务：把这套流程**适配到本机**——用 codeagent 作为 LLM 执行角色（替换参考实现里的直连 API 调用），并指向本地真实的文档/源码/评测集。

## 参考实现结构（mvp-flywheel/）

| 路径 | 作用 | 是否可改 |
|------|------|---------|
| `fw/runner.py` | 编排状态机（固定流水线：知识生成→Coder 写码→评测→Review 归因→决策→修订→重测） | **不要重写** |
| `fw/config.py` | Config：src_dir / evalset_dir / work_dir / knowledge_dir / compiler / compile_flags / evalset_format / max_rounds 等 | 可改（适配用） |
| `roles/__init__.py` | 三个抽象接口：`KnowledgeGenAgent` / `CoderAgent` / `ReviewAgent` | **适配器必须实现这三个接口** |
| `roles/llm_roles.py` | 参考实现（直接调 DeepSeek API）。可参考其 prompt 设计，但调用方式换成 codeagent CLI | 参考 |
| `eval/__init__.py` | 评测闭环：编译必过（gcc/g++ -Wall -Werror）+ 测试主判（运行测试解析 `PASS n/total`）+ 失败详情捕获（report.failures） | **不要重写** |
| `revise/__init__.py` | 修订闭环（归因入队→知识版本+1→重测） | **不要重写** |

## 硬性要求（红线）

1. **知识文档不得包含源代码**：知识生成输出的知识必须是解释型（签名/职责/算法步骤自然语言或伪代码/边界条件），**严禁复制源码原文**。知识里出现源码函数体 = 失败。
2. **信息隔离**：Coder 只能看到知识文档 + 接口头文件，**不能读源码实现文件**。
3. **目录隔离（防作弊红线）**：被测源码必须放在飞轮项目目录之外（如 `src-biz/`，`chmod -R a-w` 只读）；codeagent 的 workdir 只指向飞轮目录；evalset 内不得存放源码实现文件（只放测试文件）；接口头文件复制到飞轮目录内 `interfaces/`，评测编译 `-I` 指向该目录。
4. **评测集期望输出必须来自源码实际行为**（探针程序跑真实源码拿期望输出），禁止 LLM 编造。
5. 评测集约定：原生测试文件（`test_*.c`/`.cpp`）含 main、逐用例断言、运行后打印 `PASS n/total`。
6. 只改适配层（roles/ 新增 codeagent 实现类 + config），**不要改 fw/、eval/、revise/ 核心逻辑**。

### 目录布局（照此执行）

```text
/workspace/
├── flywheel/            ← codeagent workdir 只在这里
│   ├── knowledge/       ← 知识文档（首版/修订版）
│   ├── interfaces/      ← 接口头文件副本（评测编译 -I 指向）
│   ├── evalset/         ← 只放测试文件 test_*.c/.cpp（期望输出已固化）
│   └── fw/ eval/ roles/
└── src-biz/             ← 业务源码（飞轮目录之外，只读）
```

- 源码只对知识生成 Agent 可见（显式传参）；Coder/Review 的 prompt 与环境不得出现源码路径
- 评测编译命令只引用 interfaces/ + evalset/ + 生成代码，不依赖源码目录
- 若 CLI 支持轨迹（JSONL），编排层审计 Coder 会话中无源码目录读取记录；生成代码与源码相似度 > 0.85 触发疑似抄源码检查

## 适配步骤

1. 阅读 `mvp-flywheel/` 代码，理解三个角色接口的输入输出（KnowledgeDoc / EvalReport / Attribution 数据结构见 `roles/__init__.py`）。
2. **确认 codeagent CLI 能力**（适配前提，先用最小用例验证）：
   - 是否支持非交互模式（一条命令直接出结果，不需要人工确认）
   - 是否支持结构化输出（--json 或类似，能解析出代码/JSON）
   - 能否指定模型
   - 失败/限流时如何表现
3. 实现三个适配器类（放在 `roles/` 下，例如 `roles/codeagent_roles.py`）：
   - **CodeagentKnowledgeGen**：读源码（单文件或目录，一次处理一个模块）→ codeagent 生成解释型知识文档 → 返回 `KnowledgeDoc`。prompt 必须包含"严禁输出源码原文"约束。
   - **CodeagentCoder**：输入 = 知识文档 + 接口头文件（信息隔离）→ codeagent 生成代码 → 写 `.c/.cpp` 文件。要求纯代码输出（无 Markdown 围栏、无 main）。
   - **CodeagentReview**：输入 = 评测报告（含 failures 失败详情）+ 知识文档 → codeagent 归因，输出 JSON（summary / weak_spots / corrections[{id, knowledge_path, criterion, detail}]）。
   - 健壮性：codeagent 输出为空/异常时重试或兜底（参考 `llm_roles.py` 的 `_chat_retry` / `_extract_code` / `_extract_json`）。
4. 配置：`Config` 指向本地源码目录、评测集目录；`compiler` 按实际语言（C 用 gcc，C++ 用 g++）；`evalset_format` 设 auto 或 native。
5. 自验（必须真实执行）：
   - 用本地一个真实模块跑通一轮（知识生成→写码→编译→测试）
   - 人为制造缺陷（如删除一个边界处理）验证修订闭环：R1 失败 → 归因 → 修订 → R2 通过
   - 检查生成的知识文档无源码泄漏（grep 源码特征串，应零命中）

## 验收清单

- [ ] 三个适配器实现 roles 接口，可插入 `KnowledgeFlywheel`（构造时传入）
- [ ] 本地真实模块端到端跑通（知识→代码→编译→测试）
- [ ] 修订闭环验证（缺陷注入后 R1 失败 → R2 通过）
- [ ] 知识文档无源码泄漏（特征串检查零命中）
- [ ] 中间产物落盘（知识 vN、代码 rN、评测 round_N.json）

## 参考

- 角色 prompt 设计参考：`roles/llm_roles.py`（LLMKnowledgeGen / LLMCoder / LLMReview 的 system prompt 可直接复用）
- 数据结构：`roles/__init__.py`（KnowledgeDoc / EvalReport / Correction / Attribution）
- 评测约定：`eval/__init__.py` 与评测集构建指南（附录 C：探针跑源码 → 测试文件 → PASS n/total）
