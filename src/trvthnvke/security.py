"""Deterministic confinement for paths, commands, and policy pins."""

from __future__ import annotations

import functools
import hashlib
import os
import re
import shlex
import signal
import subprocess
import threading
from pathlib import Path
from typing import Any


class ConfineError(ValueError):
    pass


class CommandDenied(ValueError):
    pass


class RegexTimeout(ValueError):
    pass


ALLOWED_ENV_DEFAULT = ("PYTHONPATH", "TRVTHNVKE_OFFLINE", "TRUTHGATE_OFFLINE", "LANG", "LC_ALL")
DEFAULT_ARGV_PREFIXES = (
    ("python3", "-m", "trvthnvke"),
    ("python", "-m", "trvthnvke"),
    # pre-0.4.0 module name, still allowed so old policies keep verifying
    ("python3", "-m", "truthgate"),
    ("python", "-m", "truthgate"),
    ("test", "-f"),
    ("test", "-d"),
)

DEFAULT_COVERAGE_EXTS = ("py", "toml", "yml", "yaml", "md", "nix", "json", "sh")

MAX_PATTERN_LEN = 256
MAX_SEARCH_TEXT = 2 * 1024 * 1024

_EXCLUDED_TOP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".direnv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
_INCLUDED_HIDDEN_DIRS = {".github", ".trvthnvke", ".truthgate"}


@functools.lru_cache(maxsize=None)
def pathish_pattern(dirs: tuple[str, ...], exts: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = []
    if dirs:
        dir_alt = "|".join(re.escape(d) for d in dirs)
        alternatives.append(rf"(?:{dir_alt})/[A-Za-z0-9_./-]+")
    if exts:
        ext_alt = "|".join(re.escape(e) for e in exts)
        alternatives.append(rf"[A-Za-z0-9_./-]+\.(?:{ext_alt})")
    if not alternatives:
        return re.compile(r"(?!x)x")
    body = "|".join(alternatives)
    return re.compile(rf"(?<![A-Za-z0-9_])({body})")


def discover_top_dirs(root: Path) -> list[str]:
    names: list[str] = []
    for entry in root.iterdir():
        if entry.is_symlink():
            continue
        if not entry.is_dir():
            continue
        name = entry.name
        if name in _EXCLUDED_TOP_DIRS:
            continue
        if name.endswith(".egg-info"):
            continue
        if name == "result" or name.startswith("result-"):
            continue
        if name.startswith("."):
            if name not in _INCLUDED_HIDDEN_DIRS:
                continue
        names.append(name)
    return sorted(names)


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
    env["TRVTHNVKE_OFFLINE"] = "1"
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
                # flags like -m trvthnvke are not paths
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


def coverage_tokens(visible: str, dirs: list[str] | tuple[str, ...], exts: list[str] | tuple[str, ...]) -> set[str]:
    pattern = pathish_pattern(tuple(dirs), tuple(exts))
    return {m.group(1) for m in pattern.finditer(visible)}


def bounded_regex_search(pattern: str, text: str, flags: int = 0, timeout_sec: float = 2.0) -> re.Match[str] | None:
    if len(pattern) > MAX_PATTERN_LEN:
        raise ValueError("pattern too long")
    if len(text) > MAX_SEARCH_TEXT:
        raise ValueError("text too large for pattern search")
    compiled = re.compile(pattern, flags)
    if hasattr(signal, "setitimer") and threading.current_thread() is threading.main_thread() and timeout_sec > 0:
        def _on_alarm(signum: int, frame: Any) -> None:
            raise RegexTimeout("pattern timed out")

        previous = signal.signal(signal.SIGALRM, _on_alarm)
        signal.setitimer(signal.ITIMER_REAL, timeout_sec)
        try:
            return compiled.search(text)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)
    return compiled.search(text)


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
