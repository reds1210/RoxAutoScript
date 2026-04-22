# Handoff: Vision Guild Order Material Logic

Track:

- `codex/vision-claim-rewards-live-captures`

Scope:

- stayed inside Engine C ownership for code and assets:
  - `src/roxauto/vision/`
  - `assets/templates/`
  - `docs/vision/`
  - `tests/vision/`
- added this round-9 handoff under `docs/handoffs/` because the active prompt requires a readable cross-thread handoff artifact there
- kept scope locked to the first-cut `daily_ui.guild_order_submit` vision contract
- did not change task, runtime, or app semantics
- did not pretend guild-order live evidence exists where it does not

Files changed in this run:

- `assets/templates/daily_ui/manifest.json`
- `assets/templates/daily_ui/anchors/daily_guild_order_hub_entry.svg`
- `assets/templates/daily_ui/anchors/daily_guild_order_list_panel.svg`
- `assets/templates/daily_ui/anchors/daily_guild_order_detail_panel.svg`
- `assets/templates/daily_ui/anchors/daily_guild_order_submit_button.svg`
- `assets/templates/daily_ui/anchors/daily_guild_order_refresh_button.svg`
- `assets/templates/daily_ui/anchors/daily_guild_order_unavailable_state.svg`
- `assets/templates/daily_ui/anchors/daily_guild_order_insufficient_material_feedback.svg`
- `assets/templates/daily_ui/anchors/daily_guild_order_submit_result_state.svg`
- `src/roxauto/vision/repository.py`
- `src/roxauto/vision/validation.py`
- `docs/vision/README.md`
- `docs/vision/guild_order_material_logic/README.md`
- `docs/handoffs/vision-guild-order-material-logic.md`
- `tests/vision/test_repository.py`
- `tests/vision/test_validation.py`
- `tests/vision/test_tooling.py`

Public APIs added or changed:

- `AnchorRepository.get_guild_order_scene_contract()`
  - returns the manifest-level scene contract for `daily_ui.guild_order_submit`
- `VisionWorkspaceReadinessReport.metadata["guild_order_scene_contract"]`
  - exposes the normalized guild-order scene contract in workspace readiness/tooling payloads
- template validation for `daily_ui.guild_order_submit`
  - now enforces that placeholder, ready, and blocked anchor partitions remain machine-readable and consistent with anchor metadata

Contract changes in this run:

- `daily_ui.guild_order_submit`
  - new manifest-level task support entry under `metadata.task_support`
  - required inspection roles:
    - `guild_hub_entry`
    - `guild_order_list`
    - `guild_order_detail`
    - `submit_affordance`
    - `refresh_affordance`
    - `unavailable_state`
    - `insufficient_material_feedback`
    - `submit_result_state`
  - workflow id:
    - `daily-ui-guild-order-submit`
  - scene contract:
    - `evidence_state`: `placeholder_only`
    - `decision_surface_state`: `blocked_by_missing_material_evidence`
    - `ready_anchor_ids`: none
    - `placeholder_anchor_ids`: all eight current guild-order anchors
    - `blocked_anchor_ids`: none
    - `blocked_scene_ids`:
      - `guild_order_requirement_material`
      - `guild_order_required_quantity`
      - `guild_order_available_material_count`

New placeholder anchors:

- `daily_ui.guild_order_hub_entry`
- `daily_ui.guild_order_list_panel`
- `daily_ui.guild_order_detail_panel`
- `daily_ui.guild_order_submit_button`
- `daily_ui.guild_order_refresh_button`
- `daily_ui.guild_order_unavailable_state`
- `daily_ui.guild_order_insufficient_material_feedback`
- `daily_ui.guild_order_submit_result_state`

Current truthful answer:

- the first-cut guild-order state inventory is now explicit
- none of those guild-order anchors are promoted live anchors yet
- material labels, required quantities, and available counts remain blocked
- Engine C is intentionally shipping scaffolding plus a truthful contract, not a fake-ready evidence claim

Assumptions:

- no reviewed Engine E guild-order evidence packet is available in this worktree today
- the first-cut task/runtime work still needs these scene ids even before live promotion
- material-aware `submit` versus `refresh` semantics should stay blocked until visible evidence exists for the requirement and count surfaces

Verification performed:

- `python -m json.tool assets/templates/daily_ui/manifest.json`
- `python -m unittest tests.vision.test_repository tests.vision.test_validation tests.vision.test_tooling`
- `scripts/run-autonomy-loop.ps1`

Known limitations:

- there is still no reviewed live guild-order golden or supporting-capture set in this branch
- readiness metadata exposes the guild-order scene contract, but task foundations and runtime reporting still need their own follow-through in Engine D and Engine A
- the placeholder anchors are full-surface SVG scaffolds, not production-ready crops

Blockers:

- missing reviewed live evidence for:
  - guild-order list and detail screens
  - submit/refresh affordances
  - unavailable and submit-result states
  - requirement material labels
  - required quantity
  - available quantity/count surfaces
- until those surfaces are captured honestly, Engine C should keep the contract in `placeholder_only`

Recommended next step:

- Engine E should land a reviewed guild-order evidence packet with exact device provenance
- after that, Engine C should promote only the scenes that are truly proven and keep the count surfaces blocked if they still are not stably visible
- Engine D can consume `guild_order_scene_contract` immediately for readiness/blocker messaging, but should not claim material-count support until Engine E plus Engine C promote that evidence
