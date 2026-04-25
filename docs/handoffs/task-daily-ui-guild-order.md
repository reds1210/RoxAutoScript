# Task Daily UI Guild Order Handoff

Date:

- `2026-04-25`

Branch:

- final worktree branch: `codex/feature-guild-order-submit`
- note: this pass started from a worktree that was actually on `codex/feature-merchant-commission-meow`; the branch was corrected before the final autonomy loop and PR prep

Scope:

- completed the first full `guild_order_submit` feature slice
- kept scope to `submit / skip / refresh` only
- did not add crafting, gathering, pathing, generic buying, shared navigation extraction, or shared material extraction
- kept custom-order handling explicitly out of scope for V1 runtime actioning

Changed files:

- `assets/templates/daily_ui/manifest.json`
- `src/roxauto/tasks/daily_ui/__init__.py`
- `src/roxauto/tasks/daily_ui/guild_order_submit.py`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/guild_order_submit.task.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `tests/app/test_viewmodels.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/daily_ui/test_guild_order_submit.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/test_inventory_fixtures.py`
- `tests/vision/test_repository.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/task-daily-ui-guild-order.md`

What shipped:

- added a fixtured runtime bridge for `daily_ui.guild_order_submit`
- added bounded live route recovery into the guild-order detail scene
- added OCR-backed inspection with preserved text evidence fields:
  - `raw_text`
  - `normalized_text`
  - `bbox`
  - `confidence`
  - `screenshot_ref`
  - `reader`
- added truthful policy flow for:
  - standard-order `submit`
  - standard-order `refresh`
  - explicit `skip`
- added signature-based post-action verification so `submit` and `refresh` only succeed when the detail signature changes
- kept missing evidence honest:
  - standard-order evidence gaps stay `order_state_unknown`
  - dispatch failures stay `runtime_dispatch_failed`
  - unchanged post-action signatures stay `submit_verification_failed` or `refresh_verification_failed`
- kept custom-order actioning disabled in V1:
  - runtime preserves evidence
  - decision path records a truthful `custom_order_disabled` skip
- promoted the foundation blueprint from `spec_only` to `fixtured`
- changed task readiness from blocked foundation gating to runtime-ready with warning-only placeholder assets
- updated the daily-ui scene contract so refresh affordance live evidence is marked captured

Tests run:

- `python -m unittest tests.tasks.daily_ui.test_guild_order_submit tests.tasks.daily_ui.test_foundations tests.tasks.test_catalog tests.tasks.test_inventory_fixtures tests.vision.test_repository tests.vision.test_validation`
- `python -m unittest tests.app.test_viewmodels tests.vision.test_tooling`
- `scripts/run-autonomy-loop.ps1`

Autonomy loop result:

- `runtime_logs/autonomy/quality-gate.json`: `passed`
- `runtime_logs/autonomy/agent-packet.json`: generated
- `runtime_logs/autonomy/handoff-brief.md`: generated
- quality-gate checks:
  - `doctor`: `passed`
  - `pytest`: `223 passed`
  - `ruff`: `passed`

Blockers:

- V1 does not action custom-order candidate selection; it records a truthful skip instead
- unavailable-state and insufficient-material-state scene truth are still placeholder-backed evidence in the vision manifest
- Windows OCR on this path does not surface a native confidence value, so `confidence` may remain `null` even when the evidence packet is otherwise complete

Recommended next step:

- capture reviewed live evidence for completed / unavailable and insufficient-material states
- if product scope still needs it after that, open a separate V2 slice for custom-order candidate inspection and selection
- keep follow-up work on this branch and request Codex automatic review or `@codex review` on the PR
