# Merchant Commission Meow Full Route 2026-04-25

Scope for this pass stayed inside `商會委託 -> 喵手商團`.

## What Landed

- fixed `MerchantCommissionMeowActiveRoundResolution.from_dict(...)`
- added machine-readable round-trip helpers for:
  - `MerchantCommissionMeowSubmitPanelInspection`
  - `MerchantCommissionMeowSubmitPanelNavigationPlan`
  - `MerchantCommissionMeowSubmitPanelResolution`
  - `MerchantCommissionMeowActiveRoundNavigationPlan`
- added validated entry orchestration:
  - `resolve_merchant_commission_meow_entry_accept(...)`
- added validated main-screen orchestration:
  - `resolve_merchant_commission_meow_from_main_screen(...)`
- added navigation plans and result contracts for:
  - entry accept
  - main-screen first-round run
- added tests for:
  - active-round resolution round-trip
  - entry accept route
  - main-screen first-round route

## Runtime Truth Added

The Meow Group slice is no longer limited to an already-accepted active loop.

This pass validated one bounded full route from the main screen:

1. main screen
2. activity smile button
3. `CARNIVAL`
4. `商會委託`
5. `立即前往`
6. NPC dialog `商會委託`
7. `喵手商團 -> 接受`
8. close merchant list
9. expand left task tab
10. one validated task-list swipe
11. tap `[日常] 商會委託`
12. tap the top submit option
13. resolve submit panel

## Live Validation

Validated device:

- `127.0.0.1:16416`

Validated date:

- `2026-04-25`

The new main-screen helper was executed live and completed one bounded Meow route pass.

Captured evidence:

- start screen:
  - `runtime_logs/merchant_commission_live/2026-04-25/current_127_0_0_1_16416.png`
- machine-readable run output:
  - `runtime_logs/merchant_commission_live/2026-04-25/full_route_resolution.json`
- immediate post-run capture:
  - `runtime_logs/merchant_commission_live/2026-04-25/after_full_route_first_round_127_0_0_1_16416.png`
- cleanup capture after dismissing the unexpected overlay:
  - `runtime_logs/merchant_commission_live/2026-04-25/after_back_from_season_overlay_127_0_0_1_16416.png`

The live run reported:

- entry route executed as planned
- active round reached the submit panel
- submit-panel inspection state:
  - `full`
- submit-panel action:
  - `direct_submit`

## Current Boundary

This pass truthfully validated that the Meow Group helper can execute from the main screen and reach one live submit action on the reserved device.

It did not yet convert this slice into a fully app-exposed task runner, and it did not claim hands-off `10/10` completion from one top-level command.

One live nuisance remains documented:

- after the full-route helper returned, the UI surfaced a season/activity overlay stack that required one manual cleanup action via `Back`

So the honest status after this pass is:

- main-screen Meow first-round helper: live-validated
- accepted active-round helper: live-validated
- fully polished end-state cleanup: still needs one follow-up pass
