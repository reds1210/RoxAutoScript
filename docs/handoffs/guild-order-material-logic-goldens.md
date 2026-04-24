# Guild Order Material Logic Goldens Handoff

Track:

- `codex/claim-rewards-goldens`

ADB serial claim:

- primary reserved and used:
  - `127.0.0.1:16480`
- fallback reserved and used after the primary probe failed to reach guild UI:
  - `127.0.0.1:16416`
- did not use:
  - `127.0.0.1:16448`
  - `127.0.0.1:16512`

Scope:

- stayed inside Engine E ownership only
- kept scope locked to the first-cut `daily_ui.guild_order_submit` evidence wave
- wrote only to:
  - `docs/vision/guild_order_material_logic/`
  - `docs/vision/README.md`
  - `docs/handoffs/guild-order-material-logic-goldens.md`
- did not edit runtime, task, app, manifest, catalog, or template assets

Files changed:

- `docs/vision/guild_order_material_logic/README.md`
- `docs/vision/guild_order_material_logic/guild_order_live_evidence_packet.json`
- `docs/vision/guild_order_material_logic/raw/*`
- `docs/vision/README.md`
- `docs/handoffs/guild-order-material-logic-goldens.md`

Public APIs added or changed:

- no Python API changed
- added one machine-readable Engine E evidence packet for round 9:
  - `docs/vision/guild_order_material_logic/guild_order_live_evidence_packet.json`

Contract changes:

- no manifest or catalog contract changed in this pass
- the truthful evidence conclusion is now explicit:
  - both reserved devices were reachable through `adb`
  - both reserved devices started in `sanctuary_2f`
  - this pass captured only pre-guild navigation surfaces
  - no live guild-order target scene was reached
  - all first-cut live material surfaces remain missing

Successful live states captured:

- `world_combat_state`
  - `127.0.0.1:16480`
  - `127.0.0.1:16416`
- `team_panel`
  - `127.0.0.1:16480`
  - `127.0.0.1:16416`
- `character_profile_panel`
  - `127.0.0.1:16480`
  - `127.0.0.1:16416`
- `character_home_profile_page`
  - `127.0.0.1:16480`
- `map_info_panel`
  - `127.0.0.1:16480`
  - `127.0.0.1:16416`
- `current_map_npc_panel`
  - `127.0.0.1:16480`
- `line_switch_panel`
  - `127.0.0.1:16416`
- `right_side_quick_item_drawer`
  - `127.0.0.1:16480`

Still-missing live guild-order states:

- `guild_hub_entry`
- `guild_order_list`
- `guild_order_detail`
- `submit_affordance`
- `refresh_affordance`
- `unavailable_state`
- `insufficient_material_feedback`
- `submit_result_state`

Still-missing live material surfaces:

- `guild_order_requirement_material`
- `guild_order_required_quantity`
- `guild_order_available_material_count`

Assumptions:

- the assigned serial reservation from dispatch is authoritative, so `127.0.0.1:16480` stayed primary and `127.0.0.1:16416` stayed the only fallback
- the observed `sanctuary_2f` live state on both devices is not itself a guild-order scene
- it is better to record an honest navigation block than to guess at freeform pathing toward Guild Hall

Operator Questions:

- if the next pass needs actual guild-order list/detail evidence quickly, can one reserved device be parked at Guild Hall or at a known guild-order NPC route before the probe starts?

Verification performed:

- `adb devices`
- `adb -s 127.0.0.1:16480 get-state`
- `adb -s 127.0.0.1:16416 get-state`
- `adb -s 127.0.0.1:16480 shell uiautomator dump /sdcard/guild-order-ui-16480.xml`

Known limitations:

- this pass did not reach any target guild-order UI, so it cannot prove whether list/detail/submit/refresh scenes are visually stable yet
- both reserved devices were already inside `sanctuary_2f`, and the common navigation probes available from that live state only exposed team, character, map, and line-switch surfaces
- the `WorldMap` button did not transition away from the current-floor map during this pass

Blockers:

- no reserved device in this pass exposed a route to Guild Hall or any guild-order panel through the probed stable UI surfaces
- because no guild-order detail scene was reached, no visible material label, required quantity, or available-count surface could be captured honestly

Recommended next step:

- let Engine C consume `docs/vision/guild_order_material_logic/guild_order_live_evidence_packet.json` as the truthful round-9 Engine E input
- keep the guild-order scene contract blocked for all target scenes and live material surfaces
- run the next capture pass only after a reserved serial can reach Guild Hall or another confirmed guild-order entry route
