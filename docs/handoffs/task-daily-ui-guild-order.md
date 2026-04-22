# Task Daily UI Guild Order Handoff

Track:

- `codex/task-claim-rewards-runtime-seam`

Scope:

- Synced this worktree with the latest `main`, which brought in Engine C's first guild-order scene contract and placeholder anchors.
- Repaired the task-side integration for `daily_ui.guild_order_submit` after that merge.
- Kept scope to the bounded round-9 `submit` / `skip` / `refresh` contract only.
- Kept primary edits inside Engine D ownership:
  - `src/roxauto/tasks/`
  - `tests/tasks/`
  - task-specific foundation snapshots
- Updated shared validation expectations only where the merge changed task-owned curated outputs or exposed stale task-side assumptions.
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
- After merging Engine C's placeholder scaffolds, the task now points at the truthful currently-known anchor ids:
  - required list/detail anchors:
    - `daily_ui.guild_order_list_panel`
    - `daily_ui.guild_order_detail_panel`
  - skip / verification surfaces:
    - `daily_ui.guild_order_unavailable_state`
    - `daily_ui.guild_order_insufficient_material_feedback`
    - `daily_ui.guild_order_submit_result_state`
- Missing guild-order template records still keep their canonical manifest `source_path` in asset inventory, so workspace readiness reports can show `missing` truthfully without creating synthetic inventory mismatches.
- Template-only readiness checks now ignore golden-screenshot metadata when evaluating guild-order anchor and foundation requirements. This addresses the Codex review finding that a present golden could otherwise satisfy a missing template-anchor contract incorrectly.
- Readiness now encodes two explicit foundation blockers instead of pretending the first cut can already classify everything:
  - `foundation.daily_ui.guild_order_visible_quantity_contract`
  - `foundation.daily_ui.guild_order_result_state_contract`
- Required list/detail/submit/refresh anchors are no longer all `missing`; after the Engine C merge they resolve as placeholder scaffolds, which is a more truthful blocked state for round 9.

Assumptions:

- Engine D still needs to integrate the latest Engine C scaffolding rather than freezing the older pre-merge anchor ids.
- Visible material quantities and post-decision result states remain gating truth surfaces for round 9; this pass should not hide those gaps behind generic `spec_only` wording.
- The first cut can reuse `fixture_profiles/default_tw_guild.fixture.json` because the bounded flow stays inside fixed guild UI surfaces.

Verification performed:

- `python -m unittest tests.tasks.daily_ui.test_guild_order_submit tests.tasks.daily_ui.test_foundations tests.tasks.test_catalog tests.tasks.test_inventory_fixtures`
- `python -m pytest -q`
- `powershell -ExecutionPolicy Bypass -File scripts/run-autonomy-loop.ps1`

Autonomy loop result:

- `quality-gate.json`: `passed`
- `pytest`: `190 passed`
- `ruff check src tests`: `passed`
- `doctor`: `passed`

Known limitations:

- No runtime handlers were added in this pass.
- The merged Engine C anchors are still placeholder scaffolds, not reviewed live captures.
- `daily_ui.guild_order_submit` remains blocked until Engine C / Engine E produce truthful visible quantity evidence and promote result-state surfaces beyond placeholder-only scaffolding.

Blockers:

- Required list/detail/submit/refresh anchors are present only as placeholders, so they still do not satisfy task asset requirements truthfully.
- Missing visible quantity contract for:
  - `daily_ui.guild_order_material_label`
  - `daily_ui.guild_order_required_quantity`
  - `daily_ui.guild_order_available_quantity`
- Placeholder-only verification contract for:
  - `daily_ui.guild_order_unavailable_state`
  - `daily_ui.guild_order_insufficient_material_feedback`
  - `daily_ui.guild_order_submit_result_state`

Recommended next step:

- Engine E should capture or classify whether the visible quantity and post-submit result states are actually stable and truthful.
- Engine C should promote the minimum guild-order anchor set that satisfies:
  - required list/detail/submit/refresh anchors beyond placeholder scaffolds
  - visible material label and quantity surfaces
  - unavailable / insufficient-feedback / submit-result verification surfaces
- After those assets land, rerun the task foundation builders so `daily_ui.guild_order_submit` can move from blocked-by-foundation to a truthful implementation path without widening scope.
