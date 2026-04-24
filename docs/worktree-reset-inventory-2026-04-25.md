# Worktree Reset Inventory 2026-04-25

## Purpose

This file snapshots the local worktree and branch state before the next phase reset.

The goal is not to delete anything automatically.
The goal is to make the current sprawl visible so the next phase can start from one deliberate baseline.

Reference time zone: `Asia/Taipei`

## Current Worktrees

### 1. Root worktree

- worktree: `C:\code\RoxAutoScript`
- branch: `codex/remove-guild-check-in-add-entry-routes`
- head: `5fe1f6d`
- dirty files: `0`
- vs `origin/main`: behind `0`, ahead `1`
- note:
  - contains the current unmerged docs branch
  - this branch also contains the earlier shared-entry-route doc changes that the operator has now called out as materially inaccurate

Recommendation:

- keep for now
- do not treat its current `shared-entry-routes.md` as authoritative
- split or rewrite route docs before merging this branch

### 2. Goldens worktree

- worktree: `C:\code\RoxAutoScript-wt-claim-rewards-goldens`
- branch: `codex/claim-rewards-goldens`
- head: `fa47888`
- dirty files: `7`
- vs `origin/main`: behind `8`, ahead `3`
- current dirt:
  - untracked raw screenshots under `docs/vision/guild_order_material_logic/raw/`

Recommendation:

- freeze until the raw screenshots are either committed deliberately, moved to a new evidence branch, or deleted
- do not reuse this worktree for a fresh phase while it is dirty

### 3. Runtime worktree

- worktree: `C:\code\RoxAutoScript-wt-core-runtime-step-telemetry`
- branch: `codex/core-runtime-step-telemetry`
- head: `ce144ef`
- dirty files: `0`
- vs `origin/main`: behind `13`, ahead `5`

Recommendation:

- historical branch with unique commits
- if runtime work resumes, roll over from latest `main` instead of continuing on this old branch directly

### 4. GUI worktree

- worktree: `C:\code\RoxAutoScript-wt-gui-claim-rewards-production`
- branch: `codex/gui-claim-rewards-production-telemetry`
- head: `6d9c1e4`
- dirty files: `0`
- vs `origin/main`: behind `16`, ahead `0`

Recommendation:

- stale and clean
- strong candidate for retirement or recreation from latest `main`

### 5. Guild-order continuation worktree

- worktree: `C:\code\RoxAutoScript-wt-guild-order-submit-continuation`
- branch: `codex/guild-order-reviewed-live-evidence`
- head: `3f26d4e`
- dirty files: `0`
- vs `origin/main`: behind `3`, ahead `5`

Recommendation:

- keep
- this is one of the most current active task branches
- if a new guild-order phase starts, either rebase/merge latest `main` into it or create a fresh continuation branch from latest `main`

### 6. Merchant-commission exploration worktree

- worktree: `C:\code\RoxAutoScript-wt-merchant-commission-exploration`
- branch: `codex/merchant-commission-exploration`
- head: `17517a7`
- dirty files: `0`
- vs `origin/main`: behind `3`, ahead `6`

Recommendation:

- keep
- this is the active `商會委託` exploration line
- update from latest `main` before any next-phase delivery work

### 7. Round-8 integration worktree

- worktree: `C:\code\RoxAutoScript-wt-round8-integration`
- branch: `codex/round-8-claim-rewards-integration`
- head: `edd35ca`
- dirty files: `0`
- vs `origin/main`: behind `23`, ahead `0`

Recommendation:

- stale and superseded
- strong candidate for retirement

### 8. Task runtime seam worktree

- worktree: `C:\code\RoxAutoScript-wt-task-claim-rewards-runtime`
- branch: `codex/task-claim-rewards-runtime-seam`
- head: `75ea2f2`
- dirty files: `0`
- vs `origin/main`: behind `8`, ahead `7`

Recommendation:

- historical task branch with unique commits
- do not delete blindly
- do not use as next-phase baseline without an explicit rollover decision

### 9. Vision live-captures worktree

- worktree: `C:\code\RoxAutoScript-wt-vision-claim-rewards-live`
- branch: `codex/vision-claim-rewards-live-captures`
- head: `51381a7`
- dirty files: `0`
- vs `origin/main`: behind `10`, ahead `3`

Recommendation:

- historical branch with unique commits
- safe to keep as archive/reference
- if vision work resumes, prefer a fresh branch from latest `main`

## Local Branches Without A Dedicated Worktree

These branches currently exist locally but are not backed by a live worktree:

- `codex/dispatch-workflow`
  - head `993a792`
  - vs `origin/main`: behind `19`, ahead `1`
- `codex/guild-order-checkpoint-polling`
  - head `d449fec`
  - vs `origin/main`: behind `4`, ahead `2`
- `codex/guild-order-continuation`
  - head `b40a232`
  - vs `origin/main`: behind `3`, ahead `0`
- `codex/guild-order-current-panel`
  - head `41323fd`
  - vs `origin/main`: behind `7`, ahead `3`
- `codex/guild-order-material-plan`
  - head `fe4d226`
  - vs `origin/main`: behind `16`, ahead `1`
- `codex/guild-order-submit-continuation`
  - head `3ec5c39`
  - vs `origin/main`: behind `3`, ahead `1`
- `codex/guild-order-visual-truth-matrix`
  - head `c7dd7f1`
  - vs `origin/main`: behind `3`, ahead `2`
- `codex/guild-order-wave-rollover`
  - head `ecea77f`
  - vs `origin/main`: behind `11`, ahead `1`
- `codex/pause-round-9-guild-order`
  - head `61bbaaa`
  - vs `origin/main`: behind `10`, ahead `4`
- `codex/plain-language-glossary`
  - head `ce08b8b`
  - vs `origin/main`: behind `3`, ahead `1`
- `codex/pr-body-handoff`
  - head `fa8befc`
  - vs `origin/main`: behind `18`, ahead `2`
- `codex/round-9-device-connection-rules`
  - head `13e9e88`
  - vs `origin/main`: behind `10`, ahead `1`
- `codex/route-a-claim-rewards-plan`
  - head `0efd656`
  - vs `origin/main`: behind `17`, ahead `1`
- `codex/ui-redesign`
  - head `c931aa8`
  - vs `origin/main`: behind `21`, ahead `3`
- `main`
  - head `b40a232`
  - vs `origin/main`: behind `3`, ahead `0`

## Immediate Consolidation Notes

### Branches that are clearly stale and have no unique commits

These are the easiest retirement candidates:

- `codex/gui-claim-rewards-production-telemetry`
- `codex/round-8-claim-rewards-integration`
- local `main` should simply be fast-forwarded to `origin/main`
- `codex/guild-order-continuation` also has no unique commits relative to `origin/main`

### Branches to preserve as active or near-active lines

These should not be deleted casually:

- `codex/remove-guild-check-in-add-entry-routes`
- `codex/guild-order-reviewed-live-evidence`
- `codex/merchant-commission-exploration`
- `codex/task-claim-rewards-runtime-seam`
- `codex/core-runtime-step-telemetry`
- `codex/vision-claim-rewards-live-captures`
- `codex/claim-rewards-goldens` after the dirty raw capture issue is resolved

### Branches likely kept only for audit/history

These may still have unique commits but are probably not next-phase baselines:

- `codex/dispatch-workflow`
- `codex/guild-order-current-panel`
- `codex/guild-order-visual-truth-matrix`
- `codex/pause-round-9-guild-order`
- `codex/pr-body-handoff`
- `codex/ui-redesign`
- `codex/route-a-claim-rewards-plan`
- `codex/guild-order-material-plan`
- `codex/round-9-device-connection-rules`

## Recommended Reset Plan

If the next phase should start from one clean modern baseline:

1. fast-forward local `main` to `origin/main`
2. preserve the active exploration/task branches listed above
3. clean or archive the dirty `codex/claim-rewards-goldens` raw screenshot files
4. retire stale zero-ahead worktrees and branches
5. create fresh next-phase delivery branches from updated `main`, instead of reusing very old round-specific branches directly

## Important Constraint

Do not treat the current route docs as settled truth until the live route findings in [live-entry-route-recon-2026-04-25.md](handoffs/live-entry-route-recon-2026-04-25.md) are folded into a rewritten shared route document.
