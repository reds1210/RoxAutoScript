# Handoff: Vision Claim Rewards Curation

Track:

- `codex/vision-claim-rewards-curation`

Scope:

- advanced only the vision-owned `daily_ui.claim_rewards` curation contract
- kept `guild_check_in`, `odin`, GUI, runtime, and task-owned code unchanged
- replaced the three claim-rewards placeholder SVG anchors with curated raster templates and screenshot-style goldens
- tightened failure/inspection surfaces so GUI can render anchor id, label, threshold, current image, template path, and reference image directly

Files changed:

- `src/roxauto/vision/models.py`
- `src/roxauto/vision/repository.py`
- `src/roxauto/vision/tooling.py`
- `src/roxauto/vision/validation.py`
- `src/roxauto/vision/__init__.py`
- `assets/templates/daily_ui/manifest.json`
- `docs/vision/README.md`
- `tests/vision/test_repository.py`
- `tests/vision/test_serialization.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/vision-claim-rewards-curation.md`

Public APIs added or changed:

- added `AnchorCurationStatus`
- added `AnchorCurationReference`
- added `AnchorCurationProfile`
- `AnchorRepository` now exposes:
  - `get_anchor_curation(anchor_id)`
  - `get_primary_curation_reference(anchor_id)`
  - `resolve_curation_reference_path(anchor_id)`
  - `resolve_repository_path(path)`
  - `get_task_support(task_id)`
- `AnchorInspectionRow` now exposes:
  - `curation_status`
  - `curation_reference_count`
  - `curation_summary`
  - `curation_profile`
- `TemplateDependencyReadiness` now exposes:
  - `curation_status`
  - `curation_reference_count`
  - `curation_summary`
- `MatchInspectorState`, `ClaimRewardsCheckState`, and `FailureInspectorState` now expose:
  - `selected_anchor_label`
  - `selected_template_path`
  - `selected_reference_image_path`
  - `curation_status`
  - `curation_summary`
- `ClaimRewardsInspectorState` now exposes:
  - `selected_anchor_label`
  - `selected_template_path`
  - `selected_reference_image_path`
  - `selected_curation_status`
  - `selected_curation_summary`

Contract changes:

- `daily_ui.claim_rewards` anchors now require explicit `metadata.curation` in the template manifest
- the claim-rewards manifest now points at raster `.png` template assets instead of placeholder-only `.svg` crops
- the branch now ships one screenshot-style baseline image per claim-rewards anchor under `assets/templates/daily_ui/goldens/claim_rewards/`
- claim-rewards curation metadata currently tracks:
  - `status`
  - `intent_id`
  - `scene_id`
  - `variant_id`
  - optional `notes`
  - optional `references`
- validation now rejects a claim-rewards anchor when:
  - `metadata.curation` is missing
  - required curation fields are missing
  - a `curated` anchor has no references
  - a `curated` anchor still points at a non-raster template asset
- a curated template now resolves as `ready` in vision readiness even if Engine D's task inventory still marks it as `placeholder`; that inventory drift is surfaced as an explicit mismatch instead of degrading the actual template state
- match/failure tooling now appends template/reference context into failure explanations, and still appends curation notes when an anchor is not yet curated

Assumptions:

- this round still does not ship live ROX screenshots inside the repo
- the new goldens are repo-curated screenshot-style baselines that are materially better than vector placeholders, but they are still not live device captures from a real ROX run
- a later round may still want to replace these synthetic baselines with live zh-TW captures without changing the surrounding contract surface

What the operator will now see differently:

- claim-rewards failure panes can now show:
  - selected anchor id / label
  - selected threshold
  - selected runtime image path
  - selected template asset path
  - selected reference baseline image path
- readiness data can distinguish a genuinely curated template from a stale inventory record that still says `placeholder`
- anchor inspection surfaces now show curation summaries directly, so GUI does not need to parse manifest metadata on its own
- claim-rewards inspection now points at raster templates and screenshot-style baselines instead of only SVG placeholder geometry

Verification performed:

- `python -m unittest tests.vision.test_repository`
- `python -m unittest tests.vision.test_serialization`
- `python -m unittest tests.vision.test_validation`
- `python -m unittest tests.vision.test_tooling`
- `python -m unittest discover -s tests/vision -t .`
- `python -m unittest discover -s tests -t .`

Known limitations:

- the shipped goldens are still synthetic screenshot-style baselines, not emulator captures from a real account
- Engine D's inventory still marks `daily_ui.claim_reward` as `placeholder`, so readiness will intentionally report one inventory mismatch until that branch catches up
- failure explanations are now much more direct, but they still depend on runtime/task layers to provide the actual failed screenshot path and match candidates

Blockers:

- repeated real-flow validation still needs curated zh-TW claim-rewards screenshots
- the task asset inventory under `src/roxauto/tasks/foundations/asset_inventory.json` is still owned by Engine D, so this branch does not redefine task inventory policy

Recommended next step:

- capture live zh-TW screenshots for:
  - `reward_panel_open`
  - `reward_panel_claimable`
  - `reward_confirm_modal`
- if those live captures are approved, replace the current screenshot-style baselines in `assets/templates/daily_ui/goldens/claim_rewards/` and keep the same template/reference contract
- Engine B should consume these GUI-facing surfaces for claim-rewards failures:
  - `FailureInspectorState.anchor_id`
  - `FailureInspectorState.selected_anchor_label`
  - `FailureInspectorState.selected_threshold`
  - `FailureInspectorState.selected_image_path`
  - `FailureInspectorState.selected_template_path`
  - `FailureInspectorState.selected_reference_image_path`
  - `FailureInspectorState.failure_explanation`
  - `FailureInspectorState.claim_rewards.selected_check`
  - `FailureInspectorState.claim_rewards.selected_anchor_label`
  - `FailureInspectorState.claim_rewards.selected_threshold`
  - `FailureInspectorState.claim_rewards.selected_image_path`
  - `FailureInspectorState.claim_rewards.selected_template_path`
  - `FailureInspectorState.claim_rewards.selected_reference_image_path`
  - `FailureInspectorState.claim_rewards.selected_check_summary`
