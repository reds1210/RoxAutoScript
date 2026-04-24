# Handoff: Merchant Commission Exploration

Track:

- `codex/merchant-commission-exploration`

Scope:

- documented the first truthful `商會委託` exploration result on the reserved `舞孃` emulator serial:
  - `127.0.0.1:16416`
- kept scope to the currently validated route only:
  - `商會委託 -> 喵手商團`
- recorded the stable entry route, checkpoint pack, do-not-click rules, and MVP assessment
- did not add runtime code, task foundations, template manifests, or GUI wiring
- did not generalize across the other four `商團列表` choices

Files changed:

- `docs/handoffs/merchant-commission-exploration.md`
- `docs/vision/merchant_commission_meow/README.md`

Public APIs added or changed:

- none

Contract changes:

- docs-only truthful route contract for the currently validated `商會委託` slice
- current preferred post-accept route is now explicit:
  - after one commission is accepted, re-entry should come from the left task list
  - do not re-open `嘉年華 -> 商會委託` for every round
- current truthful answer is intentionally bounded:
  - stable fixed-UI entry into `商會委託`
  - semi-fixed `喵手商團` submission loop
  - other merchant groups remain open exploration items

Assumptions:

- `舞孃-nxa` was correctly mapped to `127.0.0.1:16416` during this pass
- the current truthful route is limited to `喵手商團`
- later work may still split the broader `商會委託` line into smaller delivery slices instead of treating all five merchant groups as one task

Verification performed:

- screenshot-gated navigation on `127.0.0.1:16416`
- validated stable route:
  - `主畫面 -> 波利活動按鈕 -> 嘉年華 -> 商會委託 -> 立即前往 -> 商會 NPC -> 商團列表 -> 喵手商團`
- validated stable post-accept route:
  - `左側 [日常] 商會委託 -> NPC 專用交付選項 -> 上交道具 -> 立即購買 -> 購買 -> 交付`
- validated two completed `喵手商團` rounds and observed auto-advance into `3/10`
- repo autonomy loop:
  - `python -m roxauto quality-gate --output runtime_logs/autonomy/quality-gate.json`
  - `python -m roxauto agent-packet --quality-gate runtime_logs/autonomy/quality-gate.json --output runtime_logs/autonomy/agent-packet.json`
  - `python -m roxauto handoff-brief --quality-gate runtime_logs/autonomy/quality-gate.json --agent-packet runtime_logs/autonomy/agent-packet.json --output runtime_logs/autonomy/handoff-brief.md`

Known limitations:

- only `喵手商團` is documented truthfully in this handoff
- the other merchant groups were not normalized into route contracts in this pass:
  - `卡普拉`
  - `准它社`
  - `威格納`
  - `王國軍需處`
- only the first two completed rounds of the `喵手商團` loop were verified end to end
- the work stops at exploration handoff and does not yet create task/runtime code

Blockers:

- no blocker for the documentation handoff itself
- broader `商會委託` implementation is still blocked on scope choice:
  - deliver `喵手商團` only first
  - or continue exploration for the other four merchant groups before generalizing

Recommended next step:

- if the user wants delivery next, keep the first cut intentionally narrow:
  - one bounded slice for `商會委託 -> 喵手商團`
- treat the current truthful behavior as:
  - fixed-UI entry
  - semi-fixed 10-round material submission loop
- keep the other merchant groups explicitly out of the first implementation until they have their own validated checkpoint packs

## Product Priority Follow-Up

Additional operator product guidance recorded after this exploration pass:

- the broader merchant-commission feature contains five merchant groups
- only two are currently worth delivery effort:
  - `喵手商團`
  - `王國軍需處`
- the remaining three merchant groups should stay in future-scope planning only

Delivery order from this point:

1. keep the first delivery slice on `喵手商團`
2. after that slice is stable, make `王國軍需處` the next merchant-group exploration or delivery target
3. keep the remaining three merchant groups out of implementation scope until the user reprioritizes them
