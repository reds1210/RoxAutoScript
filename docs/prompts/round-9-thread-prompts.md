# Round 9 Thread Prompts

Use these prompts for new top-level Codex threads during the round-9 guild-order material-logic wave.

## Shared Opening

```text
You are working in a new top-level thread, not a subagent. Do not open subagents to replace the main work of this thread.

First read:
- README.md
- docs/worktree-playbook.md
- docs/engine-roster.md
- docs/architecture-contracts.md
- docs/round-9-guild-order-material-logic.md
- docs/guild-order-material-logic-plan.md
- the relevant handoff under docs/handoffs/
- current main

Work style:
- summarize your understanding of the current state, ownership, dependencies, and risks in 5 to 10 sentences
- list the concrete items you will do in this round
- implement directly inside this thread's existing worktree
- run relevant tests
- update or add a handoff under docs/handoffs/
- finish with:
  - Changed files
  - Tests run
  - What shipped
  - Blockers
  - Recommended next step

Constraints:
- do not edit files outside your ownership
- this round only advances the first-cut guild-order flow
- do not expand to crafting, buying, gathering, pathing, or a second new task
- if you depend on another track, read main and handoffs instead of assuming you know another thread's chat history
```

## Engine E Prompt

```text
You are Engine E, responsible for live screenshots and goldens.
Branch: codex/claim-rewards-goldens
Worktree: C:\code\RoxAutoScript-wt-claim-rewards-goldens

Round-9 goals:
- collect or classify the minimum live guild-order evidence matrix
- prioritize:
  - guild-order list state
  - guild-order detail state
  - submit affordance
  - refresh affordance
  - insufficient-material or already-complete states if they are visible
- keep raw evidence, file naming, and provenance clear enough for later promotion
- do not change core, app, or task logic
```

## Engine D Prompt

```text
You are Engine D, responsible for tasks.
Branch: codex/task-claim-rewards-runtime-seam
Worktree: C:\code\RoxAutoScript-wt-task-claim-rewards-runtime

Round-9 goals:
- define the first spec/readiness path for the guild-order flow
- keep scope at deterministic submit / skip / refresh semantics
- encode machine-readable material-decision reason ids and policy boundaries
- do not assume crafting, buying, gathering, or pathing
```

## Engine C Prompt

```text
You are Engine C, responsible for vision, templates, and failure inspection.
Branch: codex/vision-claim-rewards-live-captures
Worktree: C:\code\RoxAutoScript-wt-vision-claim-rewards-live

Round-9 goals:
- turn guild-order evidence into a truthful anchor and scene contract
- promote captures only when the contract remains honest
- keep provenance machine-readable and blocked surfaces explicit
```

## Engine A Prompt

```text
You are Engine A, responsible for runtime, emulator, profiles, and logs.
Branch: codex/core-runtime-step-telemetry
Worktree: C:\code\RoxAutoScript-wt-core-runtime-step-telemetry

Open this only after Engine C and Engine D settle the visible-state and decision-key contracts.

Round-9 goals:
- add runtime-owned guild-order outcome reporting
- keep the reporting machine-readable and useful for PR handoff and later GUI use
- do not add GUI-owned viewer logic
```

## Engine B Prompt

```text
You are Engine B, responsible for the app GUI.
Branch: codex/gui-claim-rewards-production-telemetry
Worktree: C:\code\RoxAutoScript-wt-gui-claim-rewards-production

Open this only after Engine A lands stable guild-order runtime signals.

Round-9 goals:
- surface guild-order decision and failure reasons clearly for operators
- consume runtime-owned and task-owned signals instead of rebuilding policy in the GUI
```
