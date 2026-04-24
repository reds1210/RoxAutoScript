# Guild Order Material Logic Notes

This folder documents the reviewed live evidence currently available for `daily_ui.guild_order_submit`.

## 2026-04-24 Reviewed Live Evidence

Machine-readable evidence packet:

- `guild_order_live_evidence_packet.json`

Reserved serial used in this pass:

- primary:
  - `127.0.0.1:16480`
  - MuMu window label: `healer-reds.wang`

Current truthful outcome from the reviewed live route:

- the reserved healer MuMu was reachable through `adb`
- the pass started from a live world scene in `prontera`
- the reviewed route successfully reached:
  - the top-right collapsible entry grid
  - the Carnival hub
  - the guild panel with three tabs
  - the guild Activity tab
  - the live guild-order submit scene
- this pass captured the four requested live surfaces:
  - material name
  - required quantity
  - available quantity
  - submit result state

Reviewed raw trail for the successful route:

- `raw/127.0.0.1-16480-step14-before-expand-reroute.png`
- `raw/127.0.0.1-16480-step14-after-expand-reroute.png`
- `raw/127.0.0.1-16480-step15-after-carnival-reroute.png`
- `raw/127.0.0.1-16480-step16-after-guild-order-card-reroute.png`
- `raw/127.0.0.1-16480-step17-after-go-guild-panel-reroute.png`
- `raw/127.0.0.1-16480-step18-after-activity-tab.png`
- `raw/127.0.0.1-16480-step19-after-guild-order-go.png`
- `raw/127.0.0.1-16480-step20-after-submit-once.png`
- `raw/127.0.0.1-16480-step21-stable-submitted-state.png`

## Current Truthful Status

- a reviewed Engine E guild-order evidence packet now exists for a successful live route
- the current packet proves the worktree now has live evidence for:
  - guild hub entry
  - guild-order list and detail
  - submit affordance
  - material label
  - required quantity
  - available quantity
  - submit result state
- this pass did not probe:
  - refresh affordance
  - unavailable state
  - insufficient-material feedback

## Current Manifest Contract

Manifest source:

- `assets/templates/daily_ui/manifest.json`
- `metadata.task_support["daily_ui.guild_order_submit"].scene_contract`

Machine-readable state still shipped in code:

- `evidence_state`: `placeholder_only`
- `decision_surface_state`: `blocked_by_missing_material_evidence`

That contract has not been promoted in this pass. This branch intentionally adds reviewed live evidence only; it does not yet change the manifest-level placeholder or blocked partitions.

## What The New Evidence Proves

- the live route `top-right entry -> Carnival -> guild-order card -> go -> guild panel -> Activity tab -> guild-order go` is reproducible on the reserved healer MuMu
- the guild-order screen can show list and detail at the same time
- one reviewed live order showed:
  - a stable zh-TW material label on the selected order, recorded in `step19`
  - required quantity: `50`
  - available quantity before submit: `5512`
- after one live submit:
  - the previously selected order changed into a submitted state, recorded in `step20` and `step21`
  - the grid advanced to the next live order

## Expected Follow-Up

- Engine C can now review and promote the scenes or surfaces that are truly proven in `guild_order_live_evidence_packet.json`
- Engine D can stop treating material name, required quantity, available quantity, and submit-result visibility as unsupported once Engine C promotion lands
- a later Engine E pass should still capture:
  - refresh affordance
  - unavailable state
  - insufficient-material feedback
