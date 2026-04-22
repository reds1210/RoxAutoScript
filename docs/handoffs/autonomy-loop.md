# Autonomy Loop Handoff

## Scope

- Shared autonomy-loop and GitHub workflow surfaces only:
  - `src/roxauto/autonomy/`
  - `tests/autonomy/`
  - `.github/workflows/`
  - `.github/pull_request_template.md`
  - `docs/autonomy-loop.md`
  - `docs/codex-subscription-setup.md`
  - `docs/handoffs/`
- No task, GUI, vision, emulator, or runtime execution behavior changed.
- This pass focused on making PRs themselves usable as the handoff surface for the next Codex worker.

## Changed Files

- `.github/pull_request_template.md`
- `.github/workflows/autonomy-loop.yml`
- `docs/autonomy-loop.md`
- `docs/codex-subscription-setup.md`
- `docs/handoffs/autonomy-loop.md`
- `src/roxauto/autonomy/agent_packet.py`
- `src/roxauto/autonomy/handoff_brief.py`
- `tests/autonomy/test_agent_packet.py`
- `tests/autonomy/test_handoff_brief.py`

## What Shipped

- `agent-packet.json` now includes additional path signals for continuation logic:
  - `git.policy_files_touched`
  - `git.shared_files_touched`
  - `git.workflow_files_touched`
- `docs/codex-subscription-setup.md` is now included in `policy_files`, which keeps the machine-readable restart context aligned with `AGENTS.md`.
- `render_handoff_brief(...)` now includes:
  - quality-gate summary counts
  - recent commit subjects
  - shared-surface warnings when policy/shared/workflow files changed
- The GitHub workflow still posts the handoff brief as a PR comment, and now also syncs it into a managed `Latest Codex Handoff` block inside the PR body.
- The PR template now explicitly warns contributors that CI will maintain that managed handoff block.

## Why This Matters

- A next worker should be able to open the PR and immediately see:
  - whether the gate passed
  - what changed
  - whether shared surfaces moved
  - what recent commits actually landed
- That reduces dependence on archived chat history and makes the PR a better baton-passing surface across Codex threads.

## Public Contract Changes

- `agent-packet.json` now exposes `git.policy_files_touched`, `git.shared_files_touched`, and `git.workflow_files_touched`.
- `policy_files` now includes `docs/codex-subscription-setup.md`.
- PR bodies may now contain a CI-managed block delimited by:
  - `<!-- roxauto-pr-handoff:start -->`
  - `<!-- roxauto-pr-handoff:end -->`

## Verification

- `C:\code\RoxAutoScript\.venv\Scripts\python.exe -m pytest tests/autonomy/test_agent_packet.py tests/autonomy/test_handoff_brief.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-autonomy-loop.ps1 -PythonExe C:\code\RoxAutoScript\.venv\Scripts\python.exe`

## Known Limitations

- The managed PR body block is append-or-replace only; it does not attempt to interpret or rewrite the human-authored template sections above it.
- The handoff summary still relies on changed files and recent commit subjects; it does not synthesize a free-form product summary from git diffs.

## Recommended Next Step

- Observe one real PR run and confirm the managed PR body block stays readable when contributors also fill the human template.
- If the team wants stricter continuation contracts later, add optional machine-readable fields for blockers, ownership exceptions, and rollback notes instead of trying to infer them from prose.
