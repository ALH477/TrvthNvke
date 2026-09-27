from pathlib import Path

from trvthnvke.parse import parse_document

SAMPLE = """# Demo

<!-- truth:claim
id: cli-path
kind: file_exists
path: src/trvthnvke/cli.py
-->
The CLI lives at `src/trvthnvke/cli.py`.
<!-- truth:end -->

```bash truth:id=help truth:kind=command truth:expect_exit=0
python -m trvthnvke --help
```

```python truth:ignore
print("unbound on purpose")
```

```
orphan
```
"""


def test_parse_block_and_fence(tmp_path: Path) -> None:
    p = tmp_path / "README.md"
    p.write_text(SAMPLE, encoding="utf-8")
    claims, issues = parse_document(p)
    ids = {c.id: c for c in claims}
    assert "cli-path" in ids
    assert ids["cli-path"].kind == "file_exists"
    assert "help" in ids
    assert ids["help"].attrs.get("expect_exit") == "0"
    unbound = [c for c in claims if c.attrs.get("unbound") == "true"]
    assert len(unbound) == 1
    assert not any(c.id == "cli-path" and False for c in claims)
    assert issues == []
