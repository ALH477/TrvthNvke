from __future__ import annotations

import subprocess
from pathlib import Path

from .policy import DEFAULT_CONFIG_NAMES


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def find_root(start: Path) -> Path:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for p in [cur, *cur.parents]:
        if (p / ".git").exists():
            return p
        if any((p / n).is_file() for n in DEFAULT_CONFIG_NAMES):
            return p
    return start.resolve() if start.is_dir() else start.resolve().parent


def install_pre_commit(root: Path) -> Path:
    hook_dir = root / ".git" / "hooks"
    if not hook_dir.is_dir():
        raise FileNotFoundError("not a git repository (missing .git/hooks)")
    hook = hook_dir / "pre-commit"
    payload = """#!/bin/sh
# TrvthNvke README gate
if command -v trvthnvke >/dev/null 2>&1; then
  trvthnvke verify --fail
else
  python3 -m trvthnvke verify --fail
fi
"""
    hook.write_text(payload, encoding="utf-8")
    hook.chmod(0o755)
    return hook
