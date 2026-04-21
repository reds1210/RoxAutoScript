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
- standard active branch: `codex/core-runtime-claim-rewards-hardening`
- owns: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`, `tests/core/`, `tests/emulator/`, `tests/profiles/`
- may edit: `docs/architecture-contracts.md`
- worktree path: `..\RoxAutoScript-wt-core-runtime-claim-rewards`

### Engine B: GUI

- model: `gpt-5.4`
- primary branch family: `codex/gui-console-*`
- standard active branch: `codex/gui-claim-rewards-operator-hardening`
- owns: `src/roxauto/app/`, `assets/ui/`, `tests/app/`
- worktree path: `..\RoxAutoScript-wt-gui-claim-rewards`

### Engine C: Vision

- model: `gpt-5.4`
- primary branch family: `codex/vision-lab-*`
- standard active branch: `codex/vision-claim-rewards-curation`
- owns: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`, `tests/vision/`
- worktree path: `..\RoxAutoScript-wt-vision-claim-rewards`

### Engine D: Tasks

- model: `gpt-5.4`
- primary branch family: `codex/task-*` and `codex/plugin-event-framework`
- standard active branch: `codex/task-claim-rewards-real-flow`
- owns: `src/roxauto/tasks/`, `tests/tasks/`, task-specific template assets
- worktree path: `..\RoxAutoScript-wt-task-claim-rewards`

## Active Branch Order

Use this lineup as the default next wave:

1. `codex/core-runtime-claim-rewards-hardening`
2. `codex/gui-claim-rewards-operator-hardening`
3. `codex/vision-claim-rewards-curation`
4. `codex/task-claim-rewards-real-flow`

Later branch progression:

- Engine A: `codex/core-runtime-claim-rewards-hardening` -> `codex/core-runtime-step-telemetry`
- Engine B: `codex/gui-claim-rewards-operator-hardening` -> `codex/gui-claim-rewards-editor-persistence`
- Engine C: `codex/vision-claim-rewards-curation` -> `codex/vision-claim-rewards-goldens`
- Engine D: `codex/task-claim-rewards-real-flow` -> `codex/task-guild-check-in`

## Non-Negotiable Rules

- maximum active engine worktrees: `4`
- maximum active worktrees per engine: `1`
- each engine keeps its owned paths
- task engines do not start gameplay automation before platform Gate 3
