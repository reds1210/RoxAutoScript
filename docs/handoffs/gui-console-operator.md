# gui-console-operator handoff

## Scope

- Engine B ownership only: `src/roxauto/app/`, `assets/ui/`, `tests/app/`, `docs/handoffs/`.
- This round only advanced the first visible task: `daily_ui.claim_rewards`.
- The goal was an MVP product console, not more debug-panel surface.

## Changed files

- `src/roxauto/app/runtime_bridge.py`
- `src/roxauto/app/shell.py`
- `src/roxauto/app/viewmodels.py`
- `assets/ui/operator_console.qss`
- `tests/app/test_runtime_bridge.py`
- `docs/handoffs/gui-console-operator.md`

## What changed

- `OperatorConsoleRuntimeBridge` now exposes a non-blocking app-owned live controller:
  - `start_live_updates(...)`
  - `stop_live_updates(...)`
  - `schedule_refresh(...)`
  - `schedule_command(...)`
  - `schedule_claim_rewards_*`
  - `get_live_state(...)`
  - `get_instance_summaries()`
- GUI startup now instantiates `OperatorConsoleRuntimeBridge(workspace_root=...)` without injecting a fake session/adapter, so the default path uses `build_adb_live_runtime_session(...)` when running the real app.
- The UI thread no longer calls `refresh()` on a timer. Background work happens in the bridge schedule loop; the UI timer only reads `get_live_state(...)`.
- `daily_ui.claim_rewards` queue/run now uses the real task-side builder contract:
  - `build_claim_rewards_runtime_input(...)`
  - `build_claim_rewards_task_spec(...)`
  - D-line step telemetry is projected as the visible 5-step flow
- The bridge now records claim-rewards inspection history and projects failure metadata in the C-line flattened shape expected by `vision.failure.claim_rewards`.
- The shell was rebuilt into a Traditional Chinese MVP console with:
  - emulator card list
  - connection/profile/runtime summary
  - refresh/start/stop/global-stop controls
  - a primary `每日領獎` panel with progress, current step, recent run, failure reason, scope, and preset
  - secondary tabs for preview, failure analysis, readiness, and calibration/capture editor
- Styling moved away from the old engineering-panel feel and now uses card/tabs/progress-bar presentation tuned for the new layout.

## Runtime / task integration details

- `claim_rewards` step rows now come from task-side runtime step specs rather than the old app-local 2-step stub.
- Successful runs now show all 5 steps as completed.
- Failure projection now includes:
  - failure snapshot id / step id / message
  - flattened `claim_rewards` checks for the failure tab
  - selected check summary / workflow summary via `vision.failure.claim_rewards`
- The bridge still keeps a session-scoped editor draft for:
  - workflow mode
  - crop region
  - match region
  - confidence threshold
  - capture scale
  - capture offset
  - selected preview/failure source capture
- The claim-rewards editor can now persist calibration/capture settings into the workspace profile store:
  - default save path: `profiles/<profile_id>.json`
  - saved values are rebound into the live runtime session immediately
  - next app launch will reuse the stored profile when it uniquely matches the instance

## GUI behavior now

- Main surface:
  - `模擬器卡片`
  - `當前模擬器`
  - `每日領獎`
- Secondary surface:
  - `預覽`
  - `失敗分析`
  - `就緒檢查`
  - `校正 / 擷取`
- The UI timer only reads state and never performs runtime refresh directly.
- Buttons dispatch work through `schedule_*` methods only.

## Operable now

- Select a live instance from the emulator card list.
- Refresh runtime state without blocking the UI thread.
- Start queue / stop task / global emergency stop from the selected instance surface.
- Queue `daily_ui.claim_rewards`.
- Run `daily_ui.claim_rewards`.
- Read current step, progress, last run status, failure reason, and scope for `daily_ui.claim_rewards`.
- Capture preview/failure sources into the claim-rewards editor.
- Apply/reset the session-scoped claim-rewards editor overrides needed for the first task.
- Save the current claim-rewards calibration/capture settings into the workspace profile store.

## Viewer-only now

- Preview image pane
- Flattened failure inspector pane
- Readiness details pane
- Calibration/capture diagnostics pane
- Generic runtime/log diagnostics beyond the first-task workflow
- Any persistence of editor values back into packs/assets/calibration profiles

## Known limitations

- The editor workflow still includes session-scoped operator aids, but calibration/capture values can now be persisted to the workspace profile store.
- The workflow-mode control remains an app-side operator aid; it is not a production gameplay setting.
- No second task is wired into the GUI.
- The shell still depends on the production environment having working ADB/runtime access when launched outside tests.

## Verification

- `python -m py_compile src/roxauto/app/shell.py src/roxauto/app/runtime_bridge.py src/roxauto/app/viewmodels.py`
- `python -c "import tests._bootstrap; import roxauto.app; import roxauto.app.shell"`
- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- Result: `135` tests passed

## Recommended next step

- Keep GUI scope on `daily_ui.claim_rewards`, and replace the remaining app-side workflow/editor assumptions with runtime-owned production signals once the runtime/task lines expose them.
