# RoxAutoScript

ROX automation workspace focused on a Windows desktop control center for multiple MuMu emulator instances.

Current status:

- planning and architecture definition
- git repo initialized for branch-first parallel development with one local working directory
- MVP scope documented in `docs/rox-mvp-plan.md`
- installable Python foundation with runnable CLI commands
- shared runtime, registry, profile store, audit sink, and emulator discovery skeleton

Docs to read before starting work:

1. `docs/rox-mvp-plan.md`
2. `docs/engine-roster.md`
3. `docs/worktree-playbook.md`
4. `docs/architecture-contracts.md`
5. `docs/tracks/README.md`
6. `docs/autonomy-loop.md`
7. `docs/codex-subscription-setup.md`
8. `docs/plain-language-glossary.md` for a Chinese-first plain-language reference

Parallel development docs:

- `docs/engine-roster.md`: branch-first feature roster, shared branch policy, and current launch order
- `docs/worktree-playbook.md`: retained filename for compatibility; now documents the branch-first workflow, ownership, merge, and handoff rules
- `docs/architecture-contracts.md`: shared interfaces and dependency boundaries
- `docs/plain-language-glossary.md`: Chinese-first plain-language glossary for repo workflow and task names
- `docs/tracks/`: concrete briefs for each active feature branch and shared branch
- `docs/templates/worktree-handoff-template.md`: handoff format for commits and PRs

Foundation commands:

- `python -m roxauto doctor`
- `python -m roxauto demo-runtime`
- `python -m roxauto gui`

Helper scripts:

- `scripts/bootstrap-dev.ps1`
- `scripts/new-worktree.ps1` (legacy; branch-first workflow is the default)
- `scripts/bootstrap-four-engines.ps1` (legacy; branch-first workflow is the default)
- `scripts/run-autonomy-loop.ps1`

Autonomy loop:

- `python -m roxauto quality-gate --output runtime_logs/autonomy/quality-gate.json`
- `python -m roxauto agent-packet --quality-gate runtime_logs/autonomy/quality-gate.json --output runtime_logs/autonomy/agent-packet.json`
- `python -m roxauto handoff-brief --quality-gate runtime_logs/autonomy/quality-gate.json --agent-packet runtime_logs/autonomy/agent-packet.json --output runtime_logs/autonomy/handoff-brief.md`

Subscription-only Codex note:

- the default repo loop uses ChatGPT/Codex sign-in and does not require `OPENAI_API_KEY`
- use Codex GitHub automatic review or `@codex review` on pull requests for official review flows

Branch-first note:

- local work happens in `C:\code\RoxAutoScript` on one active branch at a time
- use feature branches such as `codex/feature-merchant-commission-meow` and `codex/feature-guild-order-submit` for full game features
- use shared branches such as `codex/shared-entry-navigation` and `codex/shared-material-catalog` only after at least two feature branches prove the reuse
