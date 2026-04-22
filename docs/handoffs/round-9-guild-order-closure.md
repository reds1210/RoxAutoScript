# Handoff: Round 9 Guild Order Closure

Status:

- `round-9 guild-order material logic` is paused on `2026-04-23`

Why this round was paused:

- the latest live-evidence attempt did not follow the operator-described entry route accurately enough
- dispatch should not keep opening workers on top of ambiguous navigation assumptions
- the next evidence pass should restart from explicit operator truth instead of from chat fragments or speculative button guesses

Canonical operator-provided guild-order route:

1. from the main game screen, open the collapsible logo button in the top-right area above the Facebook logo
2. choose `嘉年華`
3. choose `公會訂單`
4. tap `立即前往`
5. on the destination page, switch to the `活動` tab
6. find the `公會訂單` card
7. tap the `前往` button inside that card

Canonical operator-provided scene semantics after entry:

- the left side shows the required materials list
- tapping a row highlights that material
- the material image itself is not a valid detail affordance for this round
- the right side contains the submit area
- when materials are insufficient, the scene exposes a `獲取` affordance
- the insufficient-material recovery path is `獲取 -> 立即購買`
- during the first round, the purchase cost should be `zeny`, not crystals
- do not spend effort on manual quantity tuning for that first-round purchase path
- do not use the `求助` button in this round

Implications for the next restart brief:

- Engine E should begin from the exact entry path above and capture only proven states
- Engine C should not treat the material image as a clickable detail entry unless new evidence disproves the operator note
- Engine D should keep the first-cut policy narrow and may model the explicit insufficient-material purchase path separately from generic auto-buying
- dispatch should assign one exact ADB serial and require the handoff to state whether the worker followed the preserved route successfully

Recommended next step:

- publish a dedicated restart brief before opening any new round-9 worker thread
- the restart brief should reference this closure handoff and the paused round-9 brief directly
