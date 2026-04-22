# Route A Parallel Plan: Finish `daily_ui.claim_rewards`

## Goal

Finish the first MVP task truthfully without collapsing back to one worker at a time.

This wave stays locked to `daily_ui.claim_rewards` and uses the existing round-8 engine/worktree model. The main objective is:

- close the remaining `reward_confirm_state` truth gap
- measure real multi-device behavior instead of relying only on unit tests
- keep PR handoff quality high enough that the next Codex worker can continue from the PR alone

## Non-Negotiable Constraints

- do not start a second task
- reuse the existing round-8 engine branches and worktrees
- keep one top-level Codex thread per worktree
- do not cross ownership boundaries unless the task explicitly allows it
- rerun the repo autonomy loop in every worker before opening or updating a PR

## Current Truth

As of `main` at `5e789a7`:

- `daily_ui.reward_panel`: `live_capture`
- `daily_ui.claim_reward`: `live_capture`
- `daily_ui.reward_confirm_state`: still `curated_stand_in`
- task readiness for `daily_ui.claim_rewards`: `ready`
- remaining non-blocking warning: `daily_ui.reward_confirm_state` provenance only

The unresolved product/contract question is:

- should `reward_confirm_state` remain a strict confirm-modal contract
- or should the task/vision contract be broadened to accept the real post-claim result overlay now observed on live accounts

That decision should be made from evidence, not guesswork.

## Wave Shape

This route should run in two layers:

1. immediate parallel workers
2. conditional follow-up workers after the evidence and contract decision are clearer

### Immediate Parallel Workers

Open these first.

#### Engine E: Evidence And Capture Audit

- branch: `codex/claim-rewards-goldens`
- worktree: `C:\code\RoxAutoScript-wt-claim-rewards-goldens`
- focus:
  - verify the strongest four-device live evidence for post-tap behavior
  - keep raw/live provenance disciplined
  - capture more evidence only if it helps answer the confirm-state contract question
- must not:
  - edit runtime, GUI, or task logic

#### Engine C: Vision Contract Decision Packet

- branch: `codex/vision-claim-rewards-live-captures`
- worktree: `C:\code\RoxAutoScript-wt-vision-claim-rewards-live`
- focus:
  - turn current raw evidence into a truthful vision-side decision packet
  - either keep `reward_confirm_state` blocked with stronger machine-readable explanation
  - or promote a true live replacement if one really exists
- must not:
  - change task/runtime semantics just to make the evidence fit

#### Engine A: Runtime Smoke And Outcome Reporting

- branch: `codex/core-runtime-step-telemetry`
- worktree: `C:\code\RoxAutoScript-wt-core-runtime-step-telemetry`
- focus:
  - add a runtime-owned smoke/report surface for real claim-rewards runs
  - preserve per-instance outcome evidence so later decisions are based on real runs across devices
- must not:
  - invent app-owned viewer state
  - hard-code a final product decision about the confirm-state contract

### Conditional Follow-Up Workers

Do not open these until the immediate wave has produced evidence worth acting on.

#### Engine D: Task Contract Alignment

- branch: `codex/task-claim-rewards-runtime-seam`
- worktree: `C:\code\RoxAutoScript-wt-task-claim-rewards-runtime`
- trigger:
  - open after Engine C establishes the truthful contract direction
- focus:
  - align task readiness and task success/failure semantics with the chosen truth contract

#### Engine B: GUI Operator Surfacing

- branch: `codex/gui-claim-rewards-production-telemetry`
- worktree: `C:\code\RoxAutoScript-wt-gui-claim-rewards-production`
- trigger:
  - open after Engine A and/or Engine C land new runtime or vision truth surfaces
- focus:
  - show the final truth contract clearly to operators
  - surface smoke-run outcome summaries without rebuilding task logic in the GUI

## Why This Split Works

- Engine E can gather or classify evidence without waiting on code decisions.
- Engine C can prepare the truth contract from existing evidence without touching runtime or GUI.
- Engine A can improve real-run measurement in parallel because runtime-owned outcome reporting is useful under either contract outcome.
- Engine D and B should wait because changing task or GUI semantics before the contract is clear would create avoidable churn.

## Decision Gate

Before opening Engine D and B, dispatch should answer one question:

- observed post-tap live state should be treated as:
  - `strict_confirm_modal_only`
  - `direct_result_overlay_is_valid`

If the answer is still uncertain after the immediate wave, keep D and B paused and ask for a product decision instead of guessing.

## Launch Order

Recommended dispatch order:

1. `Engine E`
2. `Engine C`
3. `Engine A`
4. review results in the main dispatch thread
5. then open `Engine D` and `Engine B` only if the contract direction is clear

## Thread Startup Checklist

Every worker thread should begin with:

1. switch to the assigned worktree
2. merge `main`
3. confirm the worktree is clean
4. read:
   - `README.md`
   - `docs/rox-mvp-plan.md`
   - `docs/engine-roster.md`
   - `docs/worktree-playbook.md`
   - `docs/architecture-contracts.md`
   - `docs/round-8-claim-rewards-four-device-capture.md`
   - the worker's relevant handoff
5. implement only inside owned scope
6. run `scripts/run-autonomy-loop.ps1`
7. open or update one PR with a complete handoff

## Copy-Paste Prompts

### Prompt: Engine E

```text
You are Engine E on branch `codex/claim-rewards-goldens` in worktree `C:\code\RoxAutoScript-wt-claim-rewards-goldens`.

Goal: help finish Route A for `daily_ui.claim_rewards` by tightening the evidence around the remaining `reward_confirm_state` truth gap.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/round-8-claim-rewards-four-device-capture.md
7. docs/handoffs/claim-rewards-goldens.md
8. docs/handoffs/vision-claim-rewards-live-captures.md
9. docs/route-a-claim-rewards-parallel-plan.md

Rules:
- stay inside Engine E ownership only
- keep scope locked to `daily_ui.claim_rewards`
- do not edit runtime, task, or GUI code
- record exact ADB serials for any new evidence
- do not promote a raw capture to canonical status unless the evidence really satisfies the contract

Task:
- audit the current four-device raw/live evidence around post-claim behavior
- decide whether there is any true like-for-like live `reward_confirm_state` candidate
- if not, strengthen the evidence packet so dispatch can make the contract decision cleanly
- if useful and feasible, capture additional evidence locally
- update the relevant vision docs/handoff only inside your ownership

Deliverable:
- one PR
- updated handoff
- clear answer to: "do we have a true live confirm-modal capture yet?"

Before opening the PR:
- merge main
- confirm the worktree is clean
- run scripts/run-autonomy-loop.ps1
```

### Prompt: Engine C

```text
You are Engine C on branch `codex/vision-claim-rewards-live-captures` in worktree `C:\code\RoxAutoScript-wt-vision-claim-rewards-live`.

Goal: make the vision contract for `daily_ui.claim_rewards` decision-ready without faking product truth.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/round-8-claim-rewards-four-device-capture.md
7. docs/handoffs/vision-claim-rewards-live-captures.md
8. docs/handoffs/claim-rewards-goldens.md
9. docs/route-a-claim-rewards-parallel-plan.md

Rules:
- stay inside Engine C ownership
- keep scope locked to `daily_ui.claim_rewards`
- do not change task/runtime/app semantics just to match a preferred interpretation
- be explicit about whether `reward_confirm_state` remains blocked or can be promoted honestly

Task:
- review the current raw/live evidence and catalog state
- strengthen the machine-readable truth contract around `reward_confirm_state`
- either:
  - keep it as `curated_stand_in` with sharper supporting metadata and explanation
  - or promote a true live replacement if the evidence really supports it
- if appropriate, make the post-claim result overlay a first-class supporting surface without pretending it is the same as the current confirm-modal contract

Deliverable:
- one PR
- updated handoff
- a clear recommendation for dispatch: keep strict modal, or broaden the contract

Before opening the PR:
- merge main
- confirm the worktree is clean
- run scripts/run-autonomy-loop.ps1
```

### Prompt: Engine A

```text
You are Engine A on branch `codex/core-runtime-step-telemetry` in worktree `C:\code\RoxAutoScript-wt-core-runtime-step-telemetry`.

Goal: add runtime-owned smoke/outcome reporting for real `daily_ui.claim_rewards` runs so Route A can be decided from evidence across devices.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/round-8-claim-rewards-four-device-capture.md
7. docs/handoffs/core-runtime-claim-rewards.md
8. docs/handoffs/task-daily-ui-claim-rewards.md
9. docs/route-a-claim-rewards-parallel-plan.md

Rules:
- stay inside Engine A ownership
- keep scope locked to `daily_ui.claim_rewards`
- do not add app-owned viewer logic
- do not assume the final product decision for `reward_confirm_state`

Task:
- add a bounded runtime-owned surface for smoke-run or run-summary reporting
- preserve per-instance evidence useful for dispatch:
  - instance id
  - run id
  - final status
  - outcome code
  - failure reason id
  - last observed post-tap state when available
  - key anchor ids or workflow hints when available
- keep it machine-readable and suitable for later GUI or PR handoff consumption

Deliverable:
- one PR
- updated handoff
- a runtime-owned artifact or summary surface that makes four-device comparison easier

Before opening the PR:
- merge main
- confirm the worktree is clean
- run scripts/run-autonomy-loop.ps1
```

### Prompt: Engine D

```text
You are Engine D on branch `codex/task-claim-rewards-runtime-seam` in worktree `C:\code\RoxAutoScript-wt-task-claim-rewards-runtime`.

Open this thread only after dispatch confirms the Route A contract direction from Engine C.

Goal: align `daily_ui.claim_rewards` task behavior and readiness with the chosen truth contract.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/round-8-claim-rewards-four-device-capture.md
7. docs/handoffs/task-daily-ui-claim-rewards.md
8. the latest merged Engine C handoff
9. docs/route-a-claim-rewards-parallel-plan.md

Rules:
- stay inside Engine D ownership
- keep scope locked to `daily_ui.claim_rewards`
- do not touch runtime or GUI unless dispatch explicitly reassigns scope

Task:
- update task contract/readiness only after the vision truth contract is clear
- preserve machine-readable outcomes and handoff quality

Deliverable:
- one PR
- updated handoff
- task contract aligned with the chosen truth

Before opening the PR:
- merge main
- confirm the worktree is clean
- run scripts/run-autonomy-loop.ps1
```

### Prompt: Engine B

```text
You are Engine B on branch `codex/gui-claim-rewards-production-telemetry` in worktree `C:\code\RoxAutoScript-wt-gui-claim-rewards-production`.

Open this thread only after dispatch confirms that new runtime or vision truth surfaces are ready from Engine A and/or Engine C.

Goal: surface the final Route A truth clearly in the operator console without rebuilding task logic in the GUI.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/round-8-claim-rewards-four-device-capture.md
7. docs/handoffs/gui-console-operator.md
8. the latest merged Engine A and Engine C handoffs
9. docs/route-a-claim-rewards-parallel-plan.md

Rules:
- stay inside Engine B ownership
- keep scope locked to `daily_ui.claim_rewards`
- prefer runtime-owned and vision-owned signals over app-local reconstruction

Task:
- reflect the final contract truth and smoke-run evidence clearly for operators
- avoid inventing app-local workflow state

Deliverable:
- one PR
- updated handoff
- clearer operator-facing truth around claim flow status

Before opening the PR:
- merge main
- confirm the worktree is clean
- run scripts/run-autonomy-loop.ps1
```

## Dispatch Note

The main dispatch thread should not open all five workers at once.

Open:

- `Engine E`
- `Engine C`
- `Engine A`

Wait for evidence.

Then decide whether to open:

- `Engine D`
- `Engine B`

This keeps Codex parallelism high without paying for speculative churn.
