# Core Runtime Orchestration Handoff

## Scope

- Engine A kept this round inside owned `core/`, `emulator/`, owned tests, and shared runtime docs only.
- This round completed the minimum production execution path needed for the first fixed UI task: `daily_ui.claim_rewards`.
- No GUI files, no vision files, and no task foundation/task-pack definitions were changed.

## Changed Files

- `docs/architecture-contracts.md`
- `docs/handoffs/core-runtime-orchestration.md`
- `src/roxauto/core/__init__.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/__init__.py`
- `src/roxauto/emulator/execution.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_execution.py`
- `tests/emulator/test_live_runtime.py`

## Public APIs Added Or Changed

- `roxauto.core.runtime`
  - `TaskActionDispatchResult`
  - `TaskHealthCheckResult`
  - `TaskActionBridge`
  - `TaskExecutionContext.action_bridge`
  - `TaskExecutionContext.require_action_bridge()`
- Queue-driven runtime execution now injects a runtime-backed task action bridge before task step handlers run.
- `roxauto.emulator.execution`
  - `RuntimeExecutionPath`
  - `build_runtime_execution_path(adapter, ...)`
  - `build_adb_execution_path(...)`
- `roxauto.emulator.live_runtime`
  - `LiveRuntimeSession(adapter=None, execution_path=None, ...)`
  - `LiveRuntimeSession.adapter`
  - `LiveRuntimeSession.execution_path`
  - `build_adb_live_runtime_session(...)`
- `roxauto.emulator.__init__` now exports the new execution-path builders and bundle type.

## What Shipped

- The production emulator path is now explicit instead of being implied across several constructors.
- One `RuntimeExecutionPath` bundles the real adapter plus the three runtime-facing services that matter for task execution:
  - command dispatch
  - health checks
  - preview capture
- `build_adb_execution_path(...)` is now the formal ADB-backed service builder.
- `build_adb_live_runtime_session(...)` is now the formal top-level entry point for Engine B or any runtime consumer that wants a production `LiveRuntimeSession` without hand-wiring services.
- `LiveRuntimeSession` still supports the old `LiveRuntimeSession(adapter, ...)` path for compatibility, but it can now also accept a fully prepared execution bundle.
- `daily_ui.claim_rewards` can now rely on a real runtime path for:
  - dispatching deterministic interaction commands through the shared execution layer
  - refreshing runtime health
  - capturing previews
  - surfacing failure snapshots when an ADB-backed task step throws
- ADB-backed tests now prove the real path works for:
  - production refresh with preview + runtime failure snapshot
  - first-task queue execution
  - first-task failure snapshot when a task-side tap fails through the real adapter

## Current Runtime Contract For Engine D

- Task step handlers should use `TaskExecutionContext.require_action_bridge()`.
- The bridge currently exposes:
  - `dispatch(command)`
  - `tap(point)`
  - `swipe(start, end, duration_ms=250)`
  - `input_text(text)`
  - `capture_preview()`
  - `check_health()`
- Task code should not import `AdbEmulatorAdapter`, `ActionExecutor`, or GUI helpers directly.
- On failure, let bridge-backed adapter exceptions bubble unless the task intentionally converts them into `step_failure(...)`; runtime already records the failed run and failure snapshot.

## Current Runtime Contract For Engine B

- Recommended production wiring:
  - `build_adb_live_runtime_session(...)`
- That gives Engine B one fully wired object with:
  - `session.adapter`
  - `session.execution_path`
  - `session.poll(refresh_runtime=True)`
  - `session.refresh_runtime_contexts()`
  - `session.refresh(instance_id)`
- Engine B does not need to instantiate `ActionExecutor`, `HealthCheckService`, or `ScreenshotCapturePipeline` directly anymore.

## Assumptions

- `daily_ui.claim_rewards` remains the only task this round needs to support.
- Deterministic reward collection is satisfied by existing interaction primitives plus preview/health/failure observability.
- No async worker or background execution model is required for this milestone.

## Verification

- `python -m unittest tests.core.test_runtime`
- `python -m unittest tests.emulator.test_execution`
- `python -m unittest tests.emulator.test_live_runtime`
- `python -m unittest discover -s tests/core -t .`
- `python -m unittest discover -s tests/emulator -t .`
- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- Result: `117` tests passed

## Blockers

- `src/roxauto/tasks/foundations/readiness_report.json` still reports `daily_ui.claim_rewards` as `blocked_by_runtime`, but this branch was explicitly not allowed to edit task foundations snapshots.
- Engine D still needs to implement the concrete `daily_ui.claim_rewards` steps against the bridge.
- Claim-state vision verification still depends on curated `daily_ui` templates and goldens.

## Recommended Next Step

- Engine B: switch production runtime creation to `build_adb_live_runtime_session(...)`, then drive the UI from `poll(refresh_runtime=True)` / `refresh_runtime_contexts()`.
- Engine D: implement `daily_ui.claim_rewards` step handlers against `TaskExecutionContext.require_action_bridge()`, and use the runtime-provided preview / failure surfaces instead of adapter-local wiring.
