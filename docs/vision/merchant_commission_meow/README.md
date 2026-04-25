# Merchant Commission Meow Route Notes

## Runtime Delivery Status

The bounded delivery slice now has a concrete task id and runtime seam:

- task id:
  - `daily_ui.merchant_commission_meow`
- signal contract:
  - `merchant_commission_meow.v2`
- runtime bridge coverage:
  - main-screen entry
  - Meow Group acceptance
  - left task-list re-entry
  - one bounded buy-or-submit round resolution
  - round progression verification

## OCR Evidence Contract

Fixed UI checkpoints should still prefer anchor or template matching.

OCR is allowed only as bounded text evidence, and every emitted record should preserve:

- `source_type`
- `raw_text`
- `normalized_text`
- `bbox`
- `confidence`
- `screenshot_ref`
- `reader`

Low-confidence OCR must not directly drive risky actions.

For the current Meow slice, OCR is retained for round-counter verification, while high-risk taps remain gated by anchor/template-confirmed checkpoints.

This folder documents the current truthful exploration result for the first validated `商會委託` route:

- `商會委託 -> 喵手商團`

It does not claim coverage for the other four merchant groups.

## Current Truthful Status

- reserved emulator serial:
  - `127.0.0.1:16416`
- emulator role:
  - `舞孃`
- stable fixed-UI entry exists
- accepted `喵手商團` commissions become a semi-fixed repeatable submission loop
- two rounds were validated end to end
- the loop auto-advanced into `3/10`

Current truthful MVP answer:

- `商會委託` is not a single fixed tap-only task
- the first cut looks viable as a bounded semi-fixed MVP slice if implementation stays on:
  - one merchant source
  - one repeated buy-or-submit loop

## Preferred Route

Use this route for the current validated slice:

1. `主畫面`
2. tap the minimap-left `波利` activity button
3. tap `嘉年華`
4. tap `商會委託`
5. tap `立即前往`
6. wait for auto-path to the `商會` NPC
7. tap `商會委託`
8. in `商團列表`, choose `喵手商團`

After one commission is accepted, use this route instead of reopening `嘉年華`:

1. return to the main screen
2. scroll the left task list until `[日常] 商會委託` is visible
3. tap `[日常] 商會委託`
4. tap the NPC dialog's top task-specific submit option
5. use the `上交道具` panel
6. if materials are missing, tap `立即購買`
7. confirm `購買`
8. tap `交付`
9. repeat from the updated `[日常] 商會委託(n/10)` entry

## Do-Not-Click Notes

- do not use the top-right line-switch arrow near the minimap as the merchant entry
- the correct activity entry is the `波利` button above the `Facebook` button
- after `喵手商團` has been accepted, do not re-enter through `嘉年華 -> 商會委託` unless the task list route is unavailable
- do not generalize one merchant group's verified loop to the other four groups without fresh evidence

## Truthful Checkpoint Pack

### Entry checkpoints

- `idle_prontera_fountain`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416.png`
- `event_poring_menu`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_poring_button.png`
- `carnival_map`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_carnival.png`
- `merchant_commission_detail_modal`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_merchant_commission.png`
- `merchant_autopath_to_npc`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_go_now.png`
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_autopath_wait1.png`
- `merchant_npc_dialog_initial`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_autopath_wait1.png`
- `merchant_commission_list`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_npc_merchant_commission_option.png`
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_list_swipe_left_1.png`

### Accepted `喵手商團` checkpoints

- `merchant_commission_list_meow_accepted`
  - signal:
    - `接受` changed to `放棄`
    - the visible requirement bubble switched to a material hand-in task
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_accept_meow_trade.png`
- `task_list_round_1_visible`
  - signal:
    - left task list shows `[日常] 商會委託(1/10)`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_tasklist_scroll_up_1.png`
- `npc_submit_dialog_round_1`
  - signal:
    - top NPC choice becomes the current submit target
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_tap_daily_merchant_commission_task.png`
- `submit_item_panel_round_1_missing_items`
  - signal:
    - `上交道具` panel opens
    - visible required count was interpreted by the operator as `1/15`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_tap_submit_mineral_extract.png`
- `buy_confirmation_round_1`
  - signal:
    - purchase confirmation opened for the missing amount
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_buy_now_meow.png`
- `submit_item_panel_round_1_ready`
  - signal:
    - item count updated to `15/15`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_confirm_buy_meow.png`
- `task_list_round_2_visible`
  - signal:
    - after `交付`, the task auto-advanced to `[日常] 商會委託(2/10)`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_submit_full_meow_recover.png`

### Round 2 checkpoints

- `npc_submit_dialog_round_2`
  - signal:
    - top NPC choice changed to a different material
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_tap_task_round2_meow.png`
- `submit_item_panel_round_2_empty`
  - signal:
    - `上交道具` panel opened with no matching item
    - branch choices were:
      - `查看來源`
      - `立即購買`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_tap_submit_amber_round2.png`
- `buy_confirmation_round_2`
  - signal:
    - purchase confirmation opened for `15` units
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_buy_now_amber_round2.png`
- `submit_item_panel_round_2_ready`
  - signal:
    - item count updated to `15/15`
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_confirm_buy_amber_round2.png`
- `task_list_round_3_visible`
  - signal:
    - after `交付`, the task auto-advanced to `[日常] 商會委託(3/10)`
    - a new visible material requirement replaced round 2
  - evidence:
    - `runtime_logs/merchant_commission_exploration/2026-04-23/127_0_0_1_16416_after_submit_round2.png`

## Validated Interaction Model

Current truthful model for `喵手商團`:

1. accept one merchant commission
2. task list projects the active commission as `[日常] 商會委託(n/10)`
3. tapping that task re-opens the merchant NPC with one task-specific submit shortcut
4. each round asks for one material hand-in
5. the material may already exist or be purchasable through `立即購買`
6. after `交付`, the round counter advances automatically

This is not a pure fixed-UI reward claim.

This is also not freeform pathing.

The current truthful classification is:

- fixed-UI entry
- semi-fixed repeatable submission loop

## Current Boundaries

Covered in this pass:

- stable entry into `商會委託`
- stable selection of `喵手商團`
- stable re-entry through the left task list
- two completed buy-and-submit rounds

Not covered in this pass:

- the full `10/10` completion chain
- failure behavior when `立即購買` is unavailable
- behavior with insufficient `Zeny`
- the other merchant-group routes
- a final implementation contract or task id

## Product Priority Follow-Up

Current operator priority across merchant groups:

1. `喵手商團`
2. `王國軍需處`
3. the remaining three merchant groups stay in future scope for now

This document covers priority item `1` only.

If this route is delivered successfully, the next merchant-group target should be:

- `王國軍需處`

## Recommended Delivery Scope

If this route moves into delivery next, keep the first cut narrow:

- merchant source:
  - `喵手商團`
- scope:
  - accept from `商團列表`
  - re-enter through `[日常] 商會委託`
  - support `立即購買 -> 購買 -> 交付`
  - handle repeated rounds truthfully

Do not promise broader `商會委託` automation until the other merchant groups have their own checkpoint packs.
