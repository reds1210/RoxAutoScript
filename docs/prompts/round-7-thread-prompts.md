# Round 7 Thread Prompts

Use these prompts for new top-level Codex threads during the round-7 `claim_rewards` live-production-validation wave.

Model:

- `gpt-5.4`

Important:

- each prompt is for one top-level thread, not a subagent
- each thread should stay on its dedicated existing worktree
- each thread should read `main`, handoffs, and the round-7 brief instead of assuming other thread chat history

## Worktree Map

- `Engine A` -> `C:\code\RoxAutoScript-wt-core-runtime-step-telemetry` -> `codex/core-runtime-step-telemetry`
- `Engine B` -> `C:\code\RoxAutoScript-wt-gui-claim-rewards-production` -> `codex/gui-claim-rewards-production-telemetry`
- `Engine C` -> `C:\code\RoxAutoScript-wt-vision-claim-rewards-live` -> `codex/vision-claim-rewards-live-captures`
- `Engine D` -> `C:\code\RoxAutoScript-wt-task-claim-rewards-runtime` -> `codex/task-claim-rewards-runtime-seam`
- `Engine E` optional -> `C:\code\RoxAutoScript-wt-claim-rewards-goldens` -> `codex/claim-rewards-goldens`

## Recommended Start Order

1. `Engine C`
2. `Engine D`
3. `Engine A`
4. `Engine B`
5. `Engine E` only if live capture collection is the blocker

## Shared Opening

Paste this first in each new thread:

```text
You are working in a new top-level thread, not a subagent. Do not open subagents to replace the main work of this thread.

First read:
- README.md
- docs/worktree-playbook.md
- docs/engine-roster.md
- docs/architecture-contracts.md
- docs/round-7-claim-rewards-live-production.md
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

## Engine C Prompt

```text
You are Engine C, responsible for vision, templates, and failure inspection.
Branch: codex/vision-claim-rewards-live-captures
Worktree: C:\code\RoxAutoScript-wt-vision-claim-rewards-live

Ownership:
- src/roxauto/vision/
- assets/templates/
- docs/vision/
- tests/vision/
- docs/handoffs/

Round-7 goals:
- improve daily_ui.claim_rewards using live zh-TW ROX captures where possible
- keep the three anchor ids stable:
  - daily_ui.reward_panel
  - daily_ui.claim_reward
  - daily_ui.reward_confirm_state
- preserve the flatten GUI-facing failure/inspection contract while improving the truth underneath it
- make provenance explicit: live_capture vs curated_stand_in vs placeholder
- keep readiness and validation aligned with the real curated/live state of assets

Do not touch:
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/tasks/
- src/roxauto/app/

Acceptance:
- claim_rewards baselines are more credible on real ROX scenes
- failure/inspection output remains directly consumable by GUI
- tests/vision pass
- handoff clearly says which assets are live and which are still stand-ins
```

## Engine D Prompt

```text
You are Engine D, responsible for tasks.
Branch: codex/task-claim-rewards-runtime-seam
Worktree: C:\code\RoxAutoScript-wt-task-claim-rewards-runtime

Ownership:
- src/roxauto/tasks/
- tests/tasks/
- docs/handoffs/

Round-7 goals:
- keep scope limited to daily_ui.claim_rewards
- make the runtime seam explicit and machine-readable from foundations through TaskSpec
- keep failure_reason_id, outcome_code, inspection_attempts, signals, telemetry, and task_action deterministic and message-free
- keep foundations inventory and readiness aligned with the current curated/live asset state

Do not touch:
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/app/
- src/roxauto/vision/
- do not start a second task

Acceptance:
- claim_rewards runtime seam is clearer and easier for runtime to consume
- downstream layers do not need to parse free-form step messages
- tests/tasks pass
- handoff clearly says which task-owned signals A and B should consume next
```

## Engine A Prompt

```text
You are Engine A, responsible for runtime, emulator, profiles, and logs.
Branch: codex/core-runtime-step-telemetry
Worktree: C:\code\RoxAutoScript-wt-core-runtime-step-telemetry

Ownership:
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/logs/
- src/roxauto/profiles/
- tests/core/
- tests/emulator/
- tests/profiles/
- may edit docs/architecture-contracts.md
- docs/handoffs/

Round-7 goals:
- project task-owned structured failure, outcome, and inspection data into runtime-owned telemetry
- keep active_task_run, last_task_run, and last_failure_snapshot authoritative across retry, reconnect, and restart-like flows
- reduce the need for GUI to invent task history
- strengthen the runtime registration/enqueue seam for claim_rewards without broad unrelated refactors

Do not touch:
- src/roxauto/app/
- src/roxauto/vision/
- src/roxauto/tasks/ task definitions

Acceptance:
- runtime telemetry is rich enough that GUI does not need to infer core task state
- sticky failure context survives retries strongly enough for real diagnosis
- tests/core and tests/emulator pass
- handoff clearly says which runtime signals B should consume next
```

## Engine B Prompt

```text
You are Engine B, responsible for the app GUI.
Branch: codex/gui-claim-rewards-production-telemetry
Worktree: C:\code\RoxAutoScript-wt-gui-claim-rewards-production

Ownership:
- src/roxauto/app/
- assets/ui/
- tests/app/
- docs/handoffs/

Round-7 goals:
- keep daily_ui.claim_rewards as the only main operator flow
- consume runtime, task, and vision signals directly instead of inventing app-owned workflow state
- improve diagnostics and next-step guidance so the operator can see:
  - which anchor failed
  - which region matters
  - which threshold is effective
  - what to inspect next
- keep calibration and capture tools viewer-first unless lower layers expose true production editing signals

Do not touch:
- src/roxauto/core/
- src/roxauto/emulator/
- src/roxauto/vision/
- src/roxauto/tasks/

Acceptance:
- GUI feels more like a single-task operator console than a debugger
- task state still comes from runtime/task/vision surfaces
- tests/app pass
- handoff clearly separates production telemetry from viewer-only/operator-aid surfaces
```

## Engine E Prompt

```text
You are Engine E, responsible for live screenshots and goldens.
Branch: codex/claim-rewards-goldens
Worktree: C:\code\RoxAutoScript-wt-claim-rewards-goldens

Ownership:
- assets/templates/
- tests/tasks/fixtures/
- docs/vision/

Round-7 goals:
- collect and organize live zh-TW ROX screenshots and goldens for daily_ui.claim_rewards
- preserve stable file names and golden ids whenever possible
- document what each image proves and which anchor/step/failure case it supports
- do not change core, app, or task logic

Acceptance:
- C and D can use the captured assets without changing contracts again
- docs/vision clearly documents provenance
- the work stays scoped to claim_rewards only
```
