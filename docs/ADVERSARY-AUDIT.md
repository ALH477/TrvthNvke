# Adversary audit and 0.2 remediations

Original audit ran against 0.1.0. This file records each finding and the fix shipped in 0.2.0.

| ID | Finding | Fix |
| --- | --- | --- |
| C1 | `shell=True` RCE via command claims | argv-only runner + allowlist; default prefixes cannot be `echo` / `curl` |
| C2 | `severity: info` still PASS | machine failures are always `error` |
| C3 | `ignore: true` auto-pass | reason required; `strict_ignore` fails the claim |
| C4 | body not entailed by handler | `require_entailment` demands the bound path/version in the body |
| H5 | path / symlink escape | `security.confine` |
| H6 | MCP writes any path / `force` | confine + `TRUTHGATE_ALLOW_FORCE` |
| H7 | policy file unpinned | `.truthgate.lock` SHA-256 |
| H8 | mutable Actions tags | SHA-pinned checkout/setup-python/upload-artifact |
| M9 | heading-in-fence | headings inside fences ignored |
| M10 | JSON pointer without equals | equals required |
| M11 | floating flake inputs | nixpkgs 24.11 + flake-utils commit |
| M12 | `python3 -c` in self-test | replaced with `python3 -m truthgate --version` |
| H13 | `actions/setup-python` pinned to a SHA that does not exist | corrected to the `v5.1.0` commit |
| H14 | MCP replies used `Content-Length` framing, unreadable by MCP stdio clients | newline-delimited JSON; framed requests answered in kind |
| M15 | `upsert_claim` dropped top-level attrs such as `path` | all non-control op keys rendered into the block |
| M16 | editor matched claim samples inside `truth:ignore` fences and headings inside code fences | editor reuses the parser's fence and ignore spans |
| L17 | receipts recorded absolute local paths | claim and finding paths are repo-relative |

Residual: allowlisted binaries still run as the CI user; unbound prose can still lie; receipts are unsigned; `file_contains` and stdout regexes run without a timeout.
