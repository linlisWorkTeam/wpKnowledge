"""4 个实战问题修复的单元测试：沙箱隔离 / 文档截断 / 分块生成 / 说明文字剥离。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fw.config import Config
from fw.sandbox import Sandbox, SandboxViolation, build_sandbox
from roles.llm_roles import (_extract_code, _looks_like_code, _truncate_doc,
                             LLMKnowledgeGen)

BASE = Path(__file__).resolve().parents[1]


# ---------- 问题1：沙箱隔离 ----------

def test_sandbox_allows_knowledge_dir(tmp_path):
    """知识目录白名单内可读。"""
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        interfaces_dir=tmp_path / "flywheel/interfaces",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/data",
    ).resolve(BASE)
    sb = build_sandbox(cfg)
    p = tmp_path / "flywheel/knowledge/tiling_v1.md"
    p.parent.mkdir(parents=True)
    p.write_text("ok")
    assert sb.read_text(p) == "ok"


def test_sandbox_blocks_src_dir(tmp_path):
    """源码目录（src-biz）永远禁止读取——防作弊红线。"""
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        interfaces_dir=tmp_path / "flywheel/interfaces",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/data",
    ).resolve(BASE)
    sb = build_sandbox(cfg)
    src_file = tmp_path / "src-biz/add_custom_tiling.cpp"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("int main(){}")
    with pytest.raises(SandboxViolation):
        sb.assert_readable(src_file)


def test_sandbox_blocks_outside_path(tmp_path):
    """白名单外任意路径（如 /etc）禁止。"""
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/data",
    ).resolve(BASE)
    sb = build_sandbox(cfg)
    with pytest.raises(SandboxViolation):
        sb.assert_readable(Path("/etc/passwd"))


def test_sandbox_no_dotdot_escape(tmp_path):
    """.. 路径穿越被 resolve 拦截。"""
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/data",
    ).resolve(BASE)
    sb = build_sandbox(cfg)
    # flywheel/data/../src-biz/secret.cpp → resolve 后落在 src-biz，应拦截
    escaped = tmp_path / "flywheel/data/../src-biz/secret.cpp"
    with pytest.raises(SandboxViolation):
        sb.assert_readable(escaped)


def test_sandbox_denied_overrides_allowed(tmp_path):
    """即使 allowed_read_dirs 配置了 src_dir，源码仍禁止（红线优先）。"""
    cfg = Config(
        src_dir=tmp_path / "src-biz",
        knowledge_dir=tmp_path / "flywheel/knowledge",
        work_dir=tmp_path / "flywheel/data",
        allowed_read_dirs=[tmp_path / "src-biz"],  # 恶意配置试图放行源码
    ).resolve(BASE)
    sb = build_sandbox(cfg)
    src_file = tmp_path / "src-biz/x.cpp"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("x")
    with pytest.raises(SandboxViolation):
        sb.assert_readable(src_file)


# ---------- 问题2：文档截断防超时 ----------

def test_truncate_doc_short_unchanged():
    content = "# tiling\n\n## 函数\n签名..."
    assert _truncate_doc(content, 10000) == content


def test_truncate_doc_long_cut():
    content = "A" * 1000 + "B" * 1000 + "C" * 1000
    cut = _truncate_doc(content, 1000)
    assert len(cut) < 1000
    assert "已截断" in cut
    assert cut.startswith("A") and cut.endswith("C")  # 头尾保留


# ---------- 问题3：知识生成分块 ----------

def test_list_functions_finds_tiling():
    kg = LLMKnowledgeGen(chunk=False)  # 不调用 LLM
    src = (
        "AddTilingData compute_tiling(uint32_t totalLength, uint32_t cores)\n"
        "{\n"
        "    return {};\n"
        "}\n"
        "static int helper(int x) { return x; }\n"
    )
    funcs = kg._list_functions(src)
    assert "compute_tiling" in funcs
    assert "helper" in funcs


def test_chunk_trigger_threshold():
    """源码超过阈值且 chunk=True 才走分块路径（无 LLM 调用时抛错验证分支）。"""
    kg = LLMKnowledgeGen(chunk=True)
    assert kg.CHUNK_SRC_CHARS > 0
    small = "int f() { return 1; }\n"
    assert len(small) <= kg.CHUNK_SRC_CHARS
    big = ("void big() {\n" + "    int x;\n" * 500 + "}\n")
    assert len(big) > kg.CHUNK_SRC_CHARS


# ---------- 问题4：说明文字剥离 ----------

def test_extract_code_strips_prose():
    """LLM 输出说明文字 + 代码 → 只提取代码。"""
    text = (
        "以下是实现代码：\n"
        "```cpp\n"
        "#include \"add_custom_tiling.h\"\n"
        "AddTilingData compute_tiling(uint32_t a, uint32_t b) {\n"
        "    AddTilingData t;\n"
        "    t.totalLength = a;\n"
        "    return t;\n"
        "}\n"
        "```\n"
        "希望这能帮到你！"
    )
    code = _extract_code(text)
    assert code.startswith("#include")
    assert "compute_tiling" in code
    assert "以下是" not in code
    assert "希望" not in code


def test_extract_code_plain_with_prose():
    """无围栏 + 前后说明文字 → 剥离后保留代码。"""
    text = (
        "好的，我来实现这个函数。\n"
        "#include \"add_custom_tiling.h\"\n"
        "AddTilingData compute_tiling(uint32_t totalLength, uint32_t cores)\n"
        "{\n"
        "    AddTilingData tiling;\n"
        "    tiling.blockNum = 1;\n"
        "    return tiling;\n"
        "}\n"
        "以上就是完整实现。"
    )
    code = _extract_code(text)
    assert code.startswith("#include")
    assert code.endswith("}")
    assert "好的" not in code
    assert "以上就是" not in code


def test_extract_code_json():
    """JSON 结构化输出优先。"""
    text = '{"code": "#include <cstdint>\\nvoid f() { return; }\\n"}'
    code = _extract_code(text)
    assert code.startswith("#include")
    assert "void f()" in code


def test_extract_code_json_broken():
    """非法 JSON（裸换行）但含 code 字段 → 正则兜底提取。"""
    text = '{"code": "#include <cstdint>\\nvoid f() {\\n    return;\\n}\\n", "note": "ok"}'
    code = _extract_code(text)
    assert code.startswith("#include")
    assert "void f()" in code
    assert '"note"' not in code


def test_looks_like_code():
    assert _looks_like_code("#include <cstdint>") is True
    assert _looks_like_code("int main() {") is True
    assert _looks_like_code("return 0;") is True
    assert _looks_like_code("以下是实现代码：") is False
    assert _looks_like_code("希望这能帮到你！") is False
    assert _looks_like_code("```cpp") is False
