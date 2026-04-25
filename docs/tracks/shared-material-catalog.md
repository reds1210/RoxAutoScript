# Track Brief: Shared Material Catalog

## Branch

- `codex/shared-material-catalog`

## Mission

Extract reusable material definitions and text-evidence formats only after multiple features prove the reuse.

## Scope

- shared `material_id` definitions
- alias tables and text normalization
- OCR/text evidence record shapes
- reusable material fixtures and supporting docs

## Allowed Paths

- `src/roxauto/tasks/foundations/materials/`
- `src/roxauto/core/`
- `tests/`
- `docs/`

## Entry Rule

Open this branch only after:

- merchant commission and guild order both expose overlapping material surfaces
- the overlap is backed by evidence, not naming guesses

## Must Not Do

- force-merge different materials under one id without proof
- move feature-specific policy into shared material definitions
- let low-confidence OCR drive feature actions directly

## Done Means

- shared material ids or aliases are backed by evidence
- OCR/text evidence records preserve source, confidence, and screenshot references
- feature branches can reuse the shared material catalog without losing feature-local decisions
