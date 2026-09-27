from pathlib import Path

from trvthnvke.edit import apply_ops, write_if_ok
from trvthnvke.parse import parse_document


def test_upsert_and_replace(tmp_path: Path) -> None:
    p = tmp_path / "README.md"
    p.write_text("# App\n\n## Usage\n\nHello.\n", encoding="utf-8")
    result = apply_ops(
        p,
        [
            {
                "op": "upsert_claim",
                "id": "hello",
                "kind": "prose",
                "after_heading": "Usage",
                "body": "Hello world.",
            }
        ],
    )
    assert result.ok
    write_if_ok(p, result.text or "")
    claims, issues = parse_document(p)
    assert issues == []
    assert any(c.id == "hello" for c in claims)
    result = apply_ops(p, [{"op": "replace_claim_body", "id": "hello", "body": "Updated."}])
    write_if_ok(p, result.text or "")
    assert "Updated." in p.read_text(encoding="utf-8")


def test_upsert_renders_top_level_attrs(tmp_path: Path) -> None:
    p = tmp_path / "README.md"
    p.write_text("# App\n\n## Install\n\nHello.\n", encoding="utf-8")
    result = apply_ops(
        p,
        [
            {
                "op": "upsert_claim",
                "id": "cli",
                "kind": "file_exists",
                "path": "src/app.py",
                "after_heading": "Install",
                "body": "The CLI is `src/app.py`.",
            }
        ],
    )
    assert result.ok
    write_if_ok(p, result.text or "")
    claims, issues = parse_document(p)
    assert issues == []
    claim = next(c for c in claims if c.id == "cli")
    assert claim.attrs["path"] == "src/app.py"
    assert "\n\n<!-- truth:end -->" not in p.read_text(encoding="utf-8")


def test_replace_section_ignores_hash_inside_fence(tmp_path: Path) -> None:
    p = tmp_path / "README.md"
    p.write_text(
        "# T\n\n## Usage\n\ntext\n\n```bash truth:ignore\n# a comment\necho hi\n```\n\nmore\n\n## Next\n\nend\n",
        encoding="utf-8",
    )
    result = apply_ops(p, [{"op": "replace_section", "heading": "Usage", "body": "NEW"}])
    assert result.ok
    assert result.text == "# T\n\n## Usage\n\nNEW\n\n## Next\n\nend\n"


def test_find_block_skips_ignored_fence_samples(tmp_path: Path) -> None:
    from trvthnvke.edit import _find_block

    text = (
        "# T\n\n"
        "```markdown truth:ignore\n"
        "<!-- truth:claim\nid: x\nkind: prose\n-->\nsample\n<!-- truth:end -->\n"
        "```\n\n"
        "<!-- truth:claim\nid: x\nkind: prose\n-->\nreal\n<!-- truth:end -->\n"
    )
    found = _find_block(text, "x")
    assert found is not None
    assert "real" in text[found[1] : found[2]]
    p = tmp_path / "README.md"
    p.write_text(text, encoding="utf-8")
    result = apply_ops(p, [{"op": "remove_claim", "id": "x"}])
    assert result.ok and result.text is not None
    assert "real" not in result.text and "sample" in result.text
