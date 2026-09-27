from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .parse import CLAIM_END, CLAIM_OPEN, HEADING, ignored_fence_spans, in_spans, iter_fence_spans, parse_document

# Keys of an upsert_claim op that are not claim attributes.
_CONTROL_KEYS = {"op", "id", "kind", "severity", "body", "after_heading", "attrs"}
_HEAD_KEYS = ("id", "kind", "severity")


@dataclass
class EditResult:
    ok: bool
    path: str
    message: str
    text: str | None = None


def _render_block(claim: dict[str, Any], body: str) -> str:
    lines = ["<!-- truth:claim"]
    for key in _HEAD_KEYS:
        if claim.get(key) is not None:
            lines.append(f"{key}: {claim[key]}")
    attrs: dict[str, Any] = {k: v for k, v in claim.items() if k not in _CONTROL_KEYS and v is not None}
    for k, v in (claim.get("attrs") or {}).items():
        if k not in _HEAD_KEYS and v is not None:
            attrs[k] = v
    for k, v in attrs.items():
        lines.append(f"{k}: {v}")
    lines.append("-->")
    lines.append(body.rstrip())
    lines.append("<!-- truth:end -->")
    return "\n".join(lines) + "\n"


def _headings(text: str) -> list[tuple[int, int, int, str]]:
    """(start, end, level, title) for every heading outside a fenced block."""
    fences = iter_fence_spans(text)
    out: list[tuple[int, int, int, str]] = []
    for m in HEADING.finditer(text):
        if in_spans(m.start(), fences):
            continue
        out.append((m.start(), m.end(), len(m.group(1)), m.group(2).strip()))
    return out


def _find_heading(text: str, heading: str) -> tuple[int, int, int] | None:
    for start, end, level, title in _headings(text):
        if title == heading:
            return start, end, level
    return None


def apply_ops(path: Path, ops: list[dict[str, Any]]) -> EditResult:
    if not path.is_file():
        return EditResult(False, str(path), "file does not exist")
    text = path.read_text(encoding="utf-8")
    original = text
    for op in ops:
        name = op.get("op")
        if name == "replace_claim_body":
            text, err = _replace_claim_body(text, op["id"], op["body"])
            if err:
                return EditResult(False, str(path), err)
        elif name == "upsert_claim":
            text, err = _upsert_claim(text, op)
            if err:
                return EditResult(False, str(path), err)
        elif name == "remove_claim":
            text, err = _remove_claim(text, op["id"])
            if err:
                return EditResult(False, str(path), err)
        elif name == "replace_section":
            text, err = _replace_section(text, op["heading"], op["body"])
            if err:
                return EditResult(False, str(path), err)
        elif name == "set_fence_meta":
            text, err = _set_fence_meta(text, int(op["line"]), op.get("meta", ""))
            if err:
                return EditResult(False, str(path), err)
        else:
            return EditResult(False, str(path), f"unknown op {name}")
    if text == original:
        return EditResult(True, str(path), "no changes", text)
    return EditResult(True, str(path), "patched", text)


def write_if_ok(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _find_block(text: str, claim_id: str) -> tuple[int, int, int, int] | None:
    """Return (open_start, open_end, end_start, end_end) or None.

    Claim blocks that sit inside a ``truth:ignore`` fence are documentation
    samples, not live claims, and are never matched.
    """
    ignored = ignored_fence_spans(text)
    pos = 0
    while True:
        m = CLAIM_OPEN.search(text, pos)
        if not m:
            return None
        if in_spans(m.start(), ignored):
            pos = m.end()
            continue
        attrs_blob = m.group(1)
        if re.search(rf"(?m)^id:\s*{re.escape(claim_id)}\s*$", attrs_blob) or re.search(
            rf"truth:id={re.escape(claim_id)}\b", attrs_blob
        ):
            end = CLAIM_END.search(text, m.end())
            if not end:
                return None
            return m.start(), m.end(), end.start(), end.end()
        pos = m.end()


def _replace_claim_body(text: str, claim_id: str, body: str) -> tuple[str, str | None]:
    found = _find_block(text, claim_id)
    if not found:
        return text, f"claim '{claim_id}' not found"
    open_start, open_end, end_start, end_end = found
    body = body.rstrip() + "\n"
    new = text[:open_end] + "\n" + body + text[end_start:]
    return new, None


def _remove_claim(text: str, claim_id: str) -> tuple[str, str | None]:
    found = _find_block(text, claim_id)
    if not found:
        return text, f"claim '{claim_id}' not found"
    open_start, _, _, end_end = found
    new = text[:open_start] + text[end_end:]
    new = re.sub(r"\n{3,}", "\n\n", new)
    return new, None


def _upsert_claim(text: str, op: dict[str, Any]) -> tuple[str, str | None]:
    cid = op.get("id")
    if not cid:
        return text, "upsert_claim requires id"
    body = op.get("body") or ""
    if _find_block(text, cid):
        # replace whole block
        found = _find_block(text, cid)
        assert found
        open_start, _, _, end_end = found
        block = _render_block(op, body)
        return text[:open_start] + block + text[end_end:], None
    heading = op.get("after_heading")
    block = _render_block(op, body)
    if heading:
        found_h = _find_heading(text, heading)
        if not found_h:
            return text, f"heading {heading!r} not found"
        _, h_end, _ = found_h
        # insert after this heading line
        line_end = text.find("\n", h_end)
        if line_end == -1:
            line_end = len(text)
        return text[: line_end + 1] + "\n" + block + text[line_end + 1 :], None
    return text.rstrip() + "\n\n" + block, None


def _replace_section(text: str, heading: str, body: str) -> tuple[str, str | None]:
    found_h = _find_heading(text, heading)
    if not found_h:
        return text, f"heading {heading!r} not found"
    start, h_end, level = found_h
    end = len(text)
    for h_start, _, h_level, _ in _headings(text):
        if h_start > start and h_level <= level:
            end = h_start
            break
    new_section = f"{'#' * level} {heading}\n\n{body.rstrip()}\n\n"
    return text[:start] + new_section + text[end:], None


def _set_fence_meta(text: str, line: int, meta: str) -> tuple[str, str | None]:
    lines = text.splitlines(keepends=True)
    if line < 1 or line > len(lines):
        return text, "line out of range"
    raw = lines[line - 1]
    m = re.match(r"^([ \t]{0,3})(`{3,}|~{3,})(.*)$", raw.rstrip("\n"))
    if not m:
        return text, f"line {line} is not a fence opener"
    nl = "\n" if raw.endswith("\n") else ""
    lines[line - 1] = f"{m.group(1)}{m.group(2)}{meta}{nl}"
    return "".join(lines), None


def preview_ops(path: Path, ops: list[dict[str, Any]]) -> dict[str, Any]:
    result = apply_ops(path, ops)
    claims_before, _ = parse_document(path)
    preview = {
        "ok": result.ok,
        "message": result.message,
        "path": result.path,
        "changed": bool(result.text and result.text != path.read_text(encoding="utf-8")),
        "claims_before": [c.id for c in claims_before if not c.attrs.get("unbound")],
    }
    if result.ok and result.text is not None:
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write(result.text)
            tmp = Path(fh.name)
        claims_after, issues = parse_document(tmp, result.text)
        tmp.unlink(missing_ok=True)
        preview["claims_after"] = [c.id for c in claims_after if not c.attrs.get("unbound")]
        preview["parse_issues"] = issues
        preview["text"] = result.text
    return preview


def load_ops(raw: str) -> list[dict[str, Any]]:
    data = json.loads(raw)
    if isinstance(data, dict) and "ops" in data:
        return list(data["ops"])
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError("ops must be a JSON object or array")
