# Task Daily UI Claim Rewards Handoff

Track:

- `codex/task-claim-rewards-real-flow`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Stayed inside Engine D ownership:
  - `src/roxauto/tasks/`
  - `tests/tasks/`
  - `docs/handoffs/`
- Did not touch `core` / `app` / `vision` / `emulator` code and did not open a second task.

What shipped:

- Hardened the five-step state machine so `open_reward_panel` now prechecks whether the panel is already open before sending deterministic navigation. Repeated runs no longer assume the panel must always be reopened.
- Added bounded inspection retries (`claim_rewards.v2`, current budget `2`) after panel open, claim tap, confirm tap, and final claimed verification. This removes the old one-screenshot success/failure assumption.
- Tightened panel classification around the real claim-specific signals:
  - `daily_ui.reward_panel`
  - `daily_ui.claim_reward`
  - `daily_ui.reward_confirm_state`
  - `common.confirm_button`
  - `common.close_button`
- `claim_reward` and `confirm_reward_claim` now distinguish three different classes of outcomes:
  - already satisfied / recoverable state
  - runtime dispatch failure
  - post-action verification failure after retry budget
- Every step result now emits structured task-side outcome data instead of relying on message text:
  - `outcome_code`
  - `failure_reason_id`
  - `expected_panel_states`
  - `signals`
  - `inspection_attempts[]`
  - `step_outcome`
  - `telemetry`
  - `task_action` when a tap was attempted
- `_resolve_failure_reason()` now reads `failure_reason_id` from structured step data first. The old message-sniffing branches were removed.
- Builder input, runtime input, task manifest, pack catalog, and product display metadata are aligned on the new signal contract version `claim_rewards.v2`.

Files changed:

- `src/roxauto/tasks/daily_ui/claim_rewards.py`
- `src/roxauto/tasks/foundations/packs/daily_ui/daily_claim_rewards.task.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `tests/tasks/daily_ui/test_claim_rewards.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/test_inventory_fixtures.py`

Behavior changes:

- `open_reward_panel`
  - succeeds immediately with `open_panel_already_<state>` if the panel is already visible at task start
  - otherwise taps navigation and verifies against the retry budget
- `verify_claim_affordance`
  - keeps `confirm_required` recoverable unless `workflow_mode=ambiguous`
  - emits `claim_state_<state>` or `claim_state_ambiguous`
- `claim_reward`
  - skips the tap for already-claimed and already-confirm-required states
  - emits `claim_dispatch_failed` when runtime bridge dispatch is rejected
  - emits `claim_tap_advanced_to_claimed` / `claim_tap_advanced_to_confirm_required` only after post-tap verification succeeds
- `confirm_reward_claim`
  - emits `confirm_not_required` when the prior step already landed in claimed state
  - emits `confirm_modal_unavailable`, `confirm_dispatch_failed`, `confirm_completed`, or `confirm_tap_no_effect`
- `verify_claimed`
  - always performs a fresh verification pass with retry budget and emits `claimed_verified` / `claimed_unverified`

Signal contract for downstream consumers:

- Engine A should treat the following step-result fields as the authoritative runtime/failure handoff:
  - `step_result.data["outcome_code"]`
  - `step_result.data["failure_reason_id"]`
  - `step_result.data["step_outcome"]`
  - `step_result.data["task_action"]`
  - `step_result.data["telemetry"]["inspection"]`
- Engine A should stop deriving failure type from `message`. The task now gives a stable `failure_reason_id` plus a step-local `outcome_code`.
- Engine B should read GUI-facing task state from:
  - `display_model.failure_reason`
  - `display_model.steps[*].metadata["outcome_code"]`
  - `display_model.steps[*].metadata["failure_reason_id"]`
  - `display_model.steps[*].metadata["signals"]`
  - `display_model.steps[*].metadata["task_action_status"]`
- Engine B should keep using `product_display.failure_reasons` for localized labels/titles and not parse the English step messages.

Cross-track notes:

- Engine A:
  - no API signature changed
  - next integration target is to forward `failure_reason_id`, `outcome_code`, and `inspection_attempts` into runtime-owned failure snapshot metadata without app-side synthesis
- Engine B:
  - the display model now has stable per-step metadata for failure panes and run history
  - `runtime_dispatch_failed` was added to `product_display.failure_reasons`
- Engine C / vision:
  - no code change requested from this track
  - task/runtime/spec now formally require `daily_ui.reward_panel` and `daily_ui.reward_confirm_state`; future tooling that visualizes claim-rewards failure checks should use those anchors as first-class signals

Verification performed:

- `python -m unittest tests.tasks.daily_ui.test_claim_rewards`
- `python -m unittest tests.tasks.test_catalog tests.tasks.test_inventory_fixtures tests.tasks.daily_ui.test_foundations`
- `python -m unittest discover -s tests/tasks -t .`
- `python -m unittest discover -s tests -t .`

Known limitations:

- `failure_snapshot.metadata["claim_rewards"]` is still not task-native. The task now emits the right structured data, but runtime/core still decides what gets copied into failure snapshots.
- Curated `asset_inventory.json` was not expanded into the new claim signal contract because vision workspace readiness currently uses that file as a baseline dependency count. The runtime/spec contract is aligned; the curated asset inventory remains conservative.
- Navigation still depends on the existing fixed `ClaimRewardsNavigationPlan.open_panel_point`.

Blockers:

- None inside Engine D ownership.
- If the project wants runtime-owned failure snapshots to expose `claim_rewards.v2` fields directly, that requires Engine A / core-runtime work.

Recommended next step:

- Keep the next pass on `daily_ui.claim_rewards` only.
- Engine A should consume `failure_reason_id` + `outcome_code` + `inspection_attempts` from task step data and decide the runtime-side failure snapshot schema.
- Engine B should switch any remaining claim-rewards failure UI from message-based branching to `display_model.failure_reason` and per-step metadata fields.
