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
6. the track brief under `docs/tracks/`

## 3. Engine Model

Rule: one worktree maps to one delivery track.

The standard roster is now 4 fixed engines:

- `Engine A`: runtime and emulator execution
- `Engine B`: GUI and operator console
- `Engine C`: vision, calibration, and template tooling
- `Engine D`: task packs and plugin/event runtime

Each track should produce:

- one clear scope
- one owned file set
- one focused branch history

Do not use one worktree for unrelated tasks.

Model policy:

- delegated engine work uses `gpt-5.4`
- do not use mini variants by default

## 4. Standard Engine Branches

Use these as the default active lineup:

- `codex/core-runtime-orchestration`
- `codex/gui-console-operator`
- `codex/vision-lab-calibration-tools`
- `codex/task-daily-ui`

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

- `codex/core-runtime-step-runner`
- `codex/gui-console-instance-grid`

### Local worktree folder names

Recommended sibling layout:

```text
C:\code\RoxAutoScript
C:\code\RoxAutoScript-wt-engine-a-runtime
C:\code\RoxAutoScript-wt-engine-b-gui
C:\code\RoxAutoScript-wt-engine-c-vision
C:\code\RoxAutoScript-wt-engine-d-tasks
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

Merge in this order unless there is a strong reason not to:

1. `Engine A` runtime branches
2. `Engine B` GUI branches
3. `Engine C` vision branches
4. `Engine D` task/plugin branches

Reason:

- later tracks depend on contracts from earlier tracks

## 9. How To Start A Track

Recommended flow:

1. sync `main`
2. create a branch for exactly one track
3. create a worktree for that branch
4. read the track brief
5. confirm owned paths before editing
6. implement only inside owned paths whenever possible

Example:

```powershell
git switch main
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-four-engines.ps1
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
