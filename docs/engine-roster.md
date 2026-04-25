# Engine Roster

This repo now uses a branch-first delivery model.

The word `engine` is retained for historical continuity, but the active repo workflow is:

- one local working directory: `C:\code\RoxAutoScript`
- one active local coding branch at a time
- feature branches for complete game features
- shared branches only after at least two feature branches prove real reuse

## Model Policy

- default delegated model: `gpt-5.4`
- do not use mini variants for primary feature or shared branch work unless the user explicitly asks for them
- feature branches may cross `tasks`, `vision`, `runtime`, `tests`, and docs when the edits all serve one feature outcome
- shared branches must not invent feature semantics; they only extract already-proven reuse

## Standard Branch Lineup

### Governance Branch

- branch: `codex/branch-model-feature-first`
- role: repo workflow, branch rules, dispatch rules, briefs, prompts, and legacy-script positioning
- owns:
  - `AGENTS.md`
  - `README.md`
  - `docs/engine-roster.md`
  - `docs/worktree-playbook.md`
  - `docs/dispatch-workflow.md`
  - `docs/tracks/`
  - `docs/prompts/`
  - legacy helper scripts that still mention worktrees

### Feature Branch: Merchant Commission Meow

- branch: `codex/feature-merchant-commission-meow`
- role: full `merchant commission -> meow group` delivery slice
- owns:
  - `merchant_commission_*` task/runtime/vision surfaces
  - merchant-commission-specific assets, tests, docs, and handoffs
- keeps local feature-specific control of:
  - route contract
  - submit-panel inspection
  - round decision
  - progression verification

### Feature Branch: Guild Order Submit

- branch: `codex/feature-guild-order-submit`
- role: full `guild order submit` delivery slice
- owns:
  - `guild_order_*` task/runtime/vision surfaces
  - guild-order-specific assets, tests, docs, and handoffs
- first-cut boundary:
  - `submit`
  - `skip`
  - `refresh`
- keeps local feature-specific control of:
  - material policy
  - decision contract
  - custom-order logic
  - verification results

### Shared Branch: Entry Navigation

- branch: `codex/shared-entry-navigation`
- role: extract reusable entry, re-entry, close, back, go-button, and checkpoint behavior
- opens only after:
  - merchant commission and guild order both prove the same navigation segment is truly reusable
- owns:
  - shared entry-route contracts
  - shared checkpoint definitions
  - navigation helpers used by multiple features

### Shared Branch: Material Catalog

- branch: `codex/shared-material-catalog`
- role: extract reusable material definitions and evidence formats
- opens only after:
  - merchant commission and guild order both prove the same material or text-evidence surfaces are reusable
- owns:
  - shared material ids and aliases
  - normalization rules for text evidence
  - OCR/evidence record formats
  - shared material definitions and supporting fixtures

## Launch Order

Default launch order for the current branch-first model:

1. `codex/branch-model-feature-first`
2. `codex/feature-merchant-commission-meow`
3. `codex/feature-guild-order-submit`
4. `codex/shared-entry-navigation`
5. `codex/shared-material-catalog`

Rule:

- do not open shared branches before reuse is proven by at least two feature branches

## Merge Policy

- merge the governance branch first when the workflow itself changes
- merge feature branches one bounded outcome at a time
- merge shared branches only after the source feature behavior has already been validated and documented
- before switching to a new local branch, the current working tree must be clean

## Current Device Rule

- assign emulator work by exact ADB serial, not by window title alone
- do not let two active workers use the same serial at the same time
- if a branch captures live evidence, record the exact serial in the handoff

Validated local ADB serial inventory remains:

- `127.0.0.1:16416`
- `127.0.0.1:16448`
- `127.0.0.1:16480`
- `127.0.0.1:16512`

## Non-Negotiable Rules

- one local repo directory
- one active local coding branch at a time
- keep the working tree clean before switching branches
- feature branches own complete feature outcomes, not just one technical layer
- shared branches must stay strictly reusable and feature-agnostic
- do not reopen the retired local multi-worktree model unless the repo owner explicitly asks for it
