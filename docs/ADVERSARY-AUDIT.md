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

## Evidence

Spot checks for the fixes that are cheap to verify mechanically.

<!-- truth:claim
id: ev-c1
kind: file_contains
path: src/truthgate/security.py
pattern: shell=False
-->
C1's argv-only runner passes `shell=False` in `src/truthgate/security.py`.
<!-- truth:end -->

<!-- truth:claim
id: ev-c2
kind: file_contains
path: src/truthgate/verify.py
pattern: severity attr cannot downgrade
-->
C2 holds because `src/truthgate/verify.py` notes the severity attr cannot downgrade a machine failure.
<!-- truth:end -->

<!-- truth:claim
id: ev-h5
kind: file_contains
path: src/truthgate/security.py
pattern: def confine
-->
H5's confinement is `def confine` in `src/truthgate/security.py`.
<!-- truth:end -->

<!-- truth:claim
id: ev-h6
kind: file_contains
path: src/truthgate/mcp_server.py
pattern: TRUTHGATE_ALLOW_FORCE
-->
H6's guard checks `TRUTHGATE_ALLOW_FORCE` in `src/truthgate/mcp_server.py`.
<!-- truth:end -->

<!-- truth:claim
id: ev-h7
kind: file_exists
path: .truthgate.lock
-->
H7's pin is the `.truthgate.lock` file this repository ships.
<!-- truth:end -->

<!-- truth:claim
id: ev-h8
kind: file_contains
path: .github/workflows/truthgate.yml
pattern: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
-->
H8's SHA-pinned checkout is `actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11` in `.github/workflows/truthgate.yml`.
<!-- truth:end -->

<!-- truth:claim
id: ev-m11
kind: file_contains
path: flake.nix
pattern: nixos-24.11
-->
M11's pin is `nixos-24.11` in `flake.nix`.
<!-- truth:end -->

Residual: allowlisted binaries still run as the CI user; unbound prose can still lie; receipts are unsigned; `file_contains` and stdout regexes run without a timeout.
