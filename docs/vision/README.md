# Vision Contracts and Template Repository Format

This branch owns the developer-facing observability layer for anchors, calibration, recording, and failure inspection.

## Core Concepts

- `AnchorSpec`: a single template definition with an id, label, relative asset path, confidence threshold, optional match region, and metadata.
- `AnchorRepository`: a filesystem-backed repository rooted at `assets/templates/<pack>/` with a `manifest.json` file.
- `CalibrationProfile`: per-instance calibration data for scale, offsets, crop region, and anchor-specific overrides.
- `CropRegion`, `CaptureArtifact`, and `CaptureSession`: the minimal capture/crop contract for screenshot tooling and asset extraction.
- `RecordingAction` and `ReplayScript`: the minimal UI-layer recording format used by the calibration/recording tooling.
- `ReplayActionView` and `ReplayViewerState`: replay-viewer models derived from `ReplayScript` without requiring GUI widgets.
- `TemplateMatchResult`: the UI-facing result wrapper around one or more `VisionMatch` candidates.
- `FailureInspectionRecord`: a serializable snapshot of a failed match/check, including screenshot references and the best available match context.
- `TemplateWorkspaceCatalog`, `AnchorInspectorState`, `CalibrationInspectorState`, `CaptureInspectorState`, `MatchInspectorState`, and `FailureInspectorState`: viewer-safe tooling contracts that GUI panes can consume directly.

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

## Template Validation

Vision-side tooling can now validate template packs before GUI or task code consumes them:

- `validate_template_repository()` checks one loaded `AnchorRepository`.
- `validate_template_workspace()` scans `assets/templates/` and returns one report per repository folder.
- `TemplateRepositoryValidationReport` summarizes error count, warning count, anchor count, and issue details.
- `TemplateValidationIssue` carries a stable `code`, severity, affected anchor id, and path for operator-facing inspection.

Validation only enforces rules that are already part of the documented contracts:

- `repository_id`, `display_name`, and `version` must exist.
- `anchor_id` must be unique inside one repository.
- `confidence_threshold` must stay within `(0.0, 1.0]`.
- `match_region` width and height must be positive when present.
- `template_path` must stay relative to the repository root and resolve to an existing file.
- template file names should stay lowercase and use underscores.

The validator intentionally returns warnings for naming/grouping drift and errors for load-breaking conditions.

## Repository Helpers

`AnchorRepository` now provides a slightly richer loading/search boundary:

- `discover()` returns an empty list when the templates root is missing instead of failing.
- `manifest_path` and `version` expose stable metadata for tooling and diagnostics.
- `list_anchor_ids()` and `has_anchor()` support selection UIs.
- `find_anchors(query=..., tag=..., limit=...)` gives GUI/operator tooling a simple search/filter primitive.
- `resolve_template_path()` and `resolve_asset_path()` keep asset-path handling anchored at the repository root.

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
- `build_anchor_inspector()` returns anchor rows with resolved asset paths, validation issue codes, and effective calibration overrides.
- `build_calibration_inspector()` returns one calibration-focused state object with profile values, selected anchor context, and capture-session linkage.
- `build_capture_inspector()` returns selected artifact state and derived artifact metadata for capture/crop tooling.
- `build_match_inspector()` converts `TemplateMatchResult` into a viewer-safe candidate list with best/matched flags.
- `build_failure_inspector()` merges `FailureInspectionRecord`, match context, and selected anchor context into one inspector-safe payload.
- `build_vision_tooling_state()` stitches the workspace catalog, match/anchor/calibration/capture/replay/failure states into one aggregate contract.

These builders stay inside the vision layer and do not depend on `app`, `core` runtime orchestration details, or emulator transport implementations.

## Capture/Crop Workflow Skeleton

The first-wave tooling uses a simple artifact model:

1. runtime or operator tooling produces a source screenshot path
2. `create_capture_session()` records the source image, instance id, optional selected anchor, and optional crop region
3. `create_capture_artifact()` records derived files such as a manual crop or annotation output
4. the session is serialized or passed to GUI tooling for inspection

This intentionally stops at metadata and paths. Pixel processing and OCR stay out of this branch.

## Replay and Failure Inspection

- `build_replay_view()` converts a `ReplayScript` into a viewer-safe shape with labels, selection state, and payload summaries.
- `build_failure_inspection()` converts a failed match or screenshot into a serializable record for a future failure inspector pane.
- both helpers are designed to remain independent of `app`, `core`, and `emulator` implementation details.

## Serialization

- `CalibrationProfile.to_json()` and `from_json()` preserve round-trip state.
- `ReplayScript.to_json()` and `from_json()` preserve action order and payloads.
- `CaptureSession.to_json()` and `from_json()` preserve crop selections and derived artifact metadata.
- `FailureInspectionRecord.from_dict()` restores nested `TemplateMatchResult` data for later inspection.
- `AnchorRepository.load()` reads `manifest.json` from disk.

