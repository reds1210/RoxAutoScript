# Handoff: Vision Claim Rewards Live Captures

Track:

- `codex/vision-claim-rewards-live-captures`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Promoted approved round-8 live evidence into the claim-rewards vision contract.
- Kept the three GUI-facing anchor ids stable:
  - `daily_ui.reward_panel`
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- Did not edit runtime orchestration, emulator transport, or app GUI code.

Files changed in this run:

- `assets/templates/daily_ui/anchors/daily_claim_button.png`
- `assets/templates/daily_ui/manifest.json`
- `assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__claim_button__baseline__v1.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_reward_overlay__live_capture__emulator_5556__after_day7_claim_tap_2026_04_22.png`
- `src/roxauto/vision/validation.py`
- `src/roxauto/tasks/foundations/asset_inventory.json`
- `docs/vision/README.md`
- `docs/vision/claim_rewards_live/README.md`
- `docs/handoffs/vision-claim-rewards-live-captures.md`
- `tests/vision/test_repository.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`

Contract changes in this run:

- `daily_ui.claim_reward` is now truthfully promoted from `curated_stand_in` to `live_capture`.
  - primary baseline id stays `claim_button_baseline_v1`
  - canonical file path stays `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__claim_button__baseline__v1.png`
  - the underlying image is now the approved live zh-TW ROX day-7 claimable panel from `emulator-5556`
- `metadata.task_support["daily_ui.claim_rewards"].live_capture_coverage` now reflects:
  - `live_anchor_ids`:
    - `daily_ui.reward_panel`
    - `daily_ui.claim_reward`
  - `stand_in_anchor_ids`:
    - `daily_ui.reward_confirm_state`
  - `live_context_anchor_ids`:
    - none
  - `blocked_scene_ids`:
    - `reward_confirm_modal`
- `daily_ui.reward_confirm_state` remains a curated stand-in.
  - it now carries one additional live supporting capture for the post-tap reward-acquired overlay
  - this is explicitly tracked as an alternate post-tap outcome, not a modal baseline
- `catalog.json` metadata now also carries machine-readable round-8 capture inventory:
  - confirmed devices
  - landed devices
  - missing devices
- validation now also rejects claim-rewards catalog hash drift:
  - `claim_rewards_golden_sha256_mismatch`
  - `claim_rewards_supporting_capture_sha256_mismatch`
  - plus missing-`sha256` variants for both surfaces
- readiness metadata now also carries `claim_rewards_capture_inventory` in addition to `claim_rewards_live_capture_coverage`.

Current truthful live vs stand-in status:

- Live capture:
  - `daily_ui.reward_panel`
    - canonical baseline:
      - `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
    - supplemental live evidence:
      - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
      - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`
  - `daily_ui.claim_reward`
    - canonical baseline:
      - `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__claim_button__baseline__v1.png`
    - source raw capture:
      - `docs/vision/claim_rewards_live/raw/emulator-5556-after-fuli-tap-2026-04-22.png`
    - negative supporting evidence:
      - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_claimable_daily_signin__live_capture__emulator_5556__after_daily_tab_attempt_2.png`
- Curated stand-in:
  - `daily_ui.reward_confirm_state`
    - canonical baseline:
      - `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__confirm_state__baseline__v1.png`
    - supporting live evidence:
      - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_reward_confirm_modal__live_capture__emulator_5560__exit_game_prompt.png`
      - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_reward_overlay__live_capture__emulator_5556__after_day7_claim_tap_2026_04_22.png`

Four-device capture status:

- confirmed inventory on `2026-04-22`:
  - `emulator-5556`
  - `emulator-5560`
  - `127.0.0.1:5559`
  - `127.0.0.1:5563`
- landed evidence in this worktree:
  - `emulator-5556`
  - `emulator-5560`
- no approved raw assets from `127.0.0.1:5559` or `127.0.0.1:5563` landed here, so the branch records that gap explicitly instead of overstating coverage

Why `reward_confirm_state` is still blocked:

- `docs/vision/claim_rewards_live/raw/emulator-5556-after-day7-claim-tap-2026-04-22.png` is useful live provenance, but it shows a reward-acquired overlay rather than the explicit confirm-modal action surface
- no reviewed raw capture in this worktree proves the real post-claim reward confirmation modal

Flattened GUI-facing surface:

- No existing flattened key was removed or renamed.
- Expected value changes:
  - `selected_reference_kind` for `daily_ui.claim_reward` now resolves to `live_capture`
  - `reference_ids` for `daily_ui.claim_reward` now collapse to the single canonical live baseline
  - `supporting_capture_*` for `daily_ui.reward_confirm_state` now include the post-tap overlay capture
  - readiness metadata now also exposes `claim_rewards_capture_inventory`

Verification performed:

- `python -m json.tool assets/templates/daily_ui/manifest.json`
- `python -m json.tool assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `python -m unittest tests.vision.test_repository tests.vision.test_validation tests.vision.test_tooling`

Known limitations:

- `daily_ui.reward_confirm_state` still does not have an approved live zh-TW ROX confirmation-modal capture
- the round-8 program confirmed four devices, but only two currently contribute landed evidence in this branch
- `selected_region` remains the currently selected inspection overlay region; for matched checks that can still be the runtime bbox rather than the repository match window

Recommended next step:

- keep collecting approved live zh-TW ROX evidence for `reward_confirm_modal`
- if `127.0.0.1:5559` or `127.0.0.1:5563` later yield approved captures, land them as additional supporting evidence or secondary live baselines without changing the current truth contract until the images are actually reviewed
