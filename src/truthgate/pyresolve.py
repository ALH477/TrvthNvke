"""Static resolution of Python modules, symbols, and console-script entrypoints."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

from .security import ConfineError, confine

MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def resolve_module(root: Path, module: str, roots: list[str]) -> Path | None:
    if not module or not MODULE_RE.match(module):
        return None
    parts = module.split(".")
    for r in roots:
        base = Path(r) if r != "." else Path(".")
        module_path = base / Path(*parts[:-1]) / f"{parts[-1]}.py" if len(parts) > 1 else base / f"{parts[-1]}.py"
        package_path = base / Path(*parts) / "__init__.py"
        for candidate_rel in (module_path, package_path):
            try:
                candidate = confine(root, candidate_rel)
            except ConfineError:
                continue
            if candidate.is_file():
                return candidate
    return None


def has_symbol(path: Path, name: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                return True
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for n in ast.walk(target):
                    if isinstance(n, ast.Name) and n.id == name:
                        return True
        elif isinstance(node, ast.AnnAssign):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name) and n.id == name:
                    return True
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if (alias.asname or alias.name) == name:
                    return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname == name:
                    return True
                if alias.asname is None and alias.name.split(".")[0] == name:
                    return True
    return False


def console_scripts(root: Path, pyproject: str = "pyproject.toml") -> dict[str, str]:
    try:
        path = confine(root, pyproject)
    except ConfineError:
        return {}
    if not path.is_file():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    scripts = data.get("project", {}).get("scripts", {})
    return {str(k): str(v) for k, v in dict(scripts).items()}


def split_target(target: str) -> tuple[str, str] | None:
    if not target or ":" not in target:
        return None
    module, _, func = target.partition(":")
    module = module.strip()
    func = func.strip()
    if not module or not func:
        return None
    if not func.isidentifier():
        return None
    return module, func
