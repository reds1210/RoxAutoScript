# Handoff: Vision Lab Calibration Tools

Track:

- `codex/vision-lab-calibration-tools`

Scope:

- extend vision-side contracts for crop/capture tooling
- add replay-viewer and failure-inspection models/helpers
- add template-repository validation utilities for anchor packs under `assets/templates/`
- add GUI-consumable tooling state builders for anchor/calibration/capture/replay/failure panes
- keep all work inside `vision`, `assets/templates`, `docs/vision`, and `tests/vision`

Files changed:

- `src/roxauto/vision/models.py`
- `src/roxauto/vision/repository.py`
- `src/roxauto/vision/services.py`
- `src/roxauto/vision/tooling.py`
- `src/roxauto/vision/__init__.py`
- `src/roxauto/vision/validation.py`
- `docs/vision/README.md`
- `tests/vision/test_repository.py`
- `tests/vision/test_serialization.py`
- `tests/vision/test_services.py`
- `tests/vision/test_tooling.py`
- `tests/vision/test_validation.py`
- `docs/handoffs/vision-lab-calibration-tools.md`

Public APIs added or changed:

- Existing APIs from earlier handoff remain in place:
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
- Added in this round:
  - `TemplateValidationSeverity`
  - `TemplateValidationIssue`
  - `TemplateRepositoryValidationReport`
  - `TemplateWorkspaceValidationReport`
  - `validate_template_repository()`
  - `validate_template_workspace()`
- Added in this round for GUI-consumable tooling state:
  - `TemplateRepositoryCatalogEntry`
  - `TemplateWorkspaceCatalog`
  - `AnchorInspectionRow`
  - `AnchorInspectorState`
  - `CalibrationInspectorState`
  - `CaptureArtifactView`
  - `CaptureInspectorState`
  - `MatchCandidateView`
  - `MatchInspectorState`
  - `FailureInspectorState`
  - `VisionToolingState`
  - `build_template_workspace_catalog()`
  - `build_anchor_inspector()`
  - `build_calibration_inspector()`
  - `build_capture_inspector()`
  - `build_match_inspector()`
  - `build_failure_inspector()`
  - `build_vision_tooling_state()`
- `AnchorRepository` now exposes `manifest_path`, `version`, `list_anchor_ids()`, `has_anchor()`, `find_anchors()`, and missing-root-safe `discover()`
- `TemplateMatchResult.matched_candidate()` now correctly filters by `expected_anchor_id`

Contract changes:

- capture/crop tooling is represented as metadata-first contracts with file paths and optional crop regions
- replay inspection now has a viewer-safe state model independent of GUI widgets
- failure inspection can restore nested match results and best-candidate context from serialized data
- template repository diagnostics now enforce the documented manifest/path/threshold rules before GUI or task code consumes a pack
- GUI-facing anchor/calibration/capture/replay/failure panes now have vision-owned builder functions and state contracts instead of relying on `app`-local ad hoc shaping

Verification performed:

- `python -m unittest discover -s tests/vision -t .`
- `python -m unittest discover -s tests -t .`
- `python -c "import tests._bootstrap; import roxauto.vision as v; print(v.build_vision_tooling_state.__name__, v.TemplateWorkspaceCatalog.__name__)"`

Known limitations:

- no pixel-level crop, screenshot capture, or OCR implementation yet
- replay viewer state is model/service only; no widget wiring was added in this worktree
- failure inspection stores path and match metadata only; no image diffing or overlay generation yet
- validation only inspects manifest structure and filesystem references; it does not inspect pixel quality or anchor distinctness
- `app/viewmodels.py` still has its own `build_vision_workspace_snapshot()` and has not yet been switched to these vision-owned tooling builders

Blockers:

- none in this branch

Recommended next step:

- have the GUI/operator track replace `build_vision_workspace_snapshot()` with `build_vision_tooling_state()` and surface `validate_template_workspace()` output in the anchors/calibration panes before loading operator-selected template packs
