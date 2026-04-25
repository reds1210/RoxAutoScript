# Round 8 Thread Prompts

Legacy note:

- this prompt pack describes the retired engine/worktree model
- use `docs/engine-roster.md`, `docs/worktree-playbook.md`, and `docs/prompts/feature-branch-thread-prompts.md` for new branch-first work

Use these prompts for new top-level Codex threads during the round-8 `claim_rewards` four-device-capture-promotion wave.

## Shared Opening

```text
You are working in a new top-level thread, not a subagent. Do not open subagents to replace the main work of this thread.

First read:
- README.md
- docs/worktree-playbook.md
- docs/engine-roster.md
- docs/architecture-contracts.md
- docs/round-8-claim-rewards-four-device-capture.md
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
- this round only advances daily_ui.claim_rewards
- do not expand to guild_check_in, odin, or a second task
- if you depend on another track, read main and handoffs instead of assuming you know another thread's chat history
```

## Engine E Prompt

```text
You are Engine E, responsible for live screenshots and goldens.
Branch: codex/claim-rewards-goldens
Worktree: C:\code\RoxAutoScript-wt-claim-rewards-goldens

Round-8 goals:
- use the four currently ADB-visible devices to collect disciplined live evidence for daily_ui.claim_rewards
- prioritize:
  - reward_panel_claimable
  - reward_confirm_modal
- keep raw evidence, file naming, and provenance clear enough for later promotion
- do not change core, app, or task logic
```

## Engine C Prompt

```text
You are Engine C, responsible for vision, templates, and failure inspection.
Branch: codex/vision-claim-rewards-live-captures
Worktree: C:\code\RoxAutoScript-wt-vision-claim-rewards-live

Round-8 goals:
- absorb approved four-device evidence into claim-rewards goldens/validation/provenance
- promote captures only when the contract can remain truthful
- keep GUI-facing flatten provenance/failure surfaces stable
```

## Engine D Prompt

```text
You are Engine D, responsible for tasks.
Branch: codex/task-claim-rewards-runtime-seam
Worktree: C:\code\RoxAutoScript-wt-task-claim-rewards-runtime

Round-8 goals:
- stay scoped to daily_ui.claim_rewards
- refresh foundations inventory/readiness only if asset provenance changes
- keep task-owned runtime seam and result-key contracts stable and machine-readable
```

## Engine A Prompt

```text
You are Engine A, responsible for runtime, emulator, profiles, and logs.
Branch: codex/core-runtime-step-telemetry
Worktree: C:\code\RoxAutoScript-wt-core-runtime-step-telemetry

Round-8 goals:
- only make runtime changes if new asset/provenance promotion creates a real need
- otherwise verify that runtime-owned telemetry already remains sufficient for claim_rewards
```

## Engine B Prompt

```text
You are Engine B, responsible for the app GUI.
Branch: codex/gui-claim-rewards-production-telemetry
Worktree: C:\code\RoxAutoScript-wt-gui-claim-rewards-production

Round-8 goals:
- keep daily_ui.claim_rewards as the only operator flow
- only change GUI if new provenance or capture promotion materially improves operator guidance
- otherwise verify and avoid inventing new app-owned state
```
