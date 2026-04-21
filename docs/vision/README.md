# Vision Contracts and Template Repository Format

This branch owns the developer-facing observability layer for anchors, calibration, recording, and failure inspection.

## Core Concepts

- `AnchorSpec`: a single template definition with an id, label, relative asset path, confidence threshold, optional match region, and metadata.
- `AnchorCurationProfile` and `AnchorCurationReference`: the curation contract layered onto `AnchorSpec.metadata.curation`, used to track whether a task-critical template is only planned, already captured, or fully curated.
- `AnchorRepository`: a filesystem-backed repository rooted at `assets/templates/<pack>/` with a `manifest.json` file.
- `CalibrationProfile`: per-instance calibration data for scale, offsets, crop region, and anchor-specific overrides.
- `CalibrationOverrideResolution`: the normalized per-anchor result after base template values, profile crop, and anchor override are merged.
- `CropRegion`, `CaptureArtifact`, and `CaptureSession`: the minimal capture/crop contract for screenshot tooling and asset extraction.
- `InspectionOverlay` and `ImageInspectionState`: overlay-ready inspection contracts for preview, anchor, crop, match, and failure panes.
- `RecordingAction` and `ReplayScript`: the minimal UI-layer recording format used by the calibration/recording tooling.
- `ReplayActionView` and `ReplayViewerState`: replay-viewer models derived from `ReplayScript` without requiring GUI widgets.
- `TemplateMatchResult`: the UI-facing result wrapper around one or more `VisionMatch` candidates.
- `FailureInspectionRecord`: a serializable snapshot of a failed match/check, including screenshot references and the best available match context.
- `TemplateWorkspaceCatalog`, `AnchorInspectorState`, `CalibrationInspectorState`, `CaptureInspectorState`, `MatchInspectorState`, and `FailureInspectorState`: viewer-safe tooling contracts that GUI panes can consume directly.
- `VisionWorkspaceReadinessReport`: a workspace-level report that compares loaded template repositories against task-foundation template dependencies.

## Repository Layout

Each template pack is stored under its own folder:

```text
assets/templates/
  common/
    manifest.json
    anchors/
      *.svg
  daily_ui/
    manifest.json
    anchors/
      *.svg
      *.png
    goldens/
      claim_rewards/
        catalog.json
        *.png
  odin/
    manifest.json
    anchors/
      *.svg
```

## Manifest Shape

The manifest is JSON and mirrors `TemplateRepositoryManifest`:

```json
{
  "repository_id": "common",
  "display_name": "Common UI Templates",
  "version": "0.1.0",
  "metadata": {},
  "anchors": [
    {
      "anchor_id": "common.close_button",
      "label": "Close Button",
      "template_path": "anchors/common_close_button.svg",
      "confidence_threshold": 0.9,
      "match_region": [0, 0, 1920, 1080],
      "description": "Dismiss button used in modal dialogs.",
      "tags": ["dialog", "dismiss"],
      "metadata": {}
    }
  ]
}
```

Rules:

- `template_path` is always relative to the repository root.
- `match_region` is optional and uses `x, y, width, height`.
- asset names stay lowercase and use underscores.
- the repo loader treats the manifest as the source of truth.
- placeholder template anchors may set `metadata.placeholder=true` so readiness tooling can distinguish scaffold assets from fully-ready captures.
- template packs may declare `metadata.task_support` so vision validation can assert that one task has the full set of required inspection roles before GUI/runtime consumes the pack.
- task-critical anchors may declare `metadata.curation` with `status`, `intent_id`, `scene_id`, `variant_id`, optional `notes`, and optional `references` so curation work is explicit before live captures land.
- a `curated` anchor is expected to point at a raster template and at least one reference image under the same repository, typically under `goldens/<task>/`.

## Template Validation

Vision-side tooling can now validate template packs before GUI or task code consumes them:

- `validate_template_repository()` checks one loaded `AnchorRepository`.
- `validate_template_workspace()` scans `assets/templates/` and returns one report per repository folder.
- `build_vision_workspace_readiness_report()` compares template availability against `src/roxauto/tasks/foundations/asset_inventory.json`.
- `TemplateRepositoryValidationReport` summarizes error count, warning count, anchor count, and issue details.
- `TemplateValidationIssue` carries a stable `code`, severity, affected anchor id, and path for operator-facing inspection.
- `TemplateDependencyReadiness` carries task/pack/anchor-level readiness, placeholder state, and inventory-mismatch information.
- claim-rewards anchors now also validate their curation contract: they must declare `metadata.curation`, and a `curated` anchor must carry at least one reference plus a raster template asset.

Validation only enforces rules that are already part of the documented contracts:

- `repository_id`, `display_name`, and `version` must exist.
- `anchor_id` must be unique inside one repository.
- `confidence_threshold` must stay within `(0.0, 1.0]`.
- `match_region` width and height must be positive when present.
- `template_path` must stay relative to the repository root and resolve to an existing file.
- template file names should stay lowercase and use underscores.
- task-specific support contracts declared in `metadata.task_support` must resolve to anchors with unique `metadata.inspection_role` values.

The validator intentionally returns warnings for naming/grouping drift and errors for load-breaking conditions.

The readiness report is intentionally stricter than raw filesystem validation:

- it can distinguish `ready`, `placeholder`, `missing`, and `invalid` template dependencies
- it can flag stale task inventory records when an anchor now exists but the inventory still marks it missing
- it keeps task-foundation dependency checking in the vision layer without importing task runtime code

## Repository Helpers

`AnchorRepository` now provides a slightly richer loading/search boundary:

- `discover()` returns an empty list when the templates root is missing instead of failing.
- `manifest_path` and `version` expose stable metadata for tooling and diagnostics.
- `list_anchor_ids()` and `has_anchor()` support selection UIs.
- `find_anchors(query=..., tag=..., limit=...)` gives GUI/operator tooling a simple search/filter primitive.
- `resolve_template_path()` and `resolve_asset_path()` keep asset-path handling anchored at the repository root.
- `resolve_repository_path()` keeps non-template repository assets such as golden screenshots anchored at the repository root.
- `get_anchor_curation()` exposes the parsed `AnchorCurationProfile` for one anchor.
- `get_primary_curation_reference()` and `resolve_curation_reference_path()` expose the first GUI-facing baseline image for one curated anchor.
- `get_task_support()` returns manifest-level `metadata.task_support` without forcing callers to read the raw manifest dict.

## GUI Panels

The app skeleton renders five vision panes:

- Preview: the latest match result and candidate summaries.
- Calibration: per-instance scale, offsets, crop region, and anchor overrides.
- Recording: a simple replay script viewer.
- Anchors: repository contents and selected-anchor inspection.
- Failures: best candidate, failure message, and candidate list.

These panes should only consume the vision contracts. They should not implement capture, routing, or task logic directly.

## Tooling State Builders

The vision package now exposes service-layer builders so the GUI can stop inventing its own pane payload shapes:

- `build_template_workspace_catalog()` returns repository-level selection and validation state for `assets/templates/`.
- `build_template_workspace_catalog(..., asset_inventory_path=...)` can also attach the readiness report so GUI panes get validation and dependency status in one payload.
- `build_anchor_inspector()` returns anchor rows with resolved asset paths, validation issue codes, effective calibration overrides, and flattened curation fields.
- `build_calibration_inspector()` returns one calibration-focused state object with profile values, selected anchor context, and capture-session linkage.
- `build_capture_inspector()` returns selected artifact state, capture summaries, and `ImageInspectionState` payloads for source/selected artifact inspection.
- `build_match_inspector()` converts `TemplateMatchResult` into a viewer-safe candidate list plus an overlay-ready inspection state and selected-anchor curation summary.
- `build_failure_inspector()` merges `FailureInspectionRecord`, match context, selected anchor context, failure inspection overlays, and selected claim-check curation state into one payload.
- `build_vision_tooling_state()` stitches the workspace catalog, readiness report, match/anchor/calibration/capture/replay/failure states into one aggregate contract.
- `resolve_calibration_override()` centralizes per-anchor threshold/region/crop resolution so GUI and tooling do not each re-implement override logic.
- `build_image_inspection_state()` turns match/crop/calibration context into a shared `ImageInspectionState` that preview, capture, and failure panes can all consume directly.
- `FailureInspectorState.claim_rewards` now exposes a claim-specific checklist for `daily_ui.claim_rewards`, including per-check match summaries and one `ImageInspectionState` per check so GUI can focus directly on panel/button/confirm failures.
- `MatchInspectorState`, `ClaimRewardsCheckState`, `ClaimRewardsInspectorState`, and `FailureInspectorState` now flatten GUI-facing render fields such as `selected_image_path`, `selected_overlay`, `selected_overlay_summary`, `selected_threshold`, `failure_explanation`, selected curation summaries, `selected_anchor_label`, `selected_template_path`, and `selected_reference_image_path`.

These builders stay inside the vision layer and do not depend on `app`, `core` runtime orchestration details, or emulator transport implementations.

Current sample coverage:

- `daily_ui.reward_panel` now ships as a curated PNG crop plus one live zh-TW ROX baseline image for the opened reward panel scene
- `daily_ui.claim_reward` now ships as a curated PNG crop plus one curated screenshot-style baseline image for the tappable claim button scene
- `daily_ui.reward_confirm_state` now ships as a curated PNG crop plus one curated screenshot-style baseline image for the confirmation modal scene
- `docs/vision/claim_rewards_live/raw/` now keeps the supporting live capture trail for this task only
- `daily_ui.guild_check_in_button` placeholder template now exists under `assets/templates/daily_ui/`
- `odin.start_button` placeholder template exists
- Engine D's task asset inventory still marks the `daily_ui.claim_reward` dependency as `placeholder`; vision readiness now reports the curated template as `ready` and flags the inventory drift as an explicit mismatch instead of degrading the actual template status

## Claim Rewards Support

`assets/templates/daily_ui/manifest.json` now declares a claim-rewards support contract:

- task id: `daily_ui.claim_rewards`
- required inspection roles:
  - `reward_panel`
  - `claim_reward_button`
  - `confirm_state`

Each anchor participating in that contract carries:

- `metadata.task_id`
- `metadata.inspection_role`
- `metadata.stage`
- `metadata.curation.status`
- `metadata.curation.intent_id`
- `metadata.curation.scene_id`
- `metadata.curation.variant_id`
- `metadata.curation.metadata.golden_catalog_path`
- `metadata.curation.metadata.golden_id`
- `metadata.curation.metadata.live_capture`
- `metadata.curation.metadata.proof_summary`
- `metadata.curation.metadata.failure_case`

This gives the vision layer enough information to:

- validate that the pack has all three required claim-rewards checks
- resolve a stable per-check expected anchor for overlays
- expose whether the currently selected claim-rewards template is still planned or already curated
- build claim-specific failure payloads without importing task runtime code

The branch now also ships a minimal golden organization for this task only:

- `assets/templates/daily_ui/goldens/claim_rewards/catalog.json`
- `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__reward_panel__baseline__v1.png`
- `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__claim_button__baseline__v1.png`
- `assets/templates/daily_ui/goldens/claim_rewards/daily_ui_claim_rewards__confirm_state__baseline__v1.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`
- `assets/templates/daily_ui/goldens/claim_rewards/live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`

`catalog.json` is the machine-readable index for the three shipped claim-rewards baselines. It records:

- which anchor and inspection role each golden supports
- which scene and stage the image proves
- whether the file is a live capture or a curated stand-in
- the current file hash and resolution so later live replacements stay traceable
- which step or failure case each image is meant to explain during claim-rewards inspection

Current claim-rewards golden coverage:

- `daily_ui_claim_rewards__reward_panel__baseline__v1.png`: live zh-TW ROX daily sign-in panel-open golden for `daily_ui.reward_panel`
- `daily_ui_claim_rewards__claim_button__baseline__v1.png`: curated stand-in for the claimable panel state used by `daily_ui.claim_reward`
- `daily_ui_claim_rewards__confirm_state__baseline__v1.png`: curated stand-in for the confirmation modal used by `daily_ui.reward_confirm_state`
- `live/daily_ui_claim_rewards__reward_panel__live_capture__emulator_5560__daily_signin.png`: descriptive copy of the canonical live panel-open screenshot for manual review and downstream tooling
- `live/daily_ui_claim_rewards__entry_context__live_capture__emulator_5556__after_fuli_tap.png`: live pre-panel navigation evidence after the Fu Li tap, used to debug failures before the panel-open anchor appears

`daily_ui.reward_panel` is now backed by a live capture. `daily_ui.claim_reward` and `daily_ui.reward_confirm_state` still rely on curated stand-ins because the available accounts did not expose approved live claimable or confirmation-modal states during this round. The manifest and golden catalog call this out explicitly so downstream consumers can distinguish canonical live evidence from still-pending live replacements.

## GUI Consumption

When the failure metadata includes a nested `claim_rewards` payload, Engine B should consume:

- `FailureInspectorState.claim_rewards.checks`: the ordered per-check list for `reward_panel`, `claim_reward_button`, and `confirm_state`
- `FailureInspectorState.claim_rewards.selected_check`: the currently failing or selected check
- `FailureInspectorState.claim_rewards.selected_check.inspection`: the overlay-ready image state for the selected check
- `FailureInspectorState.claim_rewards.selected_image_path`
- `FailureInspectorState.claim_rewards.selected_threshold`
- `FailureInspectorState.claim_rewards.selected_overlay_summary`
- `FailureInspectorState.claim_rewards.failure_explanation`
- `FailureInspectorState.claim_rewards.selected_anchor_label`
- `FailureInspectorState.claim_rewards.selected_template_path`
- `FailureInspectorState.claim_rewards.selected_reference_image_path`
- `FailureInspectorState.claim_rewards.selected_curation_summary`
- `FailureInspectorState.claim_rewards.selected_check_summary`: a one-line summary for the selected check
- `FailureInspectorState.inspection`: the same selected-check inspection promoted to the generic failure pane for backward-compatible fallback rendering
- `FailureInspectorState.selected_image_path`
- `FailureInspectorState.selected_threshold`
- `FailureInspectorState.selected_overlay_summary`
- `FailureInspectorState.selected_anchor_label`
- `FailureInspectorState.selected_template_path`
- `FailureInspectorState.selected_reference_image_path`
- `FailureInspectorState.failure_explanation`
- `FailureInspectorState.curation_summary`

Recommended GUI behavior:

- show the checklist in claim flow order
- default focus to `current_check_id` when provided
- render `selected_check.inspection` overlays even when the generic top-level `match_result` is absent
- render the secondary panel from the flattened `selected_*` and `failure_explanation` fields first, and only fall back to nested inspection data when the GUI needs the full overlay list

## Capture/Crop Workflow Skeleton

The first-wave tooling uses a simple artifact model:

1. runtime or operator tooling produces a source screenshot path
2. `create_capture_session()` records the source image, instance id, optional selected anchor, and optional crop region
3. `create_capture_artifact()` records derived files such as a manual crop or annotation output
4. `build_capture_inspector()` and `build_image_inspection_state()` expose crop/overlay-ready inspection payloads for GUI panes

This intentionally stops at metadata and paths. Pixel processing and OCR stay out of this branch.

## Replay and Failure Inspection

- `build_replay_view()` converts a `ReplayScript` into a viewer-safe shape with labels, selection state, and payload summaries.
- `build_failure_inspection()` converts a failed match or screenshot into a serializable record for a future failure inspector pane.
- `build_image_inspection_state()` is the shared overlay generator used by preview, capture, match, and failure tooling states.
- both helpers are designed to remain independent of `app`, `core`, and `emulator` implementation details.

## Serialization

- `CalibrationProfile.to_json()` and `from_json()` preserve round-trip state.
- `ReplayScript.to_json()` and `from_json()` preserve action order and payloads.
- `CaptureSession.to_json()` and `from_json()` preserve crop selections and derived artifact metadata.
- `FailureInspectionRecord.from_dict()` restores nested `TemplateMatchResult` data for later inspection.
- `AnchorRepository.load()` reads `manifest.json` from disk.

