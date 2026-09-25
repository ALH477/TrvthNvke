from __future__ import annotations

import subprocess
from pathlib import Path


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
        if (p / ".truthgate.toml").is_file() or (p / "truthgate.toml").is_file():
            return p
    return start.resolve() if start.is_dir() else start.resolve().parent


def install_pre_commit(root: Path) -> Path:
    hook_dir = root / ".git" / "hooks"
    if not hook_dir.is_dir():
        raise FileNotFoundError("not a git repository (missing .git/hooks)")
    hook = hook_dir / "pre-commit"
    payload = """#!/bin/sh
# Truthgate README gate
if command -v truthgate >/dev/null 2>&1; then
  truthgate verify --fail
else
  python3 -m truthgate verify --fail
fi
"""
    hook.write_text(payload, encoding="utf-8")
    hook.chmod(0o755)
    return hook
