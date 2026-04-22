# Task Daily UI Claim Rewards Handoff

Track:

- `codex/task-claim-rewards-runtime-seam`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Stayed inside Engine D ownership:
  - `src/roxauto/tasks/`
  - `tests/tasks/`
  - `docs/handoffs/`
- Did not touch `core` / `emulator` / `app` / `vision`.

Files changed:

- `src/roxauto/tasks/catalog.py`
- `src/roxauto/tasks/daily_ui/__init__.py`
- `src/roxauto/tasks/daily_ui/claim_rewards.py`
- `src/roxauto/tasks/foundations/asset_inventory.json`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/daily_claim_rewards.task.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `tests/tasks/daily_ui/test_claim_rewards.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/test_inventory_fixtures.py`
- `docs/handoffs/task-daily-ui-claim-rewards.md`

Public APIs added or changed:

- Added task-owned runtime seam packaging for `daily_ui.claim_rewards`:
  - `ClaimRewardsRuntimeSeam`
  - `build_claim_rewards_runtime_seam(...)`
- `build_claim_rewards_task_spec(...)`, `build_claim_rewards_task_preset(...)`, and `build_claim_rewards_task_display_model(...)` accept `runtime_seam=` so runtime registration / enqueue code can resolve the seam once and reuse it directly.
- `build_claim_rewards_runtime_input(...)` carries stable runtime seam metadata in:
  - `runtime_input.metadata["runtime_seam"]`
  - `runtime_input.metadata["result_signal_keys"]`
- `build_claim_rewards_step_telemetry(...)` preserves machine-readable step fields and keeps `expected_panel_states` plus `observed_panel_state` in display metadata.
- Task foundations now expose provenance-aware metadata for claim-rewards asset inventory and readiness:
  - `TaskInventoryRecord.metadata["asset_provenance"]`
  - `TaskInventoryRecord.metadata["asset_state"]`
  - `TaskAssetRecord.metadata["provenance_kind"]`
  - `TaskAssetRecord.metadata["source_kind"]`
  - `TaskAssetRecord.metadata["live_capture"]`
  - `TaskAssetRecord.metadata["replacement_target"]`

Contract changes:

- Task foundations still declare the claim-rewards runtime seam explicitly in task-owned metadata:
  - `inventory.json`
  - `packs/daily_ui/catalog.json`
  - `daily_claim_rewards.task.json`
- Runtime-facing seam metadata remains stable and machine-readable:
  - `runtime_input_builder`
  - `runtime_seam_builder`
  - `task_spec_builder`
  - `task_preset_builder`
  - `task_display_builder`
  - `signal_contract_version`
  - `result_signal_keys`
- Claim-rewards asset provenance is now aligned with the current round-7 live-capture state instead of flattening everything to generic `present`:
  - `daily_ui.reward_panel` is tracked as `live_capture`
  - `daily_ui.claim_reward` is tracked as `curated_stand_in`
  - `daily_ui.reward_confirm_state` is tracked as `curated_stand_in`
  - golden `reward_panel` is live-backed
  - golden `claim_button` and `confirm_state` remain curated stand-ins
- `daily_ui.claim_rewards` task inventory now reports asset state as `mixed_live_capture_and_curated_stand_in`.
- Readiness for `daily_ui.claim_rewards` stays `ready`, but now emits non-blocking provenance warnings for the two remaining stand-in templates:
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- Snapshot tests now require generated foundations output to stay byte-for-byte aligned with the committed JSON snapshots:
  - `inventory.json`
  - `asset_inventory.json`
  - `readiness_report.json`

Assumptions:

- Runtime registration code will start from the task-owned seam metadata instead of hard-coding claim-rewards builder names in core.
- `daily_ui.reward_confirm_state` remains the task-specific signal for the confirm modal, while `common.confirm_button` stays shared and non-authoritative on its own.
- Engine D treats `assets/templates/daily_ui/manifest.json` and `assets/templates/daily_ui/goldens/claim_rewards/catalog.json` as the provenance source of truth for task-owned readiness snapshots.
- Round 7 continues to treat remaining curated stand-ins as non-blocking warnings rather than implementation blockers until Engine C / optional Engine E supply approved replacements.

Verification performed:

- `python -m unittest tests.tasks.daily_ui.test_claim_rewards`
- `python -m unittest tests.tasks.test_catalog tests.tasks.test_inventory_fixtures tests.tasks.daily_ui.test_foundations`
- `python -m unittest discover -s tests/tasks -t .`

Known limitations:

- Engine D still does not own runtime failure snapshot persistence; task-side signals are ready, but Engine A decides what enters `failure_snapshot.metadata`.
- The claim-rewards runtime seam still requires runtime-owned dependencies at build time:
  - adapter
  - navigation plan
  - matcher or vision gateway
- The pre-Gate-3 golden convention is still generic and does not match the actual vision-owned directory layout; claim-rewards uses task-owned `golden_asset_sources` metadata to bridge that mismatch.
- Two required claim-rewards templates still depend on curated stand-ins rather than approved live captures:
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`

Blockers:

- None inside Engine D ownership.
- External follow-up only: the two remaining curated stand-ins above need approved live captures before the new provenance warnings can clear.

Recommended next step:

- Engine C or optional Engine E should replace the remaining stand-ins with approved live zh-TW captures for:
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- After those assets land, rerun the task foundation builders so these task-owned snapshots update cleanly:
  - `inventory.json`
  - `asset_inventory.json`
  - `readiness_report.json`
- Engine A should continue wiring runtime-owned enqueue / telemetry flows from the existing task-owned seam and signal surfaces instead of hard-coding claim-rewards knowledge:
  - `TaskRuntimeBuilderInput.metadata["runtime_seam"]`
  - `ClaimRewardsRuntimeInput.metadata["runtime_seam"]`
  - `TaskSpec.metadata["runtime_seam"]`
  - `TaskSpec.metadata["runtime_input"]`
  - `TaskStepResult.data["failure_reason_id"]`
  - `TaskStepResult.data["outcome_code"]`
  - `TaskStepResult.data["inspection_attempts"]`
  - `TaskStepResult.data["signals"]`
  - `TaskStepResult.data["telemetry"]`
