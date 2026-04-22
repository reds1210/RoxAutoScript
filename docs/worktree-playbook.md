# Worktree Playbook

## 1. Purpose

This repo is meant to support parallel development with `git worktree`.

The goals are:

- each worktree knows exactly what it owns
- cross-track edits stay rare and explicit
- merges happen in a predictable order
- handoffs remain readable without chat history

## 2. Read Order

Every worker must read these files before editing:

1. `README.md`
2. `docs/rox-mvp-plan.md`
3. `docs/engine-roster.md`
4. `docs/worktree-playbook.md`
5. `docs/architecture-contracts.md`
6. the active round brief, currently `docs/round-9-guild-order-material-logic.md`
7. the relevant handoff under `docs/handoffs/`

## 3. Thread and Worktree Rules

- one top-level Codex thread maps to one dedicated worktree
- do not treat subagents as replacements for these top-level delivery threads
- cross-thread sync happens through `main`, handoffs, committed assets, and committed tests

For the current wave:

- reuse the existing engine worktree for the same engine
- do not create a new worktree for the same engine unless the user explicitly asks for a branch rollover
- before a new thread starts work, sync that engine worktree with `main`

## 4. Engine Model

Rule: one worktree maps to one delivery track.

The standard roster is:

- `Engine A`: runtime and emulator execution
- `Engine B`: GUI and operator console
- `Engine C`: vision, calibration, and template tooling
- `Engine D`: tasks and task foundations
- `Engine E`: optional asset curation and goldens

Model policy:

- delegated engine work uses `gpt-5.4`
- do not use mini variants by default

## 5. Active Round Branches

Use these existing branches and worktrees for round 9:

- `codex/core-runtime-step-telemetry`
- `codex/gui-claim-rewards-production-telemetry`
- `codex/vision-claim-rewards-live-captures`
- `codex/task-claim-rewards-runtime-seam`
- optional: `codex/claim-rewards-goldens`

Do not fork a fresh branch for the same engine just because a new thread starts.

## 6. Worktree Paths

Current recommended sibling layout:

```text
C:\code\RoxAutoScript
C:\code\RoxAutoScript-wt-core-runtime-step-telemetry
C:\code\RoxAutoScript-wt-gui-claim-rewards-production
C:\code\RoxAutoScript-wt-vision-claim-rewards-live
C:\code\RoxAutoScript-wt-task-claim-rewards-runtime
C:\code\RoxAutoScript-wt-claim-rewards-goldens
```

## 7. Ownership Rules

### Engine ownership map

- `Engine A`
  - owns: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`
  - may edit: `docs/architecture-contracts.md`

- `Engine B`
  - owns: `src/roxauto/app/`, `assets/ui/`

- `Engine C`
  - owns: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`

- `Engine D`
  - owns: `src/roxauto/tasks/`, `tests/tasks/`, task-specific foundations, task-specific assets

- `Engine E`
  - owns: curated screenshots, goldens, fixture examples, and supporting vision docs only

### Shared files

Shared files are high-conflict files and must be changed carefully:

- `README.md`
- `pyproject.toml`
- `docs/architecture-contracts.md`
- current round brief under `docs/round-*.md`

Rule:

- do not edit shared files unless the change is required for your track
- if you change a shared file, explain why in the handoff

## 8. Dependency Rules

The dependency direction is fixed:

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

## 9. Merge Order

For round 9, merge in this order unless there is a strong reason not to:

1. `Engine E`
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

Reason:

- raw/live evidence should settle before vision promotion
- promoted truth should settle before task/runtime hardening
- GUI should harden around the final downstream contract, not around provisional notes

## 9a. Device Capture Rule

Round 9 may still use multiple ADB-visible devices when evidence capture is required.

When a worker captures evidence:

- record the exact serial in the handoff
- prefer fixed device roles instead of random screenshot collection when more than one device is involved
- do not promote a raw capture to canonical status unless provenance is explicit and the target scene contract is satisfied

If a worker needs emulator access and `adb devices` does not already show the expected target:

- do not stop at the first empty `adb devices` result
- inspect local MuMu processes and listening localhost ports first
- attempt `adb connect` against the likely MuMu ADB ports before declaring capture blocked
- record the connection attempts and final result in the handoff

Device reservation rule:

- one active worker must not share the same ADB serial with another active worker
- dispatch should assign a primary ADB serial per worker whenever emulator work is required
- if a worker cannot identify a free device after local connect attempts, stop and raise an explicit operator question instead of guessing

## 10. How To Start A Thread

Recommended flow:

1. switch to the engine's existing worktree
2. `git merge main`
3. confirm the worktree is clean
4. read the active round brief
5. confirm owned paths before editing
6. implement only inside owned paths whenever possible

Example:

```powershell
cd C:\code\RoxAutoScript-wt-vision-claim-rewards-live
git merge main
git status
```

## 11. Handoff Rules

Every handoff must include:

- scope
- files changed
- public APIs added or changed
- assumptions
- blockers
- operator questions when device access, screenshots, or other external input is required
- verification performed
- next recommended step

Use the template in:

- `docs/templates/worktree-handoff-template.md`

## 12. Conflict Rules

If two tracks need the same file:

1. prefer moving the shared logic into the owner track
2. if that is not possible, the earlier merge-order engine edits it
3. the later track rebases or merges `main` after the earlier change lands

Do not solve cross-track conflicts by silently rewriting another track's intent.

## 13. Definition Of Done For A Track

A track is ready to merge when:

- it stays inside owned scope
- it does not violate dependency rules
- its docs are updated
- its public contract changes are documented
- the next track can continue without asking what changed

## 14. Non-Negotiable Rules

- one worktree, one scope
- one engine, one active worktree
- do not couple tasks directly to GUI widgets
- do not hide contract changes inside unrelated commits
- do not edit another track's owned area unless explicitly taking over that track
- always leave a readable handoff
- round 9 stays scoped to the first-cut guild-order flow only
