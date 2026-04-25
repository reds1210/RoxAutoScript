# Track Brief: GUI Console

Legacy note:

- this brief describes the retired engine/worktree model
- use the branch-first briefs listed in `docs/tracks/README.md` for new work

## Branch

- `codex/gui-console`

## Mission

Build the operator-facing desktop control center on top of the runtime contracts.

## Owned Paths

- `src/roxauto/app/`
- `assets/ui/`
- `tests/app/`

## Dependencies

- requires the runtime contracts from `codex/core-runtime`

## Deliverables

- main window shell
- instance grid/list
- per-instance status card
- preview panel
- start, pause, stop, and emergency-stop controls
- log viewer panel
- manual tool panel placeholder

## Must Not Do

- runtime business logic inside widgets
- task-specific branching in the GUI layer

## Done Means

- GUI consumes runtime state instead of inventing its own state model
- an operator can understand instance status and trigger commands from one screen
