from pathlib import Path

from truthgate.policy import DocPolicy, Policy
from truthgate.security import discover_top_dirs, pathish_pattern
from truthgate.verify import verify_repo


def _write_lib_repo(tmp: Path) -> None:
    (tmp / "lib").mkdir()
    (tmp / "lib" / "x.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp / "README.md").write_text(
        """# App

## Install

Not much here, but `lib/x.py` and `lib/README` are mentioned in prose only.
""",
        encoding="utf-8",
    )


def test_auto_discover_warns_on_unbound_path_token(tmp_path: Path) -> None:
    _write_lib_repo(tmp_path)
    policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md")], require_lock=False)
    report = verify_repo(tmp_path, policy)
    assert report.ok
    warnings = [f for f in report.findings if f.code == "unbound_path_token"]
    assert any(f.severity == "warning" for f in warnings)
    assert any("lib/x.py" in f.message for f in warnings)


def test_coverage_dirs_restricts_dir_alternative_but_not_ext(tmp_path: Path) -> None:
    _write_lib_repo(tmp_path)
    policy = Policy(
        root=tmp_path,
        docs=[DocPolicy(path="README.md")],
        require_lock=False,
        coverage_dirs=["src"],
    )
    report = verify_repo(tmp_path, policy)
    messages = [f.message for f in report.findings if f.code == "unbound_path_token"]
    # lib/x.py still warns: matched via the .py extension alternative
    assert any("lib/x.py" in m for m in messages)
    # lib/README has no extension and "lib" is not in coverage_dirs: no warning
    assert not any("lib/README" in m for m in messages)

    auto_policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md")], require_lock=False)
    auto_report = verify_repo(tmp_path, auto_policy)
    auto_messages = [f.message for f in auto_report.findings if f.code == "unbound_path_token"]
    assert any("lib/README" in m for m in auto_messages)


def test_doc_coverage_off_silences_warning(tmp_path: Path) -> None:
    _write_lib_repo(tmp_path)
    policy = Policy(
        root=tmp_path,
        docs=[DocPolicy(path="README.md", coverage="off")],
        require_lock=False,
    )
    assert policy.coverage == "paths"
    report = verify_repo(tmp_path, policy)
    assert not any(f.code == "unbound_path_token" for f in report.findings)


def test_discover_top_dirs_excludes_and_includes(tmp_path: Path) -> None:
    for name in (".git", "__pycache__", "result", "foo.egg-info", ".github", ".truthgate", "lib"):
        (tmp_path / name).mkdir()
    dirs = discover_top_dirs(tmp_path)
    assert ".git" not in dirs
    assert "__pycache__" not in dirs
    assert "result" not in dirs
    assert "foo.egg-info" not in dirs
    assert ".github" in dirs
    assert ".truthgate" in dirs
    assert "lib" in dirs


def test_pathish_pattern_empty_and_escaped(tmp_path: Path) -> None:
    empty = pathish_pattern((), ())
    assert empty.search("src/app.py") is None
    assert empty.search("anything at all") is None

    escaped = pathish_pattern(("a.b",), ())
    assert escaped.search("axb/c") is None
    assert escaped.search("a.b/c") is not None
