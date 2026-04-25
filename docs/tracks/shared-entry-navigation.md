# Track Brief: Shared Entry Navigation

## Branch

- `codex/shared-entry-navigation`

## Mission

Extract only the entry and re-entry behavior that at least two feature branches already proved is reusable.

## Scope

- shared entry-route contracts
- shared checkpoint packs
- close/back/go-button helpers
- reusable re-entry helpers
- shared route documentation

## Allowed Paths

- `src/roxauto/tasks/foundations/navigation/`
- `src/roxauto/core/`
- `src/roxauto/emulator/`
- `tests/`
- `docs/`

## Entry Rule

Open this branch only after:

- merchant commission and guild order both prove the same reuse
- the reusable behavior can be described without feature-specific decision policy

## Must Not Do

- invent shared flows before feature branches validate them
- absorb merchant- or guild-specific decision rules
- rewrite feature-owned route notes without a documented reason

## Done Means

- the shared route contract is reusable by at least two features
- the extraction reduces duplication without weakening truthfulness
- feature branches can consume the helper without losing their local policy boundaries
