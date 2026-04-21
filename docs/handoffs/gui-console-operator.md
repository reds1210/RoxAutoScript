# gui-console-operator handoff

## Scope

- Move the operator console onto the third-round runtime / vision / task-foundation state that is now on `main`.
- Keep the work inside Engine B ownership only: `src/roxauto/app/`, `tests/app/`, and this handoff.
- Rewire queue/detail/log/preview/capture/failure/readiness/calibration rendering so the GUI consumes shared runtime, vision, and task-readiness contracts instead of rebuilding backend state in widgets.

## Changed files

- `src/roxauto/app/runtime_bridge.py`
- `src/roxauto/app/viewmodels.py`
- `src/roxauto/app/shell.py`
- `src/roxauto/app/__init__.py`
- `tests/app/test_runtime_bridge.py`
- `tests/app/test_viewmodels.py`
- `docs/handoffs/gui-console-operator.md`

## Public APIs added or changed

- `OperatorConsoleRuntimeBridge.refresh(...)` now drives GUI refresh through `LiveRuntimeSession.poll(refresh_runtime=True, ...)` instead of `poll()` plus app-side per-instance `refresh()` stitching.
- `OperatorConsoleRuntimeBridge.refresh_runtime_contexts(...)` exposes the session-owned runtime inspection loop directly to the GUI layer.
- `OperatorConsoleRuntimeBridge` now directly consumes:
  - `LiveRuntimeSession.last_snapshot`
  - `LiveRuntimeSession.last_inspection_results`
  - `LiveRuntimeSession.last_command_result`
  - `LiveRuntimeSession.last_queue_result`
  - `build_template_workspace_catalog(...)`
  - `build_vision_workspace_readiness_report(...)`
  - `build_vision_tooling_state(...)`
  - `build_image_inspection_state(...)`
  - `TaskFoundationRepository.evaluate_task_readinesses()`
  - `TaskFoundationRepository.build_runtime_builder_inputs()`
- `OperatorConsoleState` now carries:
  - `LiveRuntimeSnapshot`
  - `LiveRuntimeInstanceSnapshot | None`
  - `RuntimeInspectionResult | None`
  - `VisionToolingState`
  - `TaskReadinessPaneView`
- `build_task_readiness_pane(...)` was added so the GUI can project foundation-owned builder / implementation readiness and gap domains without rebuilding task state.

## Assumptions

- A thin app-owned execution adapter is still acceptable until the emulator/runtime line exposes a production `EmulatorActionAdapter`; the important ownership boundary is that GUI state now comes from `LiveRuntimeSession`, not app-local sample feeds.
- The selected template repository can be inferred from runtime context, bound profile metadata, failure anchor ids, or fall back to `common` when no better signal is present.
- Preview pane scope in this round is still viewer-first: when a materialized image path exists it is rendered, otherwise the pane shows the runtime-owned path plus inspection/context metadata.

## Verification

- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- `python -c "import tests._bootstrap; import roxauto.app.shell"`
- Result: `113` tests passed

## What shipped

- Fast-forwarded this worktree to `main` first so Engine B consumes the latest `LiveRuntimeSession` and vision tooling contracts rather than an outdated local snapshot shape.
- Replaced the old app-local refresh stitching with session-owned polling:
  - GUI startup and timer refresh now use `LiveRuntimeSession.poll(refresh_runtime=True)`
  - command aftermath uses `refresh_runtime_contexts(...)` so interaction / stop / queue state lands back in `last_inspection_results`
- Reworked viewmodels so queue/detail/log/manual-control state now projects directly from:
  - `last_snapshot.instance_snapshots`
  - `last_inspection_results`
  - `last_command_result`
  - `last_queue_result`
  - `recent_events`
- Connected preview / capture / failure / anchor / calibration panes to shared inspection payloads:
  - `VisionToolingState.preview`, `capture`, `failure`, `anchors`, `calibration`
  - `build_image_inspection_state(...)` for the runtime preview viewer
  - shared calibration resolution / overlay state instead of app-local merge rules
- Added task readiness projection from foundations:
  - builder ready / blocked
  - implementation ready / blocked
  - blocked by asset / runtime / calibration / foundation
- Rewired the shell so:
  - Preview is now an inspection-driven frame/path/context viewer
  - Capture is a real capture-session / artifact viewer
  - Readiness shows both workspace readiness and task readiness / gaps
  - Calibration / Anchors / Failures render shared overlay / resolution / inspection payloads instead of placeholders
- Updated app tests to validate live-session polling, post-command inspection refresh, task-readiness projection, and shared vision preview state stitching.

## Shared surfaces now consumed by GUI

- Runtime:
  - `LiveRuntimeSession.poll(refresh_runtime=True)`
  - `LiveRuntimeSession.refresh_runtime_contexts()`
  - `LiveRuntimeSession.last_snapshot`
  - `LiveRuntimeSession.last_inspection_results`
  - `LiveRuntimeSession.last_command_result`
  - `LiveRuntimeSession.last_queue_result`
- Vision:
  - `build_image_inspection_state()`
  - `build_vision_tooling_state()`
  - `build_vision_workspace_readiness_report()`
- Task foundations:
  - `TaskFoundationRepository.evaluate_task_readinesses()`
  - `TaskFoundationRepository.build_runtime_builder_inputs()`

## Pane status

- Inspection-driven now:
  - Preview
  - Capture
  - Failures
  - Anchors
  - Calibration
  - Workspace readiness
  - Task readiness / gaps
- Still viewer-only, not editor workflow:
  - Preview
  - Capture
  - Failures
  - Anchors
  - Calibration

## Blockers

- The app still owns a thin fallback `EmulatorActionAdapter` because the production emulator execution stack is not exposed to Engine B yet; screenshot paths and interaction side effects are therefore only as real as the injected adapter.
- No live image annotation, capture authoring, or calibration editing workflow was added; this round only surfaces shared tooling state and rendered frame / overlay context.

## Next recommended step

- Replace the fallback adapter used by `OperatorConsoleRuntimeBridge` with the production emulator execution adapter, then build editor workflows on top of the now-inspection-driven preview / capture / calibration panes.
