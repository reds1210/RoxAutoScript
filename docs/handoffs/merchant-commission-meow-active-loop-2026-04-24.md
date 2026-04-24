# Merchant Commission Meow Active Loop 2026-04-24

Scope for this pass stayed inside `商會委託 -> 喵手商團`.

## What Landed

- added live submit-panel progress inspection in `src/roxauto/tasks/daily_ui/merchant_commission_meow.py`
- added `resolve_merchant_commission_meow_submit_panel(...)`
- added `resolve_merchant_commission_meow_active_round(...)`
- added real screenshot fixtures for:
  - partial inventory `7/15`
  - ready inventory `15/15`
  - empty inventory `0/15`
- added a curated empty-feedback template:
  - `assets/templates/daily_ui/anchors/merchant_commission_empty_feedback.png`

## Runtime Truth Added

The new runtime helper does not rely on OCR.

It uses two bounded checks only:

1. compare the submit-panel numerator and denominator image regions
2. if the numeric region is empty, match the empty-feedback mascot panel

This yields three truthful states:

- `full`: direct submit
- `incomplete`: immediate buy, confirm buy, then submit
- `unknown`: stop for operator

## Live Validation

Validated device:

- `127.0.0.1:16416`

Live progression that was verified during this pass:

- auto submit-panel resolver advanced `2/10 -> 3/10`
- auto submit-panel resolver advanced `3/10 -> 4/10`
- active-round runner advanced `4/10 -> 5/10`
- repeated active-round automation advanced the chain through `10/10`
- follow-up screenshot after the final round no longer showed `[日常] 商會委託`, which matches commission completion

Key evidence:

- `runtime_logs/merchant_commission_live/2026-04-24/after_auto_resolve_round2_127_0_0_1_16416.png`
- `runtime_logs/merchant_commission_live/2026-04-24/after_auto_resolve_round3_127_0_0_1_16416.png`
- `runtime_logs/merchant_commission_live/2026-04-24/after_auto_active_round4_127_0_0_1_16416.png`
- `runtime_logs/merchant_commission_live/2026-04-24/after_auto_final_round_followup.png`

## Current Boundary

This pass truthfully validated the active Meow Group loop and the submit-panel action logic.

It did not yet convert the fixed entry path from:

- main screen
- activity smile button
- `CARNIVAL`
- `商會委託`
- NPC accept flow

into the same runtime helper.

So the honest status after this pass is:

- active accepted Meow Group loop: live-validated
- fixed entry accept route: still separately validated, not yet wrapped into the same runtime helper
