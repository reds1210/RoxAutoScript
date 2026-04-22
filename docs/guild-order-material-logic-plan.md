# Guild Order Material Logic Plan

## Status

This document is a planning brief for the next bounded task wave.

It is not the active round yet.

Current repo ownership rules still keep the active round locked to `daily_ui.claim_rewards`. Do not launch new guild-order worker threads from this document until dispatch explicitly rolls the wave forward.

## Goal

Prepare a truthful first implementation path for in-game guild orders with material-aware decision logic.

The first cut should prove:

- the automation can reach the guild order UI through deterministic navigation
- the task can classify the visible order requirement and available action state
- the task can make an explicit decision using visible material evidence
- the runtime and PR handoff can explain why it submitted, skipped, or refreshed

## First-Cut Product Boundary

The first cut should mean:

- detect guild order list and detail screens
- read the current order requirement from stable UI signals
- determine whether the account already has enough materials to submit
- decide one of:
  - `submit`
  - `skip`
  - `refresh`
- verify the resulting state honestly

The first cut should not mean:

- auto-crafting missing materials
- auto-buying from exchange or NPCs
- auto-gathering or map pathing
- freeform OCR-heavy parsing without stable anchors
- hidden inventory inference from non-deterministic UI

If the UI does not provide a deterministic way to classify a material requirement or available quantity, the task should fail or skip honestly instead of guessing.

## Proposed Task Shape

Tentative pack and task naming:

- pack: `daily_ui`
- tentative task id: `daily_ui.guild_order_submit`

This keeps the scope aligned with the MVP strategy in [docs/rox-mvp-plan.md](/C:/code/RoxAutoScript/docs/rox-mvp-plan.md): fixed guild UI chores first, dynamic production chains later.

## Proposed Decision Contract

The eventual task implementation should expose machine-readable signals close to this shape:

### `GuildOrderRequirement`

Minimum fields:

- `slot_index`
- `material_label`
- `normalized_material_id` optional
- `required_quantity`
- `evidence`

### `GuildOrderAvailability`

Minimum fields:

- `material_label`
- `normalized_material_id` optional
- `available_quantity` optional
- `sufficiency`
- `evidence`

### `GuildOrderDecision`

Minimum fields:

- `decision`
- `reason_id`
- `slot_index`
- `requirements`
- `availability`
- `refresh_attempted`
- `verification_state`

Recommended `decision` values:

- `submit`
- `skip`
- `refresh`
- `abort`

Recommended `reason_id` values:

- `materials_sufficient`
- `materials_insufficient`
- `policy_blocked_material`
- `order_already_completed`
- `order_state_unknown`
- `refresh_not_allowed`
- `refresh_limit_reached`
- `submit_verification_failed`

## Policy Boundary For "Material Logic"

For this first cut, "material logic" should be limited to operator-configurable submission policy on already-visible materials.

Suggested policy surface:

- allowlist of material ids or labels that may be submitted
- blocklist of material ids or labels that should never be submitted
- reserve quantity per material
- whether refresh is allowed when a visible order is not acceptable
- max refresh attempts per run

Keep this policy machine-readable and task-owned. Do not push material policy into GUI-only state.

## Expected Vision Surfaces

The first live-capture wave should aim to classify these scenes or anchor roles:

- guild hub entry state
- guild order list
- guild order detail
- order submit affordance
- order refresh affordance
- already-completed or unavailable state
- insufficient-materials feedback state
- successful submission or accepted-order result state

If a stable inventory-count surface exists, capture it. If not, record that gap explicitly instead of pretending counts are available.

## Expected Runtime / Handoff Surfaces

When this wave becomes active, runtime-owned reporting should eventually preserve at least:

- instance id
- run id
- task id
- selected order slot
- material requirement summary
- availability summary
- decision
- decision reason id
- verification result
- last observed guild-order state

This is the minimum needed for PR handoff and later GUI consumption.

## Activation Gate

Do not activate this wave until dispatch confirms all of the following:

1. the current `claim_rewards` wave is closed or explicitly paused
2. the existing engine worktrees have been synced with `main`
3. dispatch has declared that the next user priority is guild orders
4. repo docs that define the active round have been rolled forward intentionally

This document intentionally does not edit [engine-roster.md](/C:/code/RoxAutoScript/docs/engine-roster.md) or [worktree-playbook.md](/C:/code/RoxAutoScript/docs/worktree-playbook.md). Those files should change only when dispatch officially starts the new wave.

## Reuse Policy

When this wave activates, reuse the existing engine branches and worktrees instead of creating a new worktree per engine:

- Engine A: `codex/core-runtime-step-telemetry`
- Engine B: `codex/gui-claim-rewards-production-telemetry`
- Engine C: `codex/vision-claim-rewards-live-captures`
- Engine D: `codex/task-claim-rewards-runtime-seam`
- Engine E: `codex/claim-rewards-goldens`

The engine names remain stable even when the task focus changes.

## Parallel Wave Shape

To preserve Codex parallelism without creating speculative churn, split the guild-order wave into two layers.

### Immediate Workers

Open these first after activation.

#### Engine E: Capture Matrix And Evidence Audit

- focus:
  - collect or classify live guild-order evidence across the required states
  - record exact device provenance
  - confirm whether visible material counts and result states are actually capturable
- must not:
  - edit runtime, GUI, or task logic

#### Engine C: Vision Contract And Anchor Inventory

- focus:
  - define truthful guild-order anchor roles and scene inventory
  - promote only the captures that satisfy the contract honestly
  - record missing or blocked surfaces explicitly
- must not:
  - fake task semantics to fit incomplete captures

#### Engine D: Task Blueprint And Material Decision Spec

- focus:
  - define the first spec-only task blueprint for guild-order submission
  - encode the material-decision model, reason ids, and readiness blockers
  - keep scope at deterministic submit/skip/refresh policy only
- must not:
  - require auto-craft, auto-buy, or pathing as hidden dependencies

### Conditional Follow-Up Workers

Open these only after the immediate workers settle the truth contract.

#### Engine A: Runtime Outcome Reporting

- trigger:
  - open after Engine D settles decision keys and Engine C settles visible state contracts
- focus:
  - add runtime-owned guild-order outcome surfaces for handoff and later GUI use

#### Engine B: Operator Surfacing

- trigger:
  - open after Engine A exposes stable runtime signals
- focus:
  - present guild-order decision and failure reasons clearly without rebuilding task logic in the GUI

## Recommended Launch And Merge Order

Recommended dispatch launch order after activation:

1. `Engine E`
2. `Engine D`
3. `Engine C`
4. review the result in the dispatch thread
5. then open `Engine A`
6. then open `Engine B`

Recommended merge order:

1. `Engine E`
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

This keeps raw evidence ahead of promoted truth, and promoted truth ahead of runtime or GUI hardening.

## Short Bootstrap Prompt

For any worker thread on this future wave, the dispatch thread can use this short bootstrap:

```text
You are on this branch. Read `AGENTS.md`, then read `docs/guild-order-material-logic-plan.md` and the handoff files it points to, then start the engine-specific task for your branch. Stay inside engine ownership, keep scope at first-cut guild-order submit/skip/refresh logic only, run `scripts/run-autonomy-loop.ps1`, and open or update one PR with a clear handoff.
```

## Copy-Paste Prompts

### Prompt: Engine E

```text
You are Engine E on branch `codex/claim-rewards-goldens`.

Goal: build the live evidence packet for the first guild-order material-logic wave without changing task/runtime/app behavior.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/guild-order-material-logic-plan.md
7. the latest guild-related handoff under docs/handoffs/

Rules:
- stay inside Engine E ownership
- do not edit runtime, task, or GUI code
- keep scope to guild-order evidence only
- record exact ADB serials for any new live captures
- if a stable count or result state is not actually visible, say so explicitly

Task:
- identify the minimum live guild-order scenes needed for the first cut
- capture or classify those scenes honestly
- produce a machine-readable evidence packet that tells dispatch which guild-order states are truly capturable

Deliverable:
- one PR
- updated handoff
- clear answer to which guild-order scenes are available, missing, or ambiguous
```

### Prompt: Engine D

```text
You are Engine D on branch `codex/task-claim-rewards-runtime-seam`.

Goal: define the first spec-only guild-order task contract and material-decision model without overpromising implementation.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/guild-order-material-logic-plan.md
7. docs/handoffs/task-daily-ui-foundations.md

Rules:
- stay inside Engine D ownership
- keep scope to deterministic guild-order submit/skip/refresh semantics
- do not assume auto-craft, auto-buy, or pathing
- prefer spec-only or readiness-first work if live evidence is still incomplete

Task:
- define a first guild-order task blueprint
- add or propose machine-readable material-decision reason ids
- encode truthful readiness blockers instead of hiding missing assets or missing visible counts

Deliverable:
- one PR
- updated handoff
- spec/readiness surfaces that make the eventual implementation path explicit
```

### Prompt: Engine C

```text
You are Engine C on branch `codex/vision-claim-rewards-live-captures`.

Goal: turn guild-order evidence into a truthful anchor and scene contract for the first material-logic wave.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/guild-order-material-logic-plan.md
7. the latest Engine E guild-order handoff if available

Rules:
- stay inside Engine C ownership
- do not change task/runtime/app semantics
- do not promote assets that do not satisfy the live contract honestly
- if a count surface or result surface is missing, preserve that as an explicit gap

Task:
- define or promote the minimum guild-order anchors and scene metadata needed by the first cut
- keep provenance machine-readable
- document which surfaces are blocked, placeholder, or ready

Deliverable:
- one PR
- updated handoff
- a truthful guild-order vision contract
```

### Prompt: Engine A

```text
You are Engine A on branch `codex/core-runtime-step-telemetry`.

Open this only after Engine C and Engine D settle the visible-state and decision-key contracts.

Goal: add runtime-owned guild-order outcome reporting for PR handoff and later GUI use.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/guild-order-material-logic-plan.md
7. the latest merged Engine C and Engine D guild-order handoffs

Rules:
- stay inside Engine A ownership
- do not add GUI-owned viewer logic
- keep the reporting machine-readable and task-agnostic where possible

Task:
- preserve guild-order decision and verification results in runtime-owned surfaces
- keep the signal quality high enough for PR handoff and future operator display

Deliverable:
- one PR
- updated handoff
- runtime-owned guild-order outcome reporting
```

### Prompt: Engine B

```text
You are Engine B on branch `codex/gui-claim-rewards-production-telemetry`.

Open this only after Engine A lands stable guild-order runtime signals.

Goal: surface guild-order decision and failure reasons clearly to operators without rebuilding task logic in the GUI.

Required read order:
1. README.md
2. docs/rox-mvp-plan.md
3. docs/engine-roster.md
4. docs/worktree-playbook.md
5. docs/architecture-contracts.md
6. docs/guild-order-material-logic-plan.md
7. the latest merged Engine A guild-order handoff

Rules:
- stay inside Engine B ownership
- consume runtime-owned and task-owned signals instead of reconstructing policy in the GUI

Task:
- add operator-facing guild-order decision and failure surfacing only after the lower-layer contracts are stable

Deliverable:
- one PR
- updated handoff
- clearer guild-order operator guidance
```

## Dispatch Note

When this wave activates, do not open all five workers at once.

Open:

- `Engine E`
- `Engine D`
- `Engine C`

Wait for evidence and contracts to settle.

Then decide whether to open:

- `Engine A`
- `Engine B`

This keeps parallelism high while still respecting truthful task scope and repo ownership.
