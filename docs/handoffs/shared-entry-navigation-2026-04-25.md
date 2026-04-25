# Shared Entry Navigation 2026-04-25

Track:

- `codex/shared-entry-navigation`

Scope:

- extracted only the proven shared front-half route:
  - main screen
  - top-right expanded entry
  - `CARNIVAL` hub
  - feature description card
  - `Go now` / `立即前往`
- added a narrow shared contract + helper under `src/roxauto/tasks/foundations/navigation/`
- rewired merchant commission entry runtime to use the shared helper for the shared segment only
- wired guild-order specification/foundation metadata to the same shared route contract without pulling guild panel or Activity-tab navigation into shared code
- refreshed the curated task foundation inventory/readiness artifacts after the new shared metadata landed

Files changed:

- `src/roxauto/tasks/foundations/navigation/__init__.py`
- `src/roxauto/tasks/foundations/navigation/shared_entry.py`
- `src/roxauto/tasks/__init__.py`
- `src/roxauto/tasks/catalog.py`
- `src/roxauto/tasks/daily_ui/guild_order_submit.py`
- `src/roxauto/tasks/daily_ui/merchant_commission_meow.py`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/guild_order_submit.task.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/merchant_commission_meow.task.json`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `tests/tasks/test_shared_entry_navigation.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/daily_ui/test_guild_order_submit.py`
- `tests/tasks/daily_ui/test_merchant_commission_meow.py`
- `docs/architecture-contracts.md`
- `docs/handoffs/shared-entry-navigation-2026-04-25.md`

Public APIs added or changed:

- added shared navigation contracts:
  - `SharedEntryRouteContract`
  - `SharedCheckpointPack`
- added narrow shared entry helper/runtime surfaces:
  - `SharedCarnivalEntryAdapter`
  - `SharedCarnivalEntryFeatureNavigationPlan`
  - `SharedCarnivalEntryNavigationPlan`
  - `SharedCarnivalEntryResolution`
  - `load_shared_carnival_entry_route_contract(...)`
  - `load_shared_carnival_entry_checkpoint_pack(...)`
  - `resolve_shared_carnival_entry(...)`
- `MerchantCommissionMeowSpecification` now exposes:
  - `shared_entry_route_contract`
  - `shared_checkpoint_pack`
- `GuildOrderSubmitSpecification` now exposes:
  - `shared_entry_route_contract`
  - `shared_checkpoint_pack`
- `resolve_merchant_commission_meow_entry_accept(...)` now delegates the shared front-half route to `resolve_shared_carnival_entry(...)`

Contract changes:

- the canonical shared route id is:
  - `daily_ui.shared_carnival_entry`
- the canonical shared checkpoint pack id is:
  - `daily_ui.shared_carnival_entry.checkpoints`
- the shared contract is intentionally bounded to:
  - `main_screen_idle`
  - `top_right_expanded_icon_group`
  - `carnival_hub`
  - `feature_description_card`
  - `shared_go_now_handoff`
- common close/back semantics are now explicit:
  - `description_card_close_to_carnival_hub`
  - `post_go_cleanup_feature_owned`

Assumptions:

- the top-right expanded entry -> `CARNIVAL` -> feature card -> `Go now` sequence is the only currently proven reusable slice shared by merchant commission and guild order
- guild still does not have a promoted task-owned `Go now` anchor, so the shared contract records some checkpoints as evidence-backed semantics rather than pretending every checkpoint is already anchor-backed
- post-`Go now` navigation remains meaningfully different between merchant and guild and should stay outside the shared helper

Verification performed:

- `$env:PYTHONPATH='src'; python -m pytest tests/tasks/test_shared_entry_navigation.py tests/tasks/daily_ui/test_merchant_commission_meow.py tests/tasks/daily_ui/test_guild_order_submit.py tests/tasks/daily_ui/test_foundations.py tests/tasks/test_catalog.py -q`

Known limitations:

- the shared helper is coordinate-driven like the current merchant runtime slice; it does not yet perform screenshot-gated checkpoint verification on each shared step
- guild integration in this pass is spec/foundation-level only; it does not add a new guild runtime route helper
- `common.close_button` is the only truly shared anchor in the checkpoint pack today; the other shared checkpoints still rely on per-feature anchors or reviewed live evidence

Blockers:

- guild-order still lacks a task-owned promoted `Go now` anchor in the task foundations, so the shared pack cannot claim a fully anchor-backed shared route yet
- merchant still owns the known post-run season/activity overlay cleanup via `Back`; that cleanup is documented as feature-owned, not absorbed into the shared helper

Recommended next step:

- if the guild feature branch starts runtime delivery, it should consume `daily_ui.shared_carnival_entry` for the front-half route and keep only `guild panel -> Activity tab -> guild-order card` in the guild-specific helper
- if later evidence proves a truly shared post-`Go now` scene, open a separate narrow follow-up instead of widening this helper speculatively
