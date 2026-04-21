# Handoff: Vision Lab Calibration Tools

Track:

- `codex/vision-lab-calibration-tools`

Scope:

- keep the existing vision-side calibration / inspection / validation contracts intact
- add claim-specific vision support for `daily_ui.claim_rewards`
- make reward panel / claim reward button / confirm state checks explicit in the `daily_ui` template pack
- expose a GUI-consumable claim-rewards failure payload without touching `app`, `core`, `emulator`, or `tasks`

Files changed:

- `src/roxauto/vision/__init__.py`
- `src/roxauto/vision/services.py`
- `src/roxauto/vision/tooling.py`
- `src/roxauto/vision/validation.py`
- `assets/templates/daily_ui/manifest.json`
- `assets/templates/daily_ui/anchors/daily_reward_panel.svg`
- `assets/templates/daily_ui/anchors/daily_reward_confirm_state.svg`
- `docs/vision/README.md`
- `tests/vision/test_services.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/vision-lab-calibration-tools.md`

Public APIs added or changed:

- existing APIs from earlier rounds remain in place:
  - `build_image_inspection_state()`
  - `build_failure_inspection()`
  - `build_failure_inspector()`
  - `build_match_inspector()`
  - `build_vision_tooling_state()`
  - `validate_template_repository()`
  - `build_vision_workspace_readiness_report()`
- `build_failure_inspection()` now infers `anchor_id` and fallback message from nested claim-rewards metadata when top-level fields are absent
- added GUI-facing claim-rewards failure contracts:
  - `ClaimRewardsCheckState`
  - `ClaimRewardsInspectorState`
- `FailureInspectorState` now includes:
  - `claim_rewards`
- `assets/templates/daily_ui/manifest.json` now declares `metadata.task_support["daily_ui.claim_rewards"]`
- `daily_ui` now exposes three claim-rewards inspection anchors:
  - `daily_ui.reward_panel`
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`

Contract changes:

- `daily_ui.claim_rewards` vision support is now explicit instead of implicit:
  - reward panel presence is represented by `daily_ui.reward_panel`
  - claim button verification is represented by `daily_ui.claim_reward`
  - confirmation readiness is represented by `daily_ui.reward_confirm_state`
- template validation now understands manifest-level task support contracts and will fail when a declared task is missing one of its required inspection roles
- failure inspection can now consume nested `failure_record.metadata["claim_rewards"]` payloads and build per-check match/overlay state even when no top-level `match_result` exists
- `FailureInspectorState.inspection` now falls back to the selected claim-rewards check inspection so existing failure panes still render a useful overlay without special-case logic

Assumptions:

- this round only supports `daily_ui.claim_rewards`
- `guild_check_in` and `odin` remain unchanged on the vision side
- placeholder SVG assets are still acceptable for this stage because the contract work is focused on validation, overlays, and GUI-facing inspection payloads
- Engine B will adopt the new claim-rewards surfaces from the vision package rather than rebuilding task-specific inspection logic locally

Verification performed:

- `python -m unittest tests.vision.test_services`
- `python -m unittest tests.vision.test_tooling`
- `python -m unittest tests.vision.test_validation`
- `python -m unittest discover -s tests/vision -t .`
- `python -m unittest discover -s tests -t .`

Known limitations:

- the new claim-rewards anchors are placeholder assets, not curated live captures
- the claim-rewards failure payload depends on runtime-side metadata being attached under `failure_record.metadata["claim_rewards"]`
- no OCR, pixel diffing, or emulator interaction was added in this round
- readiness inventory still only tracks task-declared required anchors, so `reward_panel` and `reward_confirm_state` currently improve inspection stability without creating new task inventory records

Blockers:

- no code blocker inside the vision-owned scope
- Engine B still needs to consume the new claim-rewards checklist surfaces in the failure pane

Recommended next step:

- Engine B should consume these surfaces for `daily_ui.claim_rewards` failures:
  - `FailureInspectorState.claim_rewards.checks`
  - `FailureInspectorState.claim_rewards.selected_check`
  - `FailureInspectorState.claim_rewards.selected_check.inspection`
  - `FailureInspectorState.claim_rewards.selected_check_summary`
  - `FailureInspectorState.inspection` as the backward-compatible focused overlay
- runtime-side failure metadata should emit:
  - `task_id = "daily_ui.claim_rewards"`
  - `claim_rewards.current_check_id`
  - `claim_rewards.checks.<role>.candidates`
  - `claim_rewards.checks.<role>.message`
  - optional per-check `source_image` and `threshold`
