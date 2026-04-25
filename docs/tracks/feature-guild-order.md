# Track Brief: Feature Guild Order

## Branch

- `codex/feature-guild-order-submit`

## Mission

Deliver the first complete `guild order submit` feature slice as one branch outcome.

## Scope

- truthful route into guild-order list/detail
- truthful material-aware decision making
- bounded `submit / skip / refresh`
- truthful verification result recording
- feature-owned handoff and evidence updates

## Allowed Paths

- `src/roxauto/tasks/`
- `src/roxauto/core/`
- `src/roxauto/emulator/`
- `src/roxauto/vision/`
- `assets/templates/`
- `tests/`
- `docs/handoffs/`
- `docs/vision/`

Rule:

- edits across these paths are allowed only when they all serve the guild-order feature outcome

## Must Keep Local

- material policy
- decision rules
- custom-order logic
- verification result semantics

## Must Not Do

- add crafting, gathering, pathing, or generic buying
- move guild-specific policy into a shared branch
- claim a blocked surface is ready without evidence

## Done Means

- the branch truthfully outputs `submit`, `skip`, or `refresh`
- the branch records `reason_id` and `verification_state`
- any missing count, result, or OCR surface remains explicitly blocked
