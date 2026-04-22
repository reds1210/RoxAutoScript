# AGENTS.md

## Mission

This repo uses a guarded autonomy loop for coding work:

1. make a bounded code change
2. run deterministic checks
3. emit a machine-readable handoff packet
4. let Codex automatic review or the next coding session continue from the handoff packet

Autonomy is allowed for coding, review, and next-step planning. Merge and deploy should stay gated until the repo owner explicitly removes those gates.

## Required Read Order

Read these files before editing:

1. `README.md`
2. `docs/rox-mvp-plan.md`
3. `docs/engine-roster.md`
4. `docs/worktree-playbook.md`
5. `docs/architecture-contracts.md`
6. `docs/autonomy-loop.md`
7. `docs/codex-subscription-setup.md`

## Non-Negotiable Rules

- respect ownership and dependency rules in `docs/worktree-playbook.md`
- do not edit outside owned scope unless the task explicitly requires a shared-file update
- rerun the autonomy quality gate after every substantive change
- do not mark work ready if the quality gate fails
- prefer Codex subscription surfaces such as the app, cloud tasks, GitHub review, and app automations over custom API scripts
- prefer small, reversible changes over broad refactors

## Local Loop Commands

Use the same commands locally and in CI:

```powershell
python -m roxauto quality-gate --output runtime_logs/autonomy/quality-gate.json
python -m roxauto agent-packet --quality-gate runtime_logs/autonomy/quality-gate.json --output runtime_logs/autonomy/agent-packet.json
python -m roxauto handoff-brief --quality-gate runtime_logs/autonomy/quality-gate.json --agent-packet runtime_logs/autonomy/agent-packet.json --output runtime_logs/autonomy/handoff-brief.md
```

Windows shortcut:

```powershell
scripts/run-autonomy-loop.ps1
```

## Definition Of Ready

An autonomous pass is ready for the next stage when:

- `quality-gate.json` reports `passed`
- the branch stays within owned scope
- tests added for new behavior are present when needed
- the pull request has either repository-level Codex automatic review enabled or an explicit `@codex review` request

## Handoff Artifacts

Every autonomous run should produce:

- `quality-gate.json`
- `agent-packet.json`
- `handoff-brief.md`

The next agent should start from those artifacts instead of reconstructing context from scratch.
