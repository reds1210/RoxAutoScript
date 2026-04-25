# Branch Playbook

This file keeps the historical path `docs/worktree-playbook.md` so existing read orders do not break.

Its content is now branch-first. Local worktree-based delivery is retired by default.

## 1. Purpose

This repo now supports parallel development through `git branch` with one local working directory.

The goals are:

- keep one authoritative local repo directory
- make branch ownership explicit
- let full game features ship through one branch when needed
- extract shared pieces only after reuse is proven
- keep handoffs readable without relying on chat history

## 2. Read Order

Every worker must read these files before editing:

1. `README.md`
2. `docs/rox-mvp-plan.md`
3. `docs/engine-roster.md`
4. `docs/worktree-playbook.md`
5. `docs/architecture-contracts.md`
6. the active feature or wave brief
7. the relevant handoff under `docs/handoffs/`

## 3. Thread And Branch Rules

- one top-level Codex thread maps to one delivery branch
- local work happens inside `C:\code\RoxAutoScript`
- do not treat subagents as replacements for top-level delivery branches
- cross-branch sync happens through `main`, PRs, handoffs, committed assets, and committed tests

Local branch hygiene:

- before creating or switching branches, confirm `git status` is clean
- if the tree is dirty, commit or stash before switching
- do not carry half-finished local changes across feature branches

## 4. Branch Model

The active branch roster is defined in `docs/engine-roster.md`.

Rule:

- one branch maps to one clear delivery scope
- feature branches may cross technical layers when all edits serve one feature outcome
- shared branches may only extract already-proven reuse

The active branch categories are:

- governance branch
- feature branch: merchant commission meow
- feature branch: guild order submit
- shared branch: entry navigation
- shared branch: material catalog

## 5. Ownership Rules

### Branch ownership map

- `codex/branch-model-feature-first`
  - owns repo workflow docs, branch rules, prompt packs, track briefs, and legacy script positioning

- `codex/feature-merchant-commission-meow`
  - owns `merchant_commission_*` feature outcomes across tasks, runtime integration, vision support, tests, docs, and handoffs

- `codex/feature-guild-order-submit`
  - owns `guild_order_*` feature outcomes across tasks, runtime integration, vision support, tests, docs, and handoffs

- `codex/shared-entry-navigation`
  - owns reusable entry routes, re-entry helpers, close/back handling, checkpoint packs, and shared route docs

- `codex/shared-material-catalog`
  - owns reusable material definitions, aliases, OCR/text-evidence normalization, and shared material docs or fixtures

### Shared files

Shared files remain high-conflict and must be changed carefully:

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `docs/architecture-contracts.md`
- active branch- or wave-level briefs

Rule:

- do not edit shared files unless the change is required for your branch outcome
- if you change a shared file, explain why in the handoff

## 6. Dependency Rules

The dependency direction is unchanged:

```text
app -> core/emulator/vision/tasks/profiles/logs
tasks -> core/emulator/vision/profiles/logs
vision -> core
emulator -> core
profiles -> core
logs -> core
```

Forbidden dependencies:

- `core` importing `app`
- `tasks` importing `app`
- `vision` importing `app`
- `emulator` importing `app`

Additional branch-first rule:

- a feature branch may touch multiple layers, but it still must not introduce forbidden import directions

## 7. Parallelism Rule

Local rule:

- one active local coding branch at a time

Parallel work is still allowed through:

- push current branch work, then switch cleanly to the next branch
- Codex cloud or other external execution lanes
- PR review and merge watch running separately from local coding

Do not assume local multi-worktree parallelism exists.

## 8. OCR And Evidence Rule

Recognition priority:

- use anchors or template matching first for fixed buttons, fixed panels, and fixed entry points
- use OCR or another bounded reader when the feature truly needs text such as material labels, counts, prices, or progress text
- if OCR is unstable, prefer a hybrid of bounded crop regions, color rules, layout rules, UI XML, or other structured evidence instead of pretending OCR is reliable

Evidence rule:

- preserve `raw_text`, `normalized_text`, `bbox`, `confidence`, `screenshot_ref`, and `reader` for text-driven decisions
- low-confidence text evidence must fall back to `skip`, `blocked`, or `stop_for_operator` unless another stronger checkpoint verifies the action safely
- shared material extraction must preserve aliases and source evidence instead of forcing one canonical material id too early

## 9. Branch Bootstrap Guide

Recommended local start flow:

1. `git status`
2. confirm the working tree is clean
3. `git switch main`
4. `git pull --ff-only`
5. `git switch -c codex/<branch-name>`
6. read the required docs
7. implement one bounded outcome

Example:

```powershell
git status
git switch main
git pull --ff-only
git switch -c codex/feature-merchant-commission-meow
```

If the branch already exists:

```powershell
git switch codex/feature-merchant-commission-meow
git merge main
git status
```

## 10. Handoff Rules

Every handoff must include:

- scope
- files changed
- public APIs added or changed
- assumptions
- blockers
- operator questions when device access or screenshots are required
- verification performed
- next recommended step

Use the template in:

- `docs/templates/worktree-handoff-template.md`

The template path is retained for compatibility even though local worktrees are no longer the default.

## 11. Conflict Rules

If two branches need the same file:

1. prefer feature-specific namespacing or shared helper extraction
2. if the logic is truly common, move it to the correct shared branch
3. otherwise, merge the earlier landed branch first and rebase or merge `main` into the later branch

Do not solve branch conflicts by silently rewriting another branch's intent.

## 12. Definition Of Done For A Branch

A branch is ready to merge when:

- it stays inside owned scope
- it does not violate dependency rules
- its docs are updated
- any contract changes are documented
- the next branch can continue without asking what changed
- the autonomy loop passes

## 13. Legacy Note

Older round plans, prompt packs, and historical handoffs may still mention the retired local worktree model.

Rule:

- treat those references as historical unless the file has been explicitly revised for branch-first delivery
- use this file and `docs/engine-roster.md` as the current authority

## 14. Non-Negotiable Rules

- one local repo directory
- one active local coding branch at a time
- keep the tree clean before switching branches
- do not couple tasks directly to GUI widgets
- do not hide contract changes inside unrelated commits
- do not edit another branch's owned area unless explicitly taking over that branch outcome
- always leave a readable handoff
- shared branches open only after reuse is proven
