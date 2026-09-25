"""Minimal MCP stdio server. No third-party SDK required.

Tools are the only surface agents need to keep READMEs honest.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .edit import apply_ops, preview_ops, write_if_ok
from .parse import parse_document
from .policy import load_policy
from .receipt import write_receipt
from .security import ConfineError, confine
from .verify import verify_repo

PROTOCOL_VERSION = "2024-11-05"


def _tool(name: str, description: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": schema,
    }


TOOLS = [
    _tool(
        "truthgate_status",
        "Show Truthgate policy, documented files, and last receipt for this repo.",
        {"type": "object", "properties": {}},
    ),
    _tool(
        "truthgate_list_claims",
        "Extract bound and unbound claims from a documented markdown file.",
        {
            "type": "object",
            "properties": {
                "doc": {"type": "string", "description": "Document path relative to repo root. Defaults to first policy doc."}
            },
        },
    ),
    _tool(
        "truthgate_verify",
        "Run CI gates against the working tree. Returns structured findings and receipts.",
        {
            "type": "object",
            "properties": {
                "write_receipt": {"type": "boolean", "default": False}
            },
        },
    ),
    _tool(
        "truthgate_propose_edit",
        "Preview structured README edits without writing. Ops: replace_claim_body, upsert_claim, remove_claim, replace_section, set_fence_meta.",
        {
            "type": "object",
            "required": ["ops"],
            "properties": {
                "doc": {"type": "string", "default": "README.md"},
                "ops": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of edit operations.",
                },
            },
        },
    ),
    _tool(
        "truthgate_apply_edit",
        "Apply structured README edits. Refuses to leave the tree failing gates unless force=true.",
        {
            "type": "object",
            "required": ["ops"],
            "properties": {
                "doc": {"type": "string", "default": "README.md"},
                "ops": {"type": "array", "items": {"type": "object"}},
                "force": {"type": "boolean", "default": False},
            },
        },
    ),
    _tool(
        "truthgate_schema",
        "Return claim kinds and allowed edit operations.",
        {"type": "object", "properties": {}},
    ),
]


class TruthgateMCP:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def handle(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "truthgate", "version": __version__},
                },
            }
        if method == "notifications/initialized" or method is None:
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": mid, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                result = self.call_tool(name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                        "structuredContent": result,
                    },
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": str(exc)}],
                    },
                }
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }

    def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        policy = load_policy(self.root)
        if name == "truthgate_status":
            return {
                "root": str(self.root),
                "docs": [d.path for d in policy.docs],
                "fail_on": policy.fail_on,
                "receipt_path": policy.receipt_path,
                "receipt_exists": (self.root / policy.receipt_path).is_file(),
            }
        if name == "truthgate_list_claims":
            rel = args.get("doc") or policy.docs[0].path
            path = confine(self.root, rel)
            if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
                raise ConfineError("doc must be markdown")
            claims, issues = parse_document(path, rel=rel)
            return {
                "path": rel,
                "issues": issues,
                "claims": [c.to_dict() for c in claims],
            }
        if name == "truthgate_verify":
            report = verify_repo(self.root, policy)
            if args.get("write_receipt"):
                write_receipt(self.root, policy.receipt_path, report)
            return report.to_dict()
        if name == "truthgate_propose_edit":
            rel = args.get("doc") or "README.md"
            path = confine(self.root, rel)
            preview = preview_ops(path, list(args.get("ops") or []))
            return preview
        if name == "truthgate_apply_edit":
            rel = args.get("doc") or "README.md"
            path = confine(self.root, rel)
            if path.suffix.lower() not in {".md", ".markdown"}:
                raise ConfineError("edits limited to markdown documents")
            ops = list(args.get("ops") or [])
            force = bool(args.get("force"))
            if force and os.environ.get("TRUTHGATE_ALLOW_FORCE") != "1":
                return {
                    "applied": False,
                    "error": "force is disabled unless TRUTHGATE_ALLOW_FORCE=1",
                }
            preview = preview_ops(path, ops)
            if not preview.get("ok"):
                return {"applied": False, "preview": preview}
            original = path.read_text(encoding="utf-8")
            result = apply_ops(path, ops)
            if result.text is not None:
                write_if_ok(path, result.text)
            report = verify_repo(self.root, policy)
            if not report.ok and not force:
                path.write_text(original, encoding="utf-8")
                return {
                    "applied": False,
                    "reverted": True,
                    "verify_ok": False,
                    "warning": "Edit would fail gates; working tree left unchanged. Use force=true to keep a failing README.",
                    "report": report.to_dict(),
                    "preview": {k: v for k, v in preview.items() if k != "text"},
                }
            return {"applied": True, "verify_ok": report.ok, "report": report.to_dict()}
        if name == "truthgate_schema":
            return {
                "kinds": [
                    "file_exists",
                    "dir_exists",
                    "glob_count",
                    "file_contains",
                    "json_pointer",
                    "toml_key",
                    "command",
                    "heading",
                    "rel_link",
                    "version_sync",
                    "python_symbol",
                    "entrypoint",
                    "prose",
                ],
                "ops": [
                    "replace_claim_body",
                    "upsert_claim",
                    "remove_claim",
                    "replace_section",
                    "set_fence_meta",
                ],
            }
        raise ValueError(f"unknown tool {name}")


def run_stdio(root: Path) -> None:
    """Serve JSON-RPC over stdio.

    MCP stdio transport is newline-delimited JSON, which is the default.
    Requests that arrive with LSP-style ``Content-Length`` headers are
    answered with the same framing.
    """
    server = TruthgateMCP(root)
    stdin = sys.stdin
    while True:
        line = stdin.readline()
        if line == "":
            return
        line = line.strip()
        if not line:
            continue
        framed = False
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            # LSP-style Content-Length framing
            if line.lower().startswith("content-length:"):
                framed = True
                try:
                    length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    continue
                # skip remaining headers
                while True:
                    hdr = stdin.readline()
                    if hdr in ("", "\r\n", "\n"):
                        break
                body = stdin.read(length)
                try:
                    msg = json.loads(body)
                except json.JSONDecodeError:
                    continue
            else:
                continue
        reply = server.handle(msg)
        if reply is None:
            continue
        payload = json.dumps(reply)
        if framed:
            sys.stdout.write(f"Content-Length: {len(payload.encode())}\r\n\r\n{payload}")
        else:
            sys.stdout.write(payload + "\n")
        sys.stdout.flush()
