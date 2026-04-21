# Core Runtime Claim Rewards Handoff

Track:

- `codex/core-runtime-claim-rewards-hardening`

Scope:

- Added runtime-owned run/step/failure telemetry for `daily_ui.claim_rewards` so GUI layers can read task progress from runtime state instead of reconstructing it from queue results or app-local workflow records.
- Preserved the runtime task-factory registration seam added earlier so claim-rewards task specs can still be built and enqueued through `LiveRuntimeSession` without importing task-pack modules inside `core` or `emulator`.
- Kept the change inside Engine A ownership: `core/`, `emulator/`, owner tests, shared architecture docs, and this handoff.

Files changed:

- `docs/architecture-contracts.md`
- `docs/handoffs/core-runtime-claim-rewards.md`
- `src/roxauto/core/__init__.py`
- `src/roxauto/core/models.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/__init__.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_live_runtime.py`

Public APIs added or changed:

- Added `TaskStepTelemetryStatus`, `TaskStepTelemetry`, and `TaskRunTelemetry` under `roxauto.core.models`.
- `InstanceRuntimeContext` now carries:
  - `active_task_run`
  - `last_task_run`
  - `last_failure_snapshot`
- `TaskRunner` now writes runtime-owned telemetry into the bound runtime context while the run is executing and finalizes it when the run ends.
- `LiveRuntimeInstanceSnapshot` now exposes:
  - `active_task_run`
  - `last_task_run`
  - `last_failure_snapshot`
- `LiveRuntimeInstanceSummary` now surfaces:
  - `active_step_id`
  - `active_step_status`
  - `last_task_id`
  - `last_run_id`
  - `last_run_status`
  - `last_step_count`
  - `last_completed_step_count`
  - `last_failure_snapshot_id`
  - `last_failure_reason`
- Existing runtime task-factory API remains:
  - `register_task_factory(...)`
  - `unregister_task_factory(...)`
  - `has_task_factory(...)`
  - `build_registered_task_spec(...)`
  - `enqueue_registered_task(...)`

Contract changes:

- Added `TaskStepTelemetry` and `TaskRunTelemetry` to `docs/architecture-contracts.md`.
- `InstanceRuntimeContext` now documents runtime-owned active/last task telemetry plus sticky `last_failure_snapshot`.
- `LiveRuntimeState` now documents that per-instance summaries should surface active step ids, last run status, and last failure ids directly.

Assumptions:

- `daily_ui.claim_rewards` remains a caller-registered task factory; runtime still does not import task-pack builders directly.
- Retry for a previously failed run may start from `error`; runtime now force-transitions `error -> busy` only for explicit queue start, then immediately re-checks health before task execution.
- `failure_snapshot` is the current blocking failure for the active/latest run, while `last_failure_snapshot` is the sticky inspection surface that survives a later successful retry.

What shipped for `daily_ui.claim_rewards`:

- Runtime now owns the step lifecycle projection:
  - pending
  - running
  - succeeded
  - failed
  - skipped
- During execution, `runtime_context.active_task_run` exposes the currently running step id/index plus per-step statuses.
- After completion, `runtime_context.last_task_run` holds the finalized step list, preview frame, failure snapshot, stop condition, attempt number, and run status.
- Failure snapshots are now stabilized for retry flows:
  - `failure_snapshot` clears after a successful retry
  - `last_failure_snapshot` keeps the latest failed attempt available for inspection
- `get_live_state()` now carries enough summary fields for Engine B to render queue/run/failure state without inventing claim-rewards step progression from app-local records.

Verification performed:

- `python -m unittest tests.core.test_runtime`
- `python -m unittest tests.emulator.test_live_runtime`
- `python -m unittest discover -s tests/core -t .`
- `python -m unittest discover -s tests/emulator -t .`
- `python -m unittest discover -s tests/profiles -t .`
- `python -m unittest tests.app.test_runtime_bridge`

Known limitations:

- Engine B still needs to consume the new runtime signals; this branch does not touch `src/roxauto/app/`.
- `LiveRuntimeInstanceSummary` is intentionally lightweight; full per-step detail still lives on `InstanceRuntimeContext.active_task_run` / `last_task_run`.
- No default claim-rewards factory is auto-registered yet; an upper layer still needs to register the existing task-side builder.

Blockers:

- None inside Engine A ownership.
- App adoption is still pending on Engine B.

Recommended next step:

- Engine B should stop deriving claim-rewards step state from queue results or app-local execution records and instead read:
  - `snapshot.get_instance_snapshot(instance_id).context.active_task_run` while a run is in progress
  - `snapshot.get_instance_snapshot(instance_id).context.last_task_run` for the finalized step list
  - `snapshot.get_instance_snapshot(instance_id).context.last_failure_snapshot` for sticky failure inspection after retries
  - `session.get_live_state(instance_id).selected_instance.last_run_status` and related summary fields for lightweight card/header state
- Engine B should also switch the claim-rewards enqueue path to the runtime registration seam:
  - `register_task_factory(...)`
  - `build_registered_task_spec(...)` or `enqueue_registered_task(...)`
