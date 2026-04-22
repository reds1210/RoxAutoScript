# Claim Rewards Live Capture Notes

This folder keeps the raw live screenshots reviewed for `daily_ui.claim_rewards`.

Promoted supporting evidence:

- `raw/emulator-5556-after-daily-tab-attempt-2.png`
  - copied to `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_claimable_daily_signin__live_capture__emulator_5556__after_daily_tab_attempt_2.png`
  - proves that the daily sign-in panel can be open while the bottom controls remain greyed and non-claimable
- `raw/emulator-5560-reward-recovery-attempt-2.png`
  - copied to `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__wrong_reward_surface__live_capture__emulator_5560__kingdom_pass_rewards.png`
  - proves that Fu Li navigation can land on a reward-like Kingdom Pass screen that must not satisfy the daily sign-in reward-panel success check
- `raw/emulator-5560-daily-signin.png`
  - copied to `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_reward_confirm_modal__live_capture__emulator_5560__exit_game_prompt.png`
  - proves that a generic confirmation dialog can appear during reward exploration and must not be treated as the reward claim confirmation modal

What was intentionally not promoted to canonical baseline:

- a newer raw capture from Engine E, `raw/emulator-5556-after-fuli-tap-2026-04-22.png`, does show a plausible live claimable day-7 panel for `daily_ui.claim_reward`, but it was not promoted in this run because the canonical template/golden asset import itself has not landed in this worktree
- no reviewed raw capture shows the real post-claim reward confirmation modal for `daily_ui.reward_confirm_state`

Additional reviewed evidence not promoted in this run:

- `raw/emulator-5556-after-day7-claim-tap-2026-04-22.png`
  - useful as post-tap overlay provenance for the claim flow
  - not a like-for-like replacement for `daily_ui.reward_confirm_state`, because it shows the reward-acquired overlay rather than the expected confirm-button modal state

Promotion rule for this track:

- canonical baseline coverage changes only when a live capture proves the positive scene required by the anchor
- negative-case live captures may be promoted into `assets/templates/daily_ui/goldens/claim_rewards/live/` and `catalog.json` to document failure surfaces without changing the positive-scene coverage state

Remaining blockers:

- approved live zh-TW claimable-panel capture
- approved live zh-TW reward-confirmation-modal capture

## 2026-04-22 Four-Device Raw Sweep

This follow-up pass used all four `adb` devices visible from this worktree:

- `127.0.0.1:5559`
- `127.0.0.1:5563`
- `emulator-5556`
- `emulator-5560`

Priority-scene outcome from this pass:

- `reward_panel_claimable`
  - clean positive raw evidence now exists on three devices:
    - `raw/127.0.0.1-5559-after-daily-signin.png`
    - `raw/127.0.0.1-5563-after-daily-signin-tab.png`
    - `raw/emulator-5560-after-daily-signin-attempt.png`
  - this raw-evidence gap is no longer blocked; canonical promotion still needs a later manifest/catalog decision
- `reward_confirm_modal`
  - still no like-for-like live positive raw for the current confirm-button modal contract
  - `127.0.0.1:5559`, `127.0.0.1:5563`, and `emulator-5560` all went straight from a tappable `簽到` button to an `已簽到` state
  - `emulator-5556` showed a post-claim `獲得獎勵 / 點擊螢幕繼續` overlay instead of the curated confirm-modal shape

Reviewed raw evidence kept from this pass:

### `127.0.0.1:5559`

- `raw/127.0.0.1-5559-current.png`
  - purpose: town-screen provenance before navigation
  - classification: negative / provenance for both priority scenes
- `raw/127.0.0.1-5559-after-tap1.png`
  - purpose: first mistap after starting navigation
  - classification: negative; transient off-path capture
- `raw/127.0.0.1-5559-blackcheck.png`
  - purpose: confirm that the mistap opened Facebook/Chrome rather than rewards UI
  - classification: negative for both priority scenes
- `raw/127.0.0.1-5559-return-game.png`
  - purpose: provenance after backing out of the browser and returning to ROX
  - classification: negative / provenance for both priority scenes
- `raw/127.0.0.1-5559-after-tap2.png`
  - purpose: launcher-menu state with the `福利` entry exposed
  - classification: negative / navigation provenance
- `raw/127.0.0.1-5559-after-fuli.png`
  - purpose: reward hub/map after entering `福利`, before switching to `每日簽到`
  - classification: negative for `reward_panel_claimable`
- `raw/127.0.0.1-5559-after-daily-signin.png`
  - purpose: daily-sign-in panel with an enabled green `簽到` button
  - classification: positive for `reward_panel_claimable`, negative for `reward_confirm_modal`
- `raw/127.0.0.1-5559-after-claim-tap.png`
  - purpose: immediate post-tap state on the same account
  - classification: negative for `reward_confirm_modal`; the UI flips directly to `已簽到`

### `127.0.0.1:5563`

- `raw/127.0.0.1-5563-after-welfare.png`
  - purpose: on-device launcher/menu provenance before landing on the sign-in panel
  - classification: negative / navigation provenance
- `raw/127.0.0.1-5563-after-daily-signin-tab.png`
  - purpose: daily-sign-in panel with an enabled green `簽到` button
  - classification: positive for `reward_panel_claimable`, negative for `reward_confirm_modal`
- `raw/127.0.0.1-5563-after-claim-tap.png`
  - purpose: immediate post-tap state on the same account
  - classification: negative for `reward_confirm_modal`; no confirm modal appears before the button resolves to `已簽到`

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
  - purpose: reward hub/map before switching to `每日簽到`
  - classification: negative / navigation provenance
- `raw/emulator-5560-after-daily-signin-attempt.png`
  - purpose: daily-sign-in panel with an enabled green `簽到` button
  - classification: positive for `reward_panel_claimable`, negative for `reward_confirm_modal`
- `raw/emulator-5560-after-claim-tap.png`
  - purpose: immediate post-tap state on the same account
  - classification: negative for `reward_confirm_modal`; the UI goes straight to `已簽到`

Current blocker state after the four-device sweep:

- raw `reward_panel_claimable` evidence is now covered by multiple live devices
- a like-for-like live `reward_confirm_modal` capture is still missing
