# Core Runtime Orchestration Handoff

## Scope

- Engine A kept changes inside `core/`, `emulator/`, and owned tests only.
- The runtime side now exposes a clearer production execution path for real ADB-backed actions and a clearer session-driving API for GUI polling.
- No GUI, vision, or task-pack code was changed in this round.

## Changed Files

- `src/roxauto/core/__init__.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/__init__.py`
- `src/roxauto/emulator/adapter.py`
- `src/roxauto/emulator/execution.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_adapter.py`
- `tests/emulator/test_execution.py`
- `tests/emulator/test_live_runtime.py`

## Public APIs Added Or Changed

- `roxauto.emulator.adapter.EmulatorAdapter` remains the stable emulator contract; `roxauto.emulator.execution.EmulatorActionAdapter` now explicitly extends the same contract instead of drifting into a parallel subset.
- `roxauto.emulator.adapter.AdbEmulatorAdapter` is the production-facing implementation for:
  - `capture_screenshot()`
  - `tap()`
  - `swipe()`
  - `input_text()`
  - `launch_app()`
  - `health_check()`
- `roxauto.emulator.adapter.AdbTransport`, `SubprocessAdbTransport`, `AdbCommandResult`, and `AdbCommandError` are now exported from `roxauto.emulator` so the app line can inject real or test transports without reaching into private internals.
- Added `RuntimeInspectionResult` in `roxauto.core.runtime`.
- Added `RuntimeCoordinator.inspect_instance()` and `inspect_instances()` for poll-driven health/preview/failure updates without forcing GUI code through ad hoc refresh-command stitching.
- `LiveRuntimeSession` now exposes:
  - `refresh_runtime_contexts(instance_id=None, run_health_check=True, capture_preview=True)`
  - `poll(instance_id=None, refresh_runtime=False, run_health_check=True, capture_preview=True)`
  - `last_sync_ok`
  - `last_inspection_results`
- `LiveRuntimeSnapshot` now includes:
  - `last_sync_ok`
  - `last_inspection_results`
- `dispatch_command(refresh)` now backfills `last_inspection_results` from the refreshed runtime contexts, so old app code and new polling code see one consistent inspection surface.

## What Shipped

- The real-device execution path is now explicit and test-covered: screenshot, tap, swipe, text input, app launch, and health check all route through the same ADB transport contract.
- `AdbEmulatorAdapter.health_check()` now follows a concrete runtime path:
  - `adb get-state`
  - then a cheap shell probe `echo health_check`
  - returns `False` on transport failure, bad device state, or probe mismatch.
- `RuntimeCoordinator.inspect_instance()` now gives Engine B a stable runtime-facing read/update operation that refreshes:
  - per-instance health state
  - preview frame
  - runtime health failure snapshot
  - derived runtime status
- Inspection preserves long-lived runtime semantics better than the old refresh-only path:
  - disconnected instances skip device calls
  - busy instances stay `busy` when polled healthy
  - paused instances stay `paused`
  - healthy `error` instances can recover to `ready`
- Runtime health failure snapshots are now updated in place instead of being recreated on every poll loop; the snapshot payload can refresh, but repeated polling no longer needs to emit a new failure event unless the failure state meaningfully changed.
- `LiveRuntimeSession` now supports two stable GUI patterns:
  - compatibility mode: `poll()` only syncs discovery, matching current fallback bridge expectations
  - production polling mode: `poll(refresh_runtime=True)` syncs discovery and refreshes runtime contexts in one call
- `refresh_runtime_contexts()` gives the GUI an explicit timer-driven API for preview/health/failure refresh without dispatching synthetic commands.
- `last_inspection_results` and `LiveRuntimeSnapshot.last_inspection_results` provide a stable output surface for app state reducers, even when the caller still uses the existing refresh command path.

## Production-Facing Runtime API

- Emulator execution contract:
  - `EmulatorAdapter`
  - `EmulatorActionAdapter`
  - `AdbEmulatorAdapter`
  - `AdbTransport`
  - `SubprocessAdbTransport`
- Session driving:
  - `LiveRuntimeSession.sync_instances()`
  - `LiveRuntimeSession.refresh_runtime_contexts()`
  - `LiveRuntimeSession.poll(refresh_runtime=True)`
  - `LiveRuntimeSession.revision`
  - `LiveRuntimeSession.last_sync_ok`
  - `LiveRuntimeSession.last_sync_error`
- Runtime reads for GUI:
  - `LiveRuntimeSession.last_snapshot`
  - `LiveRuntimeSession.snapshot(instance_id=None)`
  - `LiveRuntimeSession.get_instance_snapshot(instance_id)`
  - `LiveRuntimeSession.get_runtime_context(instance_id)`
  - `LiveRuntimeSnapshot.instance_snapshots`
  - `LiveRuntimeSnapshot.last_inspection_results`
  - `LiveRuntimeSnapshot.recent_events`
- Stable operator outputs:
  - `LiveRuntimeSession.last_command_result`
  - `LiveRuntimeSession.last_queue_result`
  - `LiveRuntimeSession.last_inspection_results`

## App Integration Notes

- Current fallback bridge can keep working as-is because `poll()` still defaults to discovery-only sync.
- Engine B should move toward:
  - `session.poll(refresh_runtime=True)` on GUI refresh cadence
  - or `session.sync_instances()` + `session.refresh_runtime_contexts()` if the UI wants tighter control
- After that switch, the app can drop the current per-instance `refresh()` loop and consume:
  - `snapshot.instance_snapshots`
  - `snapshot.last_inspection_results`
  - `snapshot.last_command_result`
  - `snapshot.last_queue_result`
  - `snapshot.recent_events`

## Assumptions

- ADB remains the only real-device transport on this branch.
- GUI polling is still single-threaded; queue execution remains synchronous.
- Because there is still no async worker, `active_run_id` is only observable during the immediate queue execution call stack, not as a long-lived background task.

## Verification

- `python -m unittest discover -s tests/core -t .`
- `python -m unittest discover -s tests/emulator -t .`
- `python -m unittest discover -s tests/profiles -t .`
- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- Result: `98` tests passed

## Blockers

- Engine B still needs to replace the current compatibility refresh loop with `poll(refresh_runtime=True)` or `refresh_runtime_contexts()`.
- Queue orchestration is still synchronous; true long-lived `active_run_id` observation still requires a later async/background worker design.

## Recommended Next Step

- In the GUI line, instantiate `LiveRuntimeSession` with `AdbEmulatorAdapter` plus the profile resolver, then replace the fallback refresh stitching with a timer-driven call to `poll(refresh_runtime=True)`.
