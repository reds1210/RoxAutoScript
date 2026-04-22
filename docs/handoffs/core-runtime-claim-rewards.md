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

## 2026-04-22 active-step focus follow-up

What shipped:

- Runtime now projects step-spec defaults into `TaskStepTelemetry.data` as soon as a step enters `running`, instead of waiting until the step returns a result.
- Running claim-rewards steps therefore expose runtime-owned focus defaults such as:
  - `runtime_step_spec`
  - `anchor_id`
  - `expected_anchor_id`
  - `signal_anchor_ids`
  - `inspection_retry_limit`
- `LiveRuntimeInstanceSummary` now flattens current-step focus fields for lightweight GUI polling:
  - `active_step_anchor_id`
  - `active_step_failure_reason_id`
  - `active_step_outcome_code`
- This keeps current-step focus aligned with the same runtime-owned path already used for sticky failure history, so GUI no longer needs to invent current claim-rewards anchor focus from task drafts while a step is in flight.

Files changed:

- `docs/architecture-contracts.md`
- `docs/handoffs/core-runtime-claim-rewards.md`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_live_runtime.py`

Public APIs added or changed:

- `LiveRuntimeInstanceSummary` now exposes:
  - `active_step_anchor_id`
  - `active_step_failure_reason_id`
  - `active_step_outcome_code`

Verification performed:

- `python -m unittest tests.core.test_runtime`
- `python -m unittest tests.emulator.test_live_runtime`

Recommended next step:

- Engine B should prefer `selected_instance.active_step_anchor_id` for current focus while a claim-rewards step is running, and reserve deeper reads of `active_task_run.steps[*].data` for drill-down views only.

## 2026-04-22 task outcome report follow-up

What shipped:

- Runtime now emits one machine-readable finished-run outcome summary for every task completion instead of leaving later consumers to reconstruct claim-rewards smoke results from free-form messages or full task telemetry dumps.
- `TaskRunner._finish_run()` now publishes and audits `task.finished` with a normalized `summary` payload that preserves:
  - `instance_id`
  - `adb_serial`
  - `run_id`
  - final `status`
  - `failure_reason_id`
  - `outcome_code`
  - `last_observed_state`
  - `workflow_mode`
  - `anchor_id`
  - `expected_anchor_id`
  - `signal_anchor_ids`
  - `matched_anchor_ids`
  - `source_image`
  - `preview_image_path`
- Runtime context metadata now keeps the latest finished-run summary under:
  - `last_task_outcome_summary`
  - `last_failed_task_outcome_summary` when the run failed or aborted for a non-manual reason
- `LiveRuntimeSession` now exposes runtime-owned reporting helpers for smoke and handoff consumers:
  - `list_task_run_summaries(task_id=None, instance_id=None)`
  - `build_task_outcome_report(task_id, instance_id=None)`
- The new report surface uses recent runtime `task.finished` events first and falls back to context-owned sticky summaries, so later GUI or PR-handoff code can compare the latest claim-rewards runs across devices without reading task-local draft state.
- One repo-level gate unblock outside normal Engine A ownership was required so the autonomy loop could evaluate this branch at all:
  - renamed a duplicate test function in `tests/autonomy/test_agent_packet.py`
  - no autonomy behavior changed; this only cleared an existing `ruff` `F811` failure from duplicated test names on `main`

Files changed:

- `docs/architecture-contracts.md`
- `docs/handoffs/core-runtime-claim-rewards.md`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/autonomy/test_agent_packet.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_live_runtime.py`

Public APIs added or changed:

- `LiveRuntimeSession.list_task_run_summaries(task_id=None, instance_id=None)`
- `LiveRuntimeSession.build_task_outcome_report(task_id, instance_id=None)`
- `task.finished` event and audit payloads now carry `summary`, a runtime-owned `TaskRunOutcomeSummary`-shaped dict

Assumptions:

- Claim-rewards success steps will supply structured `outcome_code` or `state` fields when operators want successful runs to carry richer smoke-report detail than just `status=succeeded`.
- Later consumers should treat `task.finished.summary` as the lightweight comparison surface and keep full `telemetry` / `failure_snapshot` reads for drill-down only.

Known limitations:

- The session report is backed by in-memory recent events plus sticky context summaries, not a multi-process history store.
- The summary shape is generic, but some task-specific fields remain empty for tasks that do not emit structured runtime step data.

Verification performed:

- `python -m unittest tests.core.test_runtime`
- `python -m unittest tests.emulator.test_live_runtime`
- `python -m unittest discover -s tests/core -t .`
- `python -m unittest discover -s tests/emulator -t .`

Recommended next step:

- Engine B should consume `build_task_outcome_report("daily_ui.claim_rewards")` or `list_task_run_summaries(task_id="daily_ui.claim_rewards")` for operator-facing multi-device smoke comparison instead of rebuilding the same summary from raw task telemetry or app-local draft records.

## 2026-04-22 per-instance fallback follow-up

What shipped:

- `LiveRuntimeSession.build_task_outcome_report(...)` no longer treats context fallback as all-or-nothing.
- The report now merges context-owned sticky summaries per missing instance after reading recent `task.finished` events, so one device's surviving event-buffer entry no longer causes other devices to disappear from the report when their latest run still exists under runtime context metadata.
- Coverage now simulates the review-case shape directly by keeping only one instance's `task.finished` event in the recent-event buffer and proving the report still backfills the missing instance from context.

Files changed:

- `docs/handoffs/core-runtime-claim-rewards.md`
- `src/roxauto/emulator/live_runtime.py`
- `tests/emulator/test_live_runtime.py`

Verification performed:

- `python -m unittest tests.emulator.test_live_runtime`
- `python -m ruff check src tests`

Recommended next step:

- Once this lands, Engine B can rely on `build_task_outcome_report("daily_ui.claim_rewards")` for mixed event-buffer / sticky-context situations without needing its own per-instance fallback merge logic.
