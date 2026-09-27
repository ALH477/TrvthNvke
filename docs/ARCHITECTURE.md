# Architecture

TrvthNvke is a DeMoD LLC tool maintained by GitHub user ALH477.

<!-- truth:claim
id: flake-url
kind: file_contains
path: flake.nix
pattern: github:ALH477/trvthnvke
-->
Other repositories import it as `github:ALH477/trvthnvke`, the URL `flake.nix` advertises in its template description.
<!-- truth:end -->

TrvthNvke is three surfaces on one verifier.

```text truth:ignore
README.md  --parse-->  Claims
                              \
.trvthnvke.toml --policy--+--> Verifier --> exit code + receipt
                              /
        repo tree  --evidence-+

Agents --> MCP (propose / apply ops) --> same verifier
Git hook / GitHub Action ---------------> same verifier
```

## Why HTML comments

GitHub, GitLab, and most Markdown renderers strip HTML comments. Claims stay in the file humans already edit. No sidecar can drift from the paragraph it is supposed to prove.

Fenced `truth:id=` tokens ride the info string. They are visible in raw Markdown and ignored by highlighters.

## Force, not suggestion

<!-- truth:claim
id: force-fences
kind: file_contains
path: .trvthnvke.toml
pattern: require_bound_fences = true
-->
`require_bound_fences = true` in `.trvthnvke.toml` makes undocumented shell blocks a gate failure. That stops "copy-paste commands that never ran."
<!-- truth:end -->

`trvthnvke_apply_edit` reverts when the new text fails verification; `trvthnvke edit --verify` exits non-zero.

<!-- truth:claim
id: force-fail
kind: file_contains
path: hooks/pre-commit
pattern: verify --fail
-->
`hooks/pre-commit` and the Actions workflow both run `trvthnvke verify --fail`.
<!-- truth:end -->

Prose that cannot be checked stays prose. Do not invent a verifier for motivation paragraphs.

## Edit protocol

Whole-file rewrites by agents produce silent drift. Ops are addressable:

- `replace_claim_body` keeps the binding, changes the sentence
- `upsert_claim` inserts or replaces a bound block
- `set_fence_meta` attaches `truth:id` / `truth:ignore` to an existing fence
- `replace_section` is the escape hatch for a heading's body

<!-- truth:claim
id: edit-ops-module
kind: file_contains
path: src/trvthnvke/edit.py
pattern: replace_claim_body
-->
These ops, `replace_claim_body` included, are implemented in `src/trvthnvke/edit.py`.
<!-- truth:end -->

## MCP contract

The server speaks newline-delimited JSON-RPC 2.0 on stdio, the MCP stdio transport. A request that arrives with an LSP-style `Content-Length` header is answered with the same framing.

<!-- truth:claim
id: mcp-structured-content
kind: file_contains
path: src/trvthnvke/mcp_server.py
pattern: structuredContent
-->
Tools return JSON in `structuredContent` and a text copy in `content`, as `src/trvthnvke/mcp_server.py` implements.
<!-- truth:end -->

## What this is not

Not a general docs site generator. Not an LLM-as-judge in CI. Kind handlers are deterministic on purpose.
