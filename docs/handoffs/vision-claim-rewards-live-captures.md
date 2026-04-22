# Handoff: Vision Claim Rewards Live Captures

Track:

- `codex/vision-claim-rewards-live-captures`

Scope:

- stayed inside Engine C ownership:
  - `assets/templates/`
  - `src/roxauto/vision/`
  - `docs/vision/`
  - `tests/vision/`
  - this handoff
- kept scope locked to `daily_ui.claim_rewards`
- did not edit task/runtime/app semantics
- turned the remaining post-tap truth gap into a machine-readable decision packet instead of leaving it only in raw notes

Files changed in this run:

- `assets/templates/daily_ui/manifest.json`
- `assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_claimed_result__live_capture__127_0_0_1_5559__after_claim_tap.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_claimed_result__live_capture__127_0_0_1_5563__after_claim_tap.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_claimed_result__live_capture__emulator_5560__after_claim_tap.png`
- `src/roxauto/vision/repository.py`
- `src/roxauto/vision/validation.py`
- `src/roxauto/vision/tooling.py`
- `docs/vision/README.md`
- `docs/vision/claim_rewards_live/README.md`
- `docs/handoffs/vision-claim-rewards-live-captures.md`
- `tests/vision/test_repository.py`
- `tests/vision/test_validation.py`
- `tests/vision/test_tooling.py`

Public APIs added or changed:

- `AnchorRepository.get_claim_rewards_post_tap_contract()`
  - returns the manifest-level decision packet for live post-tap behavior
- `VisionWorkspaceReadinessReport.metadata["claim_rewards_post_tap_contract"]`
  - exposes the same decision packet through readiness/report surfaces
- `ClaimRewardsInspectorState`
  - now flattens:
    - `post_tap_contract_anchor_id`
    - `post_tap_contract_scene_id`
    - `post_tap_contract_recommendation`
    - `post_tap_contract_observed_scene_ids`
    - `post_tap_contract_observed_capture_ids`
    - `post_tap_contract_summary`
- `FailureInspectorState`
  - now mirrors the same flattened `post_tap_contract_*` fields for generic failure-pane consumers

Contract changes in this run:

- `daily_ui.reward_panel`
  - unchanged: remains a truthful `live_capture`
- `daily_ui.claim_reward`
  - unchanged: remains a truthful `live_capture`
- `daily_ui.reward_confirm_state`
  - unchanged as an anchor: still a `curated_stand_in`
  - strengthened as a contract:
    - `metadata.task_support["daily_ui.claim_rewards"].post_tap_contract` now records:
      - current anchor: `daily_ui.reward_confirm_state`
      - current scene: `reward_confirm_modal`
      - current contract kind: `strict_confirm_modal_only`
      - dispatch recommendation: `direct_result_overlay_is_valid`
      - observed live outcome scenes:
        - `reward_post_tap_overlay`
        - `reward_claimed_result_state`
      - observed live outcome capture ids:
        - `post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22`
        - `post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap`
        - `post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap`
        - `post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap`
- `catalog.json`
  - now mirrors the same `post_tap_contract` packet in catalog metadata
  - now lands reviewed post-tap supporting captures from all four confirmed devices
  - `capture_inventory.landed_device_serials` is now:
    - `emulator-5556`
    - `emulator-5560`
    - `127.0.0.1:5559`
    - `127.0.0.1:5563`
  - `capture_inventory.missing_device_serials` is now empty

New supporting evidence landed:

- `post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22`
  - existing overlay evidence kept as the live post-tap result-overlay example from `emulator-5556`
- `post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap`
  - new direct claimed/result state from `127.0.0.1:5559`
- `post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap`
  - new direct claimed/result state from `127.0.0.1:5563`
- `post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap`
  - new direct claimed/result state from `emulator-5560`

Why `reward_confirm_state` still is not promoted:

- no reviewed raw/live capture in this branch shows a true like-for-like reward confirmation modal
- every reviewed live post-tap surface now lands in one of two alternate outcomes:
  - reward-result overlay
  - direct claimed/result state
- that is enough to recommend broadening the product/task contract, but not enough to pretend the current strict modal anchor is already live

Dispatch recommendation:

- recommended answer for Route A:
  - `direct_result_overlay_is_valid`
- reasoning:
  - four-device reviewed evidence no longer supports `strict_confirm_modal_only` as the truthful live product contract
  - keeping the anchor curated while recommending the broader live contract preserves truth without forcing a task/runtime change inside Engine C

Assumptions:

- the reviewed raw captures from `127.0.0.1:5559`, `127.0.0.1:5563`, and `emulator-5560` are valid zh-TW ROX post-claim evidence for the same task flow
- the direct claimed/result state is product-relevant post-tap evidence even though it is not a like-for-like modal replacement
- Engine D will decide whether to convert this recommendation into task success/failure semantics after dispatch confirms the contract direction

Blockers:

- a true live `reward_confirm_modal` capture is still missing
- this branch intentionally does not change task/runtime behavior, so the recommendation still needs Engine D follow-through before the runtime can treat direct result overlays as valid success states

Verification performed:

- `python -m json.tool assets/templates/daily_ui/manifest.json`
- `python -m json.tool assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `python -m unittest tests.vision.test_repository tests.vision.test_validation tests.vision.test_tooling`

Recommended next step:

- dispatch should treat Engine C's answer as:
  - `direct_result_overlay_is_valid`
- then open Engine D to align `daily_ui.claim_rewards` task semantics with the broadened post-tap truth contract
- Engine B only needs follow-up if operator UI should surface the new `post_tap_contract_*` fields directly
