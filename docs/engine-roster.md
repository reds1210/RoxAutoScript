# Engine Roster

This repo now uses a fixed 4-engine parallel development model.

For round 6, the active strategy is the `claim_rewards` production-hardening wave. One optional support engine may be added only for live screenshots and goldens.

## Model Policy

- default delegated model: `gpt-5.4`
- do not use mini variants for engine work unless the user explicitly asks for a smaller model
- each engine keeps a stable specialization; do not rotate ownership casually

## Standard Engine Lineup

### Engine A: Runtime

- model: `gpt-5.4`
- primary branch family: `codex/core-runtime-*`
- standard active branch: `codex/core-runtime-step-telemetry`
- owns: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`, `tests/core/`, `tests/emulator/`, `tests/profiles/`
- may edit: `docs/architecture-contracts.md`
- worktree path: `..\RoxAutoScript-wt-core-runtime-step-telemetry`

### Engine B: GUI

- model: `gpt-5.4`
- primary branch family: `codex/gui-console-*`
- standard active branch: `codex/gui-claim-rewards-production-telemetry`
- owns: `src/roxauto/app/`, `assets/ui/`, `tests/app/`
- worktree path: `..\RoxAutoScript-wt-gui-claim-rewards-production`

### Engine C: Vision

- model: `gpt-5.4`
- primary branch family: `codex/vision-lab-*`
- standard active branch: `codex/vision-claim-rewards-live-captures`
- owns: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`, `tests/vision/`
- worktree path: `..\RoxAutoScript-wt-vision-claim-rewards-live`

### Engine D: Tasks

- model: `gpt-5.4`
- primary branch family: `codex/task-*` and `codex/plugin-event-framework`
- standard active branch: `codex/task-claim-rewards-runtime-seam`
- owns: `src/roxauto/tasks/`, `tests/tasks/`, task-specific template assets
- worktree path: `..\RoxAutoScript-wt-task-claim-rewards-runtime`

### Optional Engine E: Goldens

- model: `gpt-5.4`
- primary branch family: `codex/claim-rewards-*`
- standard active branch: `codex/claim-rewards-goldens`
- owns: `assets/templates/`, `tests/tasks/fixtures/`, `docs/vision/`
- worktree path: `..\RoxAutoScript-wt-claim-rewards-goldens`

## Active Branch Order

Use this lineup as the default round-6 start order:

1. `codex/claim-rewards-goldens` only when live capture becomes the primary blocker
2. `codex/vision-claim-rewards-live-captures`
3. `codex/task-claim-rewards-runtime-seam`
4. `codex/core-runtime-step-telemetry`
5. `codex/gui-claim-rewards-production-telemetry`

Later branch progression:

- Engine A: `codex/core-runtime-step-telemetry` -> `codex/core-runtime-registered-task-seam`
- Engine B: `codex/gui-claim-rewards-production-telemetry` -> `codex/gui-claim-rewards-operator-guidance`
- Engine C: `codex/vision-claim-rewards-live-captures` -> `codex/vision-claim-rewards-failure-cases`
- Engine D: `codex/task-claim-rewards-runtime-seam` -> `codex/task-guild-check-in-foundations`
- Optional Engine E: `codex/claim-rewards-goldens` -> `codex/claim-rewards-live-goldens`

## Non-Negotiable Rules

- maximum active engine worktrees: `4`
- optional temporary asset-capture worktree: `1`
- maximum active worktrees per engine: `1`
- each engine keeps its owned paths
- task engines do not start gameplay automation before platform Gate 3
