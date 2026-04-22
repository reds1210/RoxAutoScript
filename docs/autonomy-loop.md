# Autonomy Loop

This repo now includes a minimal guarded autonomy harness for Codex subscription workflows:

1. deterministic quality gate
2. machine-readable repo packet
3. handoff brief for official Codex review surfaces and the next coding session

The goal is not blind auto-merge. The goal is to make coding, review, and strategy loopable without requiring a person to manually restate context between steps.

On pull requests, the workflow now keeps the same handoff packet visible in two places:

- an updatable PR comment for review threads
- a managed PR body section so the next worker can continue from the PR itself

## Files

- `AGENTS.md`
  Repo-level agent rules and loop contract.
- `src/roxauto/autonomy/quality_gate.py`
  Runs stable checks and writes JSON.
- `src/roxauto/autonomy/agent_packet.py`
  Captures git state, changed files, policy files, and gate output for the next agent.
- `src/roxauto/autonomy/handoff_brief.py`
  Builds a markdown handoff for Codex GitHub review or the next Codex session.
- `scripts/run-autonomy-loop.ps1`
  Windows entry point for the local loop.
- `.github/workflows/autonomy-loop.yml`
  CI loop for pull requests and codex branches that avoids API-billed review calls and refreshes the managed PR handoff section.
- `docs/codex-subscription-setup.md`
  Setup checklist for ChatGPT sign-in, GitHub connection, and Codex review.

## Local Usage

Run the full loop from the repo root:

```powershell
scripts/run-autonomy-loop.ps1
```

Manual equivalent:

```powershell
python -m roxauto quality-gate --output runtime_logs/autonomy/quality-gate.json
python -m roxauto agent-packet --quality-gate runtime_logs/autonomy/quality-gate.json --output runtime_logs/autonomy/agent-packet.json
python -m roxauto handoff-brief --quality-gate runtime_logs/autonomy/quality-gate.json --agent-packet runtime_logs/autonomy/agent-packet.json --output runtime_logs/autonomy/handoff-brief.md
```

## Environment

Required:

- ChatGPT/Codex sign-in in the Codex app, CLI, or IDE
- GitHub connected to ChatGPT for Codex review features

Not required:

- `OPENAI_API_KEY`

## Default Gate

The built-in quality gate runs:

1. `python -m roxauto doctor`
2. `python -m pytest`
3. `python -m ruff check src tests` when `ruff` is installed

If you want a stronger gate later, extend the Python command list instead of branching the workflow logic.

## Suggested Operating Policy

Use two stages instead of jumping straight to full autonomy:

1. Guarded autonomy
   Codex writes code, the repo gate validates the change, and Codex GitHub review or the next session consumes the handoff packet. Human still approves merge or deploy.
2. Expanded autonomy
   Allow auto-merge for eligible Codex scopes where:
   - owned paths are respected
   - quality gate passes
   - rollback path is already defined

## Automatic Merge

The repository now merges eligible Codex pull requests automatically after the autonomy gate passes.

Rules:

- branch scope: same-repository `codex/*` pull requests targeting `main`
- runtime gate: the `autonomy` job must pass before the merge job runs
- draft safety: draft pull requests do not auto-merge
- merge method: the workflow picks the first merge method allowed by the repository in this order: squash, rebase, merge
- review policy: if review must remain mandatory, keep that requirement in GitHub branch protection; the workflow does not parse Codex issue-comment text

This removes the manual label and repository-variable gate while still keeping the deterministic quality gate in front of merge.

## Why This Matches The Official Direction

OpenAI's current public guidance points toward harnessed agent workflows using Codex subscription surfaces:

- use Codex with ChatGPT sign-in
- run long work in Codex cloud when needed
- use deterministic checks as hard gates
- use official Codex GitHub review or app handoffs instead of custom API-billed review loops

This repo harness implements that shape locally and in CI, while keeping merge/deploy policy under your control and avoiding API-billed review by default.
