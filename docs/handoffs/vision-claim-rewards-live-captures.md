# Handoff: Vision Claim Rewards Live Captures

Track:

- `codex/vision-claim-rewards-live-captures`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Stayed inside Engine C ownership for vision contracts, template metadata, supporting raw captures, and tests.
- Did not edit `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/tasks/`, or `src/roxauto/app/`.
- Left the three anchor ids stable:
  - `daily_ui.reward_panel`
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`

Files changed:

- `src/roxauto/vision/tooling.py`
- `src/roxauto/vision/validation.py`
- `assets/templates/daily_ui/manifest.json`
- `assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `docs/vision/README.md`
- `docs/vision/claim_rewards_live/raw/*`
- `tests/vision/test_repository.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/vision-claim-rewards-live-captures.md`

Public APIs added or changed:

- `TemplateDependencyReadiness` now also exposes:
  - `failure_case`
- `MatchInspectorState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `failure_case`
- `ClaimRewardsCheckState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `failure_case`
- `ClaimRewardsInspectorState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `selected_failure_case`
- `FailureInspectorState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `failure_case`

Contract changes:

- `metadata.task_support["daily_ui.claim_rewards"]` now carries `live_capture_coverage`:
  - `live_anchor_ids`
  - `stand_in_anchor_ids`
  - `blocked_scene_ids`
- claim-rewards anchor curation metadata now requires a machine-readable `metadata.curation.metadata.failure_case`.
- claim-rewards catalog entries now mirror `failure_case` so catalog and anchor metadata stay aligned.
- validation now rejects:
  - missing `failure_case`
  - missing `live_capture_coverage`
  - live/stand-in coverage lists that do not match anchor provenance
  - catalog entries whose `failure_case` diverges from anchor metadata
- readiness metadata now carries `claim_rewards_live_capture_coverage`, and each template dependency now carries its own `failure_case`.
- failure and match tooling now flatten the currently selected region directly instead of forcing GUI to inspect nested overlay payloads to find the operative area.

Current live vs stand-in status:

- Live capture:
  - `daily_ui.reward_panel`
  - canonical baseline:
    - `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
  - supplemental live captures:
    - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
    - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`
- Curated stand-in:
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- Traceability-only raw captures copied into this worktree:
  - `docs/vision/claim_rewards_live/raw/`
  - includes additional round-7 screenshots such as `emulator-5560-reward-recovery*.png` and `runtime-previews-latest-20-sheet.png`
  - these are not promoted to canonical baselines unless they appear in `catalog.json`

Assumptions:

- The currently available live evidence is still only strong enough to keep `reward_panel_open` as the sole canonical live claim-rewards baseline.
- The extra round-7 raw captures are useful for traceability and operator context, but they do not prove the claimable-button or confirm-modal scenes.
- GUI and downstream tracks should use the new machine-readable `failure_case`, `selected_region`, and coverage metadata rather than English message parsing.

Verification performed:

- `python -m json.tool assets/templates/daily_ui/manifest.json`
- `python -m json.tool assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `python -m unittest tests.vision.test_repository`
- `python -m unittest tests.vision.test_serialization`
- `python -m unittest tests.vision.test_validation`
- `python -m unittest tests.vision.test_tooling`
- `python -m unittest tests.vision.test_services`
- `python -m unittest discover -s tests/vision -t .`
- `python -m unittest discover -s tests -t .`

Known limitations:

- `daily_ui.claim_reward` still does not have an approved live zh-TW ROX claimable-panel capture.
- `daily_ui.reward_confirm_state` still does not have an approved live zh-TW ROX confirmation-modal capture.
- `selected_region` is intentionally the currently selected inspection overlay region; for matched checks that may be the runtime match bbox rather than the repository match window.
- Engine D still owns the task inventory policy, so the existing `daily_ui.claim_reward` inventory mismatch remains expected until that track updates it.

Blockers:

- None inside Engine C ownership.
- Promoting the remaining anchors to `live_capture` still depends on approved live zh-TW ROX screenshots for:
  - `reward_panel_claimable`
  - `reward_confirm_modal`

Recommended next step:

- Capture approved live zh-TW ROX screenshots for `reward_panel_claimable` and `reward_confirm_modal`.
- Once those are available, replace the current stand-in baselines in place, move those anchors from `stand_in_anchor_ids` to `live_anchor_ids`, and remove their scene ids from `blocked_scene_ids`.
- Engine B should render `selected_region`, `selected_region_summary`, and `failure_case` directly instead of deriving region/action hints from overlay summaries or English failure strings.
