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
3. `docs/worktree-playbook.md`
4. `docs/architecture-contracts.md`
5. the track brief under `docs/tracks/`

## 3. Worktree Model

Rule: one worktree maps to one delivery track.

Current delivery tracks:

- `codex/core-runtime`
- `codex/gui-console`
- `codex/vision-lab`
- `codex/task-daily-ui`
- `codex/task-odin`

Each track should produce:

- one clear scope
- one owned file set
- one focused branch history

Do not use one worktree for unrelated tasks.

## 4. Naming Rules

### Branch names

Use:

- `codex/core-runtime`
- `codex/gui-console`
- `codex/vision-lab`
- `codex/task-daily-ui`
- `codex/task-odin`

If a track needs multiple phases, extend the name:

- `codex/core-runtime-step-runner`
- `codex/gui-console-instance-grid`

### Local worktree folder names

Recommended sibling layout:

```text
C:\code\RoxAutoScript
C:\code\RoxAutoScript-wt-core-runtime
C:\code\RoxAutoScript-wt-gui-console
C:\code\RoxAutoScript-wt-vision-lab
```

Rule:

- keep worktree names short
- match the branch name closely
- avoid spaces

## 5. Ownership Rules

Each track owns a disjoint write area.

### Track ownership map

- `codex/core-runtime`
  - owns: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`
  - may edit: `docs/architecture-contracts.md`

- `codex/gui-console`
  - owns: `src/roxauto/app/`, `assets/ui/`

- `codex/vision-lab`
  - owns: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`

- `codex/task-daily-ui`
  - owns: `src/roxauto/tasks/daily_ui/`, `assets/templates/daily_ui/`

- `codex/task-odin`
  - owns: `src/roxauto/tasks/odin/`, `assets/templates/odin/`

### Shared files

Shared files are high-conflict files and must be changed carefully:

- `README.md`
- `pyproject.toml`
- `docs/architecture-contracts.md`
- `docs/rox-mvp-plan.md`

Rule:

- do not edit shared files unless the change is required for your track
- if you change a shared file, explain why in the handoff

## 6. Dependency Rules

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

## 7. Merge Order

Merge in this order unless there is a strong reason not to:

1. `codex/core-runtime`
2. `codex/gui-console`
3. `codex/vision-lab`
4. `codex/task-daily-ui`
5. `codex/task-odin`

Reason:

- later tracks depend on contracts from earlier tracks

## 8. How To Start A Track

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
git worktree add ..\RoxAutoScript-wt-core-runtime -b codex/core-runtime
```

## 9. Handoff Rules

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

## 10. Conflict Rules

If two tracks need the same file:

1. prefer moving the shared logic into the owner track
2. if that is not possible, the earlier merge-order track edits it
3. the later track rebases after merge

Do not solve cross-track conflicts by silently rewriting another track's intent.

## 11. Definition Of Done For A Track

A track is ready to merge when:

- it stays inside owned scope
- it does not violate dependency rules
- its docs are updated
- its public contract changes are documented
- the next track can continue without asking what changed

## 12. Non-Negotiable Rules

- One worktree, one scope.
- Do not couple tasks directly to GUI widgets.
- Do not hide contract changes inside unrelated commits.
- Do not edit another track's owned area unless explicitly taking over that track.
- Always leave a readable handoff.
