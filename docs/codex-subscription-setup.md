# Codex Subscription Setup

This repo is configured for a subscription-only Codex loop:

- local development in the Codex app, CLI, or IDE using `Sign in with ChatGPT`
- deterministic repo checks inside this repository
- official Codex review in GitHub using your ChatGPT/Codex plan

The default repo flow does not require `OPENAI_API_KEY`.

## Setup Checklist

1. Sign in to the Codex app, CLI, or IDE with your ChatGPT account.
2. Connect GitHub to ChatGPT so Codex can access pull requests and repository review surfaces.
3. Enable repository-level Codex automatic reviews in GitHub if available for your account or workspace.
4. If automatic reviews are not enabled, request review on a pull request with `@codex review`.

## Local Repo Loop

Run the repo harness before asking Codex or a human to review:

```powershell
scripts/run-autonomy-loop.ps1
```

Artifacts:

- `runtime_logs/autonomy/quality-gate.json`
- `runtime_logs/autonomy/agent-packet.json`
- `runtime_logs/autonomy/handoff-brief.md`

These artifacts give Codex and reviewers a stable handoff packet without using the API platform.

## Recommended Workflow

1. Work locally in the Codex app or IDE.
2. Run `scripts/run-autonomy-loop.ps1`.
3. Commit and open a pull request.
4. Let repository-level Codex automatic review run, or comment `@codex review`.
5. Apply feedback and rerun the loop until the gate is green and the PR review is clear.

## Dispatch Workflow

If you want to use Codex more like a team of parallel workers, use the dispatch model in:

- `docs/dispatch-workflow.md`

That workflow keeps:

- one persistent main thread for user requests and task dispatch
- multiple worker threads on separate branches/worktrees
- PRs as the durable handoff surface
- PR watch / merge reporting separate from coding work

## Automatic Merge

Eligible same-repository `codex/*` pull requests targeting `main` now merge automatically after the autonomy quality gate passes.

Notes:

- no manual label or repository variable is required
- draft pull requests are excluded
- the workflow uses the first merge method allowed by the repository in this order: squash, rebase, merge
- if review must remain mandatory, keep that requirement in GitHub branch protection because the workflow does not parse Codex issue-comment text

## Pull Request Template

This repo now includes:

- `.github/pull_request_template.md`

Use it to keep every PR aligned with the subscription-only loop:

- confirm the local loop passed
- paste a short quality-gate summary
- record ownership and risk
- explicitly state whether Codex automatic review is enabled or whether you used `@codex review`

## If You Hit Plan Limits

To stay inside subscription-only usage:

- wait for your Codex usage window to reset
- or buy additional Codex credits inside ChatGPT/Codex if that option is available on your plan

Avoid adding `OPENAI_API_KEY` to this repo unless you intentionally want API-billed automation.
