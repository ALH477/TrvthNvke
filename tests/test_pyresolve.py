from pathlib import Path

from truthgate.model import Claim
from truthgate.policy import DocPolicy, Policy
from truthgate.pyresolve import console_scripts, has_symbol, resolve_module, split_target
from truthgate.verify import check_claim, verify_repo


# ---------------------------------------------------------------------------
# resolve_module
# ---------------------------------------------------------------------------


def test_resolve_module_finds_module_file(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "pkg" / "mod.py").write_text("def main():\n    pass\n", encoding="utf-8")
    found = resolve_module(tmp_path, "pkg.mod", ["src", "."])
    assert found is not None
    assert found == (tmp_path / "src" / "pkg" / "mod.py").resolve()


def test_resolve_module_finds_package_init(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    found = resolve_module(tmp_path, "pkg", ["src", "."])
    assert found is not None
    assert found == (tmp_path / "src" / "pkg" / "__init__.py").resolve()


def test_resolve_module_top_level_with_dot_root(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text("def run():\n    pass\n", encoding="utf-8")
    found = resolve_module(tmp_path, "mod", ["."])
    assert found is not None
    assert found == (tmp_path / "mod.py").resolve()


def test_resolve_module_rejects_invalid_names(tmp_path: Path) -> None:
    assert resolve_module(tmp_path, "../x", ["."]) is None
    assert resolve_module(tmp_path, "a/b", ["."]) is None
    assert resolve_module(tmp_path, ".hidden", ["."]) is None


def test_resolve_module_missing_returns_none(tmp_path: Path) -> None:
    assert resolve_module(tmp_path, "nope.nothing", ["src", "."]) is None


# ---------------------------------------------------------------------------
# has_symbol
# ---------------------------------------------------------------------------


def test_has_symbol_function_and_class(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "def foo():\n    pass\n\n\nclass Bar:\n    pass\n",
        encoding="utf-8",
    )
    assert has_symbol(f, "foo")
    assert has_symbol(f, "Bar")
    assert not has_symbol(f, "missing")


def test_has_symbol_assign_and_annassign(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "VALUE = 1\nOTHER: int = 2\nA, B = 1, 2\n",
        encoding="utf-8",
    )
    assert has_symbol(f, "VALUE")
    assert has_symbol(f, "OTHER")
    assert has_symbol(f, "A")
    assert has_symbol(f, "B")


def test_has_symbol_import_as_and_from_import(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "import os as operating_system\nimport sys\nfrom collections import OrderedDict as OD\n",
        encoding="utf-8",
    )
    assert has_symbol(f, "operating_system")
    assert has_symbol(f, "sys")
    assert has_symbol(f, "OD")
    assert not has_symbol(f, "collections")


def test_has_symbol_syntax_error_is_false(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text("def broken(:\n", encoding="utf-8")
    assert not has_symbol(f, "broken")


# ---------------------------------------------------------------------------
# console_scripts / split_target
# ---------------------------------------------------------------------------


def test_console_scripts_reads_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\nfoo = "pkg.mod:main"\n',
        encoding="utf-8",
    )
    scripts = console_scripts(tmp_path)
    assert scripts == {"foo": "pkg.mod:main"}


def test_console_scripts_missing_file(tmp_path: Path) -> None:
    assert console_scripts(tmp_path) == {}


def test_split_target() -> None:
    assert split_target("pkg.mod:func") == ("pkg.mod", "func")
    assert split_target("nocolon") is None
    assert split_target(":func") is None
    assert split_target("pkg.mod:") is None
    assert split_target("pkg.mod:1bad") is None


# ---------------------------------------------------------------------------
# check_claim: python_symbol
# ---------------------------------------------------------------------------


def _policy(tmp_path: Path) -> Policy:
    return Policy(root=tmp_path, docs=[DocPolicy(path="README.md")], require_lock=False, coverage="off")


def test_check_claim_python_symbol_pass(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("def main():\n    pass\n", encoding="utf-8")
    claim = Claim(
        id="c1",
        kind="python_symbol",
        source="block",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs={"module": "pkg.mod", "symbol": "main"},
        body="calls `main`",
    )
    ok, evidence = check_claim(tmp_path, claim, _policy(tmp_path))
    assert ok, evidence
    assert "pkg.mod" in evidence


def test_check_claim_python_symbol_missing_symbol(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("def other():\n    pass\n", encoding="utf-8")
    claim = Claim(
        id="c1",
        kind="python_symbol",
        source="block",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs={"module": "pkg.mod", "symbol": "main"},
        body="calls `main`",
    )
    ok, evidence = check_claim(tmp_path, claim, _policy(tmp_path))
    assert not ok
    assert "not defined" in evidence


def test_check_claim_python_symbol_entailment_fail(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("def main():\n    pass\n", encoding="utf-8")
    claim = Claim(
        id="c1",
        kind="python_symbol",
        source="block",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs={"module": "pkg.mod", "symbol": "main"},
        body="this body never mentions the bound value",
    )
    ok, evidence = check_claim(tmp_path, claim, _policy(tmp_path))
    assert not ok
    assert "does not mention" in evidence


# ---------------------------------------------------------------------------
# check_claim: entrypoint
# ---------------------------------------------------------------------------


def _write_entrypoint_repo(tmp_path: Path, target: str = "pkg.mod:main") -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("def main():\n    pass\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        f'[project.scripts]\nmytool = "{target}"\n',
        encoding="utf-8",
    )


def test_check_claim_entrypoint_pass_with_target(tmp_path: Path) -> None:
    _write_entrypoint_repo(tmp_path)
    claim = Claim(
        id="c1",
        kind="entrypoint",
        source="block",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs={"name": "mytool", "target": "pkg.mod:main"},
        body="installs `mytool`",
    )
    ok, evidence = check_claim(tmp_path, claim, _policy(tmp_path))
    assert ok, evidence
    assert "mytool" in evidence


def test_check_claim_entrypoint_target_mismatch(tmp_path: Path) -> None:
    _write_entrypoint_repo(tmp_path)
    claim = Claim(
        id="c1",
        kind="entrypoint",
        source="block",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs={"name": "mytool", "target": "pkg.other:main"},
        body="installs `mytool`",
    )
    ok, evidence = check_claim(tmp_path, claim, _policy(tmp_path))
    assert not ok
    assert "expected" in evidence


def test_check_claim_entrypoint_function_missing(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "mod.py").write_text("def other():\n    pass\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\nmytool = "pkg.mod:main"\n',
        encoding="utf-8",
    )
    claim = Claim(
        id="c1",
        kind="entrypoint",
        source="block",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs={"name": "mytool"},
        body="installs `mytool`",
    )
    ok, evidence = check_claim(tmp_path, claim, _policy(tmp_path))
    assert not ok
    assert "not defined" in evidence


# ---------------------------------------------------------------------------
# verify_repo end-to-end
# ---------------------------------------------------------------------------


def test_verify_repo_python_symbol_and_entrypoint_pass(tmp_path: Path) -> None:
    _write_entrypoint_repo(tmp_path)
    (tmp_path / "README.md").write_text(
        """# App

## Install

<!-- truth:claim
id: sym
kind: python_symbol
module: pkg.mod
symbol: main
-->
The `main` function drives the app.
<!-- truth:end -->

<!-- truth:claim
id: script
kind: entrypoint
name: mytool
target: pkg.mod:main
-->
Installing the package provides the `mytool` command.
<!-- truth:end -->
""",
        encoding="utf-8",
    )
    policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md")], require_lock=False, coverage="off")
    report = verify_repo(tmp_path, policy)
    assert report.ok, [f.to_dict() for f in report.findings]
