# Guild Order Material Logic Notes

This folder documents the current Engine C vision contract for `daily_ui.guild_order_submit`.

## Current Truthful Status

- no reviewed live guild-order evidence packet has landed in this worktree
- the current contract is `placeholder_only`
- material-driven decision surfaces remain blocked instead of being guessed

## Current Scene Contract

Manifest source:

- `assets/templates/daily_ui/manifest.json`
- `metadata.task_support["daily_ui.guild_order_submit"].scene_contract`

Machine-readable state:

- `evidence_state`: `placeholder_only`
- `decision_surface_state`: `blocked_by_missing_material_evidence`
- `ready_anchor_ids`: none
- `blocked_anchor_ids`: none

Placeholder anchors:

- `daily_ui.guild_order_hub_entry`
- `daily_ui.guild_order_list_panel`
- `daily_ui.guild_order_detail_panel`
- `daily_ui.guild_order_submit_button`
- `daily_ui.guild_order_refresh_button`
- `daily_ui.guild_order_unavailable_state`
- `daily_ui.guild_order_insufficient_material_feedback`
- `daily_ui.guild_order_submit_result_state`

Required first-cut scenes:

- `guild_hub_entry`
- `guild_order_list`
- `guild_order_detail`
- `guild_order_submit_affordance`
- `guild_order_refresh_affordance`
- `guild_order_unavailable_state`
- `guild_order_insufficient_material_feedback`
- `guild_order_submit_result_state`

Explicitly blocked material surfaces:

- `guild_order_requirement_material`
- `guild_order_required_quantity`
- `guild_order_available_material_count`

## Why The Contract Stays Blocked

- there is no reviewed Engine E guild-order handoff or evidence packet in this worktree yet
- without reviewed live captures, Engine C can only ship truthful scaffolding
- visible material labels and counts are important to `submit` versus `refresh` semantics, so they stay blocked until live proof exists

## Expected Follow-Up

- Engine E should land reviewed guild-order evidence with exact device provenance
- once real captures exist, Engine C can move anchors from `placeholder_anchor_ids` into `ready_anchor_ids` or `blocked_anchor_ids`
- Engine D should keep task readiness aligned with this contract and must not assume material-count visibility before the evidence exists
