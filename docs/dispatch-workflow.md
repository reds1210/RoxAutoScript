# Codex Dispatch Workflow

## Goal

Run Codex more like a supervised software team than a single chat:

- one persistent dispatch thread for the user
- one local working directory
- multiple delivery branches over time
- optional cloud or external workers when true parallelism is needed
- pull requests as the durable handoff surface

The target loop is:

`user request -> dispatch split -> branch assignment -> coding -> PRs -> review/checks -> merge -> dispatch checks for new user requests`

## Core Roles

### Dispatch Thread

One long-lived Codex Windows conversation acts as the control tower.

Responsibilities:

- keep the backlog of explicit user requests
- decide what should be done next
- split large goals into bounded branch-sized tasks
- decide whether the next task belongs on a feature branch or a shared branch
- assign branch names that match the current roster
- review PR status and merged outcomes
- after merges, check for new user requests before launching more work

Must not:

- silently drift into unrelated follow-up work
- treat repo-inferred cleanup as higher priority than explicit user requests

### Worker Threads

Each worker thread is a separate Codex conversation on one delivery branch.

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
- rewrite another branch's scope without explicit takeover

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

## Branch Types

The default branch types are:

- governance branch
- feature branch
- shared branch

Feature branch examples:

- `codex/feature-merchant-commission-meow`
- `codex/feature-guild-order-submit`

Shared branch examples:

- `codex/shared-entry-navigation`
- `codex/shared-material-catalog`

## Local Execution Rule

This repo now uses one local working directory.

Local rule:

- only one active local coding branch at a time

If more parallelism is needed:

- finish, commit, and push the current branch before switching
- or use Codex cloud or another external execution lane instead of local worktrees

## Backlog Rule

Priority order:

1. explicit user requests from the dispatch thread
2. actionable feedback on open PRs
3. merge blockers on active work
4. user-approved follow-up work

Default idle behavior:

- if there is no new user request, do not invent the next coding task automatically
- instead, report current PR/review/merge state and wait for the next user request

## Standard Operating Loop

1. The user adds or refines a requirement in the dispatch thread.
2. Dispatch turns that requirement into one or more bounded branch tasks.
3. Dispatch decides whether the task is:
   - governance
   - feature
   - shared
4. Dispatch assigns one `codex/*` branch name.
5. The operator switches the single local repo to that branch, or opens a cloud/external worker if parallelism is required.
6. The worker reads `AGENTS.md` and the required repo docs before editing.
7. The worker implements only its assigned task, runs the autonomy loop, pushes, and opens or updates one PR.
8. PR review and checks run through GitHub.
9. The PR watch lane reports review/check/merge status back to dispatch.
10. When a PR merges, dispatch checks whether the user has already asked for the next thing.
11. Only after checking for explicit user demand should dispatch launch more work.

## Worker Sizing Rule

Each branch task should be:

- small enough to fit in one PR
- reversible
- scoped to one clear outcome
- aligned with one feature or one shared extraction

Good branch tasks:

- make `merchant_commission_meow` complete one bounded verified loop
- tighten `guild_order_submit` decision reporting
- extract one shared entry route used by both merchant and guild flows
- normalize one shared material-evidence format

Bad branch tasks:

- "clean up the repo"
- "improve architecture"
- "finish all automation"
- any task that mixes merchant, guild, and shared extraction with no clear handoff boundary

## Shared Branch Rule

Shared branches are not the starting point.

Open a shared branch only when:

- at least two feature branches already prove the same reuse
- the reusable part can be described without feature-specific decision policy
- extracting it now reduces duplicated maintenance

Do not invent reusable abstractions before the feature branches prove them.

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

## Recommended Codex Surfaces

For this workflow, prefer:

- Codex Windows app for the dispatch thread
- Codex Windows app for the active local branch
- Codex cloud tasks when real parallel background work is needed
- GitHub PR review as the shared review surface
- app automations only for dispatch summaries and PR watching

## Example

User request:

- `Make merchant commission Meow stable, then reuse the shared entry flow for guild order.`

Dispatch split:

1. `codex/feature-merchant-commission-meow`
   - finish the bounded Meow feature slice
2. `codex/feature-guild-order-submit`
   - finish bounded guild-order decision flow
3. `codex/shared-entry-navigation`
   - extract only the entry/re-entry flow both features already proved

Execution:

- use the local repo on one branch at a time
- or move one of the later tasks to cloud/external execution if parallelism is required
- let each branch produce one PR
- PR watch reports checks and reviews
- merged PRs feed back into dispatch

## Non-Negotiable Rule

The user should be able to keep using one main thread as the place where requirements are stated.

Everything else exists to serve that thread:

- delivery branches implement
- PRs hand off
- review/watch flows report
- merge automation closes finished work
- dispatch returns to the user's request queue
