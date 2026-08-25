"""评测闭环：编译检查（必过门槛）+ 测试执行（主信号）+ 相似度（辅助归因）→ 置信度。

对应《codeagent执行手册》§3：
- 3.1 编译/静态检查：gcc -Wall -Werror，失败直接判失败
- 3.2 测试执行：运行评测集 cases，置信度 = 通过用例数 / 总用例数
- 3.3 相似度：辅助归因，不参与门禁判定
- 3.4 置信度与门禁判定

评测集 case schema（《评测集构建指南》§2.1 简化版）：
{
  "id": "calc-add-001",
  "module": "calc",
  "function": "add",
  "args": [2, 3],
  "expected": 5,
  "ret_type": "int"   // int | double；args 数值按类型转换
}
"""

import difflib
import json
import subprocess
from pathlib import Path

from fw.config import Config
from roles import EvalReport

_DRIVER_TMPL = """\
#include <stdio.h>
#include <math.h>

/* 被测函数声明（由 eval 注入） */
{decls}

static int _assert_eq_double(double got, double exp) {{
    return fabs(got - exp) < 1e-9;
}}

int main(void) {{
    int passed = 0, total = 0;
{checks}
    printf("PASS %d/%d\\n", passed, total);
    return total - passed;
}}
"""


def compile_check(code_path: Path, cfg: Config) -> tuple:
    """编译检查（必过门槛）。返回 (ok, errors)。"""
    inc = cfg.eval_include_dir()
    flags = [f.replace("{src_dir}", str(inc)).replace("{interfaces_dir}", str(inc))
             for f in cfg.compile_flags]
    cmd = [cfg.compiler] + flags + ["-c", str(code_path), "-o", "/dev/null"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    errors = [l for l in proc.stderr.splitlines() if "error" in l.lower()]
    return proc.returncode == 0, errors


def similarity(text_a: str, text_b: str) -> float:
    """文本相似度（辅助归因，不参与门禁判定）。"""
    if not text_a or not text_b:
        return 0.0
    return difflib.SequenceMatcher(None, text_a, text_b).ratio()


def _fmt_val(v, ret_type: str) -> str:
    """把 case 里的值格式化成 C 字面量。"""
    if ret_type == "double":
        return repr(float(v))
    return str(int(v))


def _gen_driver_c(module: str, cases: list, decls: str) -> str:
    """生成 C 测试驱动源码。每个 case 一条断言，打印 PASS n/total。"""
    checks = []
    for i, c in enumerate(cases):
        ret_type = c.get("ret_type", "int")
        args = ", ".join(_fmt_val(a, ret_type) for a in c.get("args", []))
        got = f"_g{i}"
        if ret_type == "double":
            check = (
                f'    double {got} = {c["function"]}({args});\n'
                f'    total++;\n'
                f'    if (_assert_eq_double({got}, {_fmt_val(c["expected"], ret_type)})) passed++;'
            )
        else:
            check = (
                f'    int {got} = {c["function"]}({args});\n'
                f'    total++;\n'
                f'    if ({got} == {_fmt_val(c["expected"], ret_type)}) passed++;'
            )
        checks.append(check)
    return _DRIVER_TMPL.format(decls=decls, checks="\n".join(checks))


def _collect_funcs(src_dir: Path) -> dict:
    """从源码目录收集函数声明（MVP 简化：扫描 .h 文件里的函数原型）。"""
    decls = {}
    for h in sorted(src_dir.glob("*.h")):
        text = h.read_text()
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "/*", "*", "//")) and "(" in line and ";" in line:
                name = line.split("(")[0].split()[-1]
                decls[name] = line
    return decls


def evaluate(module: str, code_path: Path, cases: list, cfg: Config,
             src_text: str = "", work_dir: "Path | None" = None) -> EvalReport:
    """完整评测闭环：编译 → 测试 → 相似度 → 置信度。"""
    report = EvalReport(module=module)
    work_dir = work_dir if work_dir is not None else cfg.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    # 3.1 编译检查（必过门槛）
    ok, errors = compile_check(code_path, cfg)
    report.compile_ok = ok
    report.compile_errors = errors
    if not ok:
        return report

    # 3.2 测试执行（主信号）
    decls = _collect_funcs(cfg.eval_include_dir())
    if not decls:
        decls = {c["function"]: f"int {c['function']}(void);" for c in cases}
    decl_str = "\n".join(decls.values())
    driver_c = _gen_driver_c(module, cases, decl_str)
    driver_file = work_dir / f"test_driver_{module}.c"
    driver_file.write_text(driver_c)
    bin_file = work_dir / f"test_driver_{module}"
    compile_cmd = [
        cfg.compiler, "-Wall", "-std=c11",
        str(driver_file), str(code_path),
        "-I", str(cfg.eval_include_dir()), "-lm", "-o", str(bin_file),
    ]
    proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        report.compile_ok = False
        report.compile_errors = proc.stderr.splitlines()[:10]
        return report

    passed, total = 0, len(cases)
    for _ in range(cfg.repeat_eval):
        run = subprocess.run([str(bin_file)], capture_output=True, text=True, timeout=60)
        for line in run.stdout.splitlines():
            if line.startswith("PASS "):
                passed = max(passed, int(line.split()[1].split("/")[0]))
    report.passed = passed
    report.total = total
    report.confidence = (passed / total) if total else 0.0

    # 3.3 相似度（辅助归因）
    if src_text:
        report.similarity = similarity(src_text, code_path.read_text())

    return report


def load_cases(evalset_dir: Path) -> list:
    """加载评测集 cases（JSON 模式）。"""
    cases = []
    cases_dir = evalset_dir / "cases"
    if not cases_dir.exists():
        return cases
    for f in sorted(cases_dir.glob("*.json")):
        data = json.loads(f.read_text())
        if isinstance(data, list):
            cases.extend(data)
        else:
            cases.extend(data.get("cases", []))
    return cases


def detect_format(evalset_dir: Path, cfg: Config) -> str:
    """自动检测评测集格式（auto 模式）。"""
    if cfg.evalset_format != "auto":
        return cfg.evalset_format
    if (evalset_dir / "cases").exists() and list((evalset_dir / "cases").glob("*.json")):
        return "json"
    native = list(evalset_dir.glob(cfg.native_test_glob))
    if native:
        return "native"
    # 兜底：看有没有任何 .c/.cpp 测试文件
    if list(evalset_dir.glob("*.c")) or list(evalset_dir.glob("*.cpp")):
        return "native"
    return "json"


def find_native_tests(evalset_dir: Path, cfg: Config, module: str = "") -> list:
    """查找原生测试文件。module 为空则取全部匹配文件。"""
    files = sorted(evalset_dir.glob(cfg.native_test_glob))
    if not files:
        files = sorted(evalset_dir.glob("*.c")) + sorted(evalset_dir.glob("*.cpp"))
    if module:
        files = [f for f in files if module in f.name]
    return files


def evaluate_native(module: str, code_path: Path, test_files: list, cfg: Config,
                    src_text: str = "", work_dir: "Path | None" = None) -> EvalReport:
    """原生测试文件模式：编译 用户本地测试文件 + 被测代码 → 运行 → PASS n/total。

    用户本地测试集约定（《评测集构建指南》附录 C）：
    - test_<module>.c/.cpp，含 main，逐用例断言
    - 运行后打印 "PASS n/total"（与 JSON 模式同约定，兼容 gtest/ctest 之外的自写驱动）
    """
    report = EvalReport(module=module)
    work_dir = work_dir if work_dir is not None else cfg.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    # 3.1 编译检查（必过门槛）
    ok, errors = compile_check(code_path, cfg)
    report.compile_ok = ok
    report.compile_errors = errors
    if not ok:
        return report

    passed, total = 0, 0
    failures: list = []
    for tf in test_files:
        bin_file = work_dir / f"native_{tf.stem}"
        is_cpp = tf.suffix in (".cpp", ".cc", ".cxx")
        compiler = "g++" if is_cpp else cfg.compiler
        std_flag = "-std=c++11" if is_cpp else "-std=c11"
        compile_cmd = [
            compiler, "-Wall", std_flag,
            str(tf), str(code_path),
            "-I", str(cfg.eval_include_dir()), "-lm", "-o", str(bin_file),
        ]
        proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            report.compile_ok = False
            report.compile_errors = proc.stderr.splitlines()[:10]
            return report
        # 重复评测取最大通过数；total 以单次为准（用例数）
        tf_total, tf_passed = 0, 0
        for _ in range(cfg.repeat_eval):
            run = subprocess.run([str(bin_file)], capture_output=True, text=True, timeout=60)
            for line in run.stdout.splitlines():
                if line.startswith("PASS "):
                    parts = line.split()[1].split("/")
                    tf_total = int(parts[1])
                    tf_passed = max(tf_passed, int(parts[0]))
                    break
        # 捕获失败详情（一次运行即可；Review 归因用）
        run = subprocess.run([str(bin_file)], capture_output=True, text=True, timeout=60)
        for line in run.stdout.splitlines():
            if line.startswith("FAIL"):
                failures.append(f"{tf.name}: {line}")
        passed += tf_passed
        total += tf_total

    report.passed = passed
    report.total = total
    report.confidence = (passed / total) if total else 0.0
    report.failures = failures
    if src_text:
        report.similarity = similarity(src_text, code_path.read_text())
    return report
