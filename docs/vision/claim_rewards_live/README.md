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

- no reviewed raw capture shows an enabled live claim button for `daily_ui.claim_reward`
- no reviewed raw capture shows the real post-claim reward confirmation modal for `daily_ui.reward_confirm_state`

Promotion rule for this track:

- canonical baseline coverage changes only when a live capture proves the positive scene required by the anchor
- negative-case live captures may be promoted into `assets/templates/daily_ui/goldens/claim_rewards/live/` and `catalog.json` to document failure surfaces without changing the positive-scene coverage state

Remaining blockers:

- approved live zh-TW claimable-panel capture
- approved live zh-TW reward-confirmation-modal capture
