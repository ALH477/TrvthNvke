from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .security import DEFAULT_ARGV_PREFIXES, DEFAULT_COVERAGE_EXTS


DEFAULT_CONFIG_NAMES = (".truthgate.toml", "truthgate.toml")


@dataclass
class DocPolicy:
    path: str
    required_headings: list[str] = field(default_factory=list)
    require_bound_fences: bool = True
    coverage: str | None = None


@dataclass
class Policy:
    root: Path
    docs: list[DocPolicy] = field(default_factory=list)
    fail_on: str = "error"  # error | warning
    allow_unbound_prose: bool = True
    command_timeout_sec: int = 15
    command_mode: str = "allowlist"
    command_allow: list[list[str]] = field(
        default_factory=lambda: [list(p) for p in DEFAULT_ARGV_PREFIXES]
    )
    allowed_env: list[str] = field(default_factory=lambda: ["PYTHONPATH", "TRUTHGATE_OFFLINE"])
    receipt_path: str = ".truthgate/receipt.json"
    version_file: str = "pyproject.toml"
    version_key: str = "project.version"
    require_lock: bool = False
    lock_path: str = ".truthgate.lock"
    coverage: str = "paths"
    coverage_severity: str = "warning"
    coverage_dirs: list[str] = field(default_factory=list)
    coverage_exts: list[str] = field(default_factory=lambda: list(DEFAULT_COVERAGE_EXTS))
    python_roots: list[str] = field(default_factory=lambda: ["src", "."])
    regex_timeout_sec: float = 2.0
    require_entailment: bool = True
    ignore_requires_reason: bool = True
    strict_ignore: bool = False

    @property
    def doc_paths(self) -> list[str]:
        return [d.path for d in self.docs]


def load_policy(root: Path) -> Policy:
    root = root.resolve()
    cfg_path = None
    for name in DEFAULT_CONFIG_NAMES:
        p = root / name
        if p.is_file():
            cfg_path = p
            break
    if cfg_path is None:
        readme = "README.md" if (root / "README.md").is_file() else None
        docs = [DocPolicy(path=readme)] if readme else []
        return Policy(root=root, docs=docs)

    raw: dict[str, Any]
    if cfg_path.suffix == ".toml":
        raw = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    else:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))

    docs_raw = raw.get("docs") or raw.get("document") or []
    docs: list[DocPolicy] = []
    if isinstance(docs_raw, dict):
        docs_raw = [docs_raw]
    for item in docs_raw:
        if isinstance(item, str):
            docs.append(DocPolicy(path=item))
        elif isinstance(item, dict):
            docs.append(
                DocPolicy(
                    path=str(item.get("path", "README.md")),
                    required_headings=list(item.get("required_headings") or []),
                    require_bound_fences=bool(item.get("require_bound_fences", True)),
                    coverage=item.get("coverage"),
                )
            )
    if not docs and (root / "README.md").is_file():
        docs = [DocPolicy(path="README.md")]

    policy_raw = raw.get("policy") or {}
    allow_raw = policy_raw.get("command_allow") or raw.get("command_allow")
    prefixes: list[list[str]] = [list(p) for p in DEFAULT_ARGV_PREFIXES]
    if allow_raw:
        prefixes = []
        for item in allow_raw:
            if isinstance(item, str):
                prefixes.append(item.split())
            elif isinstance(item, list):
                prefixes.append([str(x) for x in item])
        if not prefixes:
            prefixes = [list(p) for p in DEFAULT_ARGV_PREFIXES]
    return Policy(
        root=root,
        docs=docs,
        fail_on=str(policy_raw.get("fail_on", "error")),
        allow_unbound_prose=bool(policy_raw.get("allow_unbound_prose", True)),
        command_timeout_sec=int(policy_raw.get("command_timeout_sec", 15)),
        command_mode=str(policy_raw.get("command_mode", "allowlist")),
        command_allow=prefixes,
        allowed_env=list(policy_raw.get("allowed_env") or ["PYTHONPATH", "TRUTHGATE_OFFLINE"]),
        receipt_path=str(policy_raw.get("receipt_path", ".truthgate/receipt.json")),
        version_file=str(policy_raw.get("version_file", "pyproject.toml")),
        version_key=str(policy_raw.get("version_key", "project.version")),
        require_lock=bool(policy_raw.get("require_lock", False)),
        lock_path=str(policy_raw.get("lock_path", ".truthgate.lock")),
        coverage=str(policy_raw.get("coverage", "paths")),
        coverage_severity=str(policy_raw.get("coverage_severity", "warning")),
        coverage_dirs=list(policy_raw.get("coverage_dirs") or []),
        coverage_exts=list(policy_raw.get("coverage_exts") or list(DEFAULT_COVERAGE_EXTS)),
        python_roots=list(policy_raw.get("python_roots") or ["src", "."]),
        regex_timeout_sec=float(policy_raw.get("regex_timeout_sec", 2.0)),
        require_entailment=bool(policy_raw.get("require_entailment", True)),
        ignore_requires_reason=bool(policy_raw.get("ignore_requires_reason", True)),
        strict_ignore=bool(policy_raw.get("strict_ignore", False)),
    )


def default_config_text() -> str:
    return """# Truthgate policy — bind README claims to repository reality.

[policy]
fail_on = "error"
allow_unbound_prose = true
command_mode = "allowlist"
command_timeout_sec = 15
require_lock = true
lock_path = ".truthgate.lock"
coverage = "paths"
coverage_severity = "warning"
# coverage_dirs = ["src", "docs"]      # default: every top-level directory
# coverage_exts = ["py", "toml", "md"] # default: py toml yml yaml md nix json sh
# regex_timeout_sec = 2.0
# python_roots = ["src", "."]
require_entailment = true
ignore_requires_reason = true
strict_ignore = true
receipt_path = ".truthgate/receipt.json"
version_file = "pyproject.toml"
version_key = "project.version"
command_allow = [
  ["python3", "-m", "truthgate"],
  ["python", "-m", "truthgate"],
  ["test", "-f"],
  ["test", "-d"],
]

[[docs]]
path = "README.md"
required_headings = ["Install", "Usage"]
require_bound_fences = true
"""


def find_policy_file(root: Path) -> Path | None:
    for name in DEFAULT_CONFIG_NAMES:
        p = root / name
        if p.is_file():
            return p
    return None


def dump_lock(root: Path, lock_path: str) -> Path:
    cfg = find_policy_file(root)
    if cfg is None:
        raise FileNotFoundError("no .truthgate.toml to lock")
    payload = {
        "file": cfg.name,
        "sha256": __import__("hashlib").sha256(cfg.read_bytes()).hexdigest(),
        "alg": "sha256",
    }
    dest = root / lock_path
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest

