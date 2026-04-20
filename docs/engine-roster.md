# Engine Roster

This repo now uses a fixed 4-engine parallel development model.

## Model Policy

- default delegated model: `gpt-5.4`
- do not use mini variants for engine work unless the user explicitly asks for a smaller model
- each engine keeps a stable specialization; do not rotate ownership casually

## Standard Engine Lineup

### Engine A: Runtime

- model: `gpt-5.4`
- primary branch family: `codex/core-runtime-*`
- standard active branch: `codex/core-runtime-orchestration`
- owns: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`, `tests/core/`, `tests/emulator/`, `tests/profiles/`
- may edit: `docs/architecture-contracts.md`
- worktree path: `..\RoxAutoScript-wt-engine-a-runtime`

### Engine B: GUI

- model: `gpt-5.4`
- primary branch family: `codex/gui-console-*`
- standard active branch: `codex/gui-console-operator`
- owns: `src/roxauto/app/`, `assets/ui/`, `tests/app/`
- worktree path: `..\RoxAutoScript-wt-engine-b-gui`

### Engine C: Vision

- model: `gpt-5.4`
- primary branch family: `codex/vision-lab-*`
- standard active branch: `codex/vision-lab-calibration-tools`
- owns: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`, `tests/vision/`
- worktree path: `..\RoxAutoScript-wt-engine-c-vision`

### Engine D: Tasks

- model: `gpt-5.4`
- primary branch family: `codex/task-*` and `codex/plugin-event-framework`
- standard standby branch: `codex/task-daily-ui`
- owns: `src/roxauto/tasks/`, `tests/tasks/`, task-specific template assets
- worktree path: `..\RoxAutoScript-wt-engine-d-tasks`
- gate: stays on standby until platform Gate 3 is complete

## Active Branch Order

Use this lineup as the default next wave:

1. `codex/core-runtime-orchestration`
2. `codex/gui-console-operator`
3. `codex/vision-lab-calibration-tools`
4. `codex/task-daily-ui`

Later branch progression:

- Engine A: `codex/core-runtime-orchestration` -> `codex/core-runtime-recovery` -> `codex/task-event-runtime`
- Engine B: `codex/gui-console-operator` -> `codex/gui-console-calibration-tools`
- Engine C: `codex/vision-lab-calibration-tools` -> `codex/vision-lab-board-ocr` -> `codex/vision-lab-life-skill-assets`
- Engine D: `codex/task-daily-ui` -> `codex/task-odin` -> `codex/task-board` -> `codex/task-life-skills` -> `codex/plugin-event-framework`

## Non-Negotiable Rules

- maximum active engine worktrees: `4`
- maximum active worktrees per engine: `1`
- each engine keeps its owned paths
- task engines do not start gameplay automation before platform Gate 3
