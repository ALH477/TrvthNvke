# Security

TrvthNvke 0.2 treats the verifier as a **hostile-input linter**. README text, policy files, and MCP tool arguments are untrusted.

## What is enforced

- Paths are confined to the repository root. `..`, absolute paths, and escaping symlinks fail.
- `command` claims run `argv` only (`shell=False`) against an allowlist. Default prefixes: `python3 -m trvthnvke`, `test -f`, `test -d`. Environment is reduced; only `PYTHONPATH` entries inside the root are accepted.
- A failed machine check is always an error. `severity: info` cannot greenwash a miss.
- `ignore: true` requires `reason:` and fails when `strict_ignore = true`.
- `json_pointer` / `toml_key` / `version_sync` require `equals`.
- File claims must mention the bound path in the visible body (entailment).
- `.trvthnvke.lock` pins the SHA-256 of `.trvthnvke.toml`. CI should keep `require_lock = true`.
- MCP `doc` paths are confined. `force=true` is a no-op unless `TRVTHNVKE_ALLOW_FORCE=1`.
- `file_contains` matches a literal substring by default; `regex:` opts into Python `re` with a 256-char pattern cap, 2 MiB text cap, and a 2s timeout (`regex_timeout_sec`) enforced with `SIGALRM` on the main thread.
- Coverage warnings scan for tokens under the repository's own top-level directories (or `coverage_dirs`) with `coverage_exts` extensions.

## What it still is not

- Not a sandbox hypervisor. A listed command still runs as the CI user.
- Not a semantic entailment prover. Bind the sentence you care about.
- Not an attestation service. Receipts are unsigned JSON.
- Not a regex sandbox off the main thread. Embedders that call `verify_repo` from a worker thread get the caps but not the timeout.

## Report

<!-- truth:claim
id: sec-report
kind: prose
-->
DeMoD LLC / ALH477 — https://github.com/ALH477/TrvthNvke
<!-- truth:end -->
