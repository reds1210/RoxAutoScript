# Core Runtime Orchestration Handoff

## Scope

- Hardened Engine A runtime state synchronization and queue lifecycle behavior on top of the existing runtime coordinator branch.
- Added an emulator-side live runtime wrapper so downstream code can consume discovery, health check, preview capture, queue orchestration, and command dispatch through one Engine A entrypoint.
- Kept changes inside Engine A ownership only; no shared contract or GUI/task/vision files were changed in this follow-up.

## Changed Files

- `src/roxauto/core/instance_registry.py`
- `src/roxauto/core/runtime.py`
- `src/roxauto/emulator/__init__.py`
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

## Assumptions

- Discovery sync is the authoritative signal for whether an emulator instance is still present.
- Downstream GUI code can replace sample log/queue feeds by subscribing to `RuntimeCoordinator.event_bus` or `LiveRuntimeSession.event_bus`, then querying `list_runtime_contexts()`, `get_runtime_context()`, `snapshot()`, and `queue.list_items()`.
- Per-instance auto-binding should only happen when one resolver result is unambiguous; explicit profile selection remains the safer path when multiple candidates exist.

## Verification

- `python -m unittest discover -s tests/core -t .`
- `python -m unittest discover -s tests/emulator -t .`
- `python -m unittest discover -s tests/profiles -t .`
- `python -m unittest discover -s tests -t .`
- Result: `62` tests passed

## Blockers

- The app branch still needs to replace sample queue/log/preview data sources with `LiveRuntimeSession` or an equivalent adapter wired to the runtime event bus.
- Runtime orchestration remains synchronous; `active_run_id` is only meaningful inside the immediate queue execution path unless a later branch introduces async execution.

## Recommended Next Step

- In Engine B, instantiate `LiveRuntimeSession` with the concrete emulator adapter and a profile-resolver callback, then wire operator-console refresh, queue, preview, and failure panes to `event_bus`, `snapshot()`, `get_runtime_context()`, and `dispatch_command()`.
