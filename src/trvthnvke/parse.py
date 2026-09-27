from __future__ import annotations

import re
from pathlib import Path

from .model import ALLOWED_KINDS, Claim

CLAIM_OPEN = re.compile(r"<!--\s*truth:claim\b(.*?)-->", re.DOTALL | re.IGNORECASE)
CLAIM_END = re.compile(r"<!--\s*truth:end\s*-->", re.IGNORECASE)
FENCE_OPEN = re.compile(r"^([ \t]{0,3})(`{3,}|~{3,})([^\n]*)\n", re.MULTILINE)
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
TRUTH_TOKEN = re.compile(r"truth:([A-Za-z0-9_]+)=([^\s]+)")
KV_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.+?)\s*$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_kv_block(text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    # First line may contain leftover tokens after truth:claim
    leftover = text.strip()
    for token in TRUTH_TOKEN.finditer(leftover.split("\n", 1)[0]):
        attrs[token.group(1)] = _unquote(token.group(2))
    for line in leftover.splitlines():
        m = KV_LINE.match(line.strip())
        if m:
            attrs[m.group(1)] = _unquote(m.group(2))
    return attrs


def parse_info_tokens(info: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    info = info.strip()
    if info.startswith("{"):
        inner = info.strip("{}")
        for part in re.split(r"[,\s]+", inner):
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                if k.startswith("truth:"):
                    k = k[6:]
                attrs[k] = _unquote(v)
        return attrs
    for token in TRUTH_TOKEN.finditer(info):
        attrs[token.group(1)] = _unquote(token.group(2))
    if re.search(r"\btruth:ignore\b", info):
        attrs["ignore"] = "true"
    return attrs


def iter_fence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    scan = 0
    while scan < len(text):
        fm = FENCE_OPEN.match(text, scan)
        if not fm:
            nxt = text.find("\n", scan)
            if nxt == -1:
                break
            scan = nxt + 1
            continue
        indent, fence = fm.group(1), fm.group(2)
        close = re.compile(r"^" + re.escape(indent) + re.escape(fence) + r"[ \t]*$", re.MULTILINE)
        close_m = close.search(text, fm.end())
        if not close_m:
            break
        spans.append((fm.start(), close_m.end()))
        scan = close_m.end()
    return spans


def ignored_fence_spans(text: str) -> list[tuple[int, int]]:
    """Spans of fenced blocks whose info string carries truth:ignore."""
    spans: list[tuple[int, int]] = []
    scan = 0
    while scan < len(text):
        fm = FENCE_OPEN.match(text, scan)
        if not fm:
            nxt = text.find("\n", scan)
            if nxt == -1:
                break
            scan = nxt + 1
            continue
        indent, fence, info = fm.group(1), fm.group(2), fm.group(3)
        close = re.compile(r"^" + re.escape(indent) + re.escape(fence) + r"[ \t]*$", re.MULTILINE)
        close_m = close.search(text, fm.end())
        if not close_m:
            break
        tokens = parse_info_tokens(info)
        if str(tokens.get("ignore", "")).lower() in {"1", "true", "yes"}:
            spans.append((fm.start(), close_m.end()))
        scan = close_m.end()
    return spans


def in_spans(index: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= index < b for a, b in spans)


def extract_headings(text: str) -> list[tuple[int, int, str]]:
    fences = iter_fence_spans(text)
    out: list[tuple[int, int, str]] = []
    for m in HEADING.finditer(text):
        if any(a <= m.start() < b for a, b in fences):
            continue
        line = text[: m.start()].count("\n") + 1
        out.append((line, len(m.group(1)), m.group(2).strip()))
    return out



def extract_rel_links(text: str) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    for m in MD_LINK.finditer(text):
        href = m.group(1).strip()
        if href.startswith("#") or "://" in href or href.startswith("mailto:"):
            continue
        line = text[: m.start()].count("\n") + 1
        links.append((line, href.split()[0]))
    return links


def parse_document(
    path: Path, text: str | None = None, rel: str | None = None
) -> tuple[list[Claim], list[dict]]:
    """Return (claims, parse_issues).

    ``rel`` is the display path recorded on claims and issues (normally the
    document path relative to the repository root). Defaults to ``str(path)``.
    """
    if text is None:
        text = path.read_text(encoding="utf-8")
    rel = rel or str(path)
    issues: list[dict] = []
    claims: list[Claim] = []
    seen_ids: set[str] = set()
    ignored_spans = ignored_fence_spans(text)

    def in_ignored(index: int) -> bool:
        return in_spans(index, ignored_spans)

    # HTML comment claim blocks
    pos = 0
    while True:
        m = CLAIM_OPEN.search(text, pos)
        if not m:
            break
        if in_ignored(m.start()):
            pos = m.end()
            continue
        start = m.start()
        start_line = text[:start].count("\n") + 1
        attrs = parse_kv_block(m.group(1))
        end_m = CLAIM_END.search(text, m.end())
        if not end_m:
            issues.append(
                {
                    "path": rel,
                    "line": start_line,
                    "code": "unclosed_claim",
                    "message": "truth:claim block is missing a matching <!-- truth:end -->",
                }
            )
            break
        body = text[m.end() : end_m.start()].strip("\n")
        end_line = text[: end_m.end()].count("\n") + 1
        cid = attrs.get("id") or attrs.get("claim") or ""
        kind = attrs.get("kind") or "prose"
        ignored = str(attrs.get("ignore", "")).lower() in {"1", "true", "yes"}
        if not cid:
            issues.append(
                {
                    "path": rel,
                    "line": start_line,
                    "code": "missing_id",
                    "message": "truth:claim is missing required field id",
                }
            )
        elif cid in seen_ids:
            issues.append(
                {
                    "path": rel,
                    "line": start_line,
                    "code": "duplicate_id",
                    "message": f"duplicate claim id '{cid}'",
                }
            )
        if kind not in ALLOWED_KINDS:
            issues.append(
                {
                    "path": rel,
                    "line": start_line,
                    "code": "unknown_kind",
                    "message": f"unknown claim kind '{kind}'",
                }
            )
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            claims.append(
                Claim(
                    id=cid,
                    kind=kind,
                    source="block",
                    path=rel,
                    start_line=start_line,
                    end_line=end_line,
                    severity=attrs.get("severity", "error"),
                    attrs=attrs,
                    body=body,
                    ignored=ignored,
                )
            )
        pos = end_m.end()

    # Fenced code claims
    buf_pos = 0
    while buf_pos < len(text):
        m = FENCE_OPEN.match(text, buf_pos)
        if not m:
            # advance to next candidate
            nxt = text.find("\n", buf_pos)
            if nxt == -1:
                break
            buf_pos = nxt + 1
            continue
        indent, fence, info = m.group(1), m.group(2), m.group(3)
        start_line = text[: m.start()].count("\n") + 1
        close = re.compile(r"^" + re.escape(indent) + re.escape(fence) + r"[ \t]*$", re.MULTILINE)
        close_m = close.search(text, m.end())
        if not close_m:
            issues.append(
                {
                    "path": rel,
                    "line": start_line,
                    "code": "unclosed_fence",
                    "message": "unclosed fenced code block",
                }
            )
            break
        body = text[m.end() : close_m.start()].rstrip("\n")
        end_line = text[: close_m.end()].count("\n") + 1
        tokens = parse_info_tokens(info)
        ignored = str(tokens.get("ignore", "")).lower() in {"1", "true", "yes"}
        cid = tokens.get("id")
        kind = tokens.get("kind") or ("command" if cid else None)
        lang = info.strip().split()[0] if info.strip() and not info.strip().startswith("{") else ""
        if lang.startswith("truth:"):
            lang = ""
        if cid:
            if cid in seen_ids:
                issues.append(
                    {
                        "path": rel,
                        "line": start_line,
                        "code": "duplicate_id",
                        "message": f"duplicate claim id '{cid}'",
                    }
                )
            else:
                seen_ids.add(cid)
                attrs = dict(tokens)
                if lang:
                    attrs.setdefault("lang", lang)
                if kind == "command":
                    attrs.setdefault("run", body.strip())
                claims.append(
                    Claim(
                        id=cid,
                        kind=kind or "command",
                        source="fence",
                        path=rel,
                        start_line=start_line,
                        end_line=end_line,
                        severity=tokens.get("severity", "error"),
                        attrs=attrs,
                        body=body,
                        ignored=ignored,
                    )
                )
        elif not ignored:
            claims.append(
                Claim(
                    id=f"__unbound_fence_{start_line}",
                    kind="command",
                    source="fence",
                    path=rel,
                    start_line=start_line,
                    end_line=end_line,
                    severity="error",
                    attrs={"lang": lang, "unbound": "true"},
                    body=body,
                    ignored=False,
                )
            )
        buf_pos = close_m.end()

    return claims, issues


def document_text_without_directives(text: str) -> str:
    """Useful for rendering; not required for GitHub (comments already hidden)."""
    text = CLAIM_OPEN.sub("", text)
    text = CLAIM_END.sub("", text)
    return text
