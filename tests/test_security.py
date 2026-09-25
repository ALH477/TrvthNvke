from pathlib import Path

from truthgate.model import Claim
from truthgate.policy import DocPolicy, Policy
from truthgate.security import CommandDenied, ConfineError, confine, parse_command, run_confined_command
from truthgate.verify import check_claim, verify_repo


def test_confine_rejects_parent_and_absolute(tmp_path: Path) -> None:
    try:
        confine(tmp_path, "../etc/passwd")
        raise AssertionError("expected ConfineError")
    except ConfineError:
        pass
    try:
        confine(tmp_path, "/etc/passwd")
        raise AssertionError("expected ConfineError")
    except ConfineError:
        pass


def test_symlink_escape(tmp_path: Path) -> None:
    target = tmp_path / "link.py"
    try:
        target.symlink_to("/etc/passwd")
    except OSError:
        return
    try:
        confine(tmp_path, "link.py")
        raise AssertionError("expected ConfineError")
    except ConfineError:
        pass


def test_severity_cannot_downgrade(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """# X
## Install
<!-- truth:claim
id: lie
kind: file_exists
path: missing.py
severity: info
-->
We ship `missing.py`.
<!-- truth:end -->
""",
        encoding="utf-8",
    )
    policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md")], require_lock=False, coverage="off")
    report = verify_repo(tmp_path, policy)
    assert not report.ok
    assert any(f.severity == "error" and f.code == "claim_failed" for f in report.findings)


def test_ignore_requires_reason(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """# X
<!-- truth:claim
id: lie
kind: file_exists
path: missing.py
ignore: true
-->
We ship `missing.py`.
<!-- truth:end -->
""",
        encoding="utf-8",
    )
    policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md")], require_lock=False, coverage="off")
    report = verify_repo(tmp_path, policy)
    assert not report.ok


def test_command_not_allowlisted(tmp_path: Path) -> None:
    c = Claim(
        id="x",
        kind="command",
        source="fence",
        path="README.md",
        start_line=1,
        end_line=1,
        attrs={"run": "echo pwned"},
        body="echo pwned",
    )
    policy = Policy(root=tmp_path, require_lock=False)
    ok, evidence = check_claim(tmp_path, c, policy)
    assert not ok
    assert "allowlist" in evidence


def test_parse_command_env() -> None:
    env, argv = parse_command('PYTHONPATH=src python3 -m truthgate --version')
    assert env["PYTHONPATH"] == "src"
    assert argv[:3] == ["python3", "-m", "truthgate"]
