# Codex Dispatch Workflow

## Goal

Run Codex more like a software team than a single chat:

- one persistent dispatch thread for the user
- multiple worker threads running in parallel
- one PR-review / merge watch lane
- pull requests as the durable handoff surface

The target loop is:

`user request -> dispatch split -> parallel worker threads -> PRs -> review/checks -> auto-merge -> dispatch checks for new user requests`

## Core Roles

### Dispatch Thread

One long-lived Codex Windows conversation acts as the control tower.

Responsibilities:

- keep the backlog of explicit user requests
- decide what should be done next
- split large goals into bounded worker-sized tasks
- decide which tasks can run in parallel
- assign branch names and the correct engine/worktree ownership
- review PR status and merged outcomes
- after merges, check for new user requests before launching more work

Must not:

- silently drift into coding unrelated follow-up work
- treat repo-inferred cleanup as higher priority than explicit user requests

### Worker Threads

Each worker thread is a separate Codex conversation on one branch/worktree.

Responsibilities:

- implement one bounded task
- stay inside owned scope whenever possible
- run the repo autonomy loop
- push code
- open or update one PR
- leave a clear PR body and handoff artifacts for the next worker

Must not:

- pick unrelated backlog items on its own
- merge manually
- rewrite another worker's scope without explicit takeover

### PR Watch

One automation or monitoring lane watches GitHub.

Responsibilities:

- report newly opened PRs
- report review feedback
- report failing checks
- report successful checks
- report merge completion
- tell dispatch what is now actionable

Must not:

- invent new coding work
- bypass the dispatch thread

## Backlog Rule

Priority order:

1. explicit user requests from the dispatch thread
2. actionable feedback on open PRs
3. merge blockers on active work
4. user-approved follow-up work

Default idle behavior:

- if there is no new user request, do not invent the next coding task automatically
- instead, report current PR/review/merge state and wait for the next user request

This is important. The system should behave like supervised staff, not a self-directed product manager.

## Standard Operating Loop

1. The user adds or refines a requirement in the dispatch thread.
2. Dispatch turns that requirement into one or more bounded tasks.
3. Dispatch decides which tasks can run in parallel and which must wait.
4. Dispatch assigns branches using the repo `codex/` prefix.
5. The user opens one new Codex thread per worker task and selects the assigned branch or worktree.
6. Each worker reads `AGENTS.md` and the required repo docs before editing.
7. Each worker implements only its assigned task, runs the autonomy loop, pushes, and opens or updates a PR.
8. PR review and checks run through GitHub.
9. The PR watch lane reports review/check/merge status back to dispatch.
10. When a PR merges, dispatch checks whether the user has already asked for the next thing.
11. Only after checking for explicit user demand should dispatch launch more worker threads.

## Worker Sizing Rule

Each worker task should be:

- small enough to fit in one PR
- reversible
- scoped to one clear outcome
- aligned with one ownership area when possible

Good worker tasks:

- add one runtime-owned field and tests
- fix one GUI state projection bug
- promote one vision asset and update readiness
- tighten one autonomy-loop handoff surface

Bad worker tasks:

- "clean up the repo"
- "improve architecture"
- "finish all remaining claim-rewards work"
- any task that crosses several engines without an explicit split

## Parallelization Rule

Prefer splitting by the repo's engine ownership model:

- Engine A: `src/roxauto/core/`, `src/roxauto/emulator/`, `src/roxauto/logs/`, `src/roxauto/profiles/`
- Engine B: `src/roxauto/app/`, `assets/ui/`
- Engine C: `src/roxauto/vision/`, `assets/templates/`, `docs/vision/`
- Engine D: `src/roxauto/tasks/`, `tests/tasks/`, task assets
- Engine E: curated screenshots, goldens, fixture examples, supporting vision docs

Parallelize only when write scopes are disjoint or when the dependency order is explicit.

## Branch And Thread Pattern

Recommended pattern:

- one branch per worker task
- one top-level Codex thread per worker branch
- one PR per worker branch

Branch naming:

- use `codex/<task-scope>`
- examples:
  - `codex/runtime-sticky-failure-history`
  - `codex/gui-claim-rewards-diagnostics`
  - `codex/autonomy-pr-handoff`

Thread naming inside the app should mirror the branch purpose closely.

## Pull Request Contract

Every worker PR should make continuation easy without chat history.

Minimum PR body:

- summary
- owned paths touched
- shared files touched
- contract changes
- quality-gate result
- main regression risk
- rollback path
- next handoff note

Expected attached artifacts:

- `runtime_logs/autonomy/quality-gate.json`
- `runtime_logs/autonomy/agent-packet.json`
- `runtime_logs/autonomy/handoff-brief.md`

PR comments should be treated as the next-worker starting point, not as decoration.

## Merge Rule

GitHub automation may merge eligible `codex/* -> main` PRs after checks pass.

Dispatch still remains responsible for:

- deciding whether new work should start
- checking for user requests after merge
- launching the next worker threads

Automatic merge is not automatic prioritization.

## Recommended Codex Surfaces

For this workflow, prefer:

- Codex Windows app for the dispatch thread
- Codex Windows app worker threads on separate branches/worktrees
- Codex cloud tasks for long-running background workers when useful
- GitHub PR review as the shared review surface
- app automations only for dispatch summaries and PR watching

CLI is optional. It is useful for advanced local control, but it should not be the only control plane for a multi-worker workflow on Windows.

## Suggested Automation Shape

Recommended supporting automations:

- one dispatch automation attached to the main thread
  - summarize backlog, active workers, blocked PRs, and next launch recommendations
- one PR-watch automation
  - summarize review/check/merge state only

Avoid automations that automatically invent and start the next coding task without first checking for explicit user demand.

## Example

User request:

- `Make claim-rewards failures easier to diagnose and improve PR handoff quality.`

Dispatch split:

1. `codex/core-runtime-step-telemetry`
   - preserve runtime-owned sticky failure history
2. `codex/gui-claim-rewards-production-telemetry`
   - consume the new runtime fields in the GUI
3. `codex/autonomy-pr-handoff`
   - make PR handoff comments show the real branch and changed files

Execution:

- open 3 worker threads
- let each worker produce its own PR
- PR watch reports checks and reviews
- merged PRs feed back into dispatch
- dispatch checks whether the user asked for another requirement before launching more work

## Non-Negotiable Rule

The user should be able to keep using one main thread as the place where requirements are stated.

Everything else exists to serve that thread:

- worker threads implement
- PRs hand off
- review/watch flows report
- merge automation closes finished work
- dispatch returns to the user's request queue
