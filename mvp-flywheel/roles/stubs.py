"""角色确定性桩实现（不依托 codeagent）。

MVP 阶段用规则/模板模拟三个角色，验证编排与评测闭环逻辑。
接入 codeagent 时实现 roles/__init__.py 的接口替换即可。

桩设计（能演示完整飞轮闭环）：
- KnowledgeGenAgent：从源码提取函数签名 + 源码正文作为知识；revise 时按归因补丁更新知识
- CoderAgent：知识 → 临时代码。MVP 用「知识里的源码摘录」生成代码，可注入缺陷模拟迭代
- ReviewAgent：基于评测报告做归因（失败用例 → 对应函数 → 知识段落），只读
"""

import re
from pathlib import Path

from roles import Attribution, Correction, CoderAgent, EvalReport, KnowledgeDoc, KnowledgeGenAgent, ReviewAgent


class StubKnowledgeGen(KnowledgeGenAgent):
    """知识生成桩：源码 → 知识文档。

    知识 = 函数签名 + 源码正文摘录（OKF 风格：伪代码 + 为什么 + sources）。
    """

    def generate(self, module: str, src_file: Path, sources: list) -> KnowledgeDoc:
        src_text = src_file.read_text()
        funcs = _extract_functions(src_text)
        content = f"# {module} 模块知识\n\n"
        content += f"> 来源：{src_file}（sources: {', '.join(s['file'] for s in sources)}）\n\n"
        for name, body in funcs:
            content += f"## 函数 {name}\n\n"
            content += f"```c\n{body}\n```\n\n"
            content += f"- 为什么：{name} 的实现逻辑见上方代码摘录（MVP 桩直接引用源码行为）\n"
            content += f"- 溯源：{sources[0]['file'] if sources else src_file.name}\n\n"
        doc = KnowledgeDoc(module=module, content=content, sources=sources, version=1)
        return doc

    def revise(self, doc: KnowledgeDoc, corrections: list) -> KnowledgeDoc:
        """按归因修订知识（MVP：把 correction 的 detail 追加到知识里，标记补丁）。"""
        content = doc.content
        for c in corrections:
            content += f"\n## 修订补丁 {c.id}\n\n"
            content += f"- 判据：{c.criterion}\n- 详情：{c.detail}\n"
        doc.content = content
        return doc


class StubCoder(CoderAgent):
    """Coder 桩：知识 → 临时代码。

    MVP 策略：从知识文档提取 ```c 代码块，拼接成 .c 文件。
    支持 defect_fn 参数注入缺陷（模拟"知识不完整导致代码出错"），
    用于端到端演示迭代闭环。
    """

    def __init__(self, defect_fn=None):
        self.defect_fn = defect_fn

    def generate_code(self, doc: KnowledgeDoc, out_path: Path) -> Path:
        blocks = re.findall(r"```c\n(.*?)```", doc.content, re.S)
        code = "\n".join(b.strip() for b in blocks)
        # 补充头文件 include（源码头部 #include "xxx.h" 被函数提取跳过，需要恢复）
        for s in doc.sources or []:
            src_path = Path(s["file"])
            if src_path.suffix in (".c", ".cpp", ".cc"):
                head = src_path.read_text()
                includes = re.findall(r'#include\s+"[^"]+"', head)
                for inc in includes:
                    if inc not in code:
                        code = inc + "\n" + code
        # 知识含修订补丁（说明上一轮归因已生效）→ 不再注入缺陷，模拟"知识修订驱动代码修正"
        if self.defect_fn and "修订补丁" not in doc.content:
            code = self.defect_fn(code)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(code)
        return out_path


class StubReview(ReviewAgent):
    """Review 桩：评测报告 → 归因报告。

    归因逻辑：失败用例（passed < total）→ 涉及的函数 → 对应知识段落。
    MVP 桩用启发式：报出涉及失败用例的函数名 + 通用建议。
    """

    def attribute(self, module: str, doc: KnowledgeDoc, report: EvalReport) -> Attribution:
        corrections = []
        weak = []
        # 编译失败：直接归因到整个模块
        if not report.compile_ok:
            corrections.append(Correction(
                id=f"{module}-compile-1",
                knowledge_path=f"{module} 模块",
                criterion="生成代码必须通过编译（gcc -Wall -Werror）",
                detail="编译错误：" + "; ".join(report.compile_errors[:3]),
            ))
            weak.append(f"{module}: 编译失败")
            return Attribution(module=module, corrections=corrections, weak_spots=weak,
                               summary="编译失败，需要先修复编译错误")

        failed = report.total - report.passed
        if failed > 0:
            corrections.append(Correction(
                id=f"{module}-test-1",
                knowledge_path=f"{module} 模块函数实现",
                criterion=f"测试通过率需达 {report.passed}/{report.total}",
                detail=f"有 {failed} 条用例失败，当前置信度 {report.confidence:.2f}，"
                       f"需要检查知识中函数实现与源码行为的一致性",
            ))
            weak.append(f"{module}: 测试失败 {failed} 条")
        return Attribution(module=module, corrections=corrections, weak_spots=weak,
                           summary=f"置信度 {report.confidence:.2f}，相似度 {report.similarity:.2f}")


def _extract_functions(src_text: str) -> list:
    """从 C 源码提取函数定义（简化：按 '返回类型 函数名(...) {' 模式切分）。"""
    funcs = []
    pattern = re.compile(
        r"^(?P<ret>[A-Za-z_][\w\s\*]*?)\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^;]*?)\)\s*\{(?P<body>.*?)^\}",
        re.M | re.S,
    )
    for m in pattern.finditer(src_text):
        # 跳过 main 和明显不是定义的
        name = m.group("name")
        if name in ("main", "if", "while", "for", "return"):
            continue
        if "static" in m.group("ret") or "typedef" in m.group("ret"):
            continue
        funcs.append((name, m.group(0).strip()))
    return funcs
