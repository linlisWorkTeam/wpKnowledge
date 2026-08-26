"""受保护路径的完整 SHA-256 快照与校验。"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


class ProtectionMismatch(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(paths: list) -> dict:
    result = {}
    for raw in paths:
        root = Path(raw).resolve(strict=False)
        if not root.exists():
            continue
        files = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
        for file in files:
            result[str(file.resolve())] = sha256_file(file)
    return result


def verify(before: dict, paths: list) -> dict:
    after = snapshot(paths)
    if before != after:
        changed = sorted(set(before) | set(after))
        changed = [path for path in changed if before.get(path) != after.get(path)]
        raise ProtectionMismatch("受保护文件发生变化: " + ", ".join(changed[:20]))
    return after


def write_snapshot(path: Path, values: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
