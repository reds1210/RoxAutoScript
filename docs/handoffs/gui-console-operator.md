# gui-console-operator handoff

## Scope

- Keep this round strictly inside Engine B ownership: `src/roxauto/app/`, `tests/app/`, and this handoff.
- Only advance the first task, `daily_ui.claim_rewards`.
- Expose a usable operator surface for queue / run / preview / failure / readiness / step tracking.
- Add the smallest capture / calibration editor workflow needed for `claim_rewards`, without extending GUI wiring to `guild_check_in`, `odin`, or other gameplay automation.

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
- `OperatorConsoleRuntimeBridge.update_claim_rewards_workflow(...)` stores session-scoped editor inputs for the app-owned `claim_rewards` workflow:
  - workflow mode
  - crop region
  - match region
  - confidence threshold
  - capture scale / offset
  - selected source image / source kind
- `OperatorConsoleRuntimeBridge.reset_claim_rewards_workflow(...)` clears the session-scoped `claim_rewards` editor state for one instance.
- `OperatorConsoleRuntimeBridge.capture_claim_rewards_source(...)` snapshots the current preview or failure image into the `claim_rewards` editor workflow.
- `OperatorConsoleRuntimeBridge.queue_claim_rewards(...)` authors and enqueues an app-owned `daily_ui.claim_rewards` task spec so the GUI can operate the first task without touching `src/roxauto/tasks/`.
- `OperatorConsoleRuntimeBridge.run_claim_rewards(...)` queues and executes that app-owned `claim_rewards` workflow through the existing queue command surface.
- `OperatorConsoleRuntimeBridge.claim_rewards_pane(...)` projects queue status, last run, active step, failure summary, preview source, anchor summary, scope summary, and editor state into one GUI-facing pane model.
- `build_task_readiness_pane(...)` now scopes selected-task emphasis to runtime-owned active or queued tasks that actually exist in task readiness reports, instead of widening the selected scope from profile `allowed_tasks`.
- `TaskReadinessRowView` now carries `fixture_profile_paths` and `scope_reasons` so the GUI can render focused operator diagnostics for the selected runtime task.
- `ClaimRewardsStepView`, `ClaimRewardsEditorView`, and `ClaimRewardsPaneView` were added to `roxauto.app.viewmodels` and exported from `roxauto.app`.
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
- The `claim_rewards` execution path in this round is intentionally app-owned and synthetic: it mirrors the first task's manifest/step contract for operator validation, but it is not the production runtime/task implementation.
- Capture / calibration edits remain session-scoped operator inputs; they do not write back to task packs, vision assets, or persistent calibration files.

## Verification

- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- `python -c "import tests._bootstrap; import roxauto.app.shell"`
- Result: `113` tests passed

## What shipped

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
- Tightened selected task scope so the GUI only emphasizes runtime-owned active or queued work:
  - `daily_ui.claim_rewards` now stays focused when it is the actual active task
  - unrelated profile allowances like `odin.preset_entry` no longer bleed into the selected readiness scope
- Expanded selected-task diagnostics in the Readiness pane for the focused runtime task:
  - manifest path
  - required anchors
  - fixture profile paths
  - runtime / asset / calibration / foundation requirement ids
  - builder blockers, implementation blockers, and warnings
- Updated preview context lines to show the narrowed selected task scope with runtime-derived reasons such as `active` or `queued`.
- Added a dedicated `Claim Rewards` operator group to the shell with first-task-only controls:
  - queue the app-owned `daily_ui.claim_rewards` task
  - run it immediately through the existing queue command
  - capture the current preview image into the workflow
  - capture the latest failure screenshot into the workflow
  - edit crop region, match region, threshold, capture scale, and capture offset
  - reset the session-scoped claim editor
- Added a dedicated `Claim Rewards` observability tab so operators can read, in one place:
  - workflow status
  - runtime readiness gate
  - selected runtime scope
  - preview source path
  - last run id / status
  - active step summary
  - failure reason / failure step / failure snapshot id
  - per-step status, summary, success condition, failure condition, and screenshot path
- Wired `claim_rewards` into the shared vision/capture/calibration surfaces just far enough for the first task:
  - selecting the `daily_ui` repository when the workflow is active, queued, or being edited
  - projecting session-scoped crop/match/threshold edits through `CalibrationProfile`
  - surfacing captured preview/failure images as capture-session artifacts
  - producing an anchor match / failure surface that explains why the workflow succeeded or failed
- Added app tests for:
  - queueing and running the first task through the bridge
  - projecting failed-step and failure-surface state for ambiguous matches
  - preserving the new `claim_rewards` pane contract in `build_operator_console_state(...)`

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

- Operable now for `daily_ui.claim_rewards`:
  - queue
  - run
  - preview-source capture
  - failure-source capture
  - session-scoped crop / match / threshold / scale / offset editor
  - step / failure / readiness / preview diagnostics
- Inspection-driven viewer surfaces:
  - Preview
  - Capture
  - Failures
  - Anchors
  - Calibration
  - Workspace readiness
  - Task readiness / gaps
- Still viewer-only:
  - generic preview tab rendering
  - generic capture artifact browser
  - generic failure viewer
  - generic anchor browser
  - generic calibration pane
  - any persistence of editor changes back into packs/assets/profiles

## Blockers

- The app still owns a thin fallback `EmulatorActionAdapter` because the production emulator execution stack is not exposed to Engine B yet; screenshot paths and interaction side effects are therefore only as real as the injected adapter.
- The `claim_rewards` queue/run flow is app-owned operator scaffolding, not the production runtime bridge; the readiness report still correctly shows `runtime.daily_ui.dispatch_bridge` as the blocking requirement.
- No live image annotation or persistent calibration authoring was added; the editor only holds session-scoped values needed to exercise the first task surface.
- This handoff intentionally does not wire any second task into GUI state.

## Next recommended step

- Land the production `runtime.daily_ui.dispatch_bridge` for `daily_ui.claim_rewards`, then replace the app-owned queue/run scaffold with real runtime step telemetry while keeping the GUI scope limited to the first task until that path is stable.
