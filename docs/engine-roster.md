# Engine Roster

This repo currently uses a fixed 4-engine parallel model plus one optional support engine.

The active wave is `round-9 guild-order material logic`.

## Model Policy

- default delegated model: `gpt-5.4`
- do not use mini variants for engine work unless the user explicitly asks for them
- each engine keeps a stable specialization
- for round 9, reuse the existing worktree and branch for the same engine instead of creating a new one

## Standard Engine Lineup

### Engine A: Runtime

- model: `gpt-5.4`
- branch: `codex/core-runtime-step-telemetry`
- worktree: `C:\code\RoxAutoScript-wt-core-runtime-step-telemetry`
- owns: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`, `tests/core/`, `tests/emulator/`, `tests/profiles/`
- may edit: `docs/architecture-contracts.md`

### Engine B: GUI

- model: `gpt-5.4`
- branch: `codex/gui-claim-rewards-production-telemetry`
- worktree: `C:\code\RoxAutoScript-wt-gui-claim-rewards-production`
- owns: `src/roxauto/app/`, `assets/ui/`, `tests/app/`

### Engine C: Vision

- model: `gpt-5.4`
- branch: `codex/vision-claim-rewards-live-captures`
- worktree: `C:\code\RoxAutoScript-wt-vision-claim-rewards-live`
- owns: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`, `tests/vision/`

### Engine D: Tasks

- model: `gpt-5.4`
- branch: `codex/task-claim-rewards-runtime-seam`
- worktree: `C:\code\RoxAutoScript-wt-task-claim-rewards-runtime`
- owns: `src/roxauto/tasks/`, `tests/tasks/`, task-specific foundations and task assets

### Optional Engine E: Goldens

- model: `gpt-5.4`
- branch: `codex/claim-rewards-goldens`
- worktree: `C:\code\RoxAutoScript-wt-claim-rewards-goldens`
- owns: `assets/templates/`, `tests/tasks/fixtures/`, `docs/vision/`
- open only when live screenshots or goldens become the primary blocker

## Active Order

Default round-9 start order:

1. `Engine E`
2. `Engine D`
3. `Engine C`
4. `Engine A`
5. `Engine B`

Default round-9 merge order:

1. `Engine E`
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

## Current Capture Rule

Round 9 may still use multiple ADB-visible devices for evidence work.

When a worker captures live evidence, the handoff should record the exact ADB serial used.

## Reuse Policy

- do not create a new worktree just because a new round started
- each engine should continue on its existing round-6/round-7/round-8/round-9 branch and worktree until the user explicitly asks for a branch rollover
- before starting a new thread on one of these engines, sync that worktree with `main`

## Non-Negotiable Rules

- maximum active primary engines: `4`
- optional support engine: `1`
- maximum active worktrees per engine: `1`
- each engine keeps its owned paths
- round 9 stays scoped to the first-cut guild-order flow only
