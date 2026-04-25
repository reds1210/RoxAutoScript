# ROX MVP Plan

## 1. Goal

Build a Windows GUI control center that can:

- discover and attach to multiple MuMu emulator instances
- control each instance independently
- manage task queues from one console
- start from high-confidence repetitive daily tasks first
- stay inside a strict compliance boundary

This project is for **ROX / Ragnarok X: Next Generation / the TW official release** in the TW/HK/MO + SEA ecosystem the user described.

## 2. Research Summary

### 2.1 Game background

From the official ROX TW site, the game is a long-running mobile MMORPG built around:

- class progression and job changes
- open-world monster farming
- guild systems
- instances / party PvE
- recurring events and seasonal systems
- newer growth systems such as fourth-job era content, seasonal dungeon content, and godhood-related systems

Recent official pages visible on the TW site confirm that the live game has continued expanding with systems such as:

- fourth-job era/new servers
- seasonal/tower-style PvE content
- godhood system

### 2.2 Daily/weekly loops that matter for automation

Community guides and event checklists consistently point to the same high-frequency chores:

- mission/board tasks
- Odin's Blessing burn and combat-time consumption
- daily instance clears
- life skills such as fishing, mining, gathering, cooking
- guild donations / guild orders
- activity-point reward collection
- event check-ins and simple event dailies

Important implication:

- ROX has a mix of **fixed UI chores** and **dynamic gameplay chores**.
- Fixed UI chores are good MVP candidates.
- Dynamic content such as instances, board quests with variable routing, MVP/Mini, KVM, and GVG should not be in MVP.

### 2.3 MuMu capabilities we can leverage

Official MuMu docs confirm the platform already gives us useful primitives:

- multi-instance management
- per-instance ADB connectivity
- synchronizer for mirrored click/input across instances
- operation recording/macros
- app cloning in some setups

Useful implementation notes from official MuMu docs:

- MuMu 12 instances expose ADB ports that typically start at `16384` and increase by `32` per instance
- multi-instance launching is built in
- synchronizer only mirrors desktop-area click/input operations
- some background-running modes can break screenshot-based automation tools

This means we should treat MuMu as an execution substrate, not rebuild the emulator-control layer from scratch.

## 3. Compliance Boundary

This part is non-negotiable.

The official ROX user agreement defines an external plugin/program broadly as a non-official program intended to influence or alter game operation. Because of that, "compliance" cannot be hand-waved as a technical detail; it must be a product constraint.

Project boundary:

- allow: UI-level orchestration, ADB-driven taps/swipes/text, screenshot-based state recognition, centralized scheduling, operator-visible logs, explicit task whitelists
- do not allow: memory reading, process injection, packet manipulation, bypassing anti-cheat, hidden background control, detection evasion, credential theft, or any attempt to alter game logic directly
- recommended: keep a written allowlist of approved tasks and a kill switch that can disable any task pack immediately

If the publisher/operator has explicitly approved certain automation behaviors, encode only those behaviors.

## 4. Product Strategy

### 4.1 What the first version is

The first version is **not** "full ROX botting."

The first version is:

- a reliable multi-instance control console
- plus a small number of deterministic task packs
- plus strong observability and manual takeover

### 4.2 What the first version is not

Not MVP:

- full quest parsing
- world navigation planner
- autonomous dungeon strategy
- PvP logic
- MVP/Mini hunting logic
- anti-detection behavior
- emulator memory scraping

## 5. Recommended Tech Stack

Given the current machine already has `Python 3.12.3`, the most direct MVP stack is:

- `Python 3.12`
- `PySide6` for the desktop GUI
- `adb` / `adbutils` for device control
- `OpenCV` for template matching and anchor detection
- OCR only where necessary, not as the first dependency for every task
- `pywin32` for Windows window discovery/focus/layout helpers
- `SQLite` or simple JSON/YAML config for profiles and task presets

Why this stack:

- Windows-native emulator control is easier from Python
- GUI + ADB + CV can live in one runtime
- lower MVP complexity than splitting Electron/Tauri frontends and Python backends too early

## 6. Proposed Architecture

### 6.1 Main modules

1. `control_center`
   Unified GUI. Shows all emulator instances, task status, logs, preview, and manual controls.

2. `instance_registry`
   Discovers MuMu instances, ADB ports, labels, account/profile bindings, and runtime health.

3. `emulator_adapter`
   Wraps screenshot capture, tap, swipe, text input, app launch, focus, reconnect, and health checks.

4. `vision_engine`
   Template matching first, OCR second.
   Purpose: identify stable buttons, popups, tabs, warning states, and completion states.

5. `task_runtime`
   Runs a task as a state machine:
   `detect -> act -> verify -> retry/abort`

6. `profile_store`
   Per-account configuration:
   server, character slot, farming preset, allowed task packs, time windows, and safety thresholds.

7. `audit_log`
   Every action should produce:
   timestamp, instance id, task id, action, result, and screenshot reference.

### 6.2 Control model

Each emulator instance should be an independent actor with:

- its own connection state
- its own task queue
- its own retry counters
- its own screenshots and logs
- pause/resume/stop/manual-takeover controls

The GUI should coordinate actors, not directly contain business logic.

## 7. MVP Scope

### 7.1 MVP objective

Prove that we can reliably run **different tasks on different MuMu instances from one GUI**.

### 7.2 MVP features

#### A. Multi-instance console

- auto-detect MuMu instances by ADB port
- rename/label each instance
- bind instance to account/profile
- show live preview snapshots
- start / pause / stop per instance
- global emergency stop

#### B. Manual operation panel

- click selected anchor
- coordinate tap/swipe
- send text
- refresh screenshot
- inspect template-match results

This is essential because task development will fail without an operator toolbox.

#### C. Task runtime

- per-instance task queue
- step timeouts
- retry rules
- expected-screen verification
- screenshot-on-failure
- structured logs

#### D. First task packs

MVP should only include tasks with stable UI and high value:

1. startup/login cleanup
   - open game
   - close common popups
   - land on a known home screen

2. fixed reward collection
   - claim daily login/event reward pages where the UI is deterministic
   - collect activity chests if visible

3. guild donation / fixed guild UI chores
   - open guild panel
   - perform approved donation or fixed interaction sequence
   - verify completion

4. Odin farm setup
   - navigate through a fixed preset flow
   - enable the configured combat/farming state
   - verify the character is in the expected loop

These four are enough to validate the platform.

### 7.3 Explicitly deferred

- board mission automation
- freeform map routing
- life-skill node pathing
- dungeon combat logic
- boss hunting
- PvP/GVG
- event-specific one-off automation before the plugin system exists

## 8. Why Board Missions Are Not MVP

Board missions look attractive because they are daily and repetitive, but they are a poor first target:

- target NPCs and routes vary
- quest text often needs OCR and branching
- pathing failures are common
- combat interruptions create unstable states

Board missions should come **after** the platform has:

- robust screen detection
- fallback recovery
- state snapshots
- per-step branching

## 9. Suggested Milestones

### Phase 0: foundation

- initialize repo
- define architecture
- define compliance boundary
- define task-pack manifest format

### Phase 1: device and GUI backbone

- MuMu instance discovery
- ADB connect/reconnect
- screenshot panel
- per-instance command buttons
- logging panel

Success criterion:

- can connect to 2 to 4 MuMu instances and control them independently from one console

### Phase 2: task runtime

- state machine runner
- retry/timeout policy
- task step abstraction
- screenshot verification

Success criterion:

- can run deterministic scripted steps on multiple instances without cross-instance contamination

### Phase 3: first task packs

- startup/login cleanup
- fixed reward collection
- guild fixed chore
- Odin farm setup

Success criterion:

- one-click daily preset succeeds on at least 3 test accounts with logs and recoverable failures

### Phase 4: operator tooling

- template editor
- anchor calibration
- task replay
- failure snapshot viewer

Success criterion:

- task debugging time drops significantly because anchors and failures are visible in the tool

### Phase 5: advanced packs

- board missions
- life skills
- event plugins

This phase only starts after MVP is stable.

## 10. Branch-First Parallelization Plan

The current repo policy is branch-first local delivery:

- keep one local working directory
- use one active local branch at a time
- use feature branches for complete game features
- open shared branches only after reuse is proven by multiple feature branches

Recommended 4-engine split:

1. `Engine A`
   Standard branch:
   `codex/core-runtime-orchestration`
   Ownership:
   task runtime, emulator adapter, logging, profile store

2. `Engine B`
   Standard branch:
   `codex/gui-console-operator`
   Ownership:
   PySide6 control center, instance grid, preview panel, operator controls

3. `Engine C`
   Standard branch:
   `codex/vision-lab-calibration-tools`
   Ownership:
   template matching, screenshot utilities, anchor calibration, OCR experiments

4. `Engine D`
   Standard branch:
   `codex/task-daily-ui`
   Ownership:
   task packs, task assets, and later plugin/event runtime
   Note:
   stays on standby until platform Gate 3 is complete

Parallelization rule:

- each branch owns a disjoint functional scope
- shared contracts must be defined first
- task packs cannot directly couple themselves to GUI widgets
- delegated engine work should use `gpt-5.4` by default

Suggested merge order:

1. Engine A runtime branches
2. Engine B GUI branches
3. Engine C vision branches
4. Engine D task/plugin branches

## 11. File/Module Layout Recommendation

When implementation starts, a clean structure would be:

```text
src/
  roxauto/
    app/
    core/
    emulator/
    tasks/
    vision/
    profiles/
    logs/
tests/
docs/
assets/
```

Task packs should live under `src/roxauto/tasks/` and expose a small manifest:

```yaml
id: guild_donation
name: Guild Donation
enabled: true
requires:
  - guild_panel_anchor
steps:
  - detect: guild_home
  - act: tap_donation
  - verify: donation_complete
```

## 12. Immediate Next Steps

Recommended next implementation step:

1. scaffold Python project
2. add MuMu instance discovery + ADB connect
3. build a minimal PySide6 instance grid
4. add screenshot preview per instance
5. add a single "tap test" action

Only after that should task automation begin.

## 13. Sources

- Official ROX TW site: https://rox.gnjoy.com.tw/
- Official ROX user agreement: https://rox.gnjoy.com.tw/userAgreement.html
- Official ROX new-content/event pages observed on the TW site:
  - https://rox.gnjoy.com.tw/4thjob
  - https://rox.gnjoy.com.tw/hokuto
- Official MuMu multi-instance help:
  - https://www.mumuplayer.com/help/win/use-multi-drive-function.html
  - https://www.mumuplayer.com/help/win/connect-adb.html
  - https://www.mumuplayer.com/help/win/synchronizer-guide.html
  - https://www.mumuplayer.com/tw/help/win/set-operation-recording.html
- Community ROX guides used to identify repetitive loops:
  - https://gamingph.com/2021/05/what-is-odins-blessing-in-ragnarok-x-next-generation-rox-guide/
  - https://gamingph.com/2021/04/how-to-get-more-stamina-in-ragnarok-x-next-generation-rox/
  - https://gamingph.com/2021/06/how-to-create-guild-in-ragnarok-x-next-generation-rox-guide/
  - https://vocal.media/gamers/daily-and-weekly-task-checklist-for-fast-progression-in-rox-ragnarok-x-next-generation
