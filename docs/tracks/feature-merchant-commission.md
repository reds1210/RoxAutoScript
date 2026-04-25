# Track Brief: Feature Merchant Commission

## Branch

- `codex/feature-merchant-commission-meow`

## Mission

Deliver the first complete `merchant commission -> meow group` feature slice as one branch outcome.

## Scope

- stable main-screen entry into the feature
- commission acceptance for the validated Meow Group slice
- truthful re-entry into the active round
- bounded material submission
- bounded round progression verification
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

- edits across these paths are allowed only when they all serve the merchant commission feature outcome

## Must Keep Local

- merchant route contract
- submit-panel logic
- round decision logic
- round progression verification

## Must Not Do

- widen scope to all five merchant groups
- extract shared navigation before guild order proves the same reuse
- move merchant-specific decision policy into a shared branch

## Done Means

- the branch can complete one bounded Meow Group loop truthfully
- the branch leaves machine-readable handoff artifacts
- any still-missing surfaces are recorded honestly instead of hidden
