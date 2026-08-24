"""LLM 角色实现：Coder / Review 走真实 DeepSeek API（知识生成保留桩）。

对应《codeagent执行手册》角色约定：
- Coder Agent：知识 → 临时代码；信息隔离（不读源码实现，只看知识 + 接口头文件）
- Review Agent：评测报告（含失败详情）→ 归因 + 修订指令；只读

用法：
  from roles.llm_roles import LLMCoder, LLMReview
  fw = KnowledgeFlywheel(cfg, knowledge_gen=StubKnowledgeGen(),
                         coder=LLMCoder(), review=LLMReview())
"""

import json
import os
import re
import urllib.request
from pathlib import Path

from roles import (Attribution, Correction, CoderAgent, EvalReport, KnowledgeDoc,
                   KnowledgeGenAgent, ReviewAgent)

DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE = "https://api.deepseek.com/v1"


def _load_key() -> str:
    """取 DeepSeek API key：环境变量优先，其次 ~/.hermes/.env。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    env = Path.home() / ".hermes" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DEEPSEEK_API_KEY 未配置（环境变量或 ~/.hermes/.env）")


def _chat(messages: list, temperature: float = 0.2, max_tokens: int = 8192,
          model: str | None = None) -> str:
    """调用 DeepSeek chat completions（OpenAI 兼容）。"""
    url = (os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE) + "/chat/completions"
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_load_key()}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _chat_retry(messages: list, temperature: float = 0.2, max_tokens: int = 8192,
                model: str | None = None, attempts: int = 3) -> str:
    """调用 DeepSeek，空输出自动重试（实测 flash 模型约 40% 概率返回空 content）。"""
    last = ""
    for i in range(attempts):
        reply = _chat(messages, temperature, max_tokens, model)
        if reply and reply.strip():
            return reply
        last = reply
    return last


def _extract_code(text: str) -> str:
    """从 LLM 输出提取代码；健壮处理各种输出形态。

    优先级：闭合代码块（取最长）→ 剥掉围栏残留 → 纯文本。
    空代码块/空文本视为无效（返回空串，调用方写入前应校验）。
    """
    if not text or not text.strip():
        return ""
    blocks = re.findall(r"```(?:c|cpp|c\+\+)?\n(.*?)```", text, re.S)
    if blocks:
        # 过滤空代码块，取最长的非空块
        non_empty = [b for b in blocks if b.strip()]
        if non_empty:
            return max(non_empty, key=len).strip()
    # 未闭合围栏 / 无围栏：剥掉 ``` 行，取剩余内容
    cleaned = re.sub(r"^```(?:c|cpp|c\+\+)?\s*$", "", text, flags=re.M)
    cleaned = cleaned.replace("```", "")
    cleaned = cleaned.strip()
    return cleaned


def _extract_json(text: str) -> dict:
    """从 LLM 输出提取 JSON（容忍 ```json 包裹和前后杂文本）。"""
    m = re.search(r"```(?:json)?\n(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM 输出无 JSON: {text[:200]}")
    return json.loads(text[start:end + 1])


def _find_header(doc: KnowledgeDoc) -> str:
    """从知识来源/同目录找接口头文件，返回其内容（接口定义，非实现）。"""
    for s in doc.sources or []:
        src = Path(s["file"])
        for h in sorted(src.parent.glob("*.h")):
            return h.read_text()
    return ""


class DocKnowledgeGen(KnowledgeGenAgent):
    """知识生成桩（加载预置解释型文档，模拟仓库已有/过时文档）。

    不读源码正文，只加载指定 Markdown。用于验证 LLM Coder 在
    「知识不含源码、可能过时」的真实场景下能否理解并补全。
    """

    def __init__(self, doc_path: Path):
        self.doc_path = Path(doc_path)

    def generate(self, module: str, src_file: Path, sources: list) -> KnowledgeDoc:
        content = self.doc_path.read_text()
        return KnowledgeDoc(module=module, content=content, sources=sources, version=1)

    def revise(self, doc: KnowledgeDoc, corrections: list) -> KnowledgeDoc:
        content = doc.content
        for c in corrections:
            content += f"\n## 修订补丁 {c.id}\n\n- 判据：{c.criterion}\n- 详情：{c.detail}\n"
        doc.content = content
        return doc


class LLMCoder(CoderAgent):
    """Coder Agent（真实 LLM）：知识 → 临时代码。

    信息隔离：只读知识文档 + 接口头文件，不读源码实现文件。
    """

    def __init__(self, model: str | None = None):
        self.model = model

    def generate_code(self, doc: KnowledgeDoc, out_path: Path) -> Path:
        header = _find_header(doc)
        sys_prompt = (
            "你是一名资深 C/C++ 工程师，在知识飞轮流程中担任 Coder Agent。\n"
            "你的任务：根据【知识文档】中描述的函数行为，编写完整的函数实现代码。\n"
            "硬性要求：\n"
            "1. 只能依赖知识文档和给定的接口头文件，不得臆造头文件里没有的类型/常量；\n"
            "2. 输出必须包含 #include 头文件语句；\n"
            "3. 只输出函数实现，禁止输出 main()、禁止输出测试代码、禁止输出解释文字；\n"
            "4. 直接输出纯代码，禁止使用 Markdown 代码围栏（不要 ```cpp 包裹）；\n"
            "5. 代码必须通过 g++ -Wall -Werror 编译；\n"
            "6. 语义必须与知识文档描述完全一致，尤其是边界情况的处理。"
        )
        user_prompt = (
            f"# 知识文档（模块 {doc.module}）\n\n{doc.content}\n\n"
            f"# 接口头文件\n\n```cpp\n{header}\n```\n\n"
            "请输出该模块的完整 C++ 实现代码（含 #include）。"
        )
        reply = _chat_retry([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ], temperature=0.1, model=self.model)
        code = _extract_code(reply)
        if not code:
            raise RuntimeError("LLM Coder 输出为空，无法生成代码")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(code)
        return out_path


class LLMReview(ReviewAgent):
    """Review Agent（真实 LLM）：评测报告 → 归因 + 修订指令。只读。"""

    def __init__(self, model: str | None = None):
        self.model = model

    def attribute(self, module: str, doc: KnowledgeDoc, report: EvalReport) -> Attribution:
        # 全过 + 编译过：无归因，直接 pass（与桩语义一致，不浪费 LLM 调用）
        if report.compile_ok and report.passed >= report.total:
            return Attribution(
                module=module,
                corrections=[],
                summary=f"置信度 {report.confidence:.2f}，相似度 {report.similarity:.2f}",
                weak_spots=[],
            )

        sys_prompt = (
            "你是一名资深代码评审（Review Agent），在知识飞轮流程中负责归因与修订指令。\n"
            "输入：评测报告（编译是否通过、通过用例数、失败用例详情）+ 知识文档。\n"
            "输出：JSON，格式：\n"
            '{"summary": "一句话归因结论", "weak_spots": ["薄弱点1"], '
            '"corrections": [{"id": "模块-xxx-1", "knowledge_path": "知识段落路径", '
            '"criterion": "验证判据（可执行）", "detail": "具体修改建议"}]}\n'
            "要求：criterion 必须可执行（如\"所有用例通过\"）；detail 必须给出具体修改方向，"
            "能指导知识修订后重新生成代码。只输出 JSON。"
        )
        user_prompt = (
            f"# 评测报告\n\n"
            f"- 编译通过: {report.compile_ok}\n"
            f"- 编译错误: {json.dumps(report.compile_errors[:5], ensure_ascii=False)}\n"
            f"- 通过/总数: {report.passed}/{report.total}\n"
            f"- 失败详情: {json.dumps(report.failures[:10], ensure_ascii=False)}\n\n"
            f"# 知识文档（模块 {module}）\n\n{doc.content[:6000]}\n\n"
            "请输出归因 JSON。"
        )
        reply = _chat_retry([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ], temperature=0.1, model=self.model)
        try:
            parsed = _extract_json(reply)
        except Exception as e:
            # LLM 输出解析失败：退回桩式兜底，保证流程不断
            failed = report.total - report.passed
            return Attribution(
                module=module,
                corrections=[Correction(
                    id=f"{module}-test-1",
                    knowledge_path=f"{module} 模块函数实现",
                    criterion=f"测试通过率需达 {report.passed}/{report.total}",
                    detail=f"有 {failed} 条用例失败，当前置信度 {report.confidence:.2f}",
                )],
                summary=f"置信度 {report.confidence:.2f}（LLM 归因解析失败，兜底）",
                weak_spots=[f"{module}: 测试失败 {failed} 条"],
            )
        corrections = []
        for c in parsed.get("corrections", []):
            corrections.append(Correction(
                id=c.get("id", f"{module}-llm-1"),
                knowledge_path=c.get("knowledge_path", f"{module} 模块"),
                criterion=c.get("criterion", "测试全部通过"),
                detail=c.get("detail", ""),
            ))
        return Attribution(
            module=module,
            corrections=corrections,
            summary=parsed.get("summary", ""),
            weak_spots=parsed.get("weak_spots", []),
        )
