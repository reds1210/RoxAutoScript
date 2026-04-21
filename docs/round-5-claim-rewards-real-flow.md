# Round 5: Claim Rewards Real-Flow

## Goal

Turn `daily_ui.claim_rewards` from an MVP operator scaffold into the first real, repeatable in-game flow.

This round is not about adding more tasks. It is about making one fixed flow materially reliable.

## Current baseline

Current `main` already has:

- a zh-TW MVP operator console
- production session entry points and background runtime refresh surfaces
- persisted claim-rewards calibration/capture settings under `profiles/`
- one GUI-visible task: `每日領獎`
- claim-rewards display metadata, step telemetry, and failure/readiness panes

What is still missing is not platform skeleton. It is real-flow quality:

- curated screenshots and anchors
- runtime-owned step and failure signals that survive repeated runs
- cleaner operator guidance when a run blocks or fails
- task-side recovery and verification that do not depend on placeholder assumptions

## Definition of done

- The task runs through the real runtime path, not just app-side operator scaffolding.
- The flow uses curated claim-rewards assets instead of placeholder-only assumptions.
- Failure states are explainable from preview/failure panes without reading raw internals.
- The operator can save and reload calibration/capture settings for the task.
- A second machine/account can reuse the same flow after calibration instead of rebuilding it from scratch.

## Why this round

The platform is now sufficient to expose:

- runtime state
- queue/task execution
- preview/failure inspection
- task display metadata
- profile-backed calibration persistence

The remaining gap is game knowledge and curated assets. This round closes that gap for one narrow flow.

## Thread model

Use top-level Codex threads with one dedicated worktree per thread.

Round-5 standard threads:

- `Engine A` -> `codex/core-runtime-claim-rewards-hardening`
- `Engine B` -> `codex/gui-claim-rewards-operator-hardening`
- `Engine C` -> `codex/vision-claim-rewards-curation`
- `Engine D` -> `codex/task-claim-rewards-real-flow`

Optional support thread:

- `Engine E` -> `codex/claim-rewards-goldens`

Rules:

- do not use subagents as a replacement for these top-level threads
- each thread reads `main` plus handoffs; threads do not assume each other’s chat history
- sync happens through `main`, `docs/handoffs/`, and curated assets under `assets/templates/`

## Track layout

### Engine A

Branch: `codex/core-runtime-claim-rewards-hardening`

Ownership:

- `src/roxauto/core/`
- `src/roxauto/emulator/`
- `src/roxauto/logs/`
- `src/roxauto/profiles/`
- `tests/core/`
- `tests/emulator/`
- `tests/profiles/`

Focus:

- tighten task execution telemetry for `daily_ui.claim_rewards`
- expose stable run/step/failure surfaces for GUI consumption
- reduce app-owned assumptions in operator workflow
- keep execution path production-oriented

Acceptance:

- runtime emits enough signal that the GUI does not need to invent step state
- failure snapshots and previews remain stable after retries

### Engine B

Branch: `codex/gui-claim-rewards-operator-hardening`

Ownership:

- `src/roxauto/app/`
- `assets/ui/`
- `tests/app/`

Focus:

- make `每日領獎` the clear primary operator flow
- remove remaining mixed-language or engineering-facing copy
- replace app-side workflow assumptions with runtime/task telemetry where available
- keep calibration/inspection as secondary tools, not the main surface

Acceptance:

- the GUI reads like a product console for one task, not an internal debugger
- operator can tell what step failed and what to do next

### Engine C

Branch: `codex/vision-claim-rewards-curation`

Ownership:

- `src/roxauto/vision/`
- `assets/templates/`
- `docs/vision/`
- `tests/vision/`

Focus:

- curate real claim-rewards templates and failure cases
- replace placeholder-only assumptions for:
  - reward panel
  - claim reward button
  - confirm state
- improve failure explanation quality from actual candidates and thresholds

Acceptance:

- `daily_ui.claim_rewards` no longer depends only on placeholder anchors
- failure inspection is meaningful against real screenshots

### Engine D

Branch: `codex/task-claim-rewards-real-flow`

Ownership:

- `src/roxauto/tasks/`
- `tests/tasks/`

Focus:

- harden the claim-rewards state machine
- improve failure recovery and stop conditions for the existing five-step flow
- keep scope limited to `daily_ui.claim_rewards`

Acceptance:

- repeated runs do not rely on hand-wavy success assumptions
- step outcomes map cleanly to runtime/failure telemetry

### Optional Engine E

Branch: `codex/claim-rewards-goldens`

Open a fresh worktree for this track. Do not reuse a dirty or cross-owned worktree.

Ownership:

- `assets/templates/`
- `tests/tasks/fixtures/`
- `docs/vision/`

Focus:

- collect and organize curated screenshots and goldens for claim rewards
- document what each image proves
- support the vision and task tracks with real inputs

Acceptance:

- curated assets exist for the claim-rewards happy path and at least one failure path

## Recommended start order

1. Sync every active worktree to `main` before starting.
2. Start `Engine C` and `Engine D` together.
3. Start `Engine E` only if curated screenshots or goldens become the main blocker.
4. Start `Engine A` after C/D have made the claim-rewards failure model concrete.
5. Start `Engine B` last, once A/C/D outputs are clear enough to wire into the GUI.

## Default merge order

Use this order unless a narrower dependency forces a different one:

1. `Engine E` when it only contributes curated screenshots or goldens
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

Reason:

- curated assets and inspection expectations should stabilize before runtime and GUI integrations harden around them

## Handoff minimums

Every round-5 handoff must state:

- what changed specifically for `daily_ui.claim_rewards`
- whether the work still depends on placeholder anchors or curated assets
- what the operator will now see differently in the GUI
- what still blocks repeated real-flow runs
- whether a fresh worktree or fresh screenshots are required for the next track

## Out of scope for round 5

- second task enablement
- guild check-in implementation
- Odin implementation
- navigation AI
- combat logic
- broad OCR work outside the claim-rewards flow
- app-side reinvention of runtime or vision contracts

## Non-goals

- no second task
- no guild flow
- no Odin flow
- no navigation AI
- no combat logic
