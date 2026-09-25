from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .edit import apply_ops, load_ops, preview_ops, write_if_ok
from .gitutil import find_root, install_pre_commit
from .parse import parse_document
from .policy import default_config_text, dump_lock, load_policy
from .receipt import write_receipt
from .verify import verify_repo


def _root(ns: argparse.Namespace) -> Path:
    return find_root(Path(ns.root).resolve()) if getattr(ns, "root", None) else find_root(Path.cwd())


def cmd_init(ns: argparse.Namespace) -> int:
    root = Path(ns.root).resolve() if ns.root else Path.cwd()
    cfg = root / ".truthgate.toml"
    if cfg.exists() and not ns.force:
        print(f"exists: {cfg}", file=sys.stderr)
        return 1
    cfg.write_text(default_config_text(), encoding="utf-8")
    (root / ".truthgate").mkdir(exist_ok=True)
    gitignore = root / ".truthgate" / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("# keep directory; receipts may be committed or ignored\n", encoding="utf-8")
    print(f"wrote {cfg}")
    if ns.hook:
        try:
            hook = install_pre_commit(root)
            print(f"installed {hook}")
        except FileNotFoundError as exc:
            print(f"hook skipped: {exc}", file=sys.stderr)
    try:
        lock = dump_lock(root, ".truthgate.lock")
        print(f"wrote {lock}")
    except FileNotFoundError:
        pass
    return 0


def cmd_extract(ns: argparse.Namespace) -> int:
    root = _root(ns)
    policy = load_policy(root)
    docs = [ns.doc] if ns.doc else policy.doc_paths
    out = []
    for rel in docs:
        path = root / rel
        if not path.is_file():
            print(f"missing {rel}", file=sys.stderr)
            return 1
        claims, issues = parse_document(path, rel=rel)
        out.append(
            {
                "path": rel,
                "issues": issues,
                "claims": [c.to_dict() for c in claims],
            }
        )
    print(json.dumps(out if len(out) != 1 else out[0], indent=2))
    return 0


def cmd_verify(ns: argparse.Namespace) -> int:
    root = _root(ns)
    policy = load_policy(root)
    report = verify_repo(root, policy)
    if ns.receipt:
        write_receipt(root, policy.receipt_path, report)
    if ns.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        status = "PASS" if report.ok else "FAIL"
        print(f"truthgate {status}  claims={report.claims} checked={report.checked} passed={report.passed} errors={report.failed} warnings={report.warnings}")
        for f in report.findings:
            cid = f.claim_id or "-"
            extra = f" :: {f.evidence}" if f.evidence else ""
            print(f"  [{f.severity}] {f.path}:{f.line} {f.code} {cid} {f.message}{extra}")
    if ns.fail and not report.ok:
        return 1
    return 0


def cmd_edit(ns: argparse.Namespace) -> int:
    root = _root(ns)
    path = root / ns.doc
    raw = Path(ns.ops_file).read_text(encoding="utf-8") if ns.ops_file else ns.ops
    if raw is None:
        raw = sys.stdin.read()
    try:
        ops = load_ops(raw)
    except Exception as exc:
        print(f"invalid ops: {exc}", file=sys.stderr)
        return 2
    if ns.dry_run:
        preview = preview_ops(path, ops)
        print(json.dumps({k: v for k, v in preview.items() if k != "text" or ns.print_text}, indent=2))
        return 0 if preview["ok"] else 1
    result = apply_ops(path, ops)
    if not result.ok:
        print(result.message, file=sys.stderr)
        return 1
    if result.text is not None:
        write_if_ok(path, result.text)
    print(result.message)
    if ns.verify:
        policy = load_policy(root)
        report = verify_repo(root, policy)
        if not report.ok:
            print("edit applied but verify failed", file=sys.stderr)
            return 1
    return 0


def cmd_lock(ns: argparse.Namespace) -> int:
    root = _root(ns)
    policy = load_policy(root)
    dest = dump_lock(root, policy.lock_path)
    print(f"wrote {dest}")
    return 0


def cmd_hook(ns: argparse.Namespace) -> int:
    root = _root(ns)
    hook = install_pre_commit(root)
    print(f"installed {hook}")
    return 0


def cmd_mcp(ns: argparse.Namespace) -> int:
    from .mcp_server import run_stdio

    root = _root(ns)
    run_stdio(root)
    return 0


def cmd_schema(ns: argparse.Namespace) -> int:
    schema = {
        "$id": "https://truthgate.dev/schema/claim.json",
        "title": "TruthMD claim",
        "type": "object",
        "required": ["id", "kind"],
        "properties": {
            "id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_.-]*$"},
            "kind": {
                "enum": [
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
                    "prose",
                ]
            },
            "severity": {"enum": ["error", "warning", "info"]},
            "path": {"type": "string"},
            "glob": {"type": "string"},
            "equals": {},
            "min": {"type": "integer"},
            "max": {"type": "integer"},
            "pattern": {"type": "string"},
            "pointer": {"type": "string"},
            "key": {"type": "string"},
            "run": {"type": "string"},
            "expect_exit": {"type": "integer"},
            "expect_stdout": {"type": "string"},
            "timeout": {"type": "integer"},
            "href": {"type": "string"},
            "title": {"type": "string"},
        },
        "edit_ops": [
            "replace_claim_body",
            "upsert_claim",
            "remove_claim",
            "replace_section",
            "set_fence_meta",
        ],
    }
    print(json.dumps(schema, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="truthgate", description="Force README claims to match repository reality.")
    p.add_argument("--version", action="version", version=f"truthgate {__version__}")
    p.add_argument("--root", help="repository root (default: discover from cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="write .truthgate.toml")
    init.add_argument("--force", action="store_true")
    init.add_argument("--hook", action="store_true", help="also install git pre-commit hook")
    init.set_defaults(func=cmd_init)

    ext = sub.add_parser("extract", help="dump claims as JSON")
    ext.add_argument("--doc", help="single document path")
    ext.set_defaults(func=cmd_extract)

    ver = sub.add_parser("verify", help="run CI gates")
    ver.add_argument("--json", action="store_true")
    ver.add_argument("--fail", action="store_true", help="exit 1 if gates fail")
    ver.add_argument("--receipt", action="store_true", help="write last-run receipt")
    ver.set_defaults(func=cmd_verify)

    ed = sub.add_parser("edit", help="apply structured README ops")
    ed.add_argument("--doc", default="README.md")
    ed.add_argument("--ops", help="JSON ops string")
    ed.add_argument("--ops-file", dest="ops_file")
    ed.add_argument("--dry-run", action="store_true")
    ed.add_argument("--print-text", action="store_true")
    ed.add_argument("--verify", action="store_true", help="re-verify after apply")
    ed.set_defaults(func=cmd_edit)

    lockp = sub.add_parser("lock", help="write .truthgate.lock from current policy file")
    lockp.set_defaults(func=cmd_lock)

    hook = sub.add_parser("install-hook", help="install pre-commit gate")
    hook.set_defaults(func=cmd_hook)

    mcp = sub.add_parser("mcp", help="run MCP server on stdio")
    mcp.set_defaults(func=cmd_mcp)

    sch = sub.add_parser("schema", help="print claim + edit schema")
    sch.set_defaults(func=cmd_schema)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())
