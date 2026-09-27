from pathlib import Path

from trvthnvke.policy import Policy, DocPolicy
from trvthnvke.verify import verify_repo


def _write_repo(tmp: Path) -> None:
    (tmp / "src").mkdir()
    (tmp / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp / "README.md").write_text(
        """# App

## Install

<!-- truth:claim
id: app-file
kind: file_exists
path: src/app.py
-->
Source lives in `src/app.py`.
<!-- truth:end -->

```bash truth:id=py-help truth:kind=command truth:expect_exit=0
test -f src/app.py
```
""",
        encoding="utf-8",
    )


def test_verify_pass(tmp_path: Path) -> None:
    _write_repo(tmp_path)
    policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md", required_headings=["Install"])])
    report = verify_repo(tmp_path, policy)
    assert report.ok, [f.to_dict() for f in report.findings]


def test_verify_fail_missing_file(tmp_path: Path) -> None:
    _write_repo(tmp_path)
    readme = tmp_path / "README.md"
    text = readme.read_text(encoding="utf-8").replace("src/app.py", "src/missing.py")
    readme.write_text(text, encoding="utf-8")
    policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md")])
    report = verify_repo(tmp_path, policy)
    assert not report.ok
    assert any(f.code == "claim_failed" for f in report.findings)


def test_paths_are_repo_relative(tmp_path: Path) -> None:
    _write_repo(tmp_path)
    readme = tmp_path / "README.md"
    text = readme.read_text(encoding="utf-8").replace("src/app.py", "src/missing.py")
    readme.write_text(text, encoding="utf-8")
    policy = Policy(root=tmp_path, docs=[DocPolicy(path="README.md")])
    report = verify_repo(tmp_path, policy)
    assert not report.ok
    for finding in report.findings:
        assert finding.path == "README.md", finding
        assert str(tmp_path) not in finding.evidence, finding
    for receipt in report.receipts:
        assert receipt["path"] == "README.md", receipt
        assert str(tmp_path) not in receipt["evidence"], receipt
