# Feature Branch Thread Prompts

Use these prompts for the current branch-first workflow.

## Shared Opening

```text
You are working in one top-level branch thread, not a subagent.

First read:
- AGENTS.md
- README.md
- docs/engine-roster.md
- docs/worktree-playbook.md
- docs/architecture-contracts.md
- docs/tracks/README.md
- the branch-specific brief under docs/tracks/
- the latest relevant handoff under docs/handoffs/

Work style:
- summarize the current state, ownership, dependencies, and risks
- list the concrete items you will do in this branch
- work only on this branch outcome
- keep the local working tree clean before branch changes
- run relevant tests
- run scripts/run-autonomy-loop.ps1 before handoff
- finish with:
  - Changed files
  - Tests run
  - What shipped
  - Blockers
  - Recommended next step
```

## Governance Branch Prompt

```text
You are on branch `codex/branch-model-feature-first`.

Goal:
- update repo workflow docs, prompt packs, branch rules, and legacy-script positioning

Scope:
- docs, prompts, branch rules, and workflow scripts only

Do not:
- change game-feature behavior
- widen the task into unrelated cleanup
```

## Feature Merchant Prompt

```text
You are on branch `codex/feature-merchant-commission-meow`.

Goal:
- deliver the bounded merchant commission Meow Group feature slice

Scope:
- merchant-specific route entry
- commission acceptance
- bounded submission
- round progression verification

Rules:
- feature-local decision logic stays on this branch
- do not widen to the other merchant groups
- only extract shared behavior after guild order proves the same reuse
```

## Feature Guild Prompt

```text
You are on branch `codex/feature-guild-order-submit`.

Goal:
- deliver the bounded guild-order submit feature slice

Scope:
- truthful route into guild-order list/detail
- bounded submit / skip / refresh
- truthful decision and verification reporting

Rules:
- keep crafting, gathering, pathing, and generic buying out of scope
- feature-local material policy stays on this branch
- blocked evidence must stay blocked instead of being guessed
```

## Shared Entry Prompt

```text
You are on branch `codex/shared-entry-navigation`.

Goal:
- extract only the entry/re-entry behavior that at least two feature branches already proved reusable

Rules:
- do not invent shared abstractions before proof exists
- do not absorb merchant- or guild-specific decision policy
```

## Shared Material Prompt

```text
You are on branch `codex/shared-material-catalog`.

Goal:
- extract reusable material definitions, aliases, OCR/text-evidence records, and normalization rules

Rules:
- keep low-confidence OCR from directly driving risky actions
- do not merge different materials under one id without evidence
- do not move feature-specific decision policy into shared material definitions
```
