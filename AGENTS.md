# Agent contract for this repository

You do not freehand-rewrite README.md.

1. Call `truthgate_list_claims` or `python3 -m truthgate extract`.
2. Change code first. Then update the claim that the code made false.
3. Propose ops with `truthgate_propose_edit`.
4. Apply with `truthgate_apply_edit` (it reverts on gate failure).
5. Run `truthgate_verify`. Do not open a PR on a failing receipt.

If a sentence cannot be checked, leave it as prose. Do not invent a `command` that you have not run.

Claim ids are stable. Do not rename an id unless you also update every receipt and agent prompt that cites it.
