# Guild Order Material Logic Notes

This folder documents the current Engine C vision contract for `daily_ui.guild_order_submit`.

## 2026-04-23 Engine E Live Probe

Machine-readable evidence packet:

- `guild_order_live_evidence_packet.json`

Reserved serials used in this pass:

- primary:
  - `127.0.0.1:16480`
- fallback:
  - `127.0.0.1:16416`

Current truthful outcome from the live probe:

- both reserved devices were reachable through `adb`
- both reserved devices started in `sanctuary_2f`
- this pass captured only pre-guild navigation surfaces:
  - world/combat state
  - team panel
  - character profile or home panel
  - map info
  - current-map NPC list
  - line-switch panel
- no live guild-order target scene was reached
- no live material label, required-quantity, or available-count surface was reached

Reviewed raw probe trail:

- `raw/127.0.0.1-16480-current.png`
- `raw/127.0.0.1-16480-after-organize-tap.png`
- `raw/127.0.0.1-16480-after-avatar-tap.png`
- `raw/127.0.0.1-16480-after-char-home.png`
- `raw/127.0.0.1-16480-after-map-tap.png`
- `raw/127.0.0.1-16480-after-map-npc-expand.png`
- `raw/127.0.0.1-16480-after-right-drawer.png`
- `raw/127.0.0.1-16480-ui.xml`
- `raw/127.0.0.1-16416-current.png`
- `raw/127.0.0.1-16416-leftprobe-385.png`
- `raw/127.0.0.1-16416-char-sidebar-scroll-2.png`
- `raw/127.0.0.1-16416-after-house-tap.png`
- `raw/127.0.0.1-16416-worldmap-probe.png`

## Current Truthful Status

- a reviewed Engine E guild-order evidence packet now exists in this worktree
- that packet still proves no guild-order target scene has been reached yet
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

- the new Engine E packet shows only pre-guild navigation surfaces from `sanctuary_2f`
- without reviewed live guild-order target captures, Engine C can only ship truthful scaffolding
- visible material labels and counts are important to `submit` versus `refresh` semantics, so they stay blocked until live proof exists

## Expected Follow-Up

- Engine E has now landed a reviewed live probe with exact device provenance, but it did not reach guild-order target scenes
- the next Engine E pass should start from a reserved device that can actually reach Guild Hall or another confirmed guild-order entry route
- once real captures exist, Engine C can move anchors from `placeholder_anchor_ids` into `ready_anchor_ids` or `blocked_anchor_ids`
- Engine D should keep task readiness aligned with this contract and must not assume material-count visibility before the evidence exists
