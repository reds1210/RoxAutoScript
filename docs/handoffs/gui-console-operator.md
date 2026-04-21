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

## 2026-04-21 follow-up

- This pass stayed inside Engine B ownership and only refined `daily_ui.claim_rewards`.
- The claim-rewards main pane now consumes the task-side display projection from `build_claim_rewards_task_display_model(...)` instead of rebuilding product copy from raw step specs and failure snapshots.
- Main-surface task label, preset summary, failure reason, active-step summary, per-step display names, and per-step status text now come from task-owned metadata.
- Step rows now expose task-owned `status_text`, so the shell can show zh-TW step-state copy such as `等待確認領獎` or `獎勵狀態辨識失敗` instead of generic status labels only.
- The shell now prefers the task-owned failure title on the primary status card, which removes raw internal failure reasons like `step_failed` from the operator-facing summary.
- The primary preset summary now shows product-facing task preset text (`每日任務 | 可執行 | 固定介面的每日獎勵領取流程。`) instead of fixture-profile internals.
- The bridge now projects operator-facing `failure_check_summary` and `next_action_summary` from existing task + vision telemetry so the main pane and failure tab can answer:
  - 卡在哪一步
  - 哪個視覺檢查是目前焦點
  - 下一步應該先檢查什麼
- Scope, last-run, and tab copy were rewritten into Traditional Chinese product wording so the single-task surface reads less like an internal debugger.
- A second 2026-04-21 pass moved the claim-rewards pane closer to the Engine A runtime contract:
  - the bridge now prefers runtime-owned `active_task_run` / `last_task_run` over bridge-local `_claim_rewards_record` when projecting the main pane
  - `current_step_title` now follows the runtime-marked active step instead of falling through to the next pending row
  - runtime-owned `last_failure_snapshot` is now consumed as the sticky failure source for claim-rewards diagnostics when the current failure slot is empty
  - repository / anchor selection now recognizes claim-rewards `last_task_run` and `last_failure_snapshot`, so the failure tab stays on the `daily_ui` workspace even when bridge-local claim state is empty
- A third 2026-04-21 pass tightened operator guidance without adding new app-owned workflow state:
  - `next_action_summary` now names the selected anchor and reuses vision-provided effective match region / confidence threshold, so operators can see which anchor, area, and threshold to adjust
  - `selected_anchor_summary` now prefers the claim-failure selected check, which keeps the diagnosis focus aligned with the current failed visual check
  - the failure pane now shows template path, reference image path, effective threshold, and effective match region as viewer-first diagnostics
  - the failure pane explicitly labels those tuning details as viewer-first/operator aid, not runtime-owned task state
- The bridge can now rebuild `failure_snapshot.metadata["claim_rewards"]` from task-side step telemetry when:
  - the bridge-local inspection history cache is empty
  - the last failed run is still available from runtime-owned telemetry
- Added regression coverage for:
  - runtime-owned last-run projection after the bridge-local record cache is cleared
  - runtime-owned active-run projection while a claim-rewards run is in progress
  - rebuilding claim-rewards failure diagnostics from runtime `last_task_run` after the cached failure payload is removed

## Runtime-owned signal now visible in GUI

- Task-owned:
  - `build_claim_rewards_task_display_model(...)` now drives task name, status text, status summary, failure reason, step labels, and step state copy.
- Runtime-owned:
  - selected instance status
  - queue/running/succeeded/failed workflow state
  - latest run id / last run status
  - active step / failed step selection
- Vision-owned:
  - `vision.failure.claim_rewards` selected check / matched-vs-missing counts / selected anchor / threshold / candidate summaries
  - preview / overlay / capture / calibration resolution surfaced through `VisionToolingState`
- App projection only:
  - mapping normalized failure-check ids into operator guidance text such as `先確認是否真的出現確認彈窗`
  - translating normalized scope and diagnosis summaries into product-facing zh-TW copy
  - composing viewer-first operator guidance that points to the currently selected anchor plus vision-owned effective region / threshold

## Viewer-only and operator-aid surfaces

- `目前畫面`
  - viewer-only preview of the currently selected source image and overlay focus
- `卡關診斷`
  - viewer-only diagnosis surface built from runtime failure snapshot + vision claim-rewards inspector state
  - it explains the active visual check and candidate details, but does not change runtime behavior
  - template/reference path and effective tuning values shown here are operator aids derived from vision/calibration state, not a new runtime-owned workflow signal
- `執行條件`
  - viewer-only readiness projection from foundations/runtime requirements
- `校準工具`
  - operator aid for capture, crop, threshold, and offset tuning
  - saving here updates profile-backed calibration/capture settings, but the `workflow_mode` control is still only a diagnostic/editor aid and not a production runtime signal

## GUI behavior now

- Main surface:
  - `模擬器`
  - `執行對象`
  - `每日領獎`
- Secondary surface:
  - `目前畫面`
  - `卡關診斷`
  - `執行條件`
  - `校準工具`
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
- Failure diagnosis pane
- Readiness details pane
- Calibration/capture diagnostics pane
- Generic runtime/log diagnostics beyond the first-task workflow
- Any persistence of editor values back into packs/assets/calibration profiles

## Known limitations

- The editor workflow still includes session-scoped operator aids, but calibration/capture values can now be persisted to the workspace profile store.
- The workflow-mode control remains an app-side operator aid; it is not a production gameplay setting.
- The secondary failure pane still depends on app-side projection of normalized check ids into operator guidance copy; it is no longer inventing task state, but the wording layer is still owned by Engine B.
- Sticky claim-rewards failure snapshots only keep the full check-by-check diagnostics when the failure snapshot metadata already carries `claim_rewards`; runtime currently preserves the sticky snapshot, but not a separate historical failed-run telemetry archive after a later successful retry.
- No second task is wired into the GUI.
- The shell still depends on the production environment having working ADB/runtime access when launched outside tests.

## Verification

- `python -m py_compile src/roxauto/app/shell.py src/roxauto/app/runtime_bridge.py src/roxauto/app/viewmodels.py`
- `python -c "import tests._bootstrap; import roxauto.app; import roxauto.app.shell"`
- `python -m unittest discover -s tests/app -t .`
- `python -m unittest discover -s tests -t .`
- Result: `135` tests passed
- Follow-up result on `2026-04-21`: `142` tests passed
- Runtime-owned telemetry follow-up on `2026-04-21`:
  - `python -m py_compile src/roxauto/app/runtime_bridge.py tests/app/test_runtime_bridge.py`
  - `python -m unittest tests.app.test_runtime_bridge`
  - `python -m unittest discover -s tests/app -t .`
  - `python -m unittest discover -s tests -t .`
  - Result: `161` tests passed

## Recommended next step

- Keep GUI scope on `daily_ui.claim_rewards` only.
- If the project wants sticky failure diagnostics to survive a later successful retry without relying on previously enriched snapshot metadata, Engine A will need a runtime-owned history surface for the latest failed claim-rewards run, not only `last_failure_snapshot`.
