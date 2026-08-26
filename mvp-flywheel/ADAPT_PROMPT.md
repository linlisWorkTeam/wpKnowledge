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

## 实战问题与对策（必须处理）

以下 4 个问题在真实运行中已出现，适配时必须逐一处理：

### 问题 1：Coder 会绕过目录隔离读源码 → 需要沙箱隔离

目录隔离（workdir 不含源码）挡不住有文件系统权限的 agent。必须加**沙箱隔离**，三选一（能上多重的上多重）：

- **容器隔离（最彻底）**：知识生成阶段容器挂载 `src-biz/`（只读）；飞轮阶段（Coder/Review/评测）容器**不挂载** `src-biz/`，Coder 进程内 `ls` 源码目录必须失败
- **专用用户 + 权限**：源码目录 `chmod 700`，属主为知识生成专用用户；Coder 进程用另一个无读权限的用户运行
- **CLI 沙箱/路径黑名单**：若 codeagent CLI 支持 sandbox、路径黑名单或 access_policy，配置源码路径为禁止访问

**验收**：Coder 会话中执行 `ls src-biz/` 或 `cat <源码文件>` 必须失败；轨迹（JSONL）中无源码文件读取记录。

### 问题 2：知识文档太大导致超时 → 单文档设上限 + 分块

超大模块一次生成整篇文档会超时。规则：

- **单知识文档上限**：建议 ≤ 300 行（约 10KB），超出即拆分
- **分块生成**：一个模块拆多个知识文件（如 `模块_函数A.md`、`模块_函数B.md`），按依赖拓扑逐个生成
- **Coder 按需读**：Coder 不读整篇知识，按修订指令（readlist 的 knowledge_path）只读相关段落/文件
- 知识库目录结构 = 模块目录 + 分函数文件，保持 OKF 格式（每段带 sources）

### 问题 3：知识生成 agent 用 skill 但文档太大超时 → 生成阶段也分块

知识生成同样受输出长度限制。规则：

- **单次生成范围**：一次只生成一个函数/一个小模块的知识，禁止一次生成整个大模块
- **生成顺序**：先骨架（目录 + 每个函数的签名/职责一行）后填充（逐个函数补算法步骤与边界）
- **质量过滤**：每块生成后过质量检查（时效/一致/去重/无源码泄漏），不合格先修再合并
- 超时兜底：单次调用超时后，缩小范围重试（半个模块 → 一个函数）

### 问题 4：Coder 输出说明文字 → prompt 硬约束 + 后处理清洗

Coder 偶尔输出解释文字/Markdown 围栏导致编译失败。双保险：

- **prompt 硬约束**（system prompt 明确写）：
  > 只输出纯代码，禁止输出任何解释、注释说明、Markdown 代码围栏（```）、main()、测试代码。输出必须能直接通过 g++ -Wall -Werror 编译。
- **后处理清洗**（适配器内实现，参考 `llm_roles._extract_code`）：
  1. 有代码围栏 → 提取围栏内代码块（取最长非空块）
  2. 无围栏 → 剥掉 ``` 行和首尾说明文字
  3. 空输出 → 重试（最多 3 次）
  4. 清洗后仍编译失败 → 把编译错误反馈给 codeagent 重写（这轮不算，计入 max_rounds）
- **结构化输出优先**：若 CLI 支持 --json，要求 codeagent 返回 `{"code": "..."}` 字段，从字段取值最稳

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
