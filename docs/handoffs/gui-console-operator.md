# gui-console-operator handoff

## Scope

- Move the operator console off app-local sample feeds and onto `main`'s `LiveRuntimeSession`.
- Keep the work inside Engine B ownership only: `src/roxauto/app/`, `tests/app/`, and this handoff.
- Rewire queue/detail/log/preview/failure/readiness rendering so the GUI consumes shared runtime and vision contracts instead of rebuilding backend state in widgets.

## Changed files

- `src/roxauto/app/runtime_bridge.py`
- `src/roxauto/app/viewmodels.py`
- `src/roxauto/app/shell.py`
- `src/roxauto/app/__init__.py`
- `tests/app/test_runtime_bridge.py`
- `tests/app/test_viewmodels.py`
- `docs/handoffs/gui-console-operator.md`

## Public APIs added or changed

- `OperatorConsoleRuntimeBridge` now wraps `LiveRuntimeSession` directly and uses `poll()`, `last_snapshot`, `dispatch_command()`, and `last_queue_result` instead of owning a parallel `RuntimeCoordinator` state cache.
- `OperatorConsoleRuntimeBridge.vision_tooling_state(...)` now builds GUI-facing vision context from `build_template_workspace_catalog(...)`, `build_vision_workspace_readiness_report(...)`, and `build_vision_tooling_state(...)`.
- `build_console_snapshot_from_runtime(...)` now projects `LiveRuntimeSnapshot` instead of loose `InstanceState`/`InstanceRuntimeContext` collections.
- `OperatorConsoleState` now carries `LiveRuntimeSnapshot`, `LiveRuntimeInstanceSnapshot | None`, and shared `VisionToolingState` so shell code can render directly from shared contracts.

## Assumptions

- A thin app-owned execution adapter is still acceptable until the emulator/runtime line exposes a production `EmulatorActionAdapter`; the important ownership boundary is that GUI state now comes from `LiveRuntimeSession`, not app-local sample feeds.
- The selected template repository can be inferred from runtime context, bound profile metadata, failure anchor ids, or fall back to `common` when no better signal is present.
- Preview pane scope in this round is a real frame/path/context viewer: when a materialized image path exists it is rendered, otherwise the pane shows the runtime-owned path plus context metadata.

## Verification

- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- `python -c "import tests._bootstrap; import roxauto.app.shell"`
- Result: `89` tests passed

## What shipped

- Fast-forwarded this worktree to `main` first so Engine B consumes the latest `LiveRuntimeSession` and vision tooling contracts rather than an outdated local snapshot shape.
- Replaced the old app-local runtime bridge internals with a `LiveRuntimeSession` wrapper that drives refresh via `poll()` plus per-instance refresh, routes manual commands through shared command contracts, and exposes runtime snapshots/queue state without maintaining a duplicate event or queue model.
- Reworked viewmodels so queue/detail/log/manual-control state now projects directly from `LiveRuntimeSnapshot`, `LiveRuntimeInstanceSnapshot`, `recent_events`, `last_command_result`, and `last_queue_result`.
- Rewired the shell to rebuild UI state from the bridge on every refresh/command, added a workspace readiness tab, and upgraded preview rendering into a real frame/path/context viewer that loads the image when the runtime path exists.
- Connected anchors/calibration/failure/workspace panes to shared vision builders so repository catalog, readiness counts, selected anchor details, calibration overrides, capture artifacts, and failure snapshots no longer depend on ad hoc placeholder data.
- Updated app tests to validate live-session refresh, queue execution, emergency stop propagation, runtime snapshot projection, and shared vision state stitching.

## Blockers

- The app still owns a thin fallback `EmulatorActionAdapter` because the production emulator execution stack is not exposed to Engine B yet; screenshot paths and interaction side effects are therefore only as real as the injected adapter.
- No live image annotation or calibration editing workflow was added; this round only surfaces shared tooling state and rendered frame paths/context.

## Next recommended step

- Replace the fallback adapter used by `OperatorConsoleRuntimeBridge` with the production emulator execution adapter, then extend the preview/readiness panes into full image-inspection and calibration-editing flows on top of the now-shared runtime/vision state.
