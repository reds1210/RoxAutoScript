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

## 2026-04-22 Four-Device Raw Sweep

Scope for this pass:

- stayed inside `daily_ui.claim_rewards`
- wrote only to:
  - `docs/vision/claim_rewards_live/raw/`
  - `docs/vision/claim_rewards_live/README.md`
  - this handoff
- did not edit `assets/templates/...`, `manifest.json`, `catalog.json`, task code, runtime code, or GUI code

Devices visible through `adb` during this pass:

- `127.0.0.1:5559`
- `127.0.0.1:5563`
- `emulator-5556`
- `emulator-5560`

New raw evidence kept from this pass:

- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-current.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-after-tap1.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-blackcheck.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-return-game.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-after-tap2.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-after-fuli.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-after-daily-signin.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5559-after-claim-tap.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5563-after-welfare.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5563-after-daily-signin-tab.png`
- `docs/vision/claim_rewards_live/raw/127.0.0.1-5563-after-claim-tap.png`
- `docs/vision/claim_rewards_live/raw/emulator-5556-current-check.png`
- `docs/vision/claim_rewards_live/raw/emulator-5556-after-modal-tap.png`
- `docs/vision/claim_rewards_live/raw/emulator-5556-after-back.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-current-live.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-after-daily-signin-attempt.png`
- `docs/vision/claim_rewards_live/raw/emulator-5560-after-claim-tap.png`

Device findings:

- `127.0.0.1:5559`
  - `127.0.0.1-5559-current.png`
    - purpose: town-screen provenance before navigation
    - classification: negative / provenance
  - `127.0.0.1-5559-after-tap1.png`
    - purpose: first mistap while trying to reach rewards
    - classification: negative
  - `127.0.0.1-5559-blackcheck.png`
    - purpose: confirms the mistap opened Facebook/Chrome instead of rewards UI
    - classification: negative
  - `127.0.0.1-5559-return-game.png`
    - purpose: provenance after backing out of the browser
    - classification: negative / provenance
  - `127.0.0.1-5559-after-tap2.png`
    - purpose: launcher-menu state with the `福利` entry available
    - classification: negative / navigation provenance
  - `127.0.0.1-5559-after-fuli.png`
    - purpose: reward hub/map before switching to `每日簽到`
    - classification: negative for `reward_panel_claimable`
  - `127.0.0.1-5559-after-daily-signin.png`
    - purpose: daily-sign-in panel with an enabled green `簽到` button
    - classification: positive for `reward_panel_claimable`
  - `127.0.0.1-5559-after-claim-tap.png`
    - purpose: immediate post-tap state on the same account
    - classification: negative for `reward_confirm_modal`; the UI resolves directly to `已簽到`

- `127.0.0.1:5563`
  - `127.0.0.1-5563-after-welfare.png`
    - purpose: launcher/menu provenance before landing on `每日簽到`
    - classification: negative / navigation provenance
  - `127.0.0.1-5563-after-daily-signin-tab.png`
    - purpose: daily-sign-in panel with an enabled green `簽到` button
    - classification: positive for `reward_panel_claimable`
  - `127.0.0.1-5563-after-claim-tap.png`
    - purpose: immediate post-tap state on the same account
    - classification: negative for `reward_confirm_modal`; no confirm modal appears before the UI flips to `已簽到`

- `emulator-5556`
  - `emulator-5556-current-check.png`
    - purpose: post-claim reward-result overlay with `獲得獎勵 / 點擊螢幕繼續`
    - classification: positive for post-claim provenance, but negative for the current `reward_confirm_modal` contract
  - `emulator-5556-after-modal-tap.png`
    - purpose: repeat capture of the same post-claim reward-result overlay after another tap
    - classification: positive for post-claim provenance, but negative for the current `reward_confirm_modal` contract
  - `emulator-5556-after-back.png`
    - purpose: reward-map state after dismissing the result overlay
    - classification: negative / provenance for the current priority scenes

- `emulator-5560`
  - `emulator-5560-current-live.png`
    - purpose: reward hub/map before switching to `每日簽到`
    - classification: negative / navigation provenance
  - `emulator-5560-after-daily-signin-attempt.png`
    - purpose: daily-sign-in panel with an enabled green `簽到` button
    - classification: positive for `reward_panel_claimable`
  - `emulator-5560-after-claim-tap.png`
    - purpose: immediate post-tap state on the same account
    - classification: negative for `reward_confirm_modal`; the UI resolves directly to `已簽到`

Outcome from this pass:

- closed the raw-evidence gap for `reward_panel_claimable` with clean positive live captures on:
  - `127.0.0.1:5559`
  - `127.0.0.1:5563`
  - `emulator-5560`
- confirmed again that the current live accounts do not surface a like-for-like `reward_confirm_modal`
  - `127.0.0.1:5559`, `127.0.0.1:5563`, and `emulator-5560` go straight from `簽到` to `已簽到`
  - `emulator-5556` shows a reward-result overlay instead of the curated confirm-button modal
- kept all changes inside raw evidence and documentation only

Updated blockers after the four-device sweep:

- `reward_panel_claimable`
  - raw live evidence is now available on multiple devices
  - the remaining work is only canonical promotion / catalog selection, not raw capture discovery
- `reward_confirm_modal`
  - still blocked for canonical live replacement
  - no device in this pass produced the current confirm-button modal shape

Recommended next step after the four-device sweep:

- have Engine C and D choose one of the clean daily-sign-in captures as the live raw source for `reward_panel_claimable`:
  - `127.0.0.1-5559-after-daily-signin.png`
  - `127.0.0.1-5563-after-daily-signin-tab.png`
  - `emulator-5560-after-daily-signin-attempt.png`
- keep `emulator-5556-current-check.png` and `emulator-5556-after-modal-tap.png` as supporting post-claim overlay evidence only unless the confirm-state contract is broadened beyond the explicit confirm-button modal
- continue capture attempts for `reward_confirm_modal` on another account/day-state that still presents a real confirmation dialog before the claim resolves

## 2026-04-22 Route A Confirm-State Audit Packet

Track:

- `codex/claim-rewards-goldens`

Scope:

- stayed inside `daily_ui.claim_rewards`
- wrote only to:
  - `docs/vision/claim_rewards_live/reward_confirm_state_decision_packet.json`
  - `docs/vision/claim_rewards_live/README.md`
  - `docs/handoffs/claim-rewards-goldens.md`
- did not edit runtime, task, GUI, manifest, catalog, or canonical asset files

Files changed:

- `docs/vision/claim_rewards_live/reward_confirm_state_decision_packet.json`
- `docs/vision/claim_rewards_live/README.md`
- `docs/handoffs/claim-rewards-goldens.md`

Public APIs added or changed:

- no Python API changed
- added one machine-readable evidence packet for dispatch/vision review:
  - `docs/vision/claim_rewards_live/reward_confirm_state_decision_packet.json`

Contract changes:

- no manifest/catalog contract changed in this pass
- evidence conclusion is now written down explicitly:
  - reviewed devices with a true live `reward_confirm_modal`: `0`
  - reviewed devices with a direct post-tap claimed/result state: `3`
  - reviewed devices with a post-tap reward overlay: `1`
- the packet also records that the current workspace probe saw no `adb` devices, so this pass was an evidence audit only

Assumptions:

- the four-device sweep recorded earlier in this handoff remains the authoritative raw evidence set for Route A
- `emulator-5556-after-day7-claim-tap-2026-04-22.png` is still useful live post-tap evidence, but not a like-for-like modal replacement
- `127.0.0.1:5559`, `127.0.0.1:5563`, and `emulator-5560` direct-to-result captures remain valid evidence that the current live accounts often skip the explicit modal

Verification performed:

- `adb devices`
- `python -m json.tool docs/vision/claim_rewards_live/reward_confirm_state_decision_packet.json`

Known limitations:

- no new live screenshots were captured in this pass because `adb devices` returned no visible devices from this workspace
- the new packet summarizes evidence; it does not itself broaden the task or vision contract
- the unresolved product question still belongs to dispatch / Engine C:
  - keep `strict_confirm_modal_only`
  - or broaden to treat direct result overlays as valid post-tap truth

Blockers:

- there is still no reviewed live confirm-button modal capture for `daily_ui.reward_confirm_state`
- current workspace device visibility prevented a fresh capture attempt during this pass

Recommended next step:

- let Engine C consume `docs/vision/claim_rewards_live/reward_confirm_state_decision_packet.json` as the evidence-side answer for Route A
- keep the answer to "do we have a true live confirm-modal capture yet?" as `no`
- only attempt canonical live replacement after a reachable account/day-state exposes the explicit confirmation action surface before claim resolution
