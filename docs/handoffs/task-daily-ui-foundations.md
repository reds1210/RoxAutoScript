# Task Daily UI Foundations Handoff

## Scope

- Extended the pre-Gate-3 task foundations with typed readiness schema, runtime-builder input, and readiness evaluation.
- Kept the work at the foundations layer only; no gameplay automation handlers were added.

## Changed Files

- `src/roxauto/tasks/__init__.py`
- `src/roxauto/tasks/models.py`
- `src/roxauto/tasks/catalog.py`
- `src/roxauto/tasks/daily_ui/foundations.py`
- `src/roxauto/tasks/daily_ui/__init__.py`
- `src/roxauto/tasks/odin/foundations.py`
- `src/roxauto/tasks/odin/__init__.py`
- `src/roxauto/tasks/foundations/conventions/golden_screenshots.json`
- `src/roxauto/tasks/foundations/conventions/README.md`
- `src/roxauto/tasks/foundations/fixture_profiles/default_tw_daily.fixture.json`
- `src/roxauto/tasks/foundations/fixture_profiles/default_tw_guild.fixture.json`
- `src/roxauto/tasks/foundations/fixture_profiles/default_tw_odin.fixture.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/daily_claim_rewards.task.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/guild_check_in.task.json`
- `src/roxauto/tasks/foundations/packs/odin/catalog.json`
- `src/roxauto/tasks/foundations/packs/odin/odin_preset_entry.task.json`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/asset_inventory.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `tests/tasks/test_models.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/test_inventory_fixtures.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/odin/test_foundations.py`

## Verification

- `python -m unittest discover -s tests/tasks -t .`
- `python -m unittest discover -s tests -t .`

## What shipped

- Added typed readiness schema under `src/roxauto/tasks/models.py`: `TaskReadinessState`, `TaskGapDomain`, `TaskReadinessRequirement`, `TaskReadinessReport`, `TaskReadinessCollection`, and `TaskRuntimeBuilderInput`.
- Added repository-side readiness evaluators: `build_runtime_builder_input()`, `build_runtime_builder_inputs()`, `evaluate_task_readiness()`, `evaluate_task_readinesses()`, and `load_readiness_report()`.
- Curated `inventory.json` now carries `asset_requirement_ids`, `runtime_requirement_ids`, and `calibration_requirement_ids`, which lets later task-implementation work decide whether a task is blocked by asset, runtime, calibration, or foundation.
- Added `readiness_report.json` as a serialized snapshot of the current pre-Gate-3 state.
- Current readiness states are:
  - `daily_ui.claim_rewards`: builder `ready`, implementation `blocked_by_runtime`
  - `daily_ui.guild_check_in`: builder `blocked_by_asset`, implementation `blocked_by_asset`
  - `odin.preset_entry`: builder `ready`, implementation `blocked_by_calibration`
- Placeholder anchors and planned goldens remain visible as warning requirements instead of being mixed into runtime or calibration blockers.

## Blockers

- Still foundations-only; future task implementations depend on Gate 3 runtime and GUI integration.
- `daily_ui.claim_rewards` still needs a production runtime action-dispatch bridge.
- `daily_ui.guild_check_in` still needs a curated guild check-in template asset beyond placeholder scaffolding.
- `odin.preset_entry` still needs an Odin idle-state calibration profile.

## Next Step

- Keep task readiness output as the source of truth for future `daily_ui` and `odin` implementations.
- Once the runtime bridge, curated guild asset, and Odin calibration profile are available, task implementation work can consume `TaskRuntimeBuilderInput` and `TaskReadinessReport` directly.
