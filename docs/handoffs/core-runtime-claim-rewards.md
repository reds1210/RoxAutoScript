# Core Runtime Claim Rewards Handoff

Track:

- `codex/core-runtime-step-telemetry`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Stayed inside Engine A ownership:
  - `src/roxauto/core/`
  - `src/roxauto/emulator/`
  - `tests/core/`
  - `tests/emulator/`
  - `docs/architecture-contracts.md`
  - `docs/handoffs/`
- Did not touch `tasks/`, `app/`, `vision/`, or a second task.

What shipped:

- Runtime failure snapshots now preserve structured task-side step-failure signals instead of storing only generic `message` text.
- `TaskRunner._capture_failure_snapshot()` now projects failed-step data into runtime-owned `FailureSnapshotMetadata.metadata` using a generic runtime path, not a `daily_ui.claim_rewards` hardcode.
- When a failed `TaskStepResult.data` provides them, runtime failure snapshots now promote:
  - `failure_reason_id`
  - `outcome_code`
  - `inspection_attempts`
  - `step_outcome`
  - `task_action`
  - `inspection`
- Runtime also stores the full primitive-cloned step payload under `failure_snapshot.metadata["step_data"]` so downstream consumers can access the full structured failure context without re-reading task-local objects.
- Existing task-run telemetry behavior is unchanged:
  - `TaskStepTelemetry.data` still carries the full step result payload
  - `active_task_run`, `last_task_run`, `failure_snapshot`, and sticky `last_failure_snapshot` keep the same retry behavior as before
- `LiveRuntimeInstanceSummary` now flattens the claim-rewards signals that GUI/header surfaces usually need first:
  - `failure_step_id`
  - `failure_reason_id`
  - `failure_outcome_code`
  - `failure_inspection_attempt_count`
  - `last_step_id`
  - `last_step_status`
  - `last_step_failure_reason_id`
  - `last_step_outcome_code`
  - `last_failure_step_id`
  - `last_failure_reason_id`
  - `last_failure_outcome_code`
  - `last_failure_inspection_attempt_count`
- Reconnect / rediscover flows now have coverage proving `last_task_run` and `last_failure_snapshot` remain authoritative after a failed claim-rewards run, even if the instance is marked disconnected and then reconnected.
- Health-check and stop-condition snapshots keep their existing generic schema; this round only hardens task step failure snapshots.

Files changed:

- `docs/handoffs/core-runtime-claim-rewards.md`
- `docs/architecture-contracts.md`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_live_runtime.py`

Public APIs added or changed:

- No public method signatures changed.
- Runtime-owned `FailureSnapshotMetadata.metadata` for task step failures now exposes these machine-readable fields when present in the failed step payload:
  - `step_data`
  - `failure_reason_id`
  - `outcome_code`
  - `inspection_attempts`
  - `step_outcome`
  - `task_action`
  - `inspection`
- `LiveRuntimeInstanceSummary` now exposes flattened task-runtime state for GUI consumers:
  - `failure_step_id`
  - `failure_reason_id`
  - `failure_outcome_code`
  - `failure_inspection_attempt_count`
  - `last_step_id`
  - `last_step_status`
  - `last_step_failure_reason_id`
  - `last_step_outcome_code`
  - `last_failure_step_id`
  - `last_failure_reason_id`
  - `last_failure_outcome_code`
  - `last_failure_inspection_attempt_count`

Assumptions:

- `main` already contains the Engine D `claim_rewards.v2` structured step payload contract.
- Downstream consumers that need task-specific diagnosis should read runtime-owned failure snapshot metadata first and use `message` only as a fallback.

Known limitations:

- Snapshot field promotion is intentionally selective. Additional task-specific keys remain available under `failure_snapshot.metadata["step_data"]` rather than being flattened one-by-one into runtime.
- `LiveRuntimeInstanceSummary` now exposes the primary claim-rewards failure/outcome fields, but detailed per-attempt inspection payloads still live under `context.failure_snapshot.metadata["inspection_attempts"]` and `context.last_task_run.steps[*].data`.
- Event summary payloads remain generic; this round does not add task-specific fields to runtime event names or summary counters.

Verification performed:

- `python -m unittest tests.core.test_runtime`
- `python -m unittest tests.emulator.test_live_runtime`
- `python -m unittest discover -s tests/core -t .`
- `python -m unittest discover -s tests/emulator -t .`

Blockers:

- None inside Engine A ownership.
- Engine B still needs to switch any remaining claim-rewards diagnostics from message fallbacks to the new runtime summary / snapshot fields.

Recommended next step:

- Keep the next pass on `daily_ui.claim_rewards` only.
- Engine B should switch claim-rewards card/detail/failure panes to runtime-owned fields in this order:
  - lightweight state from `session.get_live_state(instance_id).selected_instance`
  - `failure_reason_id`
  - `failure_outcome_code`
  - `last_failure_reason_id`
  - `last_failure_outcome_code`
  - `last_step_id`
  - `last_step_status`
  - deep inspection from `context.failure_snapshot.metadata`
  - `inspection_attempts`
  - `inspection`
  - `step_data`
- If later tasks need the same runtime diagnosis path, extend the generic projection rules in `core/runtime.py` rather than adding task-specific branches.

## 2026-04-22 follow-up

What shipped:

- Runtime now preserves the latest non-manual failed `TaskRunTelemetry` projection on `InstanceRuntimeContext.last_failed_task_run` instead of leaving `last_failure_snapshot` as the only sticky failure surface after a later successful retry.
- `TaskRunner._finalize_run_telemetry()` now records failed or health-aborted runs into `last_failed_task_run` while still letting `last_task_run` move forward to the latest run result.
- `_RuntimeTaskActionBridge` and task execution metadata now expose `last_failed_task_run` alongside `last_task_run` / `last_failure_snapshot`, so runtime-owned task handlers and downstream consumers can read the preserved failure run without app-local caches.
- `LiveRuntimeInstanceSnapshot` now exposes `last_failed_task_run`.
- `LiveRuntimeInstanceSummary` now flattens the preserved failed-run projection into lightweight fields:
  - `last_failed_task_id`
  - `last_failed_run_id`
  - `last_failed_run_status`
  - `last_failed_step_count`
  - `last_failed_completed_step_count`
  - `last_failed_step_id`
  - `last_failed_step_status`
  - `last_failed_step_failure_reason_id`
  - `last_failed_step_outcome_code`
- Coverage now proves the preserved failed-run telemetry survives:
  - a later successful retry
  - reconnect / rediscover flows
  - health-check aborts that should still remain diagnosable as runtime failures

Files changed:

- `docs/architecture-contracts.md`
- `docs/handoffs/core-runtime-claim-rewards.md`
- `src/roxauto/core/models.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_live_runtime.py`

Public APIs added or changed:

- `InstanceRuntimeContext` now exposes `last_failed_task_run`.
- `LiveRuntimeInstanceSnapshot` now exposes `last_failed_task_run`.
- `LiveRuntimeInstanceSummary` now exposes:
  - `last_failed_task_id`
  - `last_failed_run_id`
  - `last_failed_run_status`
  - `last_failed_step_count`
  - `last_failed_completed_step_count`
  - `last_failed_step_id`
  - `last_failed_step_status`
  - `last_failed_step_failure_reason_id`
  - `last_failed_step_outcome_code`

Assumptions:

- Manual operator stop should remain a pause/control signal, not overwrite the preserved failed-run history surface.
- Downstream consumers that need deep sticky diagnosis after a later successful retry should prefer `context.last_failed_task_run.steps[*].data` over relying on enriched `last_failure_snapshot.metadata` alone.

Known limitations:

- `last_failed_task_run` currently keeps only the latest failed or health-aborted run, not a multi-run history archive.
- Summary flattening intentionally stays lightweight; detailed retry-attempt payloads still live under `last_failed_task_run.steps[*].data` and `last_failure_snapshot.metadata`.

Verification performed:

- `python -m unittest tests.core.test_runtime`
- `python -m unittest tests.emulator.test_live_runtime`

Recommended next step:

- Engine B should consume `context.last_failed_task_run` as the sticky fallback when `last_failure_snapshot.metadata` no longer carries enough claim-rewards diagnostics after a later success.

## 2026-04-22 runtime-owned anchor follow-up

What shipped:

- Runtime now projects claim-rewards step-spec diagnostics into runtime-owned surfaces instead of leaving anchor/workflow reconstruction to GUI draft state.
- `TaskRunner` reads `TaskSpec.metadata["runtime_input"]["step_specs"]` and promotes step-spec defaults into failed `FailureSnapshotMetadata.metadata`:
  - `step_spec`
  - `step_display_name`
  - `anchor_id`
  - `expected_anchor_id`
  - `signal_anchor_ids`
  - `inspection_retry_limit`
- Failed snapshots now also flatten additional inspection-facing fields when the step payload carries them:
  - `expected_panel_states`
  - `observed_panel_state`
  - `matched_anchor_ids`
  - `workflow_mode`
  - `inspection_reason`
  - `source_image`
- Runtime-owned `TaskStepTelemetry.data` now keeps additive step-spec defaults through `runtime_step_spec` plus top-level anchor fields, so `last_failed_task_run.steps[*].data` remains useful after a later retry.
- `LiveRuntimeInstanceSummary` now exposes lightweight anchor ids for current and sticky history surfaces:
  - `failure_anchor_id`
  - `last_step_anchor_id`
  - `last_failure_anchor_id`
  - `last_failed_step_anchor_id`

Files changed:

- `docs/architecture-contracts.md`
- `docs/handoffs/core-runtime-claim-rewards.md`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_live_runtime.py`

Verification performed:

- `python -m unittest tests.core.test_runtime`
- `python -m unittest tests.emulator.test_live_runtime`

Recommended next step:

- Engine B should stop backfilling `anchor_id` / `expected_anchor_id` from claim-rewards drafts when runtime snapshots or `last_failed_task_run` already provide them, and treat draft state as viewer/editor state only.
