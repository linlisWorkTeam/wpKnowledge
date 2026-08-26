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

from fw.sandbox import SandboxViolation, build_sandbox, read_header
from roles import (Attribution, Correction, CoderAgent, EvalReport, KnowledgeDoc,
                   KnowledgeGenAgent, ReviewAgent)
from roles.providers import CodeAgentProvider, DeepSeekProvider
from fw.error_codes import EMPTY_MODEL_OUTPUT, INCOMPLETE_CONTEXT

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
          model: str | None = None, timeout: int = 180) -> str:
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _chat_retry(messages: list, temperature: float = 0.2, max_tokens: int = 8192,
                model: str | None = None, attempts: int = 4, timeout: int = 180,
                provider=None) -> str:
    """通过显式 provider 调用模型，空输出做有限重试。

    连续空输出时微调 temperature 抖动（0.1→0.3），提高重试成功率。
    重试耗尽仍为空 → 抛 RuntimeError（错误码 EMPTY_MODEL_OUTPUT，契约 §6）。
    """
    last = ""
    for i in range(attempts):
        t = temperature + (0.1 * (i % 2))  # 抖动，避免同样参数重复空
        if provider is None:
            raise RuntimeError("必须显式提供模型 provider；生产使用 CodeAgentProvider")
        reply = provider.chat(messages, temperature=t, max_tokens=max_tokens, timeout=timeout)
        if reply and reply.strip():
            return reply
        last = reply
    raise RuntimeError(
        f"模型连续 {attempts} 次返回空输出（{EMPTY_MODEL_OUTPUT}）")


# C/C++ 代码行特征：以这些开头的行视为代码，否则视为说明文字（问题4 剥离用）
_CODE_LINE_START = (
    "#include", "#define", "#pragma", "#if", "#ifdef", "#ifndef", "#else", "#endif",
    "typedef", "using", "namespace", "struct", "class", "template", "enum", "union",
    "extern", "static", "inline", "constexpr", "const", "volatile", "unsigned",
    "signed", "int", "uint", "int8_t", "uint8_t", "int16_t", "uint16_t", "int32_t",
    "uint32_t", "int64_t", "uint64_t", "size_t", "float", "double", "char", "bool",
    "void", "long", "short", "auto", "return", "if", "else", "for", "while", "switch",
    "case", "break", "continue", "do", "goto", "throw", "try", "catch", "new",
    "delete", "operator", "friend", "public", "private", "protected", "virtual",
    "override", "final", "default", "nullptr", "true", "false", "}",
)


def _looks_like_code(line: str) -> bool:
    """判断一行是否像 C/C++ 代码（问题4：剥离 LLM 输出的说明文字）。"""
    s = line.strip()
    if not s:
        return True  # 空行保留（代码内部空行）
    if s.startswith("```"):
        return False
    # 注释行算代码（可能随代码输出）
    if s.startswith(("//", "/*", "*")):
        return True
    # 大括号结尾的代码块结束/开始
    if s in ("{", "}", "};", "};", "};"):
        return True
    # 以 { 结尾的行（函数体开始）
    if s.endswith("{"):
        return True
    # 以 ; 结尾的行（语句）
    if s.endswith(";"):
        return True
    # 以代码关键字开头
    for kw in _CODE_LINE_START:
        if s.startswith(kw):
            return True
    # 函数签名：类型 函数名( ... ( 出现
    if "(" in s and ")" in s and not s.startswith(("中文", "以下", "实现", "代码")):
        return True
    return False


def _extract_code(text: str) -> str:
    """从 LLM 输出提取代码；健壮处理各种输出形态。

    优先级：JSON {"code": ...} → 闭合代码块（取最长）→ 剥围栏 → 纯文本。
    增强（问题4）：剥离自然语言说明行（保留代码主体），空结果返回空串。
    """
    if not text or not text.strip():
        return ""
    # 1) JSON 形态：{"code": "..."}（结构化输出最稳）
    try:
        parsed = _extract_json(text)
        if isinstance(parsed, dict) and parsed.get("code"):
            return str(parsed["code"]).strip()
    except Exception:
        pass
    # 1b) JSON 形态兜底：非法 JSON 但含 "code" 字段 → 正则提取字符串（容忍裸换行）
    m = re.search(r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.S)
    if m:
        try:
            code_str = json.loads('"' + m.group(1) + '"')
            if code_str.strip():
                return code_str.strip()
        except Exception:
            pass
    # 2) 闭合代码块（取最长非空块）
    blocks = re.findall(r"```(?:c|cpp|c\+\+)?\n(.*?)```", text, re.S)
    if blocks:
        non_empty = [b for b in blocks if b.strip()]
        if non_empty:
            return max(non_empty, key=len).strip()
    # 3) 剥围栏残留
    cleaned = re.sub(r"^```(?:c|cpp|c\+\+)?\s*$", "", text, flags=re.M)
    cleaned = cleaned.replace("```", "")
    # 4) 剥离说明文字：逐行保留代码行
    lines = cleaned.splitlines()
    code_lines = [ln for ln in lines if _looks_like_code(ln)]
    cleaned = "\n".join(code_lines).strip()
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


def _truncate_doc(content: str, max_chars: int) -> str:
    """知识文档截断（问题2：文档太大防超时）。

    保留头部（签名/职责）+ 尾部（边界条件），中间省略；省略处打标记，
    让 Coder 知道文档不完整（可要求补齐而不是臆造）。
    """
    if len(content) <= max_chars:
        return content
    head = content[: int(max_chars * 0.6)]
    tail = content[-int(max_chars * 0.3):]
    return (
        head + "\n\n[文档超长已截断：省略 "
        f"{len(content) - len(head) - len(tail)} 字符；如需完整信息请要求补齐]\n\n"
        + tail
    )


def _find_header(doc: KnowledgeDoc, cfg=None) -> str:
    """从接口头文件副本目录读取接口定义（沙箱白名单内，非源码实现）。

    修复（问题1 沙箱隔离）：不再从 doc.sources 的源码路径找头文件
    （那可能指向 src-biz 源码目录）；只从 cfg.interfaces_dir 读接口副本。
    没有 cfg 时回退到 doc.sources 同目录（向后兼容旧调用）。
    """
    if cfg is not None:
        header = read_header(cfg, doc.module, sandbox=build_sandbox(cfg))
        if header:
            return header
    for s in doc.sources or []:
        src = Path(s["file"])
        for h in sorted(src.parent.glob("*.h")):
            return h.read_text(encoding="utf-8")
    return ""


class DocKnowledgeGen(KnowledgeGenAgent):
    """知识生成桩（加载预置解释型文档，模拟仓库已有/过时文档）。

    不读源码正文，只加载指定 Markdown。用于验证 LLM Coder 在
    「知识不含源码、可能过时」的真实场景下能否理解并补全。
    """

    def __init__(self, doc_path: Path):
        self.doc_path = Path(doc_path)

    def generate(self, module: str, src_file: Path, sources: list) -> KnowledgeDoc:
        content = self.doc_path.read_text(encoding="utf-8")
        return KnowledgeDoc(module=module, content=content, sources=sources, version=1)

    def revise(self, doc: KnowledgeDoc, corrections: list) -> KnowledgeDoc:
        content = doc.content
        for c in corrections:
            content += f"\n## 修订补丁 {c.id}\n\n- 判据：{c.criterion}\n- 详情：{c.detail}\n"
        doc.content = content
        return doc


class LLMKnowledgeGen(KnowledgeGenAgent):
    """知识生成 Agent（真实 LLM）：源码 → 解释型知识文档。

    严格按飞轮流程：知识为解释型 Markdown（签名/职责/算法步骤/边界/伪代码），
    **禁止包含源码原文**（Coder 只能依赖知识理解，不得直接拿到实现）。

    分块生成（问题3 防超时）：源码过大时先列函数清单，再逐函数生成段落，
    每次 LLM 调用只处理一个函数，避免单次 prompt 超长导致超时。
    """

    CHUNK_SRC_CHARS = 4000   # 源码超此阈值启用分块

    def __init__(self, model: str | None = None, chunk: bool = True,
                 api_timeout: int = 180, provider=None):
        self.model = model
        self.chunk = chunk
        self.api_timeout = api_timeout
        self.provider = provider

    def _sys_prompt(self) -> str:
        return (
            "你是一名资深 C/C++ 工程师，在知识飞轮流程中担任知识生成 Agent（唯一执笔者）。\n"
            "你的任务：阅读【源码】与【接口头文件】，为后续 Coder Agent 生成一份**解释型知识文档**。\n"
            "硬性要求：\n"
            "1. **严禁输出源码原文**：不得复制/摘录函数体实现代码；\n"
            "2. 必须包含：函数签名、职责说明、输入参数语义、输出字段语义、算法步骤（用自然语言或伪代码描述，不贴实现）、边界条件与特殊处理；\n"
            "3. 伪代码允许，但必须是重新组织过的描述，不能是源码逐行复制；\n"
            "4. 若源码存在边界缺陷（如除零、溢出风险），在文档中标注出来；\n"
            "5. 输出 Markdown 格式，含溯源（文件路径）。"
        )

    def _list_functions(self, src_text: str) -> list:
        """提取源码函数清单（正则，确定性）。返回函数名列表。"""
        names = []
        for m in re.finditer(
                r"^\s*(?:[A-Za-z_][\w:<>]*\s+)+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
                src_text, re.M):
            name = m.group(1)
            if name not in ("if", "for", "while", "switch", "return", "sizeof"):
                names.append(name)
        return names or [""]  # 空则整体当一段

    def _gen_chunk(self, module: str, header: str, src_text: str,
                   scope_desc: str) -> str:
        """生成单个函数/段落的知识描述。"""
        user_prompt = (
            f"# 接口头文件\n\n```cpp\n{header}\n```\n\n"
            f"# 源码（仅知识生成 Agent 可见，不得写入输出）\n\n```cpp\n{src_text}\n```\n\n"
            f"请生成模块 {module} 中【{scope_desc}】的解释型知识段落"
            f"（Markdown，禁止包含源码原文，只描述该部分）。"
        )
        reply = _chat_retry([
            {"role": "system", "content": self._sys_prompt()},
            {"role": "user", "content": user_prompt},
        ], temperature=0.2, model=self.model, timeout=self.api_timeout, provider=self.provider)
        content = reply.strip()
        if not content:
            raise RuntimeError(f"LLM 知识生成输出为空（段落：{scope_desc}）")
        return content

    def generate(self, module: str, src_file: Path, sources: list) -> KnowledgeDoc:
        src_text = src_file.read_text(encoding="utf-8")
        header = ""
        for h in sorted(src_file.parent.glob("*.h")):
            header = h.read_text(encoding="utf-8")
            break

        if self.chunk and len(src_text) > self.CHUNK_SRC_CHARS:
            # 分块：列函数清单 → 逐函数生成 → 拼装
            funcs = self._list_functions(src_text)
            sections = []
            for fn in funcs:
                sections.append(self._gen_chunk(module, header, src_text, fn or module))
            content = (
                f"# {module} 模块知识（分块生成）\n\n"
                f"> 溯源：{src_file}（仅签名，无源码正文）\n\n"
                + "\n\n---\n\n".join(sections)
            )
        else:
            sys_prompt = self._sys_prompt()
            user_prompt = (
                f"# 接口头文件\n\n```cpp\n{header}\n```\n\n"
                f"# 源码（仅知识生成 Agent 可见，不得写入输出）\n\n```cpp\n{src_text}\n```\n\n"
                f"请生成模块 {module} 的解释型知识文档（Markdown，禁止包含源码原文）。"
            )
            reply = _chat_retry([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ], temperature=0.2, model=self.model, timeout=self.api_timeout, provider=self.provider)
            content = reply.strip()
            if not content:
                raise RuntimeError("LLM 知识生成输出为空")
        return KnowledgeDoc(module=module, content=content, sources=sources, version=1)

    def revise(self, doc: KnowledgeDoc, corrections: list) -> KnowledgeDoc:
        content = doc.content
        for c in corrections:
            content += f"\n## 修订补丁 {c.id}\n\n- 判据：{c.criterion}\n- 详情：{c.detail}\n"
        doc.content = content
        return doc


class LLMCoder(CoderAgent):
    """Coder Agent（真实 LLM）：知识 → 临时代码。

    信息隔离（问题1 沙箱）：只读知识文档 + 接口头文件（interfaces_dir），
    不读源码实现文件；所有路径读取经沙箱白名单校验，源码目录永远拒绝。
    """

    def __init__(self, model: str | None = None, cfg=None, api_timeout: int = 180,
                 provider=None):
        self.model = model
        self.cfg = cfg
        self.api_timeout = api_timeout
        self.provider = provider
        self.sandbox = build_sandbox(cfg) if cfg is not None else None

    def generate_code(self, doc: KnowledgeDoc, out_path: Path) -> Path:
        # 沙箱校验：知识文档必须可读（白名单内）
        if self.sandbox is not None:
            try:
                self.sandbox.assert_writable(out_path)
            except SandboxViolation as e:
                raise SandboxViolation(f"Coder 输出路径被沙箱拦截: {e}")
        header = _find_header(doc, self.cfg)
        # 问题2：文档太大 → 截断（防 prompt 超长/超时）
        max_chars = self.cfg.max_doc_chars if self.cfg is not None else 6000
        doc_content = _truncate_doc(doc.content, max_chars)
        sys_prompt = (
            "你是一名资深 C/C++ 工程师，在知识飞轮流程中担任 Coder Agent。\n"
            "你的任务：根据【知识文档】中描述的函数行为，编写完整的函数实现代码。\n"
            "硬性要求：\n"
            "1. 只能依赖知识文档和给定的接口头文件，不得臆造头文件里没有的类型/常量；\n"
            "2. 输出必须包含 #include 头文件语句；\n"
            "3. **只输出纯代码**：禁止输出 main()、禁止输出测试代码、禁止输出任何解释文字；\n"
            "4. **直接输出代码本身，不要用 Markdown 代码围栏**（不要 ```cpp 包裹），"
            "不要以\"以下是实现\"等文字开头；\n"
            "5. 输出必须以 #include 或函数签名开头，以函数体结束；\n"
            "6. 代码必须通过 g++ -Wall -Werror 编译；\n"
            "7. 语义必须与知识文档描述完全一致，尤其是边界情况的处理；\n"
            "8. 若知识文档被截断，只实现你能确定的部分，不要臆造未知语义。\n\n"
            "输出示例（唯一允许的形态）：\n"
            "#include \"xxx.h\"\n"
            "RetType func(Args...) {\n"
            "    // 实现\n"
            "    return ...;\n"
            "}\n"
        )
        user_prompt = (
            f"# 知识文档（模块 {doc.module}）\n\n{doc_content}\n\n"
            f"# 接口头文件\n\n```cpp\n{header}\n```\n\n"
            "请输出该模块的完整 C++ 实现代码（含 #include）。"
        )
        reply = _chat_retry([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ], temperature=0.1, model=self.model, timeout=self.api_timeout, provider=self.provider)
        code = _extract_code(reply)
        if not code:
            raise RuntimeError("LLM Coder 输出为空，无法生成代码")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(code, encoding="utf-8")
        return out_path


class LLMReview(ReviewAgent):
    """Review Agent（真实 LLM）：评测报告 → 归因 + 修订指令。只读。"""

    def __init__(self, model: str | None = None, cfg=None, api_timeout: int = 180,
                 provider=None):
        self.model = model
        self.cfg = cfg
        self.api_timeout = api_timeout
        self.provider = provider

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
        # 问题2：文档太大 → 截断（Review 只读关键段落，防超时）
        max_chars = self.cfg.max_doc_chars if self.cfg is not None else 6000
        doc_content = _truncate_doc(doc.content, max_chars)
        user_prompt = (
            f"# 评测报告\n\n"
            f"- 编译通过: {report.compile_ok}\n"
            f"- 编译错误: {json.dumps(report.compile_errors[:5], ensure_ascii=False)}\n"
            f"- 通过/总数: {report.passed}/{report.total}\n"
            f"- 失败详情: {json.dumps(report.failures[:10], ensure_ascii=False)}\n\n"
            f"# 知识文档（模块 {module}）\n\n{doc_content}\n\n"
            "请输出归因 JSON。"
        )
        reply = _chat_retry([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ], temperature=0.1, model=self.model, timeout=self.api_timeout, provider=self.provider)
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


def build_llm_roles(cfg):
    """按配置构建显式 provider；生产模式不会回退外部 API。"""
    cfg.validate()
    if cfg.model_provider == "codeagent":
        provider = CodeAgentProvider(cfg.codeagent_command, cfg.model_id)
    elif cfg.model_provider == "deepseek":
        provider = DeepSeekProvider(model=cfg.model_id)
    else:
        raise RuntimeError(f"不支持的 LLM provider: {cfg.model_provider}")
    return (
        LLMKnowledgeGen(model=cfg.model_id, chunk=cfg.knowledge_chunk,
                        api_timeout=cfg.api_timeout, provider=provider),
        LLMCoder(model=cfg.model_id, cfg=cfg, api_timeout=cfg.api_timeout, provider=provider),
        LLMReview(model=cfg.model_id, cfg=cfg, api_timeout=cfg.api_timeout, provider=provider),
    )
