# Handoff: Vision Lab Anchor Engine

Track:

- `codex/vision-lab-anchor-engine`

Scope:

- vision-side contracts for anchor/template handling
- calibration and recording models
- filesystem-backed template repository loading
- app skeleton for preview, calibration, recording, anchor inspection, and failure inspection
- sample template assets and documentation

Files changed:

- `src/roxauto/vision/models.py`
- `src/roxauto/vision/repository.py`
- `src/roxauto/vision/services.py`
- `src/roxauto/vision/__init__.py`
- `src/roxauto/app/viewmodels.py`
- `src/roxauto/app/shell.py`
- `src/roxauto/app/__init__.py`
- `assets/templates/common/manifest.json`
- `assets/templates/common/anchors/common_close_button.svg`
- `assets/templates/common/anchors/common_confirm_button.svg`
- `assets/templates/daily_ui/manifest.json`
- `assets/templates/daily_ui/anchors/daily_claim_button.svg`
- `assets/templates/odin/manifest.json`
- `assets/templates/odin/anchors/odin_start_button.svg`
- `docs/vision/README.md`
- `tests/app/test_viewmodels.py`
- `tests/vision/test_repository.py`
- `tests/vision/test_serialization.py`
- `docs/handoffs/vision-lab-anchor-engine.md`

Public APIs added or changed:

- `AnchorSpec`
- `TemplateRepositoryManifest`
- `AnchorRepository`
- `CalibrationProfile`
- `RecordingAction`
- `ReplayScript`
- `TemplateMatchResult`
- `build_match_result()`
- `build_vision_workspace_snapshot()`

Contract changes:

- template repositories now load from `assets/templates/<pack>/manifest.json`
- template asset paths are relative to the repository root
- app viewmodels now expose preview, calibration, recording, anchor, and failure panes

Assumptions:

- template assets can be scaffolded with SVG placeholders until real screenshots are captured
- GUI remains lazily imported and runnable without PySide6 installed
- the new vision models stay independent of core/emulator runtime changes

Verification performed:

- `python -m unittest discover -s tests -t .`
- `python -m roxauto doctor` not rerun yet in this branch

Known limitations:

- no real screenshot capture or OCR implementation yet
- template matching is still a result wrapper/service layer, not a pixel pipeline
- GUI panes are skeletons and display repository/state summaries only

Blockers:

- none

Recommended next step:

- wire real capture/match inputs into `build_vision_workspace_snapshot()` and the GUI refresh path

