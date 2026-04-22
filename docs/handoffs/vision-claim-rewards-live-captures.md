# Handoff: Vision Claim Rewards Live Captures

Track:

- `codex/vision-claim-rewards-live-captures`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Stayed inside Engine C ownership for vision contracts, template metadata, supporting raw captures, and tests.
- Did not edit `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/tasks/`, or `src/roxauto/app/`.
- Left the three anchor ids stable:
  - `daily_ui.reward_panel`
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`

Files changed:

- `src/roxauto/vision/models.py`
- `src/roxauto/vision/repository.py`
- `src/roxauto/vision/tooling.py`
- `src/roxauto/vision/validation.py`
- `src/roxauto/vision/__init__.py`
- `assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `docs/vision/README.md`
- `docs/vision/claim_rewards_live/README.md`
- `tests/vision/test_repository.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/vision-claim-rewards-live-captures.md`

Public APIs added or changed:

- `ClaimRewardsGoldenCatalog`
- `ClaimRewardsGoldenCatalogEntry`
- `ClaimRewardsSupportingCapture`
- `AnchorRepository` now also exposes:
  - `list_curation_references(anchor_id)`
  - `resolve_curation_reference_paths(anchor_id)`
  - `resolve_claim_rewards_catalog_path()`
  - `get_claim_rewards_golden_catalog()`
  - `get_claim_rewards_anchor_golden(anchor_id)`
  - `resolve_claim_rewards_golden_image_path(anchor_id)`
  - `list_claim_rewards_supporting_captures(anchor_id)`
  - `resolve_claim_rewards_supporting_capture_paths(anchor_id)`
- `TemplateDependencyReadiness` now also exposes:
  - `golden_catalog_path`
  - `selected_golden_id`
  - `selected_golden_image_path`
  - `failure_case`
  - `selected_reference_id`
  - `selected_reference_kind`
  - `reference_ids`
  - `reference_image_paths`
  - `live_reference_count`
  - `live_reference_ids`
  - `live_reference_image_paths`
  - `supporting_capture_count`
  - `supporting_capture_ids`
  - `supporting_capture_image_paths`
  - `supporting_capture_evidence_roles`
  - `supporting_capture_failure_cases`
  - `live_supporting_capture_count`
  - `live_supporting_capture_ids`
- `MatchInspectorState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `golden_catalog_path`
  - `selected_golden_id`
  - `selected_golden_image_path`
  - `failure_case`
  - `selected_reference_id`
  - `selected_reference_kind`
  - `reference_ids`
  - `reference_image_paths`
  - `live_reference_count`
  - `live_reference_ids`
  - `live_reference_image_paths`
  - `supporting_capture_count`
  - `supporting_capture_ids`
  - `supporting_capture_image_paths`
  - `supporting_capture_evidence_roles`
  - `supporting_capture_failure_cases`
  - `live_supporting_capture_count`
  - `live_supporting_capture_ids`
- `ClaimRewardsCheckState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `golden_catalog_path`
  - `selected_golden_id`
  - `selected_golden_image_path`
  - `failure_case`
  - `selected_reference_id`
  - `selected_reference_kind`
  - `reference_ids`
  - `reference_image_paths`
  - `live_reference_count`
  - `live_reference_ids`
  - `live_reference_image_paths`
  - `supporting_capture_count`
  - `supporting_capture_ids`
  - `supporting_capture_image_paths`
  - `supporting_capture_evidence_roles`
  - `supporting_capture_failure_cases`
  - `live_supporting_capture_count`
  - `live_supporting_capture_ids`
- `ClaimRewardsInspectorState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `selected_failure_case`
  - `golden_catalog_path`
  - `selected_golden_id`
  - `selected_golden_image_path`
  - `selected_reference_id`
  - `selected_reference_kind`
  - `reference_ids`
  - `reference_image_paths`
  - `live_reference_count`
  - `live_reference_ids`
  - `live_reference_image_paths`
  - `supporting_capture_count`
  - `supporting_capture_ids`
  - `supporting_capture_image_paths`
  - `supporting_capture_evidence_roles`
  - `supporting_capture_failure_cases`
  - `live_supporting_capture_count`
  - `live_supporting_capture_ids`
- `FailureInspectorState` now also exposes:
  - `selected_region`
  - `selected_region_summary`
  - `golden_catalog_path`
  - `selected_golden_id`
  - `selected_golden_image_path`
  - `failure_case`
  - `selected_reference_id`
  - `selected_reference_kind`
  - `reference_ids`
  - `reference_image_paths`
  - `live_reference_count`
  - `live_reference_ids`
  - `live_reference_image_paths`
  - `supporting_capture_count`
  - `supporting_capture_ids`
  - `supporting_capture_image_paths`
  - `supporting_capture_evidence_roles`
  - `supporting_capture_failure_cases`
  - `live_supporting_capture_count`
  - `live_supporting_capture_ids`

Contract changes:

- `metadata.task_support["daily_ui.claim_rewards"]` now carries `live_capture_coverage`:
  - `live_anchor_ids`
  - `stand_in_anchor_ids`
  - `live_context_anchor_ids`
  - `blocked_scene_ids`
- `daily_ui.claim_reward` now keeps its curated stand-in primary baseline, but also declares a machine-readable supplemental live context reference:
  - primary reference stays `claim_button_baseline_v1`
  - live context reference is `claim_button_live_context_reward_panel_open_v1`
  - it reuses the approved live reward-panel baseline as surrounding ROX panel evidence without pretending the enabled claimable state is already live
- claim-rewards anchor curation metadata now requires a machine-readable `metadata.curation.metadata.failure_case`.
- claim-rewards catalog entries now mirror `failure_case` so catalog and anchor metadata stay aligned.
- claim-rewards catalog supporting captures now require explicit `capture_id`, `failure_case`, and `evidence_role`, and each golden now references those support captures by id.
- validation now rejects:
  - missing `failure_case`
  - missing `live_capture_coverage`
  - live/stand-in coverage lists that do not match anchor provenance
  - live-context anchors listed in coverage that do not actually declare a live reference
  - catalog entries whose `failure_case` diverges from anchor metadata
- golden support-capture ids that do not resolve, point at the wrong anchor, or omit their evidence role / failure case
- readiness metadata now carries `claim_rewards_live_capture_coverage`, and each template dependency now carries its own `failure_case` plus primary/supplemental reference surfaces and catalog-backed supporting-capture surfaces.
- failure and match tooling now flatten the currently selected region directly, plus the selected golden id, selected reference id/kind, and the available live-reference/supporting-capture lists, instead of forcing GUI to reconstruct provenance from summaries or English text.

Current live vs stand-in status:

- Live capture:
  - `daily_ui.reward_panel`
  - canonical baseline:
    - `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
  - supplemental live captures:
    - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
    - `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`
- Curated stand-in:
  - `daily_ui.claim_reward`
    - still screenshot-style for the actual enabled button state
    - now has one supplemental live context reference plus one explicit live negative-case supporting capture in the golden catalog:
      - `claim_button_live_context_reward_panel_open_v1`
      - points at `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
      - role: scene-context only, not claimable-state proof
  - `daily_ui.reward_confirm_state`
    - still stand-in only
    - no approved live confirm-modal reference yet
- Traceability-only raw captures copied into this worktree:
  - `docs/vision/claim_rewards_live/raw/`
  - includes additional round-7 screenshots such as `emulator-5560-reward-recovery*.png` and `runtime-previews-latest-20-sheet.png`
  - these are not promoted to canonical baselines unless they appear in `catalog.json`

Assumptions:

- The currently available live evidence is still only strong enough to keep `reward_panel_open` as the sole canonical live claim-rewards baseline.
- The approved live reward-panel baseline is trustworthy enough to serve as scene-context evidence for `daily_ui.claim_reward`, but not to upgrade that anchor to `live_capture`.
- The extra round-7 raw captures are useful for traceability and operator context, but they still do not prove the claimable-button or confirm-modal scenes.
- The new raw candidate `emulator-5556-after-fuli-tap-2026-04-22.png` is promising positive evidence for `reward_panel_claimable`, but this run does not promote it because the canonical template/golden asset import itself has not landed in this worktree state.
- GUI and downstream tracks should use the new machine-readable `failure_case`, `selected_region`, and coverage metadata rather than English message parsing.

Verification performed:

- `python -m json.tool assets/templates/daily_ui/manifest.json`
- `python -m json.tool assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `python -m unittest tests.vision.test_repository`
- `python -m unittest tests.vision.test_serialization`
- `python -m unittest tests.vision.test_validation`
- `python -m unittest tests.vision.test_tooling`
- `python -m unittest tests.vision.test_services`
- `python -m unittest discover -s tests/vision -t .`
- `python -m unittest discover -s tests -t .`

Known limitations:

- `daily_ui.claim_reward` still does not have an approved live zh-TW ROX claimable-panel capture.
- `daily_ui.reward_confirm_state` still does not have an approved live zh-TW ROX confirmation-modal capture.
- `daily_ui.claim_reward` now has real ROX scene context, but it is still a stand-in for the actual enabled button state and should not be treated as full live-capture parity.
- `selected_region` is intentionally the currently selected inspection overlay region; for matched checks that may be the runtime match bbox rather than the repository match window.
- Engine E's `2026-04-22` raw claimable-panel candidate is not promoted here because this run stayed within metadata/docs/tests ownership and did not import or replace the canonical template/golden image files themselves.

Blockers:

- None inside Engine C ownership.
- Promoting the remaining anchors to `live_capture` still depends on approved live zh-TW ROX screenshots for:
  - `reward_panel_claimable`
  - `reward_confirm_modal`

Recommended next step:

- Import the `2026-04-22` raw claimable-panel candidate into this worktree as a canonical daily-ui template/golden asset, then promote `daily_ui.claim_reward` from `curated_stand_in` to `live_capture` in manifest/catalog/coverage together.
- Continue capturing approved live zh-TW ROX evidence for `reward_confirm_modal`; the post-tap overlay evidence is useful, but it still does not match the confirm-button modal anchor.
- Engine B should render `selected_region`, `selected_region_summary`, `selected_golden_id`, `selected_reference_id`, `selected_reference_kind`, the `live_reference_*` fields, and the new `supporting_capture_*` fields directly instead of deriving provenance/action hints from overlay summaries or English failure strings.
