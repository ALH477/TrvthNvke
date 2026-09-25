from __future__ import annotations

import json
import re
import tomllib
from glob import glob
from pathlib import Path
from typing import Any

from .model import Claim, Finding, VerifyReport
from .parse import extract_headings, extract_rel_links, ignored_fence_spans, parse_document
from .policy import Policy, find_policy_file
from .pyresolve import console_scripts, has_symbol, resolve_module, split_target
from .security import (
    CommandDenied,
    ConfineError,
    confine,
    coverage_tokens,
    run_confined_command,
    strip_ignored_and_comments,
)


def _pointer_get(data: Any, pointer: str) -> Any:
    if not pointer or pointer == "/":
        return data
    if not pointer.startswith("/"):
        cur = data
        for part in pointer.split("."):
            if isinstance(cur, dict):
                cur = cur[part]
            else:
                raise KeyError(pointer)
        return cur
    cur = data
    for raw in pointer.lstrip("/").split("/"):
        raw = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            cur = cur[int(raw)]
        elif isinstance(cur, dict):
            cur = cur[raw]
        else:
            raise KeyError(pointer)
    return cur


def _read_jsonish(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".toml":
        return tomllib.loads(text)
    return json.loads(text)


def _entail(claim: Claim, needle: str, policy: Policy) -> tuple[bool, str]:
    if not policy.require_entailment or not needle:
        return True, ""
    if needle not in (claim.body or ""):
        return False, f"claim body does not mention bound value {needle!r}"
    return True, ""


def check_claim(root: Path, claim: Claim, policy: Policy) -> tuple[bool, str]:
    if claim.ignored:
        reason = (claim.attrs.get("reason") or "").strip()
        if policy.ignore_requires_reason and not reason:
            return False, "ignored claim is missing reason"
        if policy.strict_ignore:
            return False, "ignored claims fail under strict_ignore"
        return True, f"ignored:{reason or 'no-reason'}"

    kind = claim.kind
    attrs = claim.attrs

    if attrs.get("unbound") == "true":
        return False, "unbound fenced block — add truth:id=... or truth:ignore"

    if kind == "prose":
        return True, "prose tracked; no machine check"

    if kind == "file_exists":
        rel = attrs.get("path") or attrs.get("file")
        try:
            target = confine(root, rel or "")
        except ConfineError as exc:
            return False, str(exc)
        ok_ent, ent = _entail(claim, str(rel), policy)
        if not ok_ent:
            return False, ent
        return target.is_file(), f"file {rel} exists={target.is_file()}"

    if kind == "dir_exists":
        rel = attrs.get("path") or attrs.get("dir")
        try:
            target = confine(root, rel or "")
        except ConfineError as exc:
            return False, str(exc)
        ok_ent, ent = _entail(claim, str(rel), policy)
        if not ok_ent:
            return False, ent
        return target.is_dir(), f"dir {rel} exists={target.is_dir()}"

    if kind == "glob_count":
        pattern = attrs.get("glob") or attrs.get("pattern")
        if not pattern:
            return False, "glob_count claim missing glob"
        if ".." in Path_parts(pattern):
            return False, "glob parent traversal rejected"
        matches = []
        for item in glob(str(root / pattern), recursive=True):
            try:
                matches.append(confine(root, str(Path(item).resolve().relative_to(root.resolve()))))
            except (ConfineError, ValueError):
                return False, f"glob matched path outside root: {item}"
        expected = attrs.get("equals") or attrs.get("count")
        minimum = attrs.get("min")
        maximum = attrs.get("max")
        n = len(matches)
        ok = True
        parts = [f"matched {n}"]
        if expected is not None:
            ok = ok and n == int(expected)
            parts.append(f"equals {expected}")
        if minimum is not None:
            ok = ok and n >= int(minimum)
            parts.append(f"min {minimum}")
        if maximum is not None:
            ok = ok and n <= int(maximum)
            parts.append(f"max {maximum}")
        if expected is None and minimum is None and maximum is None:
            return False, "glob_count needs equals, min, or max"
        return ok, "; ".join(parts)

    if kind == "file_contains":
        rel = attrs.get("path") or attrs.get("file")
        pattern = attrs.get("pattern") or attrs.get("regex") or attrs.get("text")
        if not rel or not pattern:
            return False, "file_contains needs path and pattern"
        if len(pattern) > 256:
            return False, "file_contains pattern too long"
        try:
            target = confine(root, rel)
        except ConfineError as exc:
            return False, str(exc)
        if not target.is_file():
            return False, f"missing file {rel}"
        text = target.read_text(encoding="utf-8")
        flags = re.MULTILINE
        if attrs.get("ignore_case") in {"1", "true", "yes"}:
            flags |= re.IGNORECASE
        try:
            found = re.search(pattern, text, flags) is not None
        except re.error as exc:
            return False, f"invalid pattern: {exc}"
        ok_ent, ent = _entail(claim, rel, policy)
        if not ok_ent:
            return False, ent
        return found, f"pattern {'found' if found else 'not found'} in {rel}"

    if kind in {"json_pointer", "toml_key"}:
        rel = attrs.get("path") or attrs.get("file")
        pointer = attrs.get("pointer") or attrs.get("key")
        expected = attrs.get("equals")
        if not rel or not pointer:
            return False, f"{kind} needs path and pointer/key"
        if expected is None:
            return False, f"{kind} requires equals (presence-only checks are forbidden)"
        try:
            target = confine(root, rel)
        except ConfineError as exc:
            return False, str(exc)
        if not target.is_file():
            return False, f"missing file {rel}"
        try:
            data = _read_jsonish(target)
            value = _pointer_get(data, pointer)
        except Exception as exc:
            return False, f"lookup failed: {exc}"
        return str(value) == str(expected), f"{pointer} = {value!r} expected {expected!r}"

    if kind == "command":
        if policy.command_mode == "off":
            return False, "command claims are disabled by policy.command_mode=off"
        run = attrs.get("run") or claim.body.strip()
        if not run:
            return False, "command claim has empty body"
        try:
            proc = run_confined_command(
                root,
                run,
                timeout=int(attrs.get("timeout") or policy.command_timeout_sec),
                prefixes=policy.command_allow,
                allowed_env=policy.allowed_env,
            )
        except CommandDenied as exc:
            return False, str(exc)
        except ConfineError as exc:
            return False, str(exc)
        except Exception as exc:
            return False, f"command rejected: {exc}"
        expect_exit = int(attrs.get("expect_exit", 0))
        if proc.returncode != expect_exit:
            tail = (proc.stderr or proc.stdout)[-400:]
            return False, f"exit {proc.returncode} expected {expect_exit}: {tail}"
        stdout_pat = attrs.get("expect_stdout")
        if stdout_pat:
            if stdout_pat.startswith("~/") and stdout_pat.endswith("/"):
                pat = stdout_pat[2:-1]
                if len(pat) > 128:
                    return False, "stdout pattern too long"
                if not re.search(pat, proc.stdout or ""):
                    return False, f"stdout did not match /{pat}/"
            elif stdout_pat not in (proc.stdout or ""):
                return False, "stdout missing expected substring"
        return True, f"exit {proc.returncode}"

    if kind == "heading":
        title = attrs.get("title") or attrs.get("heading") or claim.body.strip()
        doc = Path(claim.path)
        if not doc.is_absolute():
            try:
                doc = confine(root, claim.path)
            except ConfineError as exc:
                return False, str(exc)
        text = doc.read_text(encoding="utf-8") if doc.is_file() else ""
        headings = [h[2] for h in extract_headings(text)]
        return title in headings, f"heading {title!r} present={title in headings}"

    if kind == "rel_link":
        href = attrs.get("href") or attrs.get("path")
        if not href:
            return False, "rel_link missing href"
        try:
            target = confine(root, href)
        except ConfineError as exc:
            return False, str(exc)
        return target.exists(), f"{href} exists={target.exists()}"

    if kind == "version_sync":
        version_file = attrs.get("path") or policy.version_file
        key = attrs.get("key") or policy.version_key
        needle = attrs.get("equals") or attrs.get("version")
        if not needle:
            return False, "version_sync requires equals"
        try:
            target = confine(root, version_file)
        except ConfineError as exc:
            return False, str(exc)
        if not target.is_file():
            return False, f"missing {version_file}"
        data = _read_jsonish(target)
        try:
            value = _pointer_get(data, key)
        except Exception as exc:
            return False, f"version lookup failed: {exc}"
        body = claim.body or ""
        ok = str(value) == str(needle) and str(value) in body
        return ok, f"version {value!r} vs claimed {needle!r}"

    if kind == "python_symbol":
        module = attrs.get("module")
        if not module:
            return False, "python_symbol needs module"
        symbol = attrs.get("symbol")
        roots_attr = attrs.get("roots")
        if roots_attr:
            roots = [r.strip() for r in roots_attr.split(",") if r.strip()]
        else:
            roots = getattr(policy, "python_roots", None) or ["src", "."]
        path = resolve_module(root, module, roots)
        if path is None:
            return False, f"module {module!r} not found under {roots}"
        rel = path.relative_to(root.resolve()).as_posix()
        if symbol and not has_symbol(path, symbol):
            return False, f"symbol {symbol!r} not defined in {rel}"
        ok_ent, ent = _entail(claim, symbol or module, policy)
        if not ok_ent:
            return False, ent
        evidence = f"{module} -> {rel}"
        if symbol:
            evidence += f" defines {symbol}"
        return True, evidence

    if kind == "entrypoint":
        name = attrs.get("name")
        if not name:
            return False, "entrypoint needs name"
        target = attrs.get("target")
        scripts = console_scripts(root)
        if name not in scripts:
            return False, f"console script {name!r} not declared in pyproject.toml"
        if target and scripts[name] != target:
            return False, f"console script {name!r} -> {scripts[name]!r}, expected {target!r}"
        parsed = split_target(scripts[name])
        if parsed is None:
            return False, "malformed console script target"
        module, func = parsed
        roots_attr = attrs.get("roots")
        if roots_attr:
            roots = [r.strip() for r in roots_attr.split(",") if r.strip()]
        else:
            roots = getattr(policy, "python_roots", None) or ["src", "."]
        path = resolve_module(root, module, roots)
        if path is None:
            return False, f"module {module!r} not found under {roots}"
        rel = path.relative_to(root.resolve()).as_posix()
        if not has_symbol(path, func):
            return False, f"{func!r} not defined in {rel}"
        ok_ent, ent = _entail(claim, name, policy)
        if not ok_ent:
            return False, ent
        return True, f"{name} -> {scripts[name]} ({rel})"

    return False, f"no verifier for kind {kind}"


def Path_parts(pattern: str) -> tuple[str, ...]:
    from pathlib import PurePosixPath

    return PurePosixPath(pattern).parts


def _check_policy_lock(root: Path, policy: Policy) -> Finding | None:
    if not policy.require_lock:
        return None
    cfg = find_policy_file(root)
    if cfg is None:
        return Finding(None, policy.lock_path, 1, "error", "missing_policy", "require_lock set but no policy file")
    lock = root / policy.lock_path
    if not lock.is_file():
        return Finding(None, policy.lock_path, 1, "error", "missing_lock", f"missing {policy.lock_path}; run truthgate lock")
    try:
        payload = json.loads(lock.read_text(encoding="utf-8"))
        expected = payload.get("sha256")
    except Exception:
        return Finding(None, policy.lock_path, 1, "error", "bad_lock", "lock file is not valid JSON")
    import hashlib

    actual = hashlib.sha256(cfg.read_bytes()).hexdigest()
    if actual != expected:
        return Finding(
            None,
            policy.lock_path,
            1,
            "error",
            "policy_drift",
            "policy file hash does not match .truthgate.lock",
            evidence=f"lock={expected} actual={actual}",
        )
    return None


def verify_repo(root: Path, policy: Policy) -> VerifyReport:
    findings: list[Finding] = []
    all_claims: list[Claim] = []
    docs: list[str] = []
    receipts: list[dict[str, Any]] = []

    lock_finding = _check_policy_lock(root, policy)
    if lock_finding:
        findings.append(lock_finding)

    for doc_policy in policy.docs:
        try:
            path = confine(root, doc_policy.path)
        except ConfineError as exc:
            findings.append(
                Finding(None, doc_policy.path, 1, "error", "doc_escape", str(exc))
            )
            docs.append(doc_policy.path)
            continue
        docs.append(doc_policy.path)
        if not path.is_file():
            findings.append(
                Finding(
                    claim_id=None,
                    path=doc_policy.path,
                    line=1,
                    severity="error",
                    code="missing_doc",
                    message=f"documented file {doc_policy.path} does not exist",
                )
            )
            continue
        text = path.read_text(encoding="utf-8")
        claims, issues = parse_document(path, text, rel=doc_policy.path)
        all_claims.extend(claims)
        for issue in issues:
            findings.append(
                Finding(
                    claim_id=None,
                    path=issue["path"],
                    line=int(issue["line"]),
                    severity="error",
                    code=issue["code"],
                    message=issue["message"],
                )
            )

        headings = [h[2] for h in extract_headings(text)]
        for required in doc_policy.required_headings:
            if required not in headings:
                findings.append(
                    Finding(
                        claim_id=None,
                        path=doc_policy.path,
                        line=1,
                        severity="error",
                        code="missing_heading",
                        message=f"required heading {required!r} is missing",
                    )
                )

        if doc_policy.require_bound_fences:
            for claim in claims:
                if claim.source == "fence" and claim.attrs.get("unbound") == "true":
                    findings.append(
                        Finding(
                            claim_id=claim.id,
                            path=doc_policy.path,
                            line=claim.start_line,
                            severity="error",
                            code="unbound_fence",
                            message="code fence must declare truth:id=... or truth:ignore",
                            evidence=claim.body[:120],
                        )
                    )

        for line, href in extract_rel_links(text):
            if href.startswith("http") or href.startswith("mailto:"):
                continue
            try:
                target = confine(path.parent, href.split("#")[0])
                # also must stay in repo root
                confine(root, str(target.relative_to(root.resolve())))
            except (ConfineError, ValueError):
                findings.append(
                    Finding(None, doc_policy.path, line, "warning", "broken_rel_link", f"relative link rejected: {href}")
                )
                continue
            if not target.exists():
                findings.append(
                    Finding(
                        claim_id=None,
                        path=doc_policy.path,
                        line=line,
                        severity="warning",
                        code="broken_rel_link",
                        message=f"relative link does not resolve: {href}",
                    )
                )

        bound_needles: set[str] = set()
        for claim in claims:
            if claim.attrs.get("unbound") == "true":
                continue
            for key in ("path", "file", "glob", "href"):
                if claim.attrs.get(key):
                    bound_needles.add(str(claim.attrs[key]))
            bound_needles.update(coverage_tokens(claim.body or ""))
            ok, evidence = check_claim(root, claim, policy)
            receipts.append(
                {
                    "id": claim.id,
                    "kind": claim.kind,
                    "ok": ok,
                    "evidence": evidence,
                    "line": claim.start_line,
                    "path": str(claim.path),
                }
            )
            if not ok:
                # machine failure is always an error; severity attr cannot downgrade
                findings.append(
                    Finding(
                        claim_id=claim.id,
                        path=str(claim.path),
                        line=claim.start_line,
                        severity="error",
                        code="claim_failed",
                        message=f"claim '{claim.id}' ({claim.kind}) failed",
                        evidence=evidence,
                    )
                )

        if policy.coverage == "paths":
            visible = strip_ignored_and_comments(text, ignored_fence_spans(text))
            for token in coverage_tokens(visible):
                if token in bound_needles:
                    continue
                if any(token in (c.body or "") or token in str(c.attrs) for c in claims):
                    continue
                findings.append(
                    Finding(
                        None,
                        doc_policy.path,
                        1,
                        policy.coverage_severity,
                        "unbound_path_token",
                        f"path-like token {token!r} is not bound to a claim",
                    )
                )

    failed = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    checked = len(receipts)
    passed = sum(1 for r in receipts if r["ok"])
    if policy.fail_on == "warning":
        ok = failed == 0 and warnings == 0
    else:
        ok = failed == 0
    return VerifyReport(
        ok=ok,
        docs=docs,
        claims=len([c for c in all_claims if not c.attrs.get("unbound")]),
        checked=checked,
        passed=passed,
        failed=failed,
        warnings=warnings,
        findings=findings,
        receipts=receipts,
    )
