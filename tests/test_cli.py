import json
from pathlib import Path

from trvthnvke.cli import main


def _repo(tmp: Path) -> None:
    (tmp / ".trvthnvke.toml").write_text('[policy]\nrequire_lock = false\n\n[[docs]]\npath = "README.md"\n', encoding="utf-8")
    (tmp / "README.md").write_text(
        "# App\n\n<!-- truth:claim\nid: v\nkind: prose\n-->\nold\n<!-- truth:end -->\n",
        encoding="utf-8",
    )


def test_edit_ops_file(tmp_path: Path, capsys=None) -> None:
    _repo(tmp_path)
    ops = tmp_path / "ops.json"
    ops.write_text(json.dumps([{"op": "replace_claim_body", "id": "v", "body": "new"}]), encoding="utf-8")
    rc = main(["--root", str(tmp_path), "edit", "--doc", "README.md", "--ops-file", str(ops)])
    assert rc == 0
    assert "\nnew\n" in (tmp_path / "README.md").read_text(encoding="utf-8")
