# Round 6: Claim Rewards Production Hardening

## Goal

Turn `daily_ui.claim_rewards` from a curated, explainable MVP flow into the first flow that is closer to real-device repeatability.

This round is still scoped to one task. The difference is that the remaining app-side assumptions should shrink, and live ROX capture quality should replace screenshot-style stand-ins where possible.

## Starting point

Current `main` already has:

- runtime-owned task run and step telemetry
- GUI surfaces that can show current step, last run, failure reason, and operator guidance
- curated claim-rewards templates and screenshot-style baselines
- task-side `claim_rewards.v2` step outcomes and structured failure reasons
- persisted calibration and capture settings under `profiles/`

The main remaining gap is fidelity:

- the curated baselines are still not guaranteed to be live zh-TW ROX captures
- some failure and editor guidance is still app-owned rather than runtime-owned
- the runtime registration and enqueue seam for the task is not yet the only production path

## Definition of done

- `daily_ui.claim_rewards` can be queued and observed through the runtime/task seam without depending on app-local workflow reconstruction
- the primary claim-rewards anchors and goldens are backed by live zh-TW scene captures or clearly versioned curated replacements
- runtime failure snapshots preserve the structured task-side signals needed for repeated debugging
- GUI diagnostics point operators to the right anchor, image, and threshold without re-deriving task state from raw messages

## Thread lineup

### Engine E (optional first)

Branch: `codex/claim-rewards-goldens`

Open only if live screenshots and goldens are the current blocker.

Ownership:

- `assets/templates/`
- `tests/tasks/fixtures/`
- `docs/vision/`

Focus:

- capture and organize live zh-TW ROX screenshots for:
  - reward panel open
  - reward panel claimable
  - reward confirmation modal
- document what each golden proves
- replace screenshot-style stand-ins where possible

Acceptance:

- claim-rewards baselines clearly state whether they are live-device or curated stand-ins
- vision and task tracks can point to concrete screenshots rather than abstract placeholders

### Engine C

Branch: `codex/vision-claim-rewards-live-captures`

Ownership:

- `src/roxauto/vision/`
- `assets/templates/`
- `docs/vision/`
- `tests/vision/`

Focus:

- replace or augment screenshot-style curated baselines with live ROX captures
- expand failure cases around the same three anchors:
  - `daily_ui.reward_panel`
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
- keep the flattened GUI-facing inspection surface stable while improving fidelity underneath

Acceptance:

- vision readiness makes it clear when an asset is live, curated stand-in, placeholder, or mismatched inventory
- failure inspection remains readable without the GUI rebuilding nested payloads

### Engine D

Branch: `codex/task-claim-rewards-runtime-seam`

Ownership:

- `src/roxauto/tasks/`
- `tests/tasks/`
- `docs/handoffs/`

Focus:

- keep scope limited to `daily_ui.claim_rewards`
- formalize the runtime seam expected by task registration and enqueue
- make sure task-side failure and result structures remain deterministic and machine-readable
- align foundations inventory and readiness with the now-curated asset set

Acceptance:

- task builders and runtime inputs are ready to be registered and enqueued through runtime-owned seams
- task-side failure data is no longer message-parsed by downstream layers

### Engine A

Branch: `codex/core-runtime-step-telemetry`

Ownership:

- `src/roxauto/core/`
- `src/roxauto/emulator/`
- `src/roxauto/logs/`
- `src/roxauto/profiles/`
- `tests/core/`
- `tests/emulator/`
- `tests/profiles/`

Focus:

- carry task-side structured failure and outcome signals into runtime-owned telemetry and failure snapshots
- keep `active_task_run`, `last_task_run`, and `last_failure_snapshot` authoritative after retries and restarts
- reinforce the runtime registration and enqueue seam so GUI code is not the source of truth for claim-rewards execution state

Acceptance:

- runtime telemetry is rich enough that GUI no longer needs task-specific state reconstruction beyond display formatting
- sticky failure inspection survives retries without losing the previous failure context

### Engine B

Branch: `codex/gui-claim-rewards-production-telemetry`

Ownership:

- `src/roxauto/app/`
- `assets/ui/`
- `tests/app/`

Focus:

- consume the runtime, task, and vision signals as-is instead of projecting new app-owned workflow assumptions
- keep `每日領獎` as the main operator flow
- improve the operator's next-step guidance so failure tabs point clearly to the right anchor or calibration area
- keep calibration and capture editors viewer-first unless the lower layers expose a production signal for editing

Acceptance:

- GUI guidance is clearer, but task state still comes from runtime, task, and vision surfaces
- remaining viewer-only surfaces are explicit in the handoff

## Recommended start order

1. `Engine E` only if live capture is the real blocker.
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

## Recommended merge order

1. `Engine E` when used
2. `Engine C`
3. `Engine D`
4. `Engine A`
5. `Engine B`

Reason:

- live capture and asset fidelity should settle before runtime and GUI integrations harden around them

## Out of scope

- second task enablement
- guild check-in implementation
- Odin implementation
- navigation AI
- combat logic
- broad OCR or unrelated vision work
