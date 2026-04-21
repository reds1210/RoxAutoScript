# Handoff: Vision Claim Rewards Live Captures

Track:

- `codex/vision-claim-rewards-live-captures`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Stayed inside Engine C ownership for code, templates, vision docs, and tests; no task/runtime/app directories were edited.
- Promoted the `daily_ui.reward_panel` baseline from a screenshot-style stand-in to a live zh-TW ROX capture while keeping the three claim-rewards anchor ids stable.
- Kept `daily_ui.claim_reward` and `daily_ui.reward_confirm_state` as curated stand-ins, but made the readiness and failure surfaces explicit about that difference.

Files changed:

- `src/roxauto/vision/models.py`
- `src/roxauto/vision/tooling.py`
- `src/roxauto/vision/validation.py`
- `src/roxauto/vision/__init__.py`
- `assets/templates/daily_ui/anchors/daily_reward_panel.png`
- `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
- `assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`
- `assets/templates/daily_ui/manifest.json`
- `docs/vision/README.md`
- `docs/vision/claim_rewards_live/raw/*`
- `tests/vision/test_repository.py`
- `tests/vision/test_serialization.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/vision-claim-rewards-live-captures.md`

Public APIs added or changed:

- Added `AnchorAssetProvenanceKind`.
- Added `AnchorAssetProvenance`.
- `AnchorCurationProfile` now exposes:
  - `provenance`
  - `provenance_kind`
  - `provenance_summary`
  - `is_live_capture`
- `TemplateDependencyReadiness` now exposes:
  - `provenance_kind`
  - `provenance_summary`
- `AnchorInspectionRow`, `MatchInspectorState`, `ClaimRewardsCheckState`, and `FailureInspectorState` now expose:
  - `provenance_kind`
  - `provenance_summary`
- `ClaimRewardsInspectorState` now exposes:
  - `selected_provenance_kind`
  - `selected_provenance_summary`

Contract changes:

- `daily_ui.claim_rewards` anchors now require `metadata.curation.provenance` in addition to the existing curation fields.
- Validation now rejects a claim-rewards anchor when `metadata.curation.provenance` is missing.
- Validation now rejects a curated anchor when its provenance still claims `placeholder`.
- Readiness now distinguishes:
  - `ready` + `live_capture`
  - `ready` + `curated_stand_in`
  - `placeholder`
  - `inventory_mismatch`
- `metadata.task_support.daily_ui.claim_rewards.golden_catalog_path` now points at `goldens/claim_rewards/catalog.json`, and each curated anchor maps back to a `golden_id` entry in that catalog.
- The shipped claim-rewards anchors are now explicitly marked as:
  - `daily_ui.reward_panel`: `provenance.kind = live_capture`, `locale = zh-TW`, `source = mumu_emulator_5556`
  - `daily_ui.claim_reward`: `provenance.kind = curated_stand_in`, `locale = zh-TW`, `source = repo_curated_baseline`
  - `daily_ui.reward_confirm_state`: `provenance.kind = curated_stand_in`, `locale = zh-TW`, `source = repo_curated_baseline`
- Failure/match/check summaries now carry explicit provenance context so GUI does not need to reopen manifest metadata to explain what kind of baseline was used.

What is live vs stand-in now:

- Live capture:
  - `daily_ui.reward_panel`
  - primary baseline: `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
  - supplemental captures:
    - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
    - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`
- Curated stand-in:
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- Raw supporting screenshots copied for traceability:
  - `docs/vision/claim_rewards_live/raw/`

Assumptions:

- The available live capture evidence is sufficient to promote the panel-open baseline only.
- The claimable-button and confirm-modal baselines still do not have approved live zh-TW ROX captures in this worktree.
- When those captures become available later, the intended upgrade path is to change provenance from `curated_stand_in` to `live_capture` without redesigning the surrounding readiness or failure surfaces.

Verification performed:

- `python -m unittest tests.vision.test_repository`
- `python -m unittest tests.vision.test_serialization`
- `python -m unittest tests.vision.test_validation`
- `python -m unittest tests.vision.test_tooling`
- `python -m unittest tests.vision.test_services`
- `python -m unittest discover -s tests/vision -t .`
- `python -m unittest discover -s tests -t .`

Known limitations:

- Only the panel-open baseline has been promoted to a live capture in this pass.
- `failure_explanation` now warns when a claim-rewards baseline is still a curated stand-in, which currently still applies to the claim-button and confirm-state checks.
- Engine D's asset inventory remains conservative, so the existing `daily_ui.claim_reward` inventory mismatch is still expected until that track intentionally updates its inventory policy.

Blockers:

- None inside Engine C ownership.
- Promoting the remaining anchors to `live_capture` still depends on approved live zh-TW ROX screenshots for:
  - `reward_panel_claimable`
  - `reward_confirm_modal`

Recommended next step:

- Capture approved live zh-TW ROX screenshots for `reward_panel_claimable` and `reward_confirm_modal` and replace the current screenshot-style baselines.
- After those assets land, update `metadata.curation.provenance` for those two anchors from `curated_stand_in` to `live_capture` and keep the same flattened readiness/failure surface.
- Engine B can optionally surface `selected_provenance_kind` / `selected_provenance_summary` in the claim-rewards diagnostics pane, but no new manifest parsing should be required.
