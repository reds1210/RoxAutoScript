# Round 9: Guild Order Material Logic

## Status

This round is paused as of `2026-04-23`.

Reason:

- the last live-evidence pass did not follow the operator-described UI route precisely enough
- dispatch should not open new round-9 worker threads until a restart brief is published from the preserved operator truth below

This file is now a paused reference brief, not an active launch order.

Model note:

- the product and evidence content in this file is still useful
- any engine/worktree launch expectations should be treated as legacy and superseded by `docs/engine-roster.md` and `docs/worktree-playbook.md`

## Goal

Start the next bounded MVP wave after `claim_rewards` and keep scope tight.

This round is about the first truthful implementation path for guild orders with material-aware decision logic. When resumed, the wave should prove:

- the automation can reach the guild-order UI through deterministic navigation
- the task can classify visible guild-order requirement states honestly
- the task can decide `submit`, `skip`, or `refresh` using visible material evidence only
- runtime and PR handoff surfaces can explain what decision was made and why

This round is not about building the full resource-production loop.

## Preserved Operator Truth

Use this section as the canonical restart point for the next guild-order evidence pass.

Entry path from the main game screen:

1. open the collapsible logo button in the top-right area above the Facebook logo
2. choose `嘉年華`
3. choose `公會訂單`
4. tap `立即前往`
5. on the page with tabs such as `訊息`, `成就`, and `活動`, switch to `活動`
6. find the `公會訂單` card near the lower area of the page
7. tap the `前往` button inside that card

Guild-order scene truth after entry:

- the left side lists the required materials
- tapping a material row can highlight it
- the material image itself is not a stable detail-entry affordance and should not be treated as one
- the right side is the submission area
- if quantity is insufficient, the scene shows a `獲取` affordance
- `獲取` leads to a flow where tapping `立即購買` opens the purchase confirmation
- for the first guild-order round, purchase cost is expected to be `zeny`, not crystals
- quantity entry does not need to be tuned manually for the first-cut flow; direct purchase is acceptable
- do not use the `求助` button in this round

## First-Cut Scope

Round 9 stays limited to when resumed:

- guild-order list and detail UI detection
- stable guild-order anchors and scenes
- task-owned material-decision policy for already-visible materials
- runtime-owned outcome reporting for guild-order runs
- operator-facing surfacing only after lower-layer contracts settle

Round 9 explicitly does not include:

- auto-crafting
- generic or unrestricted auto-buying outside the explicit first-round `獲取 -> 立即購買` guild-order recovery path
- auto-gathering
- pathing
- OCR-heavy freeform parsing
- a second new task beyond guild-order submit/skip/refresh

## Execution Stability Rule

Guild-order exploration may temporarily use bounded coordinate probes to collect truthful live evidence, but those probes are not the production runtime contract.

For this round:

- coordinate-only tapping is acceptable only for screenshot-gated exploration or evidence collection
- every exploratory tap should be followed by an immediate screenshot and checkpoint classification
- if the observed checkpoint does not match the expected state, the worker should stop and record the mismatch instead of probing sideways

For future runnable automation:

- a guild-order task must not infer progress from tap coordinates alone
- every `detect -> act -> verify` step should verify the next checkpoint from screenshot, anchor, or other machine-readable visual evidence
- waiting for transitions should prefer bounded polling until the expected checkpoint appears or a timeout expires
- fixed sleeps may remain as small backoff defaults, but they must not be the only proof that the UI advanced
- fixed coordinate hotzones are acceptable only when the surrounding panel is already verified stable and the post-tap checkpoint is also verified immediately

This rule exists because emulator performance, animation timing, and device load can vary across machines even when the ADB serial, resolution, and route are nominally the same.

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

Validated local ADB serials on `2026-04-23`:

- `127.0.0.1:16416`
- `127.0.0.1:16448`
- `127.0.0.1:16480`
- `127.0.0.1:16512`

Observed MuMu window titles on the same machine:

- `舞孃-nxa`
- `Android Device-1-3`
- `鐵匠-zippoluo0202`
- `補師-reds.wang`

If a worker needs emulator access:

- first try the currently connected `adb` targets
- if the needed device is missing, inspect local MuMu windows and listening localhost ports
- attempt `adb connect` to likely MuMu ports before declaring capture blocked
- verify the chosen serial with a cheap command such as `adb -s <serial> get-state` before starting real work

Device reservation rule:

- do not let two active workers use the same ADB serial at the same time
- dispatch should assign device work by ADB serial, not by window title alone, unless the mapping was revalidated in that handoff
- if no free serial remains after local connect attempts, add an `Operator Questions` section to the PR or handoff and wait instead of racing another worker for the same device

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

Every new round-9 worker should read after dispatch publishes a restart brief:

1. `README.md`
2. `docs/rox-mvp-plan.md`
3. `docs/engine-roster.md`
4. `docs/worktree-playbook.md`
5. `docs/architecture-contracts.md`
6. this file
7. `docs/guild-order-material-logic-plan.md`
8. the relevant handoff under `docs/handoffs/`

Recommended round-9 prompt pack after a restart brief exists:

- `docs/prompts/round-9-thread-prompts.md`

## Non-Negotiable Rule

Round 9 stays scoped to the first-cut guild-order flow only when resumed.

Do not expand this round into crafting, gathering, buying, or generic inventory automation.
Do not launch new round-9 worker threads from this brief while it remains paused.
