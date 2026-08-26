"""确定性评测闭环：编译必过、测试主判、相似度仅诊断。"""

import difflib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from fw.config import Config
from roles import EvalReport

_DRIVER_TMPL = """\
#include <stdio.h>
#include <math.h>
{decls}
static int _assert_eq_double(double got, double exp) {{ return fabs(got - exp) < 1e-9; }}
int main(void) {{
    int passed = 0, total = 0;
{checks}
    printf("PASS %d/%d\\n", passed, total);
    return total - passed;
}}
"""


def _read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _compile_flags(cfg: Config) -> list:
    inc = cfg.eval_include_dir()
    return [
        str(flag).replace("{src_dir}", str(inc)).replace("{interfaces_dir}", str(inc))
        for flag in cfg.compile_flags
    ]


def compile_check(code_path: Path, cfg: Config) -> tuple:
    """跨平台编译检查；临时对象文件不写入源码目录。"""
    with tempfile.TemporaryDirectory(prefix="flywheel-compile-") as tmp:
        obj = Path(tmp) / "candidate.o"
        cmd = [cfg.compiler] + _compile_flags(cfg) + ["-c", str(code_path), "-o", str(obj)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, [f"compiler unavailable: {exc}"]
    errors = [line for line in proc.stderr.splitlines() if line.strip()]
    return proc.returncode == 0, errors


def similarity(text_a: str, text_b: str) -> float:
    if not text_a or not text_b:
        return 0.0
    return difflib.SequenceMatcher(None, text_a, text_b).ratio()


def _fmt_val(value, ret_type: str) -> str:
    return repr(float(value)) if ret_type == "double" else str(int(value))


def _gen_driver_c(module: str, cases: list, decls: str) -> str:
    checks = []
    for i, case in enumerate(cases):
        ret_type = case.get("ret_type", "int")
        args = ", ".join(_fmt_val(arg, ret_type) for arg in case.get("args", []))
        got = f"_g{i}"
        if ret_type == "double":
            checks.append(
                f"    double {got} = {case['function']}({args});\n"
                f"    total++;\n"
                f"    if (_assert_eq_double({got}, {_fmt_val(case['expected'], ret_type)})) passed++;"
            )
        else:
            checks.append(
                f"    int {got} = {case['function']}({args});\n"
                f"    total++;\n"
                f"    if ({got} == {_fmt_val(case['expected'], ret_type)}) passed++;"
            )
    return _DRIVER_TMPL.format(decls=decls, checks="\n".join(checks))


def _collect_funcs(interface_dir: Path) -> dict:
    decls = {}
    for header in sorted(Path(interface_dir).glob("*.h")):
        for line in _read_text(header).splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "/*", "*", "//")) and "(" in line and ";" in line:
                decls[line.split("(")[0].split()[-1]] = line
    return decls


def _parse_pass(stdout: str) -> tuple[int, int] | None:
    for line in stdout.splitlines():
        if line.startswith("PASS "):
            try:
                passed, total = line.split()[1].split("/")
                return int(passed), int(total)
            except (ValueError, IndexError):
                return None
    return None


def _summarize_reps(confidences: list, cfg: Config) -> dict:
    if not confidences:
        return {"mean": 0.0, "variance": 0.0, "min": 0.0, "unstable": False}
    mean = sum(confidences) / len(confidences)
    variance = sum((value - mean) ** 2 for value in confidences) / len(confidences)
    return {
        "mean": mean,
        "variance": variance,
        "min": min(confidences),
        "unstable": variance > cfg.variance_threshold,
    }


def _apply_reps(report: EvalReport, repetitions: list, cfg: Config) -> EvalReport:
    """保留每次结果并写入统计；兼容旧测试传入 float 列表。"""
    normalized = []
    for index, item in enumerate(repetitions, 1):
        if isinstance(item, dict):
            row = dict(item)
            row.setdefault("index", index)
            normalized.append(row)
        else:
            normalized.append({"index": index, "confidence": float(item)})
    confidences = [float(row.get("confidence", 0.0)) for row in normalized]
    stats = _summarize_reps(confidences, cfg)
    report.repetitions = normalized
    report.reps_count = len(normalized)
    report.reps_mean = stats["mean"]
    report.reps_variance = stats["variance"]
    report.reps_min = stats["min"]
    report.unstable = stats["unstable"]
    report.confidence = stats["mean"]
    return report


def _binary_path(work_dir: Path, name: str) -> Path:
    return work_dir / (name + (".exe" if os.name == "nt" else ""))


def _run_binary(binary: Path) -> tuple[subprocess.CompletedProcess, tuple[int, int] | None]:
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                         encoding="utf-8", errors="replace")
    return run, _parse_pass(run.stdout)


def evaluate(module: str, code_path: Path, cases: list, cfg: Config,
             src_text: str = "", work_dir: "Path | None" = None) -> EvalReport:
    report = EvalReport(module=module, split="train")
    if not cases:
        report.reason_codes.append("ZERO_CASES")
        return report
    work_dir = Path(work_dir or cfg.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    report.compile_ok, report.compile_errors = compile_check(code_path, cfg)
    if not report.compile_ok:
        report.reason_codes.append("COMPILE_FAILED")
        return report

    decls = _collect_funcs(cfg.eval_include_dir())
    if not decls:
        decls = {case["function"]: f"int {case['function']}(void);" for case in cases}
    driver = work_dir / f"test_driver_{module}.c"
    driver.write_text(_gen_driver_c(module, cases, "\n".join(decls.values())), encoding="utf-8")
    binary = _binary_path(work_dir, f"test_driver_{module}")
    cmd = [cfg.compiler, "-Wall", "-std=c11", str(driver), str(code_path),
           "-I", str(cfg.eval_include_dir()), "-lm", "-o", str(binary)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        report.compile_ok = False
        report.compile_errors = proc.stderr.splitlines()[:20]
        report.reason_codes.append("COMPILE_FAILED")
        return report

    repetitions = []
    total = len(cases)
    for index in range(1, cfg.repeat_eval + 1):
        run, result = _run_binary(binary)
        if result is None:
            passed, actual_total = 0, total
            failures = ["missing PASS summary"] + run.stdout.splitlines()[:10]
        else:
            passed, actual_total = result
            failures = [line for line in run.stdout.splitlines() if line.startswith("FAIL")]
        repetitions.append({
            "index": index,
            "passed": passed,
            "total": actual_total,
            "confidence": passed / actual_total if actual_total else 0.0,
            "exit_code": run.returncode,
        })
        report.failures.extend(failures)
    report.total = total
    _apply_reps(report, repetitions, cfg)
    report.passed = round(report.confidence * total)
    if report.unstable:
        report.reason_codes.append("UNSTABLE_RESULT")
    if src_text:
        report.similarity = similarity(src_text, _read_text(code_path))
    return report


def load_cases(evalset_dir: Path) -> list:
    cases = []
    cases_dir = Path(evalset_dir) / "cases"
    if not cases_dir.exists():
        return cases
    for file in sorted(cases_dir.glob("*.json")):
        data = json.loads(_read_text(file))
        cases.extend(data if isinstance(data, list) else data.get("cases", []))
    return cases


def detect_format(evalset_dir: Path, cfg: Config) -> str:
    if cfg.evalset_format != "auto":
        return cfg.evalset_format
    evalset_dir = Path(evalset_dir)
    if (evalset_dir / "cases").exists() and list((evalset_dir / "cases").glob("*.json")):
        return "json"
    if list(evalset_dir.glob(cfg.native_test_glob)) or list(evalset_dir.glob("*.c")) or list(evalset_dir.glob("*.cpp")):
        return "native"
    if (evalset_dir / "train").exists():
        return "native"
    return "json"


def find_native_tests(evalset_dir: Path, cfg: Config, module: str = "") -> list:
    evalset_dir = Path(evalset_dir)
    files = sorted(evalset_dir.glob(cfg.native_test_glob))
    if not files:
        files = sorted(evalset_dir.glob("*.c")) + sorted(evalset_dir.glob("*.cpp"))
    if module:
        files = [file for file in files if module in file.name]
    return files


def evaluate_native(module: str, code_path: Path, test_files: list, cfg: Config,
                    src_text: str = "", work_dir: "Path | None" = None) -> EvalReport:
    report = EvalReport(module=module, split="train")
    if not test_files:
        report.reason_codes.append("ZERO_CASES")
        return report
    work_dir = Path(work_dir or cfg.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    report.compile_ok, report.compile_errors = compile_check(code_path, cfg)
    if not report.compile_ok:
        report.reason_codes.append("COMPILE_FAILED")
        return report

    binaries = []
    for test_file in test_files:
        is_cpp = test_file.suffix in (".cpp", ".cc", ".cxx")
        compiler = "g++" if is_cpp else cfg.compiler
        binary = _binary_path(work_dir, f"native_{test_file.stem}")
        cmd = [compiler, "-Wall", "-std=c++11" if is_cpp else "-std=c11",
               str(test_file), str(code_path), "-I", str(cfg.eval_include_dir()),
               "-lm", "-o", str(binary)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            report.compile_ok = False
            report.compile_errors = proc.stderr.splitlines()[:20]
            report.reason_codes.append("COMPILE_FAILED")
            return report
        binaries.append((test_file, binary))

    repetitions = []
    expected_total = None
    for index in range(1, cfg.repeat_eval + 1):
        passed_sum = total_sum = 0
        for test_file, binary in binaries:
            run, result = _run_binary(binary)
            if result is None:
                report.failures.append(f"{test_file.name}: missing PASS summary")
                continue
            passed, total = result
            passed_sum += passed
            total_sum += total
            report.failures.extend(
                f"{test_file.name}: {line}" for line in run.stdout.splitlines() if line.startswith("FAIL")
            )
        expected_total = total_sum if expected_total is None else expected_total
        if total_sum != expected_total:
            report.reason_codes.append("INCONSISTENT_TOTAL")
        repetitions.append({
            "index": index,
            "passed": passed_sum,
            "total": total_sum,
            "confidence": passed_sum / total_sum if total_sum else 0.0,
        })
    report.total = expected_total or 0
    if report.total == 0:
        report.reason_codes.append("ZERO_CASES")
        return report
    _apply_reps(report, repetitions, cfg)
    report.passed = round(report.confidence * report.total)
    if report.unstable:
        report.reason_codes.append("UNSTABLE_RESULT")
    if src_text:
        report.similarity = similarity(src_text, _read_text(code_path))
    return report


def aggregate_generation_reports(reports: list, cfg: Config, split: str) -> EvalReport:
    """聚合多次独立代码生成的能力分布，门禁使用生成间均值/方差。"""
    if not reports:
        result = EvalReport(module="", split=split)
        result.reason_codes.append("NO_GENERATIONS")
        return result
    first = reports[0]
    result = EvalReport(module=first.module, split=split)
    result.compile_ok = all(report.compile_ok for report in reports)
    result.compile_errors = [error for report in reports for error in report.compile_errors]
    result.total = first.total
    result.failures = [f"g{index}: {failure}" for index, report in enumerate(reports, 1)
                       for failure in report.failures]
    result.similarity = sum(report.similarity for report in reports) / len(reports)
    generations = []
    for index, report in enumerate(reports, 1):
        generations.append({
            "index": index,
            "compile_ok": report.compile_ok,
            "confidence": report.confidence if report.valid and report.compile_ok else 0.0,
            "execution_repetitions": report.repetitions,
        })
    result.generation_results = generations
    result.generation_count = len(generations)
    _apply_reps(result, generations, cfg)
    result.passed = round(result.confidence * result.total) if result.total else 0
    result.unstable = result.unstable or any(report.unstable for report in reports)
    if result.total == 0:
        result.reason_codes.append("ZERO_CASES")
    if not result.compile_ok:
        result.reason_codes.append("COMPILE_FAILED")
    if result.unstable:
        result.reason_codes.append("UNSTABLE_RESULT")
    return result
