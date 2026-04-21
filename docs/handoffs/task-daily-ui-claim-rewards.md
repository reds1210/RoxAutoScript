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
- `build_claim_rewards_task_spec(...)`, `build_claim_rewards_task_preset(...)`, and `build_claim_rewards_task_display_model(...)` now accept `runtime_seam=` so runtime registration / enqueue code can resolve the seam once and reuse it directly.
- `build_claim_rewards_runtime_input(...)` now carries stable runtime seam metadata in `runtime_input.metadata["runtime_seam"]` and `runtime_input.metadata["result_signal_keys"]`.
- `build_claim_rewards_step_telemetry(...)` still preserves machine-readable step fields and now keeps the runtime-emitted `expected_panel_states` plus `observed_panel_state` in display metadata.

Contract changes:

- Task foundations now declare the claim-rewards runtime seam explicitly in task-owned metadata:
  - `inventory.json`
  - `packs/daily_ui/catalog.json`
  - `daily_claim_rewards.task.json`
- Runtime-facing seam metadata is stable and machine-readable:
  - `runtime_input_builder`
  - `runtime_seam_builder`
  - `task_spec_builder`
  - `task_preset_builder`
  - `task_display_builder`
  - `signal_contract_version`
  - `result_signal_keys`
- Claim-rewards curated asset state is now aligned across task foundations:
  - required templates are `present`
  - curated goldens are `present`
  - readiness warnings for claim-rewards asset drift are cleared
- Golden case inventory for `daily_ui.claim_rewards` now matches the repo-curated assets:
  - `reward_panel`
  - `claim_button`
  - `confirm_state`
- Confirmation-modal classification still requires claim-specific evidence and no longer treats `common.confirm_button` alone as sufficient.

Assumptions:

- Runtime registration code will start from the task-owned seam metadata instead of hard-coding claim-rewards builder names in core.
- `daily_ui.reward_confirm_state` remains the task-specific signal for the confirm modal, while `common.confirm_button` stays shared and non-authoritative on its own.
- Repo-curated claim-rewards assets under `assets/templates/daily_ui/` are the source of truth for Engine D readiness until Engine C / optional Engine E replace them with newer live captures.

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
- The pre-Gate-3 golden convention is still generic and does not match the actual vision-owned directory layout; claim-rewards now uses task-owned `golden_asset_sources` metadata to bridge that mismatch.

Blockers:

- None inside Engine D ownership.

Recommended next step:

- Engine A should read these task-owned runtime signals instead of hard-coding claim-rewards knowledge:
  - `TaskRuntimeBuilderInput.metadata["runtime_seam"]`
  - `ClaimRewardsRuntimeInput.metadata["runtime_seam"]`
  - `TaskSpec.metadata["runtime_seam"]`
  - `TaskSpec.metadata["runtime_input"]`
  - `TaskStepResult.data["failure_reason_id"]`
  - `TaskStepResult.data["outcome_code"]`
  - `TaskStepResult.data["inspection_attempts"]`
  - `TaskStepResult.data["signals"]`
  - `TaskStepResult.data["telemetry"]`
- Engine B should read these task-owned display signals and stop branching on step message text:
  - `display_model.failure_reason`
  - `display_model.steps[*].metadata["failure_reason_id"]`
  - `display_model.steps[*].metadata["outcome_code"]`
  - `display_model.steps[*].metadata["expected_panel_states"]`
  - `display_model.steps[*].metadata["observed_panel_state"]`
  - `display_model.steps[*].metadata["signals"]`
  - `display_model.steps[*].metadata["task_action_status"]`
- After Engine A wires the runtime seam, revalidate that the runtime-owned enqueue path only depends on these task-owned metadata surfaces and not on GUI-side claim-rewards assumptions.
