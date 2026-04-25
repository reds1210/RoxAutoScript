# Handoff: Branch Model Feature First

Track:

- `codex/branch-model-feature-first`

Scope:

- migrated the repo's active collaboration model from local multi-worktree delivery to branch-first delivery in one local working directory
- rewrote the core workflow docs to make feature branches and shared branches the primary delivery units
- kept `docs/worktree-playbook.md` as a compatibility path, but replaced its content with branch-first rules
- added branch-first feature/shared track briefs and prompt guidance
- downgraded the old local worktree helper scripts to explicit legacy helpers that now require opt-in
- did not change game-feature runtime logic

Files changed:

- `AGENTS.md`
- `README.md`
- `docs/architecture-contracts.md`
- `docs/codex-subscription-setup.md`
- `docs/dispatch-workflow.md`
- `docs/engine-roster.md`
- `docs/guild-order-material-logic-plan.md`
- `docs/merchant-commission-exploration-plan.md`
- `docs/prompts/feature-branch-thread-prompts.md`
- `docs/prompts/round-6-thread-prompts.md`
- `docs/prompts/round-7-thread-prompts.md`
- `docs/prompts/round-8-thread-prompts.md`
- `docs/prompts/round-9-thread-prompts.md`
- `docs/round-9-guild-order-material-logic.md`
- `docs/rox-mvp-plan.md`
- `docs/tracks/README.md`
- `docs/tracks/core-runtime.md`
- `docs/tracks/feature-guild-order.md`
- `docs/tracks/feature-merchant-commission.md`
- `docs/tracks/gui-console.md`
- `docs/tracks/shared-entry-navigation.md`
- `docs/tracks/shared-material-catalog.md`
- `docs/tracks/task-daily-ui.md`
- `docs/tracks/task-odin.md`
- `docs/tracks/vision-lab.md`
- `docs/worktree-playbook.md`
- `docs/handoffs/branch-model-feature-first.md`
- `scripts/bootstrap-four-engines.ps1`
- `scripts/new-worktree.ps1`

Public APIs added or changed:

- documented new shared contract surfaces in `docs/architecture-contracts.md`:
  - `ObservedTextEvidence`
  - `MaterialDefinition`
  - `MaterialEvidenceRecord`
  - `SharedEntryRouteContract`
  - `SharedCheckpointPack`

Workflow changes:

- active delivery now assumes:
  - one local repo directory
  - one active local coding branch at a time
  - feature branches for full feature slices
  - shared branches only after reuse is proven
- new active branch roster:
  - `codex/branch-model-feature-first`
  - `codex/feature-merchant-commission-meow`
  - `codex/feature-guild-order-submit`
  - `codex/shared-entry-navigation`
  - `codex/shared-material-catalog`
- legacy worktree scripts now fail fast with branch-first guidance unless the caller explicitly passes `-AllowLegacyWorktree`

Assumptions:

- local disk pressure is now strong enough that the repo should not treat multiple local worktrees as the normal workflow
- merchant commission Meow and guild order submit remain the first two feature branches worth formalizing
- historical round plans and prompt packs are still useful for product truth, but their worktree launch instructions are no longer authoritative

Known limitations:

- many older historical docs still contain worktree wording; they are now treated as legacy unless explicitly revised
- `scripts/run-autonomy-loop.ps1` still relies on the local Python environment resolving `roxauto`; in this session the loop was rerun successfully with `PYTHONPATH=src` set in the shell

Verification performed:

- `git diff --check`
- `powershell -ExecutionPolicy Bypass -File scripts/new-worktree.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/bootstrap-four-engines.ps1`
- `$env:PYTHONPATH='src'; powershell -ExecutionPolicy Bypass -File scripts/run-autonomy-loop.ps1`

Autonomy loop result:

- `quality-gate.json`: `passed`
- handoff artifacts refreshed under `runtime_logs/autonomy/`

Recommended next step:

- merge this governance branch first
- then open `codex/feature-merchant-commission-meow`
- after merchant and guild both prove reuse, open `codex/shared-entry-navigation` and `codex/shared-material-catalog` as needed
