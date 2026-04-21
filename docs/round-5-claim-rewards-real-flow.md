# Round 5: Claim Rewards Real-Flow

## Goal

Turn `daily_ui.claim_rewards` from an MVP operator scaffold into the first real, repeatable in-game flow.

This round is not about adding more tasks. It is about making one fixed flow materially reliable.

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
- improve failure explanation quality from actual candidates/thresholds

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

Open a fresh worktree for this track. Do not reuse the currently dirty vision worktree.

Ownership:

- `assets/templates/`
- `tests/tasks/fixtures/`
- `docs/vision/`

Focus:

- collect and organize curated screenshots / goldens for claim rewards
- document what each image proves
- support the vision and task tracks with real inputs

Acceptance:

- curated assets exist for the claim-rewards happy path and at least one failure path

## Recommended order

1. Commit the current main changes first.
2. Start `Engine C` and `Engine D` together.
3. Start `Engine A` once the real failure/asset expectations are clearer.
4. Start `Engine B` after A/C/D have first outputs.
5. Use `Engine E` only if asset curation starts blocking C and D.

## Non-goals

- no second task
- no guild flow
- no Odin flow
- no navigation AI
- no combat logic
