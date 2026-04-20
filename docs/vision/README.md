# Vision Contracts and Template Repository Format

This branch owns the developer-facing observability layer for anchors, calibration, recording, and failure inspection.

## Core Concepts

- `AnchorSpec`: a single template definition with an id, label, relative asset path, confidence threshold, optional match region, and metadata.
- `AnchorRepository`: a filesystem-backed repository rooted at `assets/templates/<pack>/` with a `manifest.json` file.
- `CalibrationProfile`: per-instance calibration data for scale, offsets, crop region, and anchor-specific overrides.
- `RecordingAction` and `ReplayScript`: the minimal UI-layer recording format used by the calibration/recording tooling.
- `TemplateMatchResult`: the UI-facing result wrapper around one or more `VisionMatch` candidates.

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

## GUI Panels

The app skeleton renders five vision panes:

- Preview: the latest match result and candidate summaries.
- Calibration: per-instance scale, offsets, crop region, and anchor overrides.
- Recording: a simple replay script viewer.
- Anchors: repository contents and selected-anchor inspection.
- Failures: best candidate, failure message, and candidate list.

## Serialization

- `CalibrationProfile.to_json()` and `from_json()` preserve round-trip state.
- `ReplayScript.to_json()` and `from_json()` preserve action order and payloads.
- `AnchorRepository.load()` reads `manifest.json` from disk.

