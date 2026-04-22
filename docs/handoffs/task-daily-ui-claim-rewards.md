# Task Daily UI Claim Rewards Handoff

Track:

- `codex/task-claim-rewards-runtime-seam`

Scope:

- Kept scope on `daily_ui.claim_rewards` only.
- Stayed inside Engine D ownership:
  - `src/roxauto/tasks/`
  - `tests/tasks/`
  - `docs/handoffs/`
- Did not touch `core` / `emulator` / `app` / `vision`.

Files changed:

- `src/roxauto/tasks/catalog.py`
- `src/roxauto/tasks/daily_ui/claim_rewards.py`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/asset_inventory.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/daily_claim_rewards.task.json`
- `tests/tasks/daily_ui/test_claim_rewards.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/test_inventory_fixtures.py`
- `docs/handoffs/task-daily-ui-claim-rewards.md`

Public APIs added or changed:

- `ClaimRewardsRuntimeInput` now exposes task-owned `supporting_anchor_ids` in addition to `required_anchor_ids`.
- `build_claim_rewards_runtime_input(...)` now carries the Route A task contract directly in machine-readable metadata:
  - `metadata["supporting_anchor_ids"]`
  - `metadata["supporting_golden_screen_slugs"]`
  - `metadata["post_claim_resolution"]`
  - `metadata["claim_rewards_live_capture_coverage"]`
  - `metadata["claim_rewards_capture_inventory"]`
  - `metadata["claim_rewards_alternate_post_tap_capture_ids"]`
- `build_claim_rewards_runtime_seam(...)` and `build_claim_rewards_task_spec(...)` now surface `supporting_anchor_ids` alongside the existing runtime seam metadata so downstream runtime / GUI consumers do not need to infer optional-vs-required anchor roles from behavior.
- `TaskFoundationRepository` task-owned inventories now preserve requirement level for tracked support assets:
  - template metadata includes `requirement_level`
  - golden metadata includes `requirement_level`
  - readiness warnings include `metadata["requirement_level"]`
- Task inventory/readiness now import machine-readable claim-rewards evidence context from the vision-owned manifest/catalog instead of flattening the task contract to anchor presence only:
  - `claim_rewards_live_capture_coverage`
  - `claim_rewards_capture_inventory`
  - `claim_rewards_alternate_post_tap_capture_ids`

Contract changes:

- This run aligns Engine D with Route A decision:
  - `direct_result_overlay_is_valid`
- `daily_ui.claim_rewards` task contract now treats post-tap `claimed` as the primary valid success path while keeping `confirm_required` as an optional follow-up path when the client still presents an explicit confirmation modal.
- `daily_ui.reward_confirm_state` is no longer modeled as a required task anchor in task-owned foundations:
  - required anchors now:
    - `daily_ui.reward_panel`
    - `daily_ui.claim_reward`
    - `common.confirm_button`
    - `common.close_button`
  - supporting anchor now:
    - `daily_ui.reward_confirm_state`
- The supporting golden stays explicit and machine-readable:
  - supporting golden screen slug:
    - `confirm_state`
- Task readiness remains `ready`, but the remaining stand-in is now reported as a supporting-provenance warning instead of being implied by the required-anchor contract.
- Task behavior was kept consistent with the already-shipped runtime semantics:
  - direct post-tap `claimed` path stays valid
  - explicit confirm modal path still works when present
  - outcome codes and runtime seam builder names stay stable

Assumptions:

- Dispatch chose `direct_result_overlay_is_valid` after Engine C kept `reward_confirm_modal` blocked but preserved the live post-tap reward overlay as truthful supporting evidence.
- Engine D should align task-owned readiness and metadata with the chosen truth contract instead of forcing runtime or GUI layers to reverse-engineer that choice from step outcomes.
- `daily_ui.reward_confirm_state` is still useful for optional recovery / confirmation flows, so it remains tracked as supporting task evidence rather than being deleted outright.

Verification performed:

- `python -m unittest tests.tasks.daily_ui.test_claim_rewards tests.tasks.daily_ui.test_foundations tests.tasks.test_catalog tests.tasks.test_inventory_fixtures`
- `python -m unittest discover -s tests/tasks -t .`
- `powershell -ExecutionPolicy Bypass -File scripts/run-autonomy-loop.ps1`
  - `quality-gate.json`: `passed`
  - `pytest`: `177 passed`
  - `ruff check src tests`: `passed`

Known limitations:

- `daily_ui.reward_confirm_state` still does not have an approved live zh-TW confirm-modal baseline.
- The supporting warning for `daily_ui.reward_confirm_state` remains expected until Engine C lands a truthful live confirm-modal replacement.
- This branch intentionally does not change runtime-owned smoke reporting, failure snapshot persistence, or GUI rendering. Downstream engines must consume the new task-owned metadata rather than expecting Engine D to update their owned surfaces directly.

Blockers:

- None inside Engine D ownership.
- External evidence gap only:
  - a real live `reward_confirm_modal` capture is still missing

Recommended next step:

- Engine A should read the new task-owned metadata instead of inferring the contract from current step order alone:
  - `TaskRuntimeBuilderInput.metadata["post_claim_resolution"]`
  - `TaskRuntimeBuilderInput.metadata["supporting_anchor_ids"]`
  - `TaskRuntimeBuilderInput.metadata["claim_rewards_live_capture_coverage"]`
  - `TaskRuntimeBuilderInput.metadata["claim_rewards_capture_inventory"]`
  - `TaskRuntimeBuilderInput.metadata["claim_rewards_alternate_post_tap_capture_ids"]`
- Engine B should surface the same task-owned distinction to operators:
  - required live anchors vs supporting stand-in anchors
  - direct-result accepted path vs optional confirm-modal path
- If Engine C later lands a truthful live `reward_confirm_modal`, rerun the task foundation builders so the supporting warning and provenance metadata update cleanly without another contract rewrite.
