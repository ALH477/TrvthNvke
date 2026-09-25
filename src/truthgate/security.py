"""Deterministic confinement for paths, commands, and policy pins."""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any


class ConfineError(ValueError):
    pass


class CommandDenied(ValueError):
    pass


ALLOWED_ENV_DEFAULT = ("PYTHONPATH", "TRUTHGATE_OFFLINE", "LANG", "LC_ALL")
DEFAULT_ARGV_PREFIXES = (
    ("python3", "-m", "truthgate"),
    ("python", "-m", "truthgate"),
    ("test", "-f"),
    ("test", "-d"),
)

PATHISH = re.compile(
    r"(?<![A-Za-z0-9_])((?:src|nix|docs|hooks|templates|examples|\.github|\.truthgate)"
    r"/[A-Za-z0-9_./-]+|[A-Za-z0-9_./-]+\.(?:py|toml|yml|yaml|md|nix|json|sh))"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def confine(root: Path, rel: str | os.PathLike[str]) -> Path:
    root = root.resolve()
    rel_s = str(rel).strip()
    if not rel_s:
        raise ConfineError("empty path")
    if rel_s.startswith("~") or Path(rel_s).is_absolute() or rel_s.startswith("/"):
        raise ConfineError(f"absolute path rejected: {rel_s}")
    parts = Path(rel_s).parts
    if any(p == ".." for p in parts):
        raise ConfineError(f"parent traversal rejected: {rel_s}")
    raw = root / rel_s
    if raw.is_symlink():
        dest = raw.resolve()
        try:
            dest.relative_to(root)
        except ValueError as exc:
            raise ConfineError(f"symlink escapes repository root: {rel_s}") from exc
    candidate = raw.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ConfineError(f"path escapes repository root: {rel_s}") from exc
    return candidate


def confine_optional(root: Path, rel: str | None) -> Path:
    if not rel:
        raise ConfineError("missing path")
    return confine(root, rel)


def parse_command(run: str) -> tuple[dict[str, str], list[str]]:
    try:
        parts = shlex.split(run, posix=True)
    except ValueError as exc:
        raise CommandDenied(f"unparseable command: {exc}") from exc
    extra_env: dict[str, str] = {}
    i = 0
    while i < len(parts) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", parts[i]):
        key, val = parts[i].split("=", 1)
        extra_env[key] = val
        i += 1
    argv = parts[i:]
    if not argv:
        raise CommandDenied("command has no argv")
    return extra_env, argv


def command_allowed(argv: list[str], prefixes: list[list[str]] | tuple[tuple[str, ...], ...]) -> bool:
    for prefix in prefixes:
        pre = list(prefix)
        if argv[: len(pre)] == pre:
            return True
    return False


def run_confined_command(
    root: Path,
    run: str,
    *,
    timeout: int,
    prefixes: list[list[str]],
    allowed_env: list[str],
    extra_timeout_hard: int = 30,
) -> subprocess.CompletedProcess[str]:
    extra_env, argv = parse_command(run)
    if not command_allowed(argv, prefixes):
        raise CommandDenied(f"command not on allowlist: {argv!r}")
    for key in extra_env:
        if key not in allowed_env:
            raise CommandDenied(f"environment key not allowed: {key}")
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TZ") if k in os.environ}
    env["TRUTHGATE_OFFLINE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    for key, val in extra_env.items():
        if key == "PYTHONPATH":
            # confine each entry
            parts = []
            for entry in val.split(":"):
                if not entry:
                    continue
                confined = confine(root, entry)
                parts.append(str(confined))
            env[key] = ":".join(parts)
        else:
            env[key] = val
    # refuse arguments that try to leave the tree
    for arg in argv[1:]:
        if arg.startswith("-"):
            continue
        if "/" in arg or arg.endswith((".py", ".toml", ".md", ".nix")):
            try:
                confine(root, arg)
            except ConfineError:
                # flags like -m truthgate are not paths
                if arg.startswith(".") or "/" in arg:
                    raise
    hard = min(timeout, extra_timeout_hard)
    return subprocess.run(
        argv,
        shell=False,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=hard,
        env=env,
    )


def coverage_tokens(visible: str) -> set[str]:
    return {m.group(1) for m in PATHISH.finditer(visible)}


def strip_ignored_and_comments(text: str, ignored_spans: list[tuple[int, int]]) -> str:
    keep = []
    i = 0
    spans = sorted(ignored_spans)
    for a, b in spans:
        if i < a:
            keep.append(text[i:a])
        i = max(i, b)
    keep.append(text[i:])
    stripped = "".join(keep)
    stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.DOTALL)
    return stripped


def policy_lock_payload(policy_text: str, policy_name: str) -> dict[str, Any]:
    return {
        "file": policy_name,
        "sha256": sha256_text(policy_text),
        "alg": "sha256",
    }
