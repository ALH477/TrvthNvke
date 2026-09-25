# Agent contract for this repository

You do not freehand-rewrite README.md.

1. Call `truthgate_list_claims` or `python3 -m truthgate extract`.
2. Change code first. Then update the claim that the code made false.
3. Propose ops with `truthgate_propose_edit`.
4. Apply with `truthgate_apply_edit` (it reverts on gate failure).
5. Run `truthgate_verify`. Do not open a PR on a failing receipt.

<!-- truth:claim
id: agent-tools-defined
kind: file_contains
path: src/truthgate/mcp_server.py
pattern: truthgate_list_claims
-->
`truthgate_list_claims` is one of the tools defined in `src/truthgate/mcp_server.py`.
<!-- truth:end -->

<!-- truth:claim
id: agent-apply-defined
kind: file_contains
path: src/truthgate/mcp_server.py
pattern: truthgate_apply_edit
-->
`truthgate_apply_edit` is also defined in `src/truthgate/mcp_server.py`.
<!-- truth:end -->

<!-- truth:claim
id: agent-apply-reverts
kind: file_contains
path: src/truthgate/mcp_server.py
pattern: "reverted": True
-->
It reverts on gate failure by returning `"reverted": True` from `src/truthgate/mcp_server.py`.
<!-- truth:end -->

If a sentence cannot be checked, leave it as prose. Do not invent a `command` that you have not run.

Claim ids are stable. Do not rename an id unless you also update every receipt and agent prompt that cites it.
