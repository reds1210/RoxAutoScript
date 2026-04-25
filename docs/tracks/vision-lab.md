# Track Brief: Vision Lab

Legacy note:

- this brief describes the retired engine/worktree model
- use the branch-first briefs listed in `docs/tracks/README.md` for new work

## Branch

- `codex/vision-lab`

## Mission

Build the screenshot and anchor-detection utilities used by task packs and manual tools.

## Owned Paths

- `src/roxauto/vision/`
- `assets/templates/`
- `docs/vision/`
- `tests/vision/`

## Dependencies

- requires shared types from `codex/core-runtime`

## Deliverables

- image loading helpers
- template-match pipeline
- anchor result format
- confidence thresholds
- optional OCR adapter boundary
- asset naming and storage rules

## Must Not Do

- GUI code
- task policy
- emulator transport code

## Done Means

- task packs can ask for anchors without knowing low-level image-processing details
- confidence and failure behavior are documented
