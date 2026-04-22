# Round 9: Guild Order Material Logic

## Goal

Start the next bounded MVP wave after `claim_rewards` and keep scope tight.

This round is about the first truthful implementation path for guild orders with material-aware decision logic. The wave should prove:

- the automation can reach the guild-order UI through deterministic navigation
- the task can classify visible guild-order requirement states honestly
- the task can decide `submit`, `skip`, or `refresh` using visible material evidence only
- runtime and PR handoff surfaces can explain what decision was made and why

This round is not about building the full resource-production loop.

## First-Cut Scope

Round 9 stays limited to:

- guild-order list and detail UI detection
- stable guild-order anchors and scenes
- task-owned material-decision policy for already-visible materials
- runtime-owned outcome reporting for guild-order runs
- operator-facing surfacing only after lower-layer contracts settle

Round 9 explicitly does not include:

- auto-crafting
- auto-buying
- auto-gathering
- pathing
- OCR-heavy freeform parsing
- a second new task beyond guild-order submit/skip/refresh

## Canonical Task Direction

Tentative task target for this round:

- `daily_ui.guild_order_submit`

Meaning:

- submit when visible requirement and visible available materials satisfy policy
- skip when the visible order is blocked by policy or insufficient materials
- refresh when the visible order is unsuitable and refresh is allowed

## Device / Evidence Rule

If a worker captures live guild-order evidence during this round:

- record the exact ADB serial
- record the relevant guild-order state name
- do not promote a capture to canonical status unless the state contract is explicit

If visible material quantities or result states are not actually capturable from stable UI, preserve that as a gap instead of guessing.

## Worker Lineup

### Engine E

Focus:

- collect or classify the minimum live guild-order evidence matrix
- confirm which guild-order states are truly capturable
- keep provenance disciplined

Success:

- dispatch can answer which states are available, missing, or ambiguous

### Engine D

Focus:

- define the first spec/readiness path for `daily_ui.guild_order_submit`
- encode machine-readable material-decision reason ids
- keep task scope at deterministic `submit` / `skip` / `refresh`

Success:

- task contract is explicit without hiding missing assets or missing visible-count gaps

### Engine C

Focus:

- define or promote the truthful guild-order anchor and scene contract
- keep provenance machine-readable
- mark blocked or placeholder surfaces explicitly

Success:

- vision contract tells the truth about what the first guild-order cut can actually see

### Engine A

Focus:

- only start after Engine C and Engine D settle visible state and decision keys
- add runtime-owned guild-order outcome surfaces for PR handoff and later GUI use

Success:

- per-run guild-order outcomes are machine-readable without task-local reconstruction

### Engine B

Focus:

- only start after Engine A lands stable runtime signals
- surface guild-order decision and failure reasons clearly for operators

Success:

- GUI stays downstream of runtime/task truth instead of inventing local policy

## Launch Order

Recommended start order:

1. `Engine E`
2. `Engine D`
3. `Engine C`
4. review evidence and contracts in dispatch
5. then open `Engine A`
6. then open `Engine B`

## Merge Order

Recommended merge order:

1. `Engine E`
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

Reason:

- evidence should settle before promotion
- promoted truth should settle before task or runtime hardening
- GUI should remain the last consumer

## Relevant Docs

Every new round-9 worker should read:

1. `README.md`
2. `docs/rox-mvp-plan.md`
3. `docs/engine-roster.md`
4. `docs/worktree-playbook.md`
5. `docs/architecture-contracts.md`
6. this file
7. `docs/guild-order-material-logic-plan.md`
8. the relevant handoff under `docs/handoffs/`

Recommended round-9 prompt pack:

- `docs/prompts/round-9-thread-prompts.md`

## Non-Negotiable Rule

Round 9 stays scoped to the first-cut guild-order flow only.

Do not expand this round into crafting, gathering, buying, or generic inventory automation.
