# Worktree Playbook

## 1. Purpose

This repo is meant to support parallel development with `git worktree`.

The goal is simple:

- each worktree should know exactly what it owns
- cross-track edits should be rare and explicit
- merges should happen in a predictable order
- handoffs should be readable without chat history

## 2. Read Order

Every worker must read these files before editing code:

1. `README.md`
2. `docs/rox-mvp-plan.md`
3. `docs/engine-roster.md`
4. `docs/worktree-playbook.md`
5. `docs/architecture-contracts.md`
6. the current round brief such as `docs/round-5-claim-rewards-real-flow.md`
7. the relevant handoff under `docs/handoffs/`

## 3. Engine Model

Rule: one worktree maps to one delivery track.

The standard roster is now 4 fixed engines, with one optional support engine for curated screenshots or goldens:

- `Engine A`: runtime and emulator execution
- `Engine B`: GUI and operator console
- `Engine C`: vision, calibration, and template tooling
- `Engine D`: task packs and plugin/event runtime
- `Engine E`: optional asset curation and goldens

Each track should produce:

- one clear scope
- one owned file set
- one focused branch history

Do not use one worktree for unrelated tasks.

Thread rule:

- one top-level Codex thread maps to one dedicated worktree
- do not treat subagents as replacements for these top-level delivery threads
- cross-thread sync happens through `main`, handoffs, and committed assets

Model policy:

- delegated engine work uses `gpt-5.4`
- do not use mini variants by default

## 4. Standard Engine Branches

Use these as the default active lineup:

- `codex/core-runtime-step-telemetry`
- `codex/gui-claim-rewards-production-telemetry`
- `codex/vision-claim-rewards-live-captures`
- `codex/task-claim-rewards-runtime-seam`

## 5. Naming Rules

### Branch names

Use the standard engine branches above first.

Later branch families:

- `codex/core-runtime-*`
- `codex/gui-console-*`
- `codex/vision-lab-*`
- `codex/task-*`
- `codex/plugin-event-framework`

If a track needs multiple phases, extend the name:

- `codex/core-runtime-registered-task-seam`
- `codex/gui-claim-rewards-operator-guidance`
- `codex/vision-claim-rewards-failure-cases`
- `codex/task-guild-check-in-foundations`
- `codex/claim-rewards-live-goldens`

### Local worktree folder names

Recommended sibling layout:

```text
C:\code\RoxAutoScript
C:\code\RoxAutoScript-wt-core-runtime-step-telemetry
C:\code\RoxAutoScript-wt-gui-claim-rewards-production
C:\code\RoxAutoScript-wt-vision-claim-rewards-live
C:\code\RoxAutoScript-wt-task-claim-rewards-runtime
```

Rule:

- keep worktree names short
- match the branch name closely
- avoid spaces

## 6. Ownership Rules

Each track owns a disjoint write area.

### Engine ownership map

- `Engine A`
  - owns: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`
  - may edit: `docs/architecture-contracts.md`

- `Engine B`
  - owns: `src/roxauto/app/`, `assets/ui/`

- `Engine C`
  - owns: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`

- `Engine D`
  - owns: `src/roxauto/tasks/`, `tests/tasks/`, task-specific assets under `assets/templates/`
  - gate: remains standby until platform Gate 3 is complete

- `Engine E`
  - owns: curated screenshots, goldens, and supporting vision docs only
  - gate: open only when asset collection blocks `Engine C` or `Engine D`

### Shared files

Shared files are high-conflict files and must be changed carefully:

- `README.md`
- `pyproject.toml`
- `docs/architecture-contracts.md`
- `docs/rox-mvp-plan.md`

Rule:

- do not edit shared files unless the change is required for your track
- if you change a shared file, explain why in the handoff

## 7. Dependency Rules

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

Reason:

- GUI must stay replaceable
- task packs must stay headless
- runtime logic must stay reusable in tests

## 8. Merge Order

For the current claim-rewards production-hardening wave, merge in this order unless there is a strong reason not to:

1. `Engine E` goldens branches when used
2. `Engine C` vision curation branches
3. `Engine D` first-task branches
4. `Engine A` runtime hardening branches
5. `Engine B` GUI/operator branches

Reason:

- live captures and task expectations should settle before runtime and GUI integrations harden around them

## 9. How To Start A Track

Recommended flow:

1. sync `main`
2. create a branch for exactly one track
3. create a worktree for that branch
4. read the track brief
5. confirm owned paths before editing
6. implement only inside owned paths whenever possible

Round-6 example:

```powershell
git switch main
git pull
git worktree add ..\RoxAutoScript-wt-core-runtime-step-telemetry -b codex/core-runtime-step-telemetry main
git worktree add ..\RoxAutoScript-wt-gui-claim-rewards-production -b codex/gui-claim-rewards-production-telemetry main
git worktree add ..\RoxAutoScript-wt-vision-claim-rewards-live -b codex/vision-claim-rewards-live-captures main
git worktree add ..\RoxAutoScript-wt-task-claim-rewards-runtime -b codex/task-claim-rewards-runtime-seam main
```

Optional support worktree:

```powershell
git worktree add ..\RoxAutoScript-wt-claim-rewards-goldens -b codex/claim-rewards-goldens main
```

## 10. Handoff Rules

Every handoff must include:

- scope
- files changed
- public APIs added or changed
- assumptions
- blockers
- verification performed
- next recommended step

Use the template in:

- `docs/templates/worktree-handoff-template.md`

## 11. Conflict Rules

If two tracks need the same file:

1. prefer moving the shared logic into the owner track
2. if that is not possible, the earlier merge-order engine edits it
3. the later track rebases after merge

Do not solve cross-track conflicts by silently rewriting another track's intent.

## 12. Definition Of Done For A Track

A track is ready to merge when:

- it stays inside owned scope
- it does not violate dependency rules
- its docs are updated
- its public contract changes are documented
- the next track can continue without asking what changed

## 13. Non-Negotiable Rules

- One worktree, one scope.
- One engine, one active worktree.
- Do not couple tasks directly to GUI widgets.
- Do not hide contract changes inside unrelated commits.
- Do not edit another track's owned area unless explicitly taking over that track.
- Always leave a readable handoff.
