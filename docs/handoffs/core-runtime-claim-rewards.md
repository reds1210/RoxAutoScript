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
