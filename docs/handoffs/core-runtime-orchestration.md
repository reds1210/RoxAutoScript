# Core Runtime Orchestration Handoff

## Scope

- Engine A kept this round inside owned `emulator/`, owned tests, and shared runtime docs only.
- This round was for MVP GUI runtime wiring, not new gameplay automation.
- No `app/`, `vision/`, or `tasks/` files were changed.

## Changed Files

- `docs/architecture-contracts.md`
- `docs/handoffs/core-runtime-orchestration.md`
- `src/roxauto/emulator/__init__.py`
- `src/roxauto/emulator/live_runtime.py`
- `tests/emulator/test_live_runtime.py`

## What Shipped

- `LiveRuntimeSession` now exposes a lightweight GUI-facing state surface:
  - `LiveRuntimeState`
  - `LiveRuntimeInstanceSummary`
  - `LiveRuntimeRefreshState`
- GUI code no longer needs to rebuild a full `LiveRuntimeSnapshot` every repaint just to render instance cards, counters, refresh banners, or selection state.
- `LiveRuntimeSession` now supports background, non-blocking runtime work scheduling:
  - `schedule_runtime_refresh(...)`
  - `schedule_rediscover(...)`
  - `schedule_sync()`
  - `wait_for_background_idle(...)`
- Background work is single-worker and coalesced to the latest scheduled request. This is the minimum reliable path for MVP GUI polling without an async refactor.
- `LiveRuntimeSession` now exposes runtime lifecycle helpers for emulator presence/state:
  - `connect_instance(...)`
  - `disconnect_instance(...)`
  - `reconnect_instance(...)`
  - `rediscover_instances(...)`
- `build_adb_live_runtime_session(...)` remains the production entry point. GUI can now build the production session once, then drive it through scheduled background refreshes plus `get_live_state(...)`.

## GUI Contract For Engine B

- Build the production session with:
  - `build_adb_live_runtime_session(...)`
- On GUI startup:
  - call `session.schedule_rediscover(refresh_runtime=False)` to populate instance cards without immediately forcing health + screenshot work
- For periodic background discovery:
  - call `session.schedule_rediscover(refresh_runtime=False)`
- For selected-instance inspection:
  - call `session.schedule_runtime_refresh(instance_id=selected_instance_id, capture_preview=True)`
- For cheap UI reads:
  - call `session.get_live_state(selected_instance_id)` on the GUI thread
- For connection lifecycle buttons:
  - runtime-only attach/update: `connect_instance(instance)`
  - mark unavailable: `disconnect_instance(instance_id, reason=...)`
  - operator-triggered reconnect intent: `reconnect_instance(instance_id, rediscover=True)`
- Avoid the old GUI pattern of:
  - `poll()`
  - then per-instance `refresh()`
  - then rebuilding a full snapshot on the UI thread

## Notes On State Surfaces

- `LiveRuntimeState.refresh_state` is the GUI spinner/banner source.
- `LiveRuntimeState.instances` is the lightweight card/list source.
- `LiveRuntimeState.selected_instance` is the cheap selected-row/detail source.
- Full `snapshot()` is still available for tests and tooling, but it is no longer the preferred GUI read model.

## Notes On Production Wiring

- Engine B still does not need to instantiate:
  - `AdbEmulatorAdapter`
  - `ActionExecutor`
  - `HealthCheckService`
  - `ScreenshotCapturePipeline`
- Those remain bundled under:
  - `build_adb_execution_path(...)`
  - `build_adb_live_runtime_session(...)`

## Notes For Engine D

- No task-pack code changed this round.
- `daily_ui.claim_rewards` should keep using `TaskExecutionContext.require_action_bridge()`.
- GUI/runtime changes here are additive and do not change the task bridge contract added in the previous round.

## Verification

- `python -m unittest tests.emulator.test_live_runtime`
- `python -m unittest tests.emulator.test_execution`
- `python -m unittest tests.core.test_runtime`

## Blockers

- GUI code in `src/roxauto/app/` still needs to switch from synchronous `poll()+refresh()` reads to the new scheduled background/session-state pattern.
- This branch intentionally did not modify app wiring, so the GUI migration itself is still pending on Engine B.

## Recommended Next Step

- Engine B should switch runtime UI updates to:
  - `session.schedule_rediscover(...)`
  - `session.schedule_runtime_refresh(...)`
  - `session.get_live_state(...)`
- Keep full `snapshot()` only for tooling/debug panes that genuinely need the full object graph.
