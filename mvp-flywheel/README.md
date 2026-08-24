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
| `roles/` | 角色接口（可插拔）+ 桩实现（stubs.py） |
| `eval/` | 评测闭环（编译必过 + 测试主判 + 相似度辅助）+ holdout 分层 |
| `revise/` | 修订闭环（pending_corrections 队列 + 版本控制/回滚） |
| `samples/` | 示例被测源码（calc 模块 C）+ 评测集（探针跑源码拿期望输出） |
| `tests/` | pytest 单测（14 个） |

## 快速开始

```bash
python3 -m pytest tests/ -v        # 跑全部单测（27 个）
python3 demo.py                    # 端到端：calc 模块（示例），一轮通过
python3 demo.py --bad-coder        # calc + 缺陷 Coder，演示修订闭环（R1 失败→R2 通过）
python3 demo_tiling.py             # 端到端：tiling 模块（算子平台真实算法），一轮通过
python3 demo_tiling.py --bad-coder # tiling + 缺陷 Coder，演示修订闭环
```

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

- 角色为确定性桩：知识生成 = 源码摘录；Coder = 知识代码块拼接；Review = 失败用例启发式归因
- 测试驱动生成仅支持 int/double 参数与返回值（可扩展 schema）
- 单模块评测；相似度为文本级（AST 级在 P1）
- 评测集期望输出必须来自源码实际行为（红线），示例集已用探针程序验证
