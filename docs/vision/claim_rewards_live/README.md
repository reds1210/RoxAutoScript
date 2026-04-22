# Claim Rewards Live Capture Notes

This folder keeps the raw live screenshots reviewed for `daily_ui.claim_rewards`.

## Route A Confirm-State Audit

Machine-readable decision packet:

- `reward_confirm_state_decision_packet.json`

Current answer for dispatch:

- no, there is still no true live `reward_confirm_modal` capture
- all four reviewed devices reached a live claimable panel
- zero reviewed devices produced a like-for-like live confirm-button modal
- three reviewed devices resolved directly to a claimed/result state after the claim tap
- one reviewed device (`emulator-5556`) resolved to a live reward-acquired overlay after the claim tap

Current workspace probe:

- `adb devices` returned no visible devices during this pass, so no new screenshots were captured
- this pass strengthens the evidence packet from the existing four-device sweep instead of claiming fresh live capture work

Round-8 capture inventory:

- confirmed ADB-visible devices:
  - `emulator-5556`
  - `emulator-5560`
  - `127.0.0.1:5559`
  - `127.0.0.1:5563`
- landed evidence in the canonical vision contract:
  - `emulator-5556`
  - `emulator-5560`
  - `127.0.0.1:5559`
  - `127.0.0.1:5563`

Promoted canonical baselines:

- `raw/emulator-5556-after-daily-tab-attempt-2.png`
  - remains the canonical live `reward_panel_open` baseline at
    `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
- `raw/emulator-5556-after-fuli-tap-2026-04-22.png`
  - promoted to the canonical live `reward_panel_claimable` baseline at
    `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__claim_button__baseline__v1.png`
  - also drives the live
    `assets/templates/daily_ui/anchors/daily_claim_button.png` crop

Promoted supporting evidence:

- `raw/emulator-5556-after-day7-claim-tap-2026-04-22.png`
  - copied to
    `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_reward_overlay__live_capture__emulator_5556__after_day7_claim_tap_2026_04_22.png`
  - proves that one live day-7 claim tap resolved into a reward-acquired overlay, not the explicit confirm-modal contract
- `raw/127.0.0.1-5559-after-claim-tap.png`
  - copied to
    `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_claimed_result__live_capture__127_0_0_1_5559__after_claim_tap.png`
  - proves that the live claim tap on `127.0.0.1:5559` resolved directly into a claimed/result state without surfacing the confirm modal
- `raw/127.0.0.1-5563-after-claim-tap.png`
  - copied to
    `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_claimed_result__live_capture__127_0_0_1_5563__after_claim_tap.png`
  - proves that the live claim tap on `127.0.0.1:5563` resolved directly into a claimed/result state without surfacing the confirm modal
- `raw/emulator-5560-after-claim-tap.png`
  - copied to
    `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_claimed_result__live_capture__emulator_5560__after_claim_tap.png`
  - proves that the live claim tap on `emulator-5560` resolved directly into a claimed/result state without surfacing the confirm modal
- `raw/emulator-5560-reward-recovery-attempt-2.png`
  - copied to
    `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__wrong_reward_surface__live_capture__emulator_5560__kingdom_pass_rewards.png`
  - proves that Fu Li navigation can land on a reward-like Kingdom Pass screen that must not satisfy the daily-sign-in reward-panel success check
- earlier-round live evidence remains promoted for:
  - the secondary panel-open descriptive copy
  - the entry-context capture after the Fu Li tap
  - the non-claimable daily-sign-in panel
  - the non-reward confirmation dialog

Current truthful status:

- `daily_ui.reward_panel`: live capture
- `daily_ui.claim_reward`: live capture
- `daily_ui.reward_confirm_state`: still curated stand-in
  - four-device live post-tap evidence now exists, but every reviewed device resolves into a reward-result surface instead of the strict confirm-modal contract
  - dispatch recommendation is now `direct_result_overlay_is_valid`, while the current confirm-modal anchor remains a curated stand-in until Engine D changes the task contract

Promotion rule for this track:

- canonical baseline coverage changes only when a live capture proves the positive scene required by the anchor
- supporting live captures may document negative cases or alternate post-tap outcomes without upgrading the positive-scene contract

## 2026-04-22 Four-Device Raw Sweep

This follow-up pass used all four `adb` devices visible from this workspace:

- `127.0.0.1:5559`
- `127.0.0.1:5563`
- `emulator-5556`
- `emulator-5560`

Priority-scene outcome from this pass:

- `reward_panel_claimable`
  - clean positive raw evidence exists on three additional devices:
    - `raw/127.0.0.1-5559-after-daily-signin.png`
    - `raw/127.0.0.1-5563-after-daily-signin-tab.png`
    - `raw/emulator-5560-after-daily-signin-attempt.png`
  - raw-evidence discovery is no longer blocked
  - canonical promotion still requires an explicit manifest/catalog decision
- `reward_confirm_modal`
  - still no like-for-like live positive raw for the current confirm-button modal contract
  - `127.0.0.1:5559`, `127.0.0.1:5563`, and `emulator-5560` all go straight from a tappable claim button to a claimed/result state
  - `emulator-5556` shows a post-claim reward-result overlay instead of the curated confirm-modal shape

Reviewed raw evidence kept from this pass:

### `127.0.0.1:5559`

- `raw/127.0.0.1-5559-current.png`
  - purpose: town-screen provenance before navigation
  - classification: negative / provenance for both priority scenes
- `raw/127.0.0.1-5559-after-tap1.png`
  - purpose: first mistap after starting navigation
  - classification: negative; transient off-path capture
- `raw/127.0.0.1-5559-blackcheck.png`
  - purpose: confirms the mistap opened Facebook/Chrome rather than rewards UI
  - classification: negative for both priority scenes
- `raw/127.0.0.1-5559-return-game.png`
  - purpose: provenance after backing out of the browser and returning to ROX
  - classification: negative / provenance for both priority scenes
- `raw/127.0.0.1-5559-after-tap2.png`
  - purpose: launcher-menu state with the rewards entry exposed
  - classification: negative / navigation provenance
- `raw/127.0.0.1-5559-after-fuli.png`
  - purpose: reward hub/map after entering welfare, before switching to daily sign-in
  - classification: negative for `reward_panel_claimable`
- `raw/127.0.0.1-5559-after-daily-signin.png`
  - purpose: daily-sign-in panel with an enabled claim button
  - classification: positive for `reward_panel_claimable`, negative for `reward_confirm_modal`
- `raw/127.0.0.1-5559-after-claim-tap.png`
  - purpose: immediate post-tap state on the same account
  - classification: negative for `reward_confirm_modal`; the UI flips directly to a claimed/result state

### `127.0.0.1:5563`

- `raw/127.0.0.1-5563-after-welfare.png`
  - purpose: on-device launcher/menu provenance before landing on the sign-in panel
  - classification: negative / navigation provenance
- `raw/127.0.0.1-5563-after-daily-signin-tab.png`
  - purpose: daily-sign-in panel with an enabled claim button
  - classification: positive for `reward_panel_claimable`, negative for `reward_confirm_modal`
- `raw/127.0.0.1-5563-after-claim-tap.png`
  - purpose: immediate post-tap state on the same account
  - classification: negative for `reward_confirm_modal`; no confirm modal appears before the button resolves to a claimed/result state

### `emulator-5556`

- `raw/emulator-5556-current-check.png`
  - purpose: post-claim reward-result overlay capture
  - classification: positive for post-claim provenance, but negative for the current `reward_confirm_modal` contract
- `raw/emulator-5556-after-modal-tap.png`
  - purpose: repeat capture of the same post-claim reward-result overlay after another tap
  - classification: positive for post-claim provenance, but negative for the current `reward_confirm_modal` contract
- `raw/emulator-5556-after-back.png`
  - purpose: reward-map state after dismissing the result overlay
  - classification: negative / provenance for both priority scenes in the current contract

### `emulator-5560`

- `raw/emulator-5560-current-live.png`
  - purpose: reward hub/map before switching to daily sign-in
  - classification: negative / navigation provenance
- `raw/emulator-5560-after-daily-signin-attempt.png`
  - purpose: daily-sign-in panel with an enabled claim button
  - classification: positive for `reward_panel_claimable`, negative for `reward_confirm_modal`
- `raw/emulator-5560-after-claim-tap.png`
  - purpose: immediate post-tap state on the same account
  - classification: negative for `reward_confirm_modal`; the UI goes straight to a claimed/result state

Current blocker state after the four-device sweep:

- raw `reward_panel_claimable` evidence is now covered by multiple live devices
- a like-for-like live `reward_confirm_modal` capture is still missing
- four-device landed evidence is now available for post-tap outcomes, but not for the strict confirm-modal scene itself
