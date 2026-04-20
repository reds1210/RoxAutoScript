# Handoff: Vision Lab Calibration Tools

Track:

- `codex/vision-lab-calibration-tools`

Scope:

- extend vision-side contracts for crop/capture tooling
- add replay-viewer and failure-inspection models/helpers
- keep all work inside `vision`, `assets/templates`, `docs/vision`, and `tests/vision`

Files changed:

- `src/roxauto/vision/models.py`
- `src/roxauto/vision/services.py`
- `src/roxauto/vision/__init__.py`
- `docs/vision/README.md`
- `tests/vision/test_serialization.py`
- `tests/vision/test_services.py`
- `docs/handoffs/vision-lab-calibration-tools.md`

Public APIs added or changed:

- `CropRegion`
- `CaptureArtifactKind`
- `CaptureArtifact`
- `CaptureSession`
- `ReplayActionView`
- `ReplayViewerState`
- `FailureInspectionRecord`
- `create_capture_session()`
- `create_capture_artifact()`
- `build_replay_view()`
- `build_failure_inspection()`
- `TemplateMatchResult.matched_candidate()` now correctly filters by `expected_anchor_id`

Contract changes:

- capture/crop tooling is represented as metadata-first contracts with file paths and optional crop regions
- replay inspection now has a viewer-safe state model independent of GUI widgets
- failure inspection can restore nested match results and best-candidate context from serialized data

Verification performed:

- `C:\code\RoxAutoScript\.venv\Scripts\python.exe -m unittest discover -s tests -t .`
- `C:\code\RoxAutoScript\.venv\Scripts\python.exe -c "import tests._bootstrap; import roxauto.vision as v; print(v.CaptureSession.__name__, v.ReplayViewerState.__name__, v.FailureInspectionRecord.__name__)"`

Known limitations:

- no pixel-level crop, screenshot capture, or OCR implementation yet
- replay viewer state is model/service only; no widget wiring was added in this worktree
- failure inspection stores path and match metadata only; no image diffing or overlay generation yet

Blockers:

- none in this branch

Recommended next step:

- have the GUI/operator track consume `ReplayViewerState`, `CaptureSession`, and `FailureInspectionRecord` instead of ad hoc placeholder data
