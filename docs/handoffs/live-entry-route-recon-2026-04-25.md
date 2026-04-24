# Live Entry Route Recon 2026-04-25

## Scope

This handoff freezes the live in-game route reconnaissance that was done together with the operator on `2026-04-25`.

The goal of this pass was not feature delivery. The goal was to stop relying on guessed route docs and replace them with operator-corrected live UI truth.

Exploration is paused after this handoff.

## Device Used

- operator-designated exploration window title: `Android Device-1-3`
- session mapping used during this pass: MuMu `-v 4`
- ADB serial used during this pass: `127.0.0.1:16512`

Notes:

- the title-to-serial mapping was inferred from local MuMu process arguments plus the current ADB-visible device inventory
- use the exact serial in future restarts, not the window title alone

## Do Not Treat As Authority

The current [shared-entry-routes.md](../shared-entry-routes.md) file is not authoritative.

Reasons:

- it was based on earlier assumptions that the operator said were materially wrong
- the file currently has encoding damage
- future route docs should be rewritten from this live handoff, not the reverse

## Verified Or Operator-Corrected Truth

### First-layer entry groups

The main game screen currently has at least these first-layer entry groups:

1. Left-side primary toggles
   - `任務`
   - `組隊`
2. Top-right expanded icon group
   - opened by the blue fold/unfold orb near the top-right corner
3. Right-side expanded function group
   - opened by the blue arrow beside `背包`

### Left-side primary toggles

Operator-corrected rule:

- first click on `任務` or `組隊`
  - switches the adjacent list
  - highlights the selected toggle
- clicking the already highlighted toggle again
  - opens the detailed panel for that category

Important:

- do not mix this rule up with clicks on individual task rows
- earlier row-level probe results from this session were contaminated by runtime state and should not be used as route truth

### Top-right expanded icon group

This group must not be labeled as a pure "activity" launcher.

It mixes:

- permanent/system-like entries
- reward/growth entries
- dynamic seasonal/event entries

Examples seen live in this pass:

- `交易行`
- `賽季`
- `嘉年華`
- `學院手冊`
- `MVP`
- `諸神`
- `王國通行證`
- `福利`
- `戰鬥成就`
- `奇蹟盛典`
- `獎勵找回`
- `卡普拉應援`
- `GVG聯賽`
- `街頭派對`
- `精彩活動`
- `禮包合集`
- `感恩季應援`
- `福運降臨`

Current operator guidance:

- `精彩活動` is seasonal/dynamic and should not be treated as a current implementation target

### Right-side expanded function group

The blue arrow beside `背包` opens a separate first-layer function group.

Examples seen live in this pass:

- `公會`
- `坐騎`
- `技能`
- `衣櫥`
- `生活`
- `精靈`
- `寵物`
- `影裝`
- `神格`
- `家園`
- `學院`
- `覺醒`
- `設定`

### Guild route truth

Do not bind `公會` to one entry route yet.

Operator correction:

- `公會` currently has more than one entry point
- future route docs should model it as a multi-entry function until the routes are explicitly verified

## Verified Shared Hub

### `嘉年華`

`嘉年華` is now verified as a shared upper-level hub, not a single feature.

Live result:

- entering `嘉年華` opens a hub/map-style page with multiple task and event nodes

Verified second-layer nodes seen in this pass:

- `商會委託`
- `委託板`
- `公會訂單`

### `嘉年華 -> 公會訂單`

Verified behavior:

- clicking `公會訂單` from `嘉年華` opens a description card
- the card includes `立即前往`

This means the route is currently:

`主畫面 -> 右上藍色收折按鈕 -> 嘉年華 -> 公會訂單說明卡 -> 立即前往`

### `嘉年華 -> 商會委託`

Verified behavior:

- clicking `商會委託` from `嘉年華` opens a description card
- the card includes `立即前往`

This means the route is currently:

`主畫面 -> 右上藍色收折按鈕 -> 嘉年華 -> 商會委託說明卡 -> 立即前往`

### `嘉年華 -> 委託板`

Status:

- visible in the `嘉年華` hub
- not yet verified in this pass

Do not mark it complete until a clean single-step probe confirms its first landing state.

## Invalid Or Contaminated Probes To Ignore

The following observations must not be promoted to route truth:

1. A mis-tap on `感恩季應援` that was initially mistaken for `精彩活動`
2. A probe sequence that accidentally dropped back to the MuMu desktop/app layer
3. Earlier contaminated row-click observations on the left-side task list

## Working Route Vocabulary For Restart

When this reconnaissance restarts, prefer these neutral terms:

- `left_primary_toggle_group`
- `top_right_expanded_icon_group`
- `right_side_expanded_function_group`
- `shared_hub`
- `description_card`
- `immediate_go_button`
- `multi_entry_function`

Do not prematurely collapse these into narrower names until live evidence says so.

## Recommended Next Restart Scope

If reconnaissance resumes later, the next clean steps should be:

1. verify `嘉年華 -> 委託板`
2. verify the second known `公會` entry path
3. rewrite `shared-entry-routes.md` from verified live truth only
