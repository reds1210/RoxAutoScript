# Track Brief: Task Daily UI

Legacy note:

- this brief describes the retired engine/worktree model
- use the branch-first briefs listed in `docs/tracks/README.md` for new work

## Branch

- `codex/task-daily-ui`

## Mission

Implement the first deterministic task pack set based on stable UI screens.

## Owned Paths

- `src/roxauto/tasks/daily_ui/`
- `assets/templates/daily_ui/`
- `tests/tasks/daily_ui/`

## Dependencies

- requires runtime contracts from `codex/core-runtime`
- requires vision helpers from `codex/vision-lab`

## Deliverables

- startup/login cleanup flow
- fixed reward collection flow
- guild fixed chore flow
- task manifests for each flow
- failure states and retry limits

## Must Not Do

- freeform board missions
- world path planning
- instance combat logic
- GUI-only shortcuts

## Done Means

- each task has clear entry, success, and failure conditions
- each task can run headlessly through the runtime layer
