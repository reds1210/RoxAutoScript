# Core Runtime Orchestration Handoff

## Scope

- Hardened Engine A runtime state synchronization and queue lifecycle behavior on top of the existing runtime coordinator branch.
- Added an emulator-side live runtime wrapper so downstream code can consume discovery, health check, preview capture, queue orchestration, and command dispatch through one Engine A entrypoint.
- Moved `LiveRuntimeSession` toward a production-ready long-lived session with safe polling, revisioned snapshots, recent-event buffering, and app-facing per-instance runtime views.
- Kept changes inside Engine A ownership only; no shared contract or GUI/task/vision files were changed in this follow-up.

## Changed Files

- `src/roxauto/core/instance_registry.py`
- `src/roxauto/core/events.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/__init__.py`
- `src/roxauto/emulator/execution.py`
- `src/roxauto/emulator/live_runtime.py`
- `src/roxauto/profiles/store.py`
- `tests/core/test_instance_registry.py`
- `tests/core/test_runtime.py`
- `tests/emulator/test_live_runtime.py`
- `tests/profiles/test_store.py`

## Public APIs Added Or Changed

- Added `RuntimeCoordinator.event_bus` so downstream consumers can subscribe to live runtime events without reaching into private internals.
- Added `RuntimeCoordinator.list_runtime_contexts()` for ordered runtime-context inspection across all known instances.
- `RuntimeCoordinator.dispatch_command()` now returns a rejected `CommandDispatchResult` for unknown instance ids instead of raising, and correctly reports partial rejection when per-instance execution results reject only some targets.
- `InstanceRegistry.sync()` now preserves existing runtime metadata on rediscovery and marks missing instances as `disconnected`.
- Added `LiveRuntimeSession` and `LiveRuntimeSnapshot` under `roxauto.emulator` as the stable Engine A composition layer for discovery + coordinator + integrated health/preview/command services.
- Added `LiveRuntimeSession.poll()`, `revision`, `last_snapshot`, `last_sync_error`, `last_command_result`, `last_queue_result`, and `get_instance_snapshot()` as stable long-lived session surfaces for the app layer.
- Added `LiveRuntimeEventRecord` and `LiveRuntimeInstanceSnapshot`, and extended `LiveRuntimeSnapshot` with `instance_snapshots`, `recent_events`, `last_sync_at`, `last_discovery_at`, and last-operation fields.
- Added `EVENT_COMMAND_EXECUTED` in `roxauto.core.events` and aligned emulator execution publishing with the shared constant.
- Added `JsonProfileStore.list_matching_profiles()` and `JsonProfileStore.resolve_binding_for_instance()` for conservative per-instance profile auto-resolution.

## What Shipped

- Instance rediscovery no longer overwrites runtime-bound metadata such as profile-binding markers already attached to registry state.
- Missing instances are now marked `disconnected` during sync, and runtime contexts mirror that state so downstream consumers stop rendering stale `ready` or `busy` entries.
- Queue execution now clears stale `active_task_id`, `active_run_id`, and transient `queue_id` markers after completion while preserving `last_run_id` and `last_run_status` for inspection.
- Refresh/pause paths keep runtime-context status aligned with registry transitions instead of waiting for a later context read to reconcile state.
- Refresh/health-failure paths now populate runtime-context health metadata and emit a synthetic `runtime.health_check` failure snapshot when manual refresh detects an unhealthy instance.
- Queue-side health failures now record `FailureSnapshotReason.HEALTH_CHECK_FAILED` instead of the generic stop-condition reason, so downstream failure panes can distinguish runtime health issues from manual stops.
- `LiveRuntimeSession.sync_instances()` can auto-bind a unique per-instance profile via an injected resolver callback, but deliberately skips ambiguous matches instead of silently binding the wrong profile.
- `LiveRuntimeSession` now gives downstream code one headless entrypoint for discovery, context queries, queue queries, refresh, queue start, and generic command dispatch without importing GUI code.
- `LiveRuntimeSession.poll()` now survives transient discovery failures, preserves the last known runtime state, and exposes the failure through `last_sync_error` instead of forcing the app to catch transport exceptions on every refresh loop.
- `LiveRuntimeSession` now tracks a monotonic `revision`, caches the most recent full snapshot, and records recent runtime events so the app can refresh only when session state actually moved.
- `LiveRuntimeSnapshot.instance_snapshots` now pre-joins `InstanceState`, `InstanceRuntimeContext`, and queued items per instance, so the GUI no longer needs to stitch together sample feeds or perform repeated joins client-side.
- Session-level `last_command_result` and `last_queue_result` now provide stable outputs for command/refresh/start-queue actions, and filtered snapshots can be queried per instance without rebuilding app-side selectors.

## Runtime-Facing API

- Poll/update loop:
  - `LiveRuntimeSession.poll()`
  - `LiveRuntimeSession.sync_instances()`
  - `LiveRuntimeSession.revision`
  - `LiveRuntimeSession.last_snapshot`
  - `LiveRuntimeSession.last_sync_error`
- Read models for rendering:
  - `LiveRuntimeSession.snapshot()`
  - `LiveRuntimeSession.get_instance_snapshot(instance_id)`
  - `LiveRuntimeSession.get_runtime_context(instance_id)`
  - `LiveRuntimeSession.list_queue_items(instance_id=None)`
  - `LiveRuntimeSnapshot.instance_snapshots`
  - `LiveRuntimeSnapshot.recent_events`
- Operator actions:
  - `LiveRuntimeSession.refresh(instance_id=None)`
  - `LiveRuntimeSession.dispatch_command(command)`
  - `LiveRuntimeSession.start_queue(instance_id)`
  - `LiveRuntimeSession.enqueue(item)` / `enqueue_many(items)`
- Stable operation outputs:
  - `LiveRuntimeSession.last_command_result`
  - `LiveRuntimeSession.last_queue_result`
  - `LiveRuntimeSnapshot.last_command_result`
  - `LiveRuntimeSnapshot.last_queue_result`

## Assumptions

- Discovery sync is the authoritative signal for whether an emulator instance is still present.
- Downstream GUI code can replace sample log/queue feeds by subscribing to `RuntimeCoordinator.event_bus` or `LiveRuntimeSession.event_bus`, then querying `revision`, `last_snapshot`, `snapshot()`, `get_instance_snapshot()`, and `list_queue_items()`.
- The app refresh loop can safely call `LiveRuntimeSession.poll()` on a timer, treat `last_sync_error` as displayable runtime health state, and continue rendering the last good snapshot during transient discovery failures.
- Per-instance auto-binding should only happen when one resolver result is unambiguous; explicit profile selection remains the safer path when multiple candidates exist.

## Verification

- `python -m unittest discover -s tests/core -t .`
- `python -m unittest discover -s tests/emulator -t .`
- `python -m unittest discover -s tests/profiles -t .`
- `python -m unittest discover -s tests -t .`
- Result: `91` tests passed

## Blockers

- The app branch still needs to replace sample queue/log/preview data sources with `LiveRuntimeSession` or an equivalent adapter wired to the runtime event bus.
- Runtime orchestration remains synchronous; `active_run_id` is only meaningful inside the immediate queue execution path unless a later branch introduces async execution.

## Recommended Next Step

- In Engine B, instantiate `LiveRuntimeSession` with the concrete emulator adapter and a profile-resolver callback, poll it on the GUI refresh cadence, and swap the sample feeds for `last_snapshot.instance_snapshots`, `recent_events`, `last_command_result`, and `last_queue_result`.
