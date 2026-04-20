# Track Brief: Task Odin

## Branch

- `codex/task-odin`

## Mission

Implement the Odin farm setup pack as a separate track from the general daily UI tasks.

## Owned Paths

- `src/roxauto/tasks/odin/`
- `assets/templates/odin/`
- `tests/tasks/odin/`

## Dependencies

- requires runtime contracts from `codex/core-runtime`
- requires vision helpers from `codex/vision-lab`

## Deliverables

- Odin preset task manifest
- flow for entering the configured farming state
- verification that the expected farming loop is active
- stop and failure conditions

## Must Not Do

- dynamic mob selection strategy
- open-world route planning
- combat optimization logic

## Done Means

- the task can reliably put a character into the configured Odin farming setup
- failure cases are visible in logs and screenshots
