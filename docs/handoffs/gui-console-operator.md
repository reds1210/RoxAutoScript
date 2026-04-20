# gui-console-operator handoff

## Scope

- Move the operator console from local sample queue/log feeds to an app-owned runtime bridge backed by `RuntimeCoordinator`, `EventBus`, and `InstanceRuntimeContext`.
- Keep all changes inside Engine B ownership plus this handoff doc; no shared contract redefinition.
- Strengthen the operator console main screen so summary metrics, instance rows, detail form, manual controls, queue, logs, and preview panes all consume app-level projections over shared runtime contracts.

## Changed files

- `src/roxauto/app/runtime_bridge.py`
- `src/roxauto/app/viewmodels.py`
- `src/roxauto/app/shell.py`
- `src/roxauto/app/__init__.py`
- `assets/ui/operator_console.qss`
- `tests/app/test_viewmodels.py`
- `tests/app/test_runtime_bridge.py`
- `docs/handoffs/gui-console-operator.md`

## Public APIs added or changed

- Added `OperatorConsoleRuntimeBridge` under `roxauto.app` as the app-layer adapter over runtime sync, queue seed, command dispatch, and event capture.
- Added `build_console_snapshot_from_runtime(...)` so the GUI can project `InstanceState` + `InstanceRuntimeContext` into console view state.
- `build_operator_console_state(...)` now accepts optional `runtime_contexts` so the detail pane can consume runtime-owned state.
- Added `build_console_summary(...)` and `build_instance_list_rows(...)` so widgets can consume GUI-specific summary and list-row projections without rebuilding runtime state in the shell.

## Assumptions

- Until a production emulator adapter is wired in, the GUI can use an app-local demo adapter for preview capture, health checks, and manual interaction echo while still exercising real runtime contracts.
- Seeded queue items are only for operator-console/demo visibility and are owned by the app layer; they do not redefine task-pack or runtime contracts.
- `command.executed` events remain a valid readable log signal for operator actions even when some commands are only routed rather than fully executed.
- App-owned events `operator.refresh.completed` and `operator.command.dispatched` are safe GUI-side signals and do not change shared runtime event contracts.

## Verification

- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- Result: `57` tests passed

## What shipped

- Added a runtime bridge that syncs doctor-discovered instances into `RuntimeCoordinator`, binds default profiles, seeds visible queue items, captures runtime events, and exposes live queue/context snapshots to the GUI.
- Rewired the operator console shell so refresh, queue actions, pause/stop/emergency stop, and interaction commands now go through the bridge instead of local sample queue/log lists.
- Updated console viewmodels so instance detail and manual-control state reflect `InstanceRuntimeContext`, including queue depth, profile binding, health checks, stop requests, preview frame, and failure snapshot references.
- Added app tests covering runtime snapshot projection, bridge refresh behavior, queue drain via `start_queue`, and emergency-stop state propagation.
- Reworked the main window into a fuller operator layout with runtime summary cards, richer per-instance list rows, structured detail fields, last-command feedback, clearer queue/log panes, and a more complete preview context pane.
- Expanded the UI stylesheet to support summary cards, runtime banners, warning text, field styling, and preview-frame presentation.

## Blockers

- The bridge still uses an app-local demo execution adapter; real screenshot files, interaction execution, and health semantics still depend on Engine A / emulator-side production wiring.
- Vision tabs still rely on text-first inspection plus a source-path placeholder; no real image widget or calibration editing flow was added in this round.

## Next recommended step

- Replace the demo adapter inside `OperatorConsoleRuntimeBridge` with the production emulator execution stack once the runtime/emulator line exposes the final adapter wiring, then upgrade the preview tab from source-path placeholder to a real frame viewer.
