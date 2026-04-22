# Claim Rewards Live Capture Notes

This folder keeps the raw live screenshots reviewed for `daily_ui.claim_rewards`.

Round-8 capture inventory:

- confirmed ADB-visible devices:
  - `emulator-5556`
  - `emulator-5560`
  - `127.0.0.1:5559`
  - `127.0.0.1:5563`
- landed evidence in this worktree:
  - `emulator-5556`
  - `emulator-5560`
- no approved raw assets from `127.0.0.1:5559` or `127.0.0.1:5563` landed in this branch, so the catalog keeps those devices tracked as inventory gaps instead of pretending four-device live parity already exists

Promoted canonical baselines:

- `raw/emulator-5556-after-daily-tab-attempt-2.png`
  - remains the canonical live `reward_panel_open` baseline at `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
- `raw/emulator-5556-after-fuli-tap-2026-04-22.png`
  - promoted to the canonical live `reward_panel_claimable` baseline at `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__claim_button__baseline__v1.png`
  - also drives the live `assets/templates/daily_ui/anchors/daily_claim_button.png` crop

Promoted supporting evidence:

- `raw/emulator-5556-after-day7-claim-tap-2026-04-22.png`
  - copied to `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__post_tap_reward_overlay__live_capture__emulator_5556__after_day7_claim_tap_2026_04_22.png`
  - proves that one live day-7 claim tap resolved into a reward-acquired overlay, not the explicit confirm-modal contract
- `raw/emulator-5560-reward-recovery-attempt-2.png`
  - copied to `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__wrong_reward_surface__live_capture__emulator_5560__kingdom_pass_rewards.png`
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
  - the live post-tap overlay is useful provenance, but it is not a like-for-like replacement for the expected reward confirmation modal

Promotion rule for this track:

- canonical baseline coverage changes only when a live capture proves the positive scene required by the anchor
- supporting live captures may document negative cases or alternate post-tap outcomes without upgrading the positive-scene contract

Remaining blockers:

- approved live zh-TW ROX reward-confirmation-modal capture
- additional approved captures from `127.0.0.1:5559` or `127.0.0.1:5563` if later rounds want actual four-device evidence instead of confirmed inventory only
