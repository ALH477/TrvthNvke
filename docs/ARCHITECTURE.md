# Architecture

Truthgate is a DeMoD LLC tool maintained by GitHub user ALH477.
Other repositories import it as `github:ALH477/truthgate`.

Truthgate is three surfaces on one verifier.

```
README.md  --parse-->  Claims
                              \
.truthgate.toml --policy--+--> Verifier --> exit code + receipt
                              /
        repo tree  --evidence-+

Agents --> MCP (propose / apply ops) --> same verifier
Git hook / GitHub Action ---------------> same verifier
```

## Why HTML comments

GitHub, GitLab, and most Markdown renderers strip HTML comments. Claims stay in the file humans already edit. No sidecar can drift from the paragraph it is supposed to prove.

Fenced `truth:id=` tokens ride the info string. They are visible in raw Markdown and ignored by highlighters.

## Force, not suggestion

1. `require_bound_fences` makes undocumented shell blocks a gate failure. That stops "copy-paste commands that never ran."
2. `truthgate_apply_edit` reverts when the new text fails verification; `truthgate edit --verify` exits non-zero.
3. `pre-commit` and the Actions workflow use `--fail`.

Prose that cannot be checked stays prose. Do not invent a verifier for motivation paragraphs.

## Edit protocol

Whole-file rewrites by agents produce silent drift. Ops are addressable:

- `replace_claim_body` keeps the binding, changes the sentence
- `upsert_claim` inserts or replaces a bound block
- `set_fence_meta` attaches `truth:id` / `truth:ignore` to an existing fence
- `replace_section` is the escape hatch for a heading's body

## MCP contract

The server speaks newline-delimited JSON-RPC 2.0 on stdio, the MCP stdio transport. A request that arrives with an LSP-style `Content-Length` header is answered with the same framing. Tools return JSON in `structuredContent` and a text copy in `content`.

## What this is not

Not a general docs site generator. Not an LLM-as-judge in CI. Kind handlers are deterministic on purpose.
