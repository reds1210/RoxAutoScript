# Merchant Commission Meow Runtime Slice 2026-04-25

Scope for this pass stayed inside `merchant commission -> Meow Group`.

## What Shipped

- delivered a runtime seam for `daily_ui.merchant_commission_meow`
- wired the full bounded slice:
  - main-screen entry
  - accept Meow Group commission
  - re-enter from the left daily task list
  - submit one bounded round
  - verify round progression
- kept fixed UI actions anchored on deterministic navigation plus anchor/template-confirmed checkpoints
- preserved OCR-derived round text as bounded evidence only
- blocked low-confidence OCR from directly approving risky actions
- updated task foundation metadata to expose the merchant runtime seam and `merchant_commission_meow.v2`
- added runtime bridge tests for:
  - runtime input and seam construction
  - full Meow slice success path
  - low-confidence progression failure

## Runtime Truth

The branch now exposes a concrete task bridge for the validated Meow Group route only.

High-risk actions stay gated by anchor or template-confirmed states:

- accept flow requires the commission list panel plus the Meow accept button
- task re-entry requires the task-list entry and then the Meow submit option
- submit flow requires the submit panel plus either:
  - submit button
  - or buy confirmation dialog plus confirm button before submit

OCR is used only for bounded round verification and evidence capture. Each text evidence payload preserves:

- `source_type`
- `raw_text`
- `normalized_text`
- `bbox`
- `confidence`
- `screenshot_ref`
- `reader`

## Current Blockers

- readiness is still `blocked_by_asset`
- Meow anchor/template assets are still missing or planned, so live production dispatch remains gated by the asset foundation layer
- the slice does not widen to other merchant groups

## Tests Run

- `python -m pytest tests/tasks/daily_ui/test_merchant_commission_meow.py tests/tasks/test_catalog.py tests/tasks/test_inventory_fixtures.py`

## Changed Files

- `src/roxauto/tasks/daily_ui/merchant_commission_meow.py`
- `src/roxauto/tasks/daily_ui/__init__.py`
- `src/roxauto/tasks/catalog.py`
- `src/roxauto/tasks/foundations/packs/daily_ui/merchant_commission_meow.task.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/daily_claim_rewards.task.json`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `tests/tasks/daily_ui/test_merchant_commission_meow.py`
- `tests/tasks/test_catalog.py`
- `docs/vision/merchant_commission_meow/README.md`

## Recommended Next Step

Land the missing Meow anchor/template assets so the runtime seam can move from `blocked_by_asset` to truthful live-dispatch readiness without widening into shared merchant abstractions.
