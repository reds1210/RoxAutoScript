# Autonomy Loop Handoff

## Scope

- Shared autonomy-loop surfaces only:
  - `src/roxauto/autonomy/`
  - `tests/autonomy/`
  - `docs/handoffs/`
- No task, GUI, vision, emulator, or runtime execution behavior changed.
- This pass focused on making the machine-readable handoff packet useful inside GitHub PR workflow runs.

## Changed Files

- `docs/handoffs/autonomy-loop.md`
- `src/roxauto/autonomy/agent_packet.py`
- `src/roxauto/autonomy/handoff_brief.py`
- `tests/autonomy/test_agent_packet.py`
- `tests/autonomy/test_handoff_brief.py`

## What Shipped

- `build_agent_packet(...)` now resolves the branch name more honestly in detached-HEAD GitHub workflow runs:
  - prefer the real git branch when available
  - otherwise fall back to `GITHUB_HEAD_REF`
  - otherwise fall back to `GITHUB_REF_NAME`
- PR workflow runs no longer let generated autonomy artifacts pollute the git-state summary:
  - `artifacts/*`
  - `runtime_logs/autonomy/*`
- In GitHub `pull_request` runs where Actions checks out the synthetic merge commit, the agent packet now prefers the merge-parent diff:
  - changed files come from `HEAD^1..HEAD^2`
  - diff excerpt comes from the same PR comparison instead of the workflow-generated artifact diff
- `render_handoff_brief(...)` now prefers `git.changed_files` when the packet provides it, so PR comments can list the real source files changed by the PR instead of transient CI artifact outputs.

## Why This Matters

- The previous PR handoff comment could say:
  - branch: `HEAD`
  - changed files: `artifacts/quality-gate.json`
- That made the PR comment a weak handoff packet for the next Codex session.
- After this pass, the same comment path can point at the actual branch and actual PR file set, which makes it usable for "previous conversation archived, continue from PR" workflows.

## Public Contract Changes

- `agent-packet.json` now includes `git.changed_files`.
- `git.branch` may now resolve from GitHub workflow environment variables when the repo is checked out in detached HEAD mode.
- Generated autonomy artifact paths are intentionally excluded from:
  - `git.status_lines`
  - `git.staged_files`
  - `git.unstaged_files`
  - `git.untracked_files`
  - `git.changed_files`

## Verification

- `C:\code\RoxAutoScript\.venv\Scripts\python.exe -m pytest tests/autonomy/test_agent_packet.py tests/autonomy/test_handoff_brief.py`
- `C:\code\RoxAutoScript\.venv\Scripts\python.exe -m ruff check src tests`
- `powershell -ExecutionPolicy Bypass -File scripts/run-autonomy-loop.ps1 -PythonExe C:\code\RoxAutoScript\.venv\Scripts\python.exe`
- Result: local autonomy loop passed, including `doctor`, `pytest`, and `ruff`

## Known Limitations

- The PR changed-file path currently assumes the GitHub `pull_request` checkout is the standard synthetic merge commit with `HEAD^1` and `HEAD^2`.
- The packet still does not query GitHub directly for PR metadata; it stays git + environment based so local and CI paths remain aligned.

## Recommended Next Step

- Let this branch open a PR so the updated PR handoff comment can be observed in a real GitHub Actions `pull_request` run.
- If the team later wants even richer continuation context, extend the packet with optional PR number / base branch / merged-from branch fields, but keep the local CLI path working without GitHub-only dependencies.
