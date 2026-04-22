# Round 8: Claim Rewards Four-Device Capture Promotion

## Goal

Keep scope locked to `daily_ui.claim_rewards` and use the now-confirmed four ADB-visible emulator targets to close the remaining live-capture gaps.

This round is not about adding a second task. It is about turning the current mixed `live_capture + curated_stand_in` state into a more trustworthy production baseline by:

- promoting a real positive `reward_panel_claimable` scene if it proves in-contract
- continuing the search for a true live `reward_confirm_modal`
- keeping provenance machine-readable from goldens through vision, tasks, runtime, and GUI

## Confirmed Device Inventory

As of `2026-04-22`, the local environment has four ADB-visible devices:

- `emulator-5556`
- `emulator-5560`
- `127.0.0.1:5559`
- `127.0.0.1:5563`

Operational rule:

- every raw/live capture added this round must record the exact ADB serial
- if a worker can also identify the MuMu window title for that serial, include it in the handoff
- do not assume the TCP serials are interchangeable with the `emulator-*` serials

## Starting Point

Current `main` already has:

- a zh-TW MVP GUI focused on `claim rewards`
- runtime-owned active, last, and last-failed task telemetry
- task-side `claim_rewards.v2` structured outcomes and runtime seam metadata
- one canonical live `reward_panel` baseline
- curated-stand-in baselines for:
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- supporting negative-case evidence for wrong reward surfaces, non-claimable states, and non-reward confirm dialogs

Current strongest new evidence:

- `docs/vision/claim_rewards_live/raw/emulator-5556-after-fuli-tap-2026-04-22.png`
  - strongest current candidate for a positive live `reward_panel_claimable` scene
- `docs/vision/claim_rewards_live/raw/emulator-5556-after-day7-claim-tap-2026-04-22.png`
  - useful supporting post-tap evidence
  - not yet a drop-in replacement for the current explicit confirm-modal contract

## Definition Of Done

Round 8 is done when:

- `daily_ui.claim_reward` is either honestly promoted to `live_capture` or explicitly remains `curated_stand_in` with documented reasons
- `daily_ui.reward_confirm_state` either gains a true live confirm-modal baseline or remains explicitly blocked with better supporting evidence
- provenance remains machine-readable all the way through:
  - goldens
  - manifest metadata
  - vision readiness / failure / inspection payloads
  - task foundations readiness
  - runtime / GUI consumption surfaces
- four-device capture work is documented clearly enough that later rounds can reproduce or extend it without chat history

## Device Role Plan

Use the four visible devices as fixed roles instead of collecting random screenshots from all of them.

### Device 1: `emulator-5556`

Primary role:

- positive `reward_panel_claimable` candidate source

Expected targets:

- `reward_panel_open`
- `reward_panel_claimable`
- post-tap reward-result evidence

### Device 2: `emulator-5560`

Primary role:

- negative-case and wrong-surface evidence

Expected targets:

- non-claimable daily-signin state
- wrong reward surface
- generic non-reward confirm dialog

### Device 3: `127.0.0.1:5559`

Primary role:

- additional positive-path capture attempt

Expected targets:

- alternate `reward_panel_claimable`
- first viable true `reward_confirm_modal`, if that account/day state still exposes it

### Device 4: `127.0.0.1:5563`

Primary role:

- state-variance and fallback positive-path capture attempt

Expected targets:

- second account/day-state confirmation for claimable panel
- alternate reward-result or confirm-modal evidence

## Thread Lineup

### Engine E

Focus:

- lead four-device screenshot collection
- keep raw evidence, naming, and provenance disciplined
- only promote when the evidence is strong enough for C to consume honestly

Success:

- new raw/live evidence exists for claimable and, ideally, confirm-modal scenes

### Engine C

Focus:

- promote approved captures into goldens / manifest / validation / readiness
- keep flatten GUI-facing provenance and failure surfaces stable

Success:

- claim-rewards vision contract tells the truth about what is live, what is stand-in, and why

### Engine D

Focus:

- refresh foundations inventory / asset inventory / readiness only when C changes asset status
- keep task-owned runtime seam and structured result keys stable

Success:

- task foundations reflect the real asset state without message parsing or hidden assumptions

### Engine A

Focus:

- only follow through if new capture promotion changes the runtime-owned focus or failure surfaces enough to justify a runtime update
- otherwise verify and stay quiet

Success:

- runtime remains the trusted source of execution and failure state

### Engine B

Focus:

- only follow through if the new provenance surfaces materially improve operator guidance
- otherwise verify and stay quiet

Success:

- GUI keeps showing trustworthy operator guidance without inventing state

## Recommended Start Order

1. `Engine E`
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

## Recommended Merge Order

1. `Engine E`
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

## Out Of Scope

- any second task
- guild check-in
- Odin
- free navigation
- combat logic
- broad OCR unrelated to `claim_rewards`
