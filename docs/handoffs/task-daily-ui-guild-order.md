# Task Daily UI Guild Order Handoff

Track:

- `codex/task-claim-rewards-runtime-seam`

Scope:

- Started the first Engine D round-9 guild-order pass.
- Kept scope to `daily_ui.guild_order_submit` only.
- Primary implementation stayed in Engine D task/spec/readiness ownership.
- Added one minimal shared compatibility repair so repo-wide vision/tooling readiness does not treat new planned guild-order anchors as claim-rewards golden-catalog anchors.
- Did not add crafting, buying, gathering, or pathing behavior.

Files changed:

- `src/roxauto/tasks/catalog.py`
- `src/roxauto/tasks/daily_ui/__init__.py`
- `src/roxauto/tasks/daily_ui/guild_order_submit.py`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/guild_order_submit.task.json`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/asset_inventory.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `src/roxauto/vision/repository.py`
- `tests/app/test_viewmodels.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/daily_ui/test_guild_order_submit.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/test_inventory_fixtures.py`
- `tests/vision/test_repository.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/task-daily-ui-guild-order.md`

Public APIs added or changed:

- Added task-owned guild-order decision models in `roxauto.tasks.daily_ui.guild_order_submit`:
  - `GuildOrderRequirement`
  - `GuildOrderAvailability`
  - `GuildOrderDecision`
  - `GuildOrderMaterialPolicy`
  - `GuildOrderDecisionContract`
  - `GuildOrderVisibilityContract`
  - `GuildOrderSubmitSpecification`
- Added task-owned loaders/builders:
  - `load_guild_order_submit_blueprint(...)`
  - `load_guild_order_submit_material_policy(...)`
  - `load_guild_order_submit_decision_contract(...)`
  - `load_guild_order_submit_visibility_contract(...)`
  - `build_guild_order_submit_specification(...)`
- `daily_ui` package exports now include the new guild-order task-owned contract surfaces.

Contract changes:

- Added a new spec-only task blueprint:
  - `daily_ui.guild_order_submit`
- Round-9 task policy is explicit and bounded:
  - allowed decisions:
    - `submit`
    - `skip`
    - `refresh`
  - disallowed behaviors:
    - `crafting`
    - `buying`
    - `gathering`
    - `pathing`
- Builder/runtime-boundary metadata now carries the guild-order task contract directly:
  - `guild_order_material_policy`
  - `guild_order_decision_contract`
  - `guild_order_visibility_contract`
  - `guild_order_handoff_fields`
  - `guild_order_spec_builders`
- Missing guild-order template records now keep their canonical manifest `source_path` in asset inventory instead of leaving that field blank, so workspace readiness reports can show `missing` truthfully without creating synthetic inventory mismatches.
- Readiness now encodes two explicit foundation blockers instead of pretending the first cut can already classify everything:
  - `foundation.daily_ui.guild_order_visible_quantity_contract`
  - `foundation.daily_ui.guild_order_result_state_contract`
- Readiness also encodes the missing required task anchors for the bounded first cut:
  - `daily_ui.guild_order_list`
  - `daily_ui.guild_order_detail`
  - `daily_ui.guild_order_submit_button`
  - `daily_ui.guild_order_refresh_button`

Assumptions:

- Engine D should define the first truthful guild-order decision contract before Engine C finishes the evidence/anchor promotion wave.
- Visible material quantities and post-decision result states remain gating truth surfaces for round 9; this pass should not hide those gaps behind generic `spec_only` wording.
- The first cut can reuse `fixture_profiles/default_tw_guild.fixture.json` because the bounded flow stays inside fixed guild UI surfaces.

Verification performed:

- `python -m unittest tests.tasks.daily_ui.test_guild_order_submit tests.tasks.daily_ui.test_foundations tests.tasks.test_catalog tests.tasks.test_inventory_fixtures`
- `python -m unittest discover -s tests/tasks -t .`
- `python -m pytest -q`
- `powershell -ExecutionPolicy Bypass -File scripts/run-autonomy-loop.ps1`

Autonomy loop result:

- `quality-gate.json`: `passed`
- `pytest`: `186 passed`
- `ruff check src tests`: `passed`
- `doctor`: `passed`

Known limitations:

- No runtime handlers were added in this pass.
- No vision assets or promoted guild-order anchors landed in this pass.
- `daily_ui.guild_order_submit` remains blocked until Engine C / Engine E produce truthful visible quantity and result-state evidence.

Blockers:

- Missing required anchors for the first bounded guild-order flow.
- Missing visible quantity contract for:
  - `daily_ui.guild_order_material_label`
  - `daily_ui.guild_order_required_quantity`
  - `daily_ui.guild_order_available_quantity`
- Missing verification contract for:
  - `daily_ui.guild_order_completed_state`
  - `daily_ui.guild_order_insufficient_material_state`
  - `daily_ui.guild_order_submit_result`

Recommended next step:

- Engine E should capture or classify whether the visible quantity and post-submit result states are actually stable and truthful.
- Engine C should promote the minimum guild-order anchor set that satisfies:
  - required list/detail/submit/refresh anchors
  - visible material label and quantity surfaces
  - completed / insufficient / submit-result verification surfaces
- After those assets land, rerun the task foundation builders so `daily_ui.guild_order_submit` can move from blocked-by-foundation to a truthful implementation path without widening scope.
