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
