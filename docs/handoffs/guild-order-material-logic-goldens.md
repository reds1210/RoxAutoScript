# Guild Order Material Logic Goldens Handoff

Track:

- `codex/guild-order-reviewed-live-evidence`

ADB serial claim:

- primary reserved and used:
  - `127.0.0.1:16480`
  - MuMu window label: `healer-reds.wang`
- visible but not used in the reviewed route:
  - `127.0.0.1:16416`
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
- refreshed the machine-readable Engine E evidence packet for round 9:
  - `docs/vision/guild_order_material_logic/guild_order_live_evidence_packet.json`

Contract changes:

- no manifest or catalog contract changed in this pass
- the truthful evidence conclusion is now explicit:
  - the reserved healer MuMu reached the live guild-order submit screen
  - this pass captured reviewed live evidence for:
    - guild hub entry
    - guild-order list
    - guild-order detail
    - submit affordance
    - material name
    - required quantity
    - available quantity
    - submit result state
- this pass intentionally did not promote the manifest-level placeholder or blocked contract; it only landed evidence

Successful live route:

1. open the top-right collapsible entry icon
2. enter `Carnival`
3. open the guild-order card
4. tap the go button
5. on the guild panel, switch to `Activity`
6. tap the guild-order card's go button
7. reach the live guild-order submit scene

Successful live states captured:

- `guild_hub_entry`
  - `raw/127.0.0.1-16480-step17-after-go-guild-panel-reroute.png`
- `guild_activity_cards`
  - `raw/127.0.0.1-16480-step18-after-activity-tab.png`
- `guild_order_list`
  - `raw/127.0.0.1-16480-step19-after-guild-order-go.png`
- `guild_order_detail`
  - `raw/127.0.0.1-16480-step19-after-guild-order-go.png`
- `submit_affordance`
  - `raw/127.0.0.1-16480-step19-after-guild-order-go.png`
- `submit_result_state`
  - `raw/127.0.0.1-16480-step20-after-submit-once.png`
  - `raw/127.0.0.1-16480-step21-stable-submitted-state.png`

Successful live material surfaces:

- `guild_order_requirement_material`
  - observed value: stable zh-TW material label shown on `step19`
  - capture: `raw/127.0.0.1-16480-step19-after-guild-order-go.png`
- `guild_order_required_quantity`
  - observed value: `50`
  - capture: `raw/127.0.0.1-16480-step19-after-guild-order-go.png`
- `guild_order_available_material_count`
  - observed value: `5512`
  - capture: `raw/127.0.0.1-16480-step19-after-guild-order-go.png`

Assumptions:

- the user-confirmed live route is authoritative for this pass
- the captured submitted badge plus auto-advance to the next order is sufficient to classify a truthful submit-result state
- one successful live order is enough for this bounded evidence pass; this pass should not widen into refresh, crafting, gathering, or pathing

Verification performed:

- `adb devices`
- `adb -s 127.0.0.1:16480 get-state`
- screenshot-gated navigation on every reviewed step
- one live submit on a reviewed order with enough materials

Known limitations:

- this pass did not capture:
  - refresh affordance
  - unavailable state
  - insufficient-material feedback
- the manifest-level guild-order contract in this branch still says `placeholder_only`; this pass did not promote it

Blockers:

- Engine C still needs to consume the new live packet before the placeholder contract can be updated truthfully
- failure-path scenes still need separate reviewed evidence

Recommended next step:

- let Engine C consume `docs/vision/guild_order_material_logic/guild_order_live_evidence_packet.json` as the new truthful round-9 Engine E input
- promote only the proven surfaces first:
  - guild hub entry
  - guild-order list and detail
  - submit affordance
  - submit-result state
  - material name
  - required quantity
  - available quantity
- keep refresh, unavailable, and insufficient-material states blocked until a separate reviewed pass lands
