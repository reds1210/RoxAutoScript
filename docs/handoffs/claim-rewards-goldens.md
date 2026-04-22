# Claim Rewards Goldens Handoff

Track:

- `codex/claim-rewards-goldens`

Scope:

- advanced only `daily_ui.claim_rewards` inside Engine E ownership
- kept changes inside:
  - `assets/templates/`
  - `tests/tasks/fixtures/`
  - `docs/vision/`
  - `docs/handoffs/`
- did not touch task runtime, GUI, core runtime, guild check-in, Odin logic, or a second task

Files changed:

- `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_claimable_daily_signin__live_capture__emulator_5556__after_daily_tab_attempt_2.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__wrong_reward_surface__live_capture__emulator_5560__kingdom_pass_rewards.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_reward_confirm_modal__live_capture__emulator_5560__exit_game_prompt.png`
- `assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `assets/templates/daily_ui/manifest.json`
- `tests/tasks/fixtures/golden_examples.json`
- `docs/vision/README.md`
- `docs/vision/claim_rewards_live/README.md`
- `docs/vision/claim_rewards_live/raw/*`
- `docs/handoffs/claim-rewards-goldens.md`

Public APIs added or changed:

- no Python API surface changed
- the template manifest for `daily_ui.claim_rewards` now carries clearer provenance metadata for Engine C and D consumption:
  - `metadata.task_support["daily_ui.claim_rewards"].live_capture_coverage`
  - `metadata.curation.metadata.golden_catalog_path`
  - `metadata.curation.metadata.golden_id`
  - `metadata.curation.metadata.source_kind`
  - `metadata.curation.metadata.live_capture`
  - `metadata.curation.metadata.replacement_target`
  - `metadata.curation.metadata.proof_summary`
  - `metadata.curation.metadata.failure_case`

Contract changes:

- promoted `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png` to a live zh-TW ROX panel-open screenshot while preserving the existing baseline filename and `golden_id`
- added supplemental live captures under `assets/templates/daily_ui/goldens/claim_rewards/live/`:
  - `daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
  - `daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`
- added negative-case live captures under `assets/templates/daily_ui/goldens/claim_rewards/live/` without changing canonical baseline coverage:
  - `daily_ui_claim_rewards__non_claimable_daily_signin__live_capture__emulator_5556__after_daily_tab_attempt_2.png`
  - `daily_ui_claim_rewards__wrong_reward_surface__live_capture__emulator_5560__kingdom_pass_rewards.png`
  - `daily_ui_claim_rewards__non_reward_confirm_modal__live_capture__emulator_5560__exit_game_prompt.png`
- expanded `catalog.json` so every shipped claim-rewards image now states:
  - which anchor it supports
  - which step it proves
  - which failure case it explains
  - whether it is a canonical live capture or a curated stand-in
- expanded `catalog.json` again so negative-case live captures are first-class supporting evidence for:
  - claim button absent or already consumed after the panel opens
  - landing on Kingdom Pass rewards instead of daily sign-in
  - hitting a generic confirmation dialog instead of the reward confirm modal
- `tests/tasks/fixtures/golden_examples.json` stays aligned with the shipped baseline naming examples and no longer points at a nonexistent confirm-modal filename

Capture coverage after this round:

- `reward panel open`
  - canonical live golden available
  - anchor: `daily_ui.reward_panel`
  - step: `open_reward_panel`
  - failure focus: panel did not open or wrong reward surface
- `reward panel claimable`
  - curated stand-in only
  - anchor: `daily_ui.claim_reward`
  - step: `verify_claim_affordance`
  - failure focus: claim button missing or not tappable
  - supporting live negative case available for an already-signed daily-sign-in panel with greyed controls
- `reward confirmation modal`
  - curated stand-in only
  - anchor: `daily_ui.reward_confirm_state`
  - step: `verify_claim_affordance`
  - failure focus: confirm modal missing after claim tap
  - supporting live negative case available for a generic non-reward confirmation dialog

Assumptions:

- the live panel-open captures taken on emulator `5560` and `5556` are valid zh-TW ROX evidence for this task
- the negative-case live captures from emulator `5556` and `5560` are useful debugging evidence even though they do not satisfy the positive-scene baseline contracts
- no approved live claimable-panel or confirm-modal state was reachable on the available accounts during this round
- downstream readers can consume the catalog and manifest metadata without needing task/runtime changes

Verification performed:

- `python -m unittest tests.tasks.test_inventory_fixtures`
- `python -m unittest discover -s tests/vision -t .`

Known limitations:

- only the panel-open scene is currently backed by a canonical live golden
- the newly added live captures for claim-button and confirm-state diagnostics are negative cases only; they must not be treated as positive baselines
- the raw capture folder contains exploratory claim-rewards screenshots for traceability; not every raw PNG is meant to be referenced as a canonical golden
- task-foundation inventory/readiness files remain owned by Engine D, so this branch does not change asset status policy there

Blockers:

- approved live zh-TW claimable-panel capture is still missing
- approved live zh-TW reward-confirmation-modal capture is still missing

Recommended next step:

- capture approved live zh-TW screenshots for the claimable panel and the confirmation modal, then replace `daily_ui_claim_rewards__claim_button__baseline__v1.png` and `daily_ui_claim_rewards__confirm_state__baseline__v1.png` in place so Engine C and D can keep the same manifest/catalog references while retaining the new negative-case supporting evidence

## 2026-04-22 Follow-Up Live Pass

Scope for this pass:

- stayed inside `daily_ui.claim_rewards`
- wrote only to `docs/vision/claim_rewards_live/raw/` and this handoff
- did not edit `manifest.json`, `catalog.json`, task code, runtime code, or GUI code

Devices visible through `adb` during this pass:

- `emulator-5556`
- `emulator-5560`
- no additional emulator instances were exposed through `adb devices` during this run even though the broader environment was described as having four running emulators

Existing raw/live evidence explicitly checked before new taps:

- `docs/vision/claim_rewards_live/raw/emulator-5556-after-daily-tab-attempt-2.png`
- `docs/vision/claim_rewards_live/raw/emulator-5556-daily-signin.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-daily-signin.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-daily-signin-attempt-2.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_claimable_daily_signin__live_capture__emulator_5556__after_daily_tab_attempt_2.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__non_reward_confirm_modal__live_capture__emulator_5560__exit_game_prompt.png`

New raw evidence captured on 2026-04-22:

- `docs/vision/claim_rewards_live/raw/emulator-5556-current-2026-04-22.png`
- `docs/vision/claim_rewards_live/raw/emulator-5556-after-fuli-tap-2026-04-22.png`
- `docs/vision/claim_rewards_live/raw/emulator-5556-after-day7-claim-tap-2026-04-22.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-current-2026-04-22.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-after-fuli-tap-2026-04-22.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-after-fuli-retry-2026-04-22.png`

Device findings:

- `emulator-5556-current-2026-04-22.png`
  - captured the account in town with the `福利` entry visible and tappable from the top-right icon cluster
- `emulator-5556-after-fuli-tap-2026-04-22.png`
  - opened `福利 > 每日簽到`
  - showed a live orange bottom-right reward button labeled `第7天饋贈`
  - this is additional positive live zh-TW ROX evidence for a claimable reward surface because the claim affordance is present and enabled on a real device capture
  - the scene does not match the earlier calendar-grid-style non-claimable captures; it is a different live `每日簽到` presentation with a live claim affordance
- `emulator-5556-after-day7-claim-tap-2026-04-22.png`
  - was captured immediately after tapping the orange `第7天饋贈` button
  - showed a live reward-result overlay with `獲得獎勵` and the claimed item row
  - proves the pre-tap orange button on `emulator-5556-after-fuli-tap-2026-04-22.png` was a real claimable reward affordance
  - does not cleanly prove the current `reward_confirm_modal` contract by itself because the overlay is a post-claim reward result with `點擊螢幕繼續`, not the same explicit confirm-button modal shape represented by `daily_ui_claim_rewards__confirm_state__baseline__v1.png`
- `emulator-5560-current-2026-04-22.png`
  - captured the account in town before navigation
- `emulator-5560-after-fuli-tap-2026-04-22.png`
  - recorded the first 2026-04-22 tap attempt on the `福利` icon
  - did not advance away from the town surface, so it is retained only as provenance for the failed first navigation attempt on this device
- `emulator-5560-after-fuli-retry-2026-04-22.png`
  - opened the same `福利 > 每日簽到` map-style reward surface
  - did not expose any bottom-right claim button during this pass
  - confirms account-state variance across reachable live devices even when navigation lands on the same overall reward page

Outcome from this pass:

- obtained additional positive live zh-TW ROX evidence for `reward_panel_claimable` in raw form on `emulator-5556`
- obtained positive live post-tap reward-result evidence on `emulator-5556`, but not a clean like-for-like replacement for the current curated `reward_confirm_modal` baseline
- did not promote any new raw PNG into `assets/templates/.../live/` during this pass because manifest/catalog ownership was out of scope and the confirm-state interpretation still needs a contract decision

Updated blockers after this pass:

- `reward_panel_claimable`
  - raw positive live evidence now exists, but Engine C and D should confirm whether the live `每日簽到` day-7 reward map with the `第7天饋贈` button is in-contract for the existing `reward_panel_claimable` scene before any canonical promotion
- `reward_confirm_modal`
  - still blocked for canonical live replacement
  - the only new positive post-tap evidence is a reward-result overlay, not an obvious match for the current confirm-button modal baseline
- environment
  - only `emulator-5556` and `emulator-5560` were available through `adb` during this run, so no broader device sweep was possible from this worktree

Recommended next step after this pass:

- have Engine C and D review `emulator-5556-after-fuli-tap-2026-04-22.png` as a candidate live `reward_panel_claimable` source image and decide whether the claimable scene contract allows this live day-7 reward presentation
- treat `emulator-5556-after-day7-claim-tap-2026-04-22.png` as supporting post-tap evidence only unless the confirm-state contract is broadened to include reward-result overlays
- if the current confirm-state contract must remain an explicit confirm-button modal, continue capture attempts on another account/day-state that still presents the pre-claim confirmation dialog rather than an immediate reward-result overlay
