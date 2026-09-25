# Changelog

## 0.3.0

Stronger claims, honest coverage, safer regexes, and a project that gates its own docs.

- **Breaking:** `file_contains` `pattern:` is a literal substring. Use `regex:` for a regular expression.
- New kind `python_symbol`: a module resolves under `python_roots` and, optionally, a top-level symbol is defined. Static `ast` check, no import.
- New kind `entrypoint`: a `[project.scripts]` console script exists, optionally points at `target`, and the target function is defined.
- Regex claims run through a bounded search: 256-char pattern cap, 2 MiB text cap, `regex_timeout_sec` (default 2 s) on the main thread.
- Coverage tokens come from the repository's own top-level directories (or `coverage_dirs`) and `coverage_exts`; per-doc `coverage = "off"` override.
- `docs/ARCHITECTURE.md`, `docs/ADVERSARY-AUDIT.md`, `AGENTS.md`, and `SECURITY.md` are gated by `.truthgate.toml`.
- Version 0.3.0.

## 0.2.0

Hardening release after the adversary audit.

- Confine all documented paths; reject `..`, absolutes, and escaping symlinks.
- Replace `shell=True` with argv execution and a command allowlist.
- Failed checks cannot be downgraded via `severity`.
- Ignored claims require a reason and fail in strict mode.
- Presence-only JSON/TOML/version lookups require `equals`.
- Entailment: file claims must mention their bound path in the body.
- Policy lock file `.truthgate.lock`.
- Path-token coverage warnings.
- MCP refuses escaped `doc` paths; `force` is env-gated.
- Headings inside fenced blocks no longer satisfy `required_headings`.
- Flake inputs pinned off `nixos-unstable`; Actions pins moved to SHAs.
- MCP stdio replies are newline-delimited JSON; `Content-Length` requests are answered in kind.
- `upsert_claim` renders top-level attributes such as `path` into the block.
- Editor ignores claim samples inside `truth:ignore` fences and headings inside code fences.
- `truthgate edit --ops-file` reads the file it was given.
- Receipts and findings record repo-relative paths.
- Corrected the `actions/setup-python` SHA pin; dev shell banner no longer shells out to `python3 -c`.
- Full Apache-2.0 text in `LICENSE`; `flake.lock` committed.
- Version 0.2.0.

## 0.1.0

Initial TruthMD dialect, verifier, MCP, and consumer flake template.
