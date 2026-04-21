# Task Daily UI Claim Rewards Handoff

Track:

- `codex/task-daily-ui`

Scope:

- Advanced only `daily_ui.claim_rewards` from foundations/spec-only into a fixtured, headless implementation-facing runtime input plus `TaskSpec` builder glue.
- Kept `daily_ui.guild_check_in`, `odin`, and non-task ownership paths unchanged.

Files changed:

- `src/roxauto/tasks/catalog.py`
- `src/roxauto/tasks/daily_ui/__init__.py`
- `src/roxauto/tasks/daily_ui/claim_rewards.py`
- `src/roxauto/tasks/foundations/inventory.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/catalog.json`
- `src/roxauto/tasks/foundations/packs/daily_ui/daily_claim_rewards.task.json`
- `src/roxauto/tasks/foundations/readiness_report.json`
- `tests/tasks/daily_ui/test_claim_rewards.py`
- `tests/tasks/daily_ui/test_foundations.py`
- `tests/tasks/test_catalog.py`
- `tests/tasks/test_inventory_fixtures.py`

Public APIs added or changed:

- Added `build_claim_rewards_runtime_input()` under `roxauto.tasks.daily_ui` to convert `TaskRuntimeBuilderInput` + readiness + foundations into a task-specific runtime input for `daily_ui.claim_rewards`.
- Added `build_claim_rewards_task_spec()` under `roxauto.tasks.daily_ui` to build a headless `TaskSpec` from that runtime input.
- Added `ClaimRewardsRuntimeInput`, `ClaimRewardsRuntimeStepSpec`, `ClaimRewardsNavigationPlan`, `ClaimRewardsInspection`, `ClaimRewardsPanelState`, `ClaimRewardsTemplateMatcher`, `ClaimRewardsVisionGateway`, `TemplateMatcherClaimRewardsVisionGateway`, `load_claim_rewards_blueprint()`, and `load_claim_rewards_anchor_specs()`.
- Added `has_claim_rewards_runtime_bridge()` so task readiness can treat `runtime.daily_ui.dispatch_bridge` as satisfied.

Contract changes:

- `daily_ui.claim_rewards` blueprint is now marked `fixtured` instead of `spec_only`.
- `daily_ui.claim_rewards` now declares `common.confirm_button` in addition to `common.close_button` and `daily_ui.claim_reward`.
- Curated readiness now reports `daily_ui.claim_rewards` implementation readiness as `ready` while keeping template/golden gaps as warnings.
- Runtime requirement details now point to both `build_claim_rewards_runtime_input()` and `build_claim_rewards_task_spec()` as the implementation-facing glue.

Assumptions:

- Reward panel classification can be driven by fixed anchors with this precedence: `common.confirm_button`, `daily_ui.claim_reward`, then `common.close_button`.
- Deterministic panel entry is still driven by a caller-supplied fixed tap point via `ClaimRewardsNavigationPlan`.
- Placeholder anchors and planned goldens remain non-blocking warnings for this task, matching the previous readiness model.

Cross-track dependencies:

- Engine A depends on `build_claim_rewards_runtime_input()` and `build_claim_rewards_task_spec()` as the integration surface for enqueue/runtime registration. A must provide the real `EmulatorActionAdapter`, the `ClaimRewardsNavigationPlan`, and either a `ClaimRewardsVisionGateway` or matcher when it instantiates the task.
- Engine C depends on the task continuing to require `common.close_button`, `common.confirm_button`, and `daily_ui.claim_reward`. C is still the owner of converting the current placeholder anchors and planned goldens into curated captures/matching inputs for production reliability.
- Engine B does not block the headless task builder, but if B wants operator-visible task launch/readiness wiring it should read `daily_ui.claim_rewards` as implementation-ready and queue this task through the runtime path rather than embedding UI-side task logic.

Verification performed:

- `python -m unittest tests.tasks.daily_ui.test_claim_rewards`
- `python -m unittest tests.tasks.daily_ui.test_foundations`
- `python -m unittest tests.tasks.test_catalog`
- `python -m unittest tests.tasks.test_inventory_fixtures`
- `python -m unittest discover -s tests/tasks -t .`
- `python -m unittest discover -s tests -t .`

Known limitations:

- No concrete template-matching backend ships here; the runtime bridge depends on a matcher or gateway implementation supplied by the caller.
- `ClaimRewardsNavigationPlan` currently carries only the fixed panel-entry tap point.
- The underlying `daily_ui` template assets are still placeholders and the golden screenshots are still planned.
- `build_claim_rewards_runtime_input()` enforces readiness for `daily_ui.claim_rewards` only; no broader task-pack framework was added in this pass.

Blockers:

- None for the task-side runtime bridge itself.
- Real device/runtime rollout still depends on a production matcher using curated captures instead of placeholder assets.

Recommended next step:

- Wire `build_claim_rewards_runtime_input()` and `build_claim_rewards_task_spec()` into the runtime enqueue path once Engine A exposes the task registration point that should instantiate task-pack builders.
