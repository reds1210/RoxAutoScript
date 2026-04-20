# RoxAutoScript

ROX automation workspace focused on a Windows desktop control center for multiple MuMu emulator instances.

Current status:

- planning and architecture definition
- git repo initialized for future `worktree`-based parallel development
- MVP scope documented in `docs/rox-mvp-plan.md`
- installable Python foundation with runnable CLI commands
- shared runtime, registry, profile store, audit sink, and emulator discovery skeleton

Docs to read before starting work:

1. `docs/rox-mvp-plan.md`
2. `docs/engine-roster.md`
3. `docs/worktree-playbook.md`
4. `docs/architecture-contracts.md`
5. `docs/tracks/README.md`

Parallel development docs:

- `docs/engine-roster.md`: fixed 4-engine roster, model policy, and current engine branch lineup
- `docs/worktree-playbook.md`: branch, worktree, ownership, merge, and handoff rules
- `docs/architecture-contracts.md`: shared interfaces and dependency boundaries
- `docs/tracks/`: concrete briefs for each worktree track
- `docs/templates/worktree-handoff-template.md`: handoff format for commits and PRs

Foundation commands:

- `python -m roxauto doctor`
- `python -m roxauto demo-runtime`
- `python -m roxauto gui`

Helper scripts:

- `scripts/bootstrap-dev.ps1`
- `scripts/new-worktree.ps1`
- `scripts/bootstrap-four-engines.ps1`
