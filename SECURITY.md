# Security

Truthgate 0.2 treats the verifier as a **hostile-input linter**. README text, policy files, and MCP tool arguments are untrusted.

## What 0.2 enforces

- Paths are confined to the repository root. `..`, absolute paths, and escaping symlinks fail.
- `command` claims run `argv` only (`shell=False`) against an allowlist. Default prefixes: `python3 -m truthgate`, `test -f`, `test -d`. Environment is reduced; only `PYTHONPATH` entries inside the root are accepted.
- A failed machine check is always an error. `severity: info` cannot greenwash a miss.
- `ignore: true` requires `reason:` and fails when `strict_ignore = true`.
- `json_pointer` / `toml_key` / `version_sync` require `equals`.
- File claims must mention the bound path in the visible body (entailment).
- `.truthgate.lock` pins the SHA-256 of `.truthgate.toml`. CI should keep `require_lock = true`.
- MCP `doc` paths are confined. `force=true` is a no-op unless `TRUTHGATE_ALLOW_FORCE=1`.

## What it still is not

- Not a sandbox hypervisor. A listed command still runs as the CI user.
- Not a semantic entailment prover. Bind the sentence you care about.
- Not an attestation service. Receipts are unsigned JSON.
- Not a regex sandbox. `file_contains` patterns and `~/.../` stdout patterns come from the README and run through Python `re` with a length cap but no timeout. A pathological pattern can stall a CI job.

## Report

DeMoD LLC / ALH477 — https://github.com/ALH477/truthgate
