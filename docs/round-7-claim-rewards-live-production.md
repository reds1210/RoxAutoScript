# Round 7: Claim Rewards Live Production Validation

## Goal

Keep scope locked to `daily_ui.claim_rewards` and push it from a well-instrumented MVP into the first flow that is credible on repeated live-device runs.

This wave is not about adding a second task. It is about removing the remaining weak assumptions around:

- live ROX capture fidelity
- task/runtime registration seams
- runtime-owned failed-run telemetry
- GUI guidance that still depends on operator-facing reconstruction

## Starting Point

Current `main` already has:

- a zh-TW MVP GUI focused on `claim rewards`
- runtime-owned task run telemetry
- task-side `claim_rewards.v2` structured outcomes and failure reasons
- curated claim-rewards templates and goldens
- one live reward-panel baseline
- persisted calibration and capture settings under `profiles/`

Current known gaps:

- `daily_ui.claim_reward` and `daily_ui.reward_confirm_state` still rely on curated stand-ins rather than approved live zh-TW ROX captures
- runtime keeps sticky failure context, but it does not yet provide richer failed-run history for later inspection
- GUI still mixes production telemetry with some viewer-only/operator-aid guidance
- task/runtime seams are formalized, but they still need to become the only trusted production path

## Definition Of Done

Round 7 is done when:

- `daily_ui.claim_rewards` can be registered, enqueued, run, retried, and diagnosed without app-owned workflow state being the source of truth
- vision provenance clearly distinguishes `live_capture` from `curated_stand_in`
- runtime preserves enough failed-run detail that a later successful retry does not destroy the operator's ability to diagnose the earlier failure
- GUI can tell the operator which anchor, region, threshold, and step are blocking progress without branching on English message text

## Worktree Policy

Round 7 reuses the existing engine worktrees and branches:

- `Engine A` -> `codex/core-runtime-step-telemetry`
- `Engine B` -> `codex/gui-claim-rewards-production-telemetry`
- `Engine C` -> `codex/vision-claim-rewards-live-captures`
- `Engine D` -> `codex/task-claim-rewards-runtime-seam`
- optional `Engine E` -> `codex/claim-rewards-goldens`

Do not create a new worktree for the same engine unless the user explicitly asks for a rollover.

## Thread Lineup

### Engine C

Focus:

- replace or augment stand-in claim-rewards baselines with live zh-TW ROX captures
- keep the existing three-anchor contract stable:
  - `daily_ui.reward_panel`
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- improve provenance, readiness, and failure inspection fidelity without changing the flatten contract that GUI already consumes

Success:

- more claim-rewards assets move from `curated_stand_in` toward `live_capture`
- failure panes can trust anchor/reference provenance without extra GUI inference

### Engine D

Focus:

- keep `daily_ui.claim_rewards` as the only task in scope
- make the runtime seam explicit and machine-readable all the way from foundations to `TaskSpec`
- keep step outcome, failure reason, inspection attempt, and telemetry payloads deterministic and message-free
- keep readiness and foundations inventory aligned with the real curated/live asset set

Success:

- runtime can enqueue/build claim-rewards through task-owned seam metadata instead of hard-coded builder names
- downstream layers do not need to parse free-form step text

### Engine A

Focus:

- project task-owned structured failure and outcome data into runtime-owned telemetry and failure snapshots
- keep `active_task_run`, `last_task_run`, and `last_failure_snapshot` authoritative across retry/reconnect/restart-like flows
- expose enough state that GUI can stop inventing step history

Success:

- runtime becomes the only trusted source for in-flight and last-run claim-rewards state
- failed-run context survives later retries strongly enough for real operator debugging

### Engine B

Focus:

- keep `claim rewards` as the only main flow in the GUI
- consume runtime/task/vision signals directly
- make diagnostics and next-step guidance more concrete:
  - which anchor failed
  - which region matters
  - which threshold is effective
  - what the operator should inspect next
- keep calibration and capture tools viewer-first unless lower layers expose true production signals

Success:

- GUI reads like a single-task product console, not a debugger
- guidance is clearer, but still grounded in runtime/task/vision truth

### Optional Engine E

Open only when live screenshots/goldens become the primary blocker.

Focus:

- collect and organize live zh-TW ROX screenshots and goldens for claim-rewards
- preserve stable file names and golden ids whenever possible
- document exactly what each screenshot proves

Success:

- C and D can upgrade fidelity without changing contracts again

## Recommended Start Order

1. `Engine C`
2. `Engine D`
3. `Engine A`
4. `Engine B`
5. `Engine E` only when live capture collection is the blocker

## Recommended Merge Order

1. `Engine E` when used
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

## Out Of Scope

- any second task
- guild check-in implementation
- odin implementation
- free navigation
- combat logic
- broad OCR unrelated to claim-rewards
