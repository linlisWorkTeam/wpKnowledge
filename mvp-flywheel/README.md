# mvp-flywheel · 知识飞轮 MVP（不依托 codeagent）

按《knowledge/2.wiki/设计/codeagent执行手册.md》P0 要求实现的**最小可用版本**，三个 LLM 角色用确定性桩替代，验证编排与评测闭环逻辑。接入 codeagent 时实现 `roles/__init__.py` 的接口替换桩即可。

## 架构

```
源码 ──▶ 知识生成Agent(桩) ──▶ 知识文档 ──▶ Coder(桩) ──▶ 临时代码
   ▲                                                        │
   │                                                        ▼
   知识生成Agent ◀── 修订指令 ◀── 编排层状态机 ◀── 评测闭环 + Review(桩)
```

对应《知识飞轮实现方案.md》§3：3 个执行 agent + 1 个编排层 + 1 个评测闭环。

## 目录

| 路径 | 内容 |
|------|------|
| `fw/` | 编排层（config / runner 状态机） |
| `roles/` | 角色接口（可插拔）+ 桩实现（stubs.py，管道自检）+ **真实 LLM 实现（llm_roles.py，DeepSeek）** |
| `eval/` | 评测闭环（编译必过 + 测试主判 + 相似度辅助）+ holdout 分层 |
| `revise/` | 修订闭环（pending_corrections 队列 + 版本控制/回滚） |
| `samples/` | 示例被测源码（calc / tiling 模块）+ 评测集（探针跑源码拿期望输出） |
| `tests/` | pytest 单测（27 个） |

## 快速开始

```bash
python3 -m pytest tests/ -v        # 跑全部单测（27 个）
python3 demo.py                    # 端到端：calc 模块（示例），一轮通过
python3 demo.py --bad-coder        # calc + 缺陷 Coder，演示修订闭环（R1 失败→R2 通过）
python3 demo_tiling.py             # 端到端：tiling 模块（算子平台真实算法），一轮通过
python3 demo_tiling.py --bad-coder # tiling + 缺陷 Coder，演示修订闭环
python3 demo_llm_full.py           # 全流程真 LLM：知识生成/Coder/Review 全走 DeepSeek
python3 demo_llm_stale.py          # 真 LLM + 过时文档：知识=预置解释型文档（无源码）
```

## 全流程真 LLM 端到端（DeepSeek，非桩）

`roles/llm_roles.py` 提供真实 LLM 实现，严格按飞轮流程：

| 角色 | 实现 | 说明 |
|------|------|------|
| 知识生成 | `LLMKnowledgeGen` | 读源码 → **解释型知识文档（强制不含源码原文）**，标注边界缺陷 |
| Coder | `LLMCoder` | 只读知识 + 接口头文件 → 写代码（信息隔离，不接触源码实现） |
| Review | `LLMReview` | 评测失败详情 → 归因 JSON + 修订指令 |

```bash
python3 demo_llm_full.py  # 全流程真 LLM：源码 → 知识(LLM,无源码) → 代码(LLM) → 评测 → 一轮过
python3 demo_llm_stale.py # 知识=预置过时文档（无源码）：LLM 理解+补全 → 一轮过（8/8）
```

**知识文档形态（红线）**：原始知识文档**不得包含源代码**——只允许签名、职责、算法步骤（自然语言/伪代码）、边界条件。LLM 知识生成 prompt 强制该约束；产物已做泄漏检查（源码特征串零命中）。

实测发现（真实数据）：
- deepseek-v4-flash 约 **40% 概率返回空 content**（已加 `_chat_retry` 空输出重试）
- 生成代码可能混入 Markdown 围栏 / 被 max_tokens 截断（已加 `_extract_code` 健壮清洗 + 8192 tokens）
- 全流程真 LLM 一轮过 8/8（similarity 0.14，非抄源码）；LLM 知识生成**准确标注源码缺陷**（totalLength=0 除零、uint32 回绕），Coder **采纳建议**实现防御（零长分支 + uint64 中间计算）

## 真实业务代码验证（tiling 模块）

`samples/tiling/` 使用 **cannbot add_custom 模板的真实 tiling 算法**（算子平台 Host 侧业务代码，纯 C++ 可本地编译）：

- 被测源码：`samples/tiling/src/add_custom_tiling.cpp`（compute_tiling：totalLength + 核数 → blockNum/numPerCore/tailNumLastCore）
- 评测集：`samples/tiling/evalset/test_tiling.cpp`（8 条用例，期望输出=探针跑真实源码）
- 验证结果：真实算法一轮通过（8/8，similarity 0.73）；缺陷实现（缺 tailNumLastCore）R1 全失败 → 修订 → R2 通过
- 附带发现：原模板 `totalLength=0` 时除零崩溃（真实缺陷，评测集排除崩溃输入）

## 评测集兼容（用户本地测试集）

支持两种评测集形态，`evalset_format=auto` 自动检测：

| 形态 | 目录结构 | 说明 |
|------|---------|------|
| **JSON cases** | `evalset/cases/*.json` | case 带 module/function/args/expected，自动生成 C 测试驱动 |
| **原生测试文件** | `evalset/test_*.c`（或 .cpp） | 用户本地测试集直接编译运行（含 main，逐用例断言，打印 `PASS n/total`） |

**使用本地测试集**（不改代码）：

```bash
python3 demo.py --evalset /你的路径/evalset
```

或代码里配置：

```python
cfg.evalset_dir = Path("/你的路径/evalset")   # 指向本地测试集目录
cfg.evalset_format = "auto"                    # auto 自动检测；也可强制 "json"/"native"
```

- native 模式约定：测试文件含 main，运行后打印 `PASS n/total`（与 JSON 模式同约定；gtest 用户可在测试框架外再打印一行 PASS 汇总）
- native 模式不做 holdout 切分（本地测试集整体作为评测信号，防止误切）
- `native_test_glob` 可配置匹配规则（默认 `test_*.c`，可改 `*.c`/`test_*.cpp`）
- 示例：`samples/evalset_native/test_calc.c`（模拟用户本地测试集形态）

## 评测方法（对应执行手册 §3/§4/§5）

- **编译必过**：gcc -Wall -Werror，失败直接判失败
- **测试主判**：置信度 = 通过用例数 / 总用例数（重复评测取最大通过数）
- **相似度辅助**：文本相似度只进归因报告，不参与门禁
- **holdout**：按模块名哈希分层（holdout_ratio=0.2），holdout 只报告不写回
- **修订闭环**：Review 归因 → pending_corrections 队列 → 修订（版本+1）→ 重测；门禁通过才合并；分数下降回滚

## 接入 codeagent（替换桩）

实现 `roles/__init__.py` 的三个接口（KnowledgeGenAgent / CoderAgent / ReviewAgent），构造时传入：

```python
fw = KnowledgeFlywheel(cfg, knowledge_gen=YourAgent(), coder=YourCoder(), review=YourReview())
```

## 已知限制（MVP）

- 桩场景（demo.py / demo_tiling.py）仅为管道自检：知识=源码摘录，**不符合飞轮知识形态**（真实流程用 demo_llm_full.py）
- 测试驱动生成仅支持 int/double 参数与返回值（可扩展 schema）
- 单模块评测；相似度为文本级（AST 级在 P1）
- 评测集期望输出必须来自源码实际行为（红线），示例集已用探针程序验证
- LLM API 依赖网络与 key（`DEEPSEEK_API_KEY`，环境变量或 ~/.hermes/.env）；空输出已自动重试 3 次
