# Architecture Contracts

## 1. Purpose

This file defines the shared contracts that all worktrees must respect.

It is intentionally small. If a contract is missing, add it here before multiple tracks build against different assumptions.

## 2. Target Package Layout

```text
src/
  roxauto/
    app/
    core/
    emulator/
    tasks/
      daily_ui/
      odin/
    vision/
    profiles/
    logs/
tests/
assets/
```

## 3. Layer Responsibilities

### `app`

Responsibilities:

- GUI widgets
- operator actions
- live previews
- instance list and control panels

Must not contain:

- emulator-specific business logic
- task step definitions
- template matching logic

### `core`

Responsibilities:

- task runtime
- state machine execution
- queueing
- event definitions
- shared types

Must stay:

- UI-free
- emulator-vendor-free

### `emulator`

Responsibilities:

- MuMu and ADB integration
- screenshots
- tap, swipe, text input
- app launch and reconnect

Must not contain:

- task-specific branching

### `vision`

Responsibilities:

- template matching
- anchors
- image preprocessing
- optional OCR adapters

Must not contain:

- task policy
- GUI code

### `tasks`

Responsibilities:

- task packs
- screen-driven state transitions
- task-specific stop conditions

Must not contain:

- GUI widget references

### `profiles`

Responsibilities:

- account and character presets
- approved task-pack list
- per-instance settings

### `logs`

Responsibilities:

- audit records
- failure snapshots
- structured execution history

## 4. Shared Runtime Concepts

These names should be reused consistently.

### `InstanceId`

- type: `str`
- example: `mumu-0`, `mumu-1`
- stable across one local machine configuration

### `InstanceState`

Minimum fields:

- `instance_id`
- `label`
- `adb_serial`
- `status`
- `last_seen_at`

Status values:

- `disconnected`
- `connecting`
- `ready`
- `busy`
- `paused`
- `error`

### `TaskSpec`

Minimum fields:

- `task_id`
- `name`
- `version`
- `entry_state`
- `steps`

### `TaskRun`

Minimum fields:

- `run_id`
- `instance_id`
- `task_id`
- `status`
- `started_at`
- `finished_at`

Status values:

- `pending`
- `running`
- `succeeded`
- `failed`
- `aborted`

### `TaskStepResult`

Minimum fields:

- `step_id`
- `status`
- `message`
- `screenshot_path`

### `VisionMatch`

Minimum fields:

- `anchor_id`
- `confidence`
- `bbox`
- `source_image`

## 5. Event Names

Use predictable event names so logs and GUI wiring stay readable.

Recommended event names:

- `instance.updated`
- `instance.error`
- `task.queued`
- `task.started`
- `task.progress`
- `task.finished`
- `alert.raised`

## 6. Task-Pack Contract

Every task pack must expose:

- a stable task id
- a short human-readable name
- required anchors
- a deterministic entry condition
- deterministic success and failure conditions

Every task step should follow:

```text
detect -> act -> verify -> retry or fail
```

## 7. Asset Rules

Template assets must be grouped by task or subsystem.

Use:

```text
assets/templates/common/
assets/templates/daily_ui/
assets/templates/odin/
```

File naming:

- lowercase
- underscores only
- meaningful names

Example:

- `guild_panel_anchor.png`
- `claim_button_idle.png`

## 8. Import Rules

Allowed import directions:

- `app` may import from any lower layer
- `tasks` may import `core`, `emulator`, `vision`, `profiles`, `logs`
- `vision` may import `core`
- `emulator` may import `core`
- `profiles` may import `core`
- `logs` may import `core`

Forbidden import directions:

- lower layer importing higher layer
- task pack importing GUI widgets

## 9. Contract Change Rule

If a worktree changes:

- shared types
- event names
- folder layout
- asset naming rules

then it must update this file in the same branch.
