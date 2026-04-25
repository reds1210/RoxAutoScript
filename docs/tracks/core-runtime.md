# Track Brief: Core Runtime

Legacy note:

- this brief describes the retired engine/worktree model
- use the branch-first briefs listed in `docs/tracks/README.md` for new work

## Branch

- `codex/core-runtime`

## Mission

Create the headless runtime layer that every other track depends on.

## Owned Paths

- `src/roxauto/core/`
- `src/roxauto/emulator/`
- `src/roxauto/logs/`
- `src/roxauto/profiles/`
- `tests/core/`
- `tests/emulator/`

## Allowed Shared File Edits

- `docs/architecture-contracts.md`
- `README.md`
- `pyproject.toml`

## Deliverables

- base package layout
- shared types
- instance registry contract
- task queue contract
- task runner/state machine contract
- structured log contract
- profile contract
- MuMu/ADB adapter interface

## Must Not Do

- PySide6 widgets
- template matching implementation details
- task-specific logic

## Done Means

- later tracks can import stable runtime primitives
- event names and status enums are documented
- at least basic tests exist for the runner and instance state transitions
