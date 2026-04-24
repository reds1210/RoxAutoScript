# Merchant Commission Exploration Plan

## Status

This is a candidate exploration brief for a new ROX task line:

- `merchant commission`

It is not an active repo wave yet.

Use this document to start one dedicated exploration thread before any parallel implementation split.

## Local Repo Research

Research performed on `2026-04-23`:

- searched `docs/`, `src/`, `tests/`, and `assets/` for `commission` and `merchant`
- result: no existing merchant-commission task, task foundation, handoff, or asset scaffolding is present in this repo today
- current task foundations only cover:
  - `daily_ui.claim_rewards`
  - `daily_ui.guild_check_in`
  - `daily_ui.guild_order_submit`
  - `odin.odin_preset_entry`

Implication:

- `merchant commission` should start as a fresh exploration-first line
- do not pretend there is already a task contract or anchor inventory for it

## Goal

Discover whether `merchant commission` can become a truthful first-cut automation target inside the repo's MVP boundary.

The first exploration pass should answer:

- how to reach the `merchant commission` UI from a stable starting screen
- whether the route is mostly fixed UI or depends on dynamic gameplay or pathing
- what the main scene checkpoints are
- what actions are available on the target screens
- what should explicitly stay out of scope for the first cut

## First-Cut Product Boundary

Until the route is proven, keep the first cut conservative.

Allowed first-cut target shape:

- deterministic navigation into the `merchant commission` UI
- scene inventory and checkpoint naming
- identifying stable buttons, tabs, cards, and result states
- identifying whether the task is:
  - fixed-UI viable
  - partially fixed but blocked by dynamic gameplay
  - not a good MVP candidate yet

Do not assume the first cut includes:

- auto-combat
- freeform pathing
- auto-buying
- auto-crafting
- dynamic quest parsing
- OCR-heavy inference without stable anchors

If the feature requires those systems too early, the exploration thread should say so explicitly instead of forcing it into a fake MVP shape.

## Unknowns To Resolve

The exploration thread must treat these as open questions:

- exact entry route to `merchant commission`
- whether it opens from one fixed city UI flow or from multiple contextual surfaces
- whether completion requires movement, combat, shopping, or material delivery
- whether there is a deterministic accept or submit loop
- whether there are daily limits, refreshes, rerolls, or rank filters
- what the stable success and failure states look like

## Exploration Rules

Use exploration mode, not delivery mode.

Rules:

- one long-running top-level thread
- one branch
- one worktree
- one reserved emulator serial where possible
- no PR churn for every correction
- screenshot-gated navigation only
- ask the operator one short question when the route becomes ambiguous

Do not:

- open parallel workers yet
- invent task semantics before the route is understood
- commit to a final task id more specific than the evidence supports

## Device Note

The user wants the idle `dancer` emulator for this task.

The exploration thread should:

1. identify which connected ADB serial currently corresponds to the `dancer` emulator
2. reserve that serial for this exploration line
3. avoid sharing that serial with any other active worker

If the serial mapping is not obvious from screenshots, ask the operator one short confirmation question in-thread.

## Expected Exploration Output

A successful first exploration pass should produce:

- a named checkpoint list
- a short route brief
- explicit do-not-click notes
- a first answer to whether `merchant commission` is MVP-viable
- a recommendation for the next split:
  - `stay in exploration`
  - `promote to Engine E/C/D`
  - `reject as out-of-scope for MVP`

## Current Product Priority

Operator product guidance is now explicit:

- there are five merchant groups in the broader `merchant commission` feature
- only two are currently worth delivery effort:
  - `meow_group`
    - operator label: `喵手商團`
  - `kingdom_supply_group`
    - operator label: `王國軍需處`
- the other three merchant groups are future-scope only for now

Implications:

- do not normalize all five merchant groups into one first implementation
- finish `meow_group` truthfully first
- treat `kingdom_supply_group` as the second valuable exploration or delivery target
- keep the remaining three merchant groups explicitly deferred unless the user reprioritizes them later

## Tentative Naming

Do not treat these as final contracts yet.

Tentative pack direction:

- `daily_ui`

Tentative task family:

- `daily_ui.merchant_commission`

Only keep that naming if the exploration pass confirms the route is truly daily or fixed-UI enough.

## Suggested Next Split If Exploration Succeeds

Only after the exploration thread validates the route:

1. `Engine E`
   - capture live evidence and provenance
2. `Engine C`
   - define truthful scene and anchor contract
3. `Engine D`
   - define task blueprint and readiness blockers
4. then decide whether `Engine A` or `Engine B` should open

Suggested merchant-group order once exploration is sufficient:

1. `meow_group` / `喵手商團`
2. `kingdom_supply_group` / `王國軍需處`
3. keep the remaining three merchant groups out of implementation scope for now

## Branch And Worktree

Use this branch and worktree for the exploration thread:

- branch: `codex/merchant-commission-exploration`
- worktree: `C:\code\RoxAutoScript-wt-merchant-commission-exploration`

## Copy-Paste Prompt

```text
You are in merchant-commission exploration mode, not delivery mode.

First read:
- AGENTS.md
- README.md
- docs/dispatch-workflow.md
- docs/worktree-playbook.md
- docs/engine-roster.md
- docs/architecture-contracts.md
- docs/merchant-commission-exploration-plan.md
- current main

Work style:
- this is one long exploration thread, not a PR-per-blocker thread
- stay on the same branch and worktree for the whole exploration pass
- first identify which ADB serial is the user's idle dancer emulator, then reserve it
- only ask the operator one short question when truly blocked
- do not open subagents
- do not click speculatively
- use screenshot-gated navigation:
  1. capture a screen with ADB
  2. identify the current checkpoint
  3. click only when one intended target is clear
  4. capture the post-click screen immediately
  5. if the result is not the expected checkpoint, stop and ask instead of probing laterally
- do not open a PR, commit, or push until the route is validated and the operator explicitly says to switch to delivery mode

Goals for this pass:
- find the stable entry route for merchant commission
- build a truthful checkpoint pack
- decide whether it is fixed UI, semi-fixed, or out of MVP scope for now
- stay in exploration mode until the route is stable

Start with:
1. summarize the exploration rules, goals, and stop conditions
2. identify which connected ADB serial is the dancer emulator
3. capture the current screen
4. describe the current screen and whether it is a good starting point
5. explore step by step using screenshot-gated navigation only
6. if you hit ambiguity, ask one minimal operator question and wait
```
