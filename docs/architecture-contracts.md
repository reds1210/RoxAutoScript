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
- screenshot capture pipeline
- action execution and command routing
- health checks and preview frame capture

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
- calibration profiles
- per-instance overrides for capture or anchor behavior
- resolved profile bindings for runtime consumption

### `logs`

Responsibilities:

- audit records
- failure snapshots
- preview frame references
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
- `manifest` optional
- `stop_conditions` optional
- `metadata` optional

### `TaskManifest`

Minimum fields:

- `task_id`
- `name`
- `version`
- `requires`
- `entry_condition`
- `success_condition`
- `failure_condition`
- `recovery_policy`
- `stop_conditions`
- `metadata`

### `TaskRun`

Minimum fields:

- `run_id`
- `instance_id`
- `task_id`
- `status`
- `started_at`
- `finished_at`
- `stop_condition` optional
- `failure_snapshot` optional
- `preview_frame` optional

Status values:

- `pending`
- `running`
- `succeeded`
- `failed`
- `aborted`

### `QueuedTask`

Minimum fields:

- `queue_id`
- `instance_id`
- `task_id`
- `priority`
- `enqueued_at`

Rules:

- queue order is deterministic
- higher priority runs first
- per-instance dequeue is supported

### `TaskStepResult`

Minimum fields:

- `step_id`
- `status`
- `message`
- `screenshot_path`

### `TaskStepTelemetry`

Minimum fields:

- `step_id`
- `description`
- `status`
- `message`
- `screenshot_path` optional
- `started_at` optional
- `finished_at` optional
- `data`

Recommended status values:

- `pending`
- `running`
- `succeeded`
- `failed`
- `skipped`

### `TaskRunTelemetry`

Minimum fields:

- `task_id`
- `run_id`
- `status`
- `step_count`
- `completed_step_count`
- `current_step_id`
- `current_step_index`
- `started_at`
- `finished_at` optional
- `queue_id` optional
- `attempt`
- `steps`
- `preview_frame` optional
- `failure_snapshot` optional
- `stop_condition` optional
- `last_updated_at`
- `metadata`

Rules:

- runtime should project the active and last completed task state through `TaskRunTelemetry` instead of forcing GUI layers to reconstruct step progress from raw events
- retries should increment `attempt` for the same task id on the same instance runtime context

### `TaskExecutionContext`

Minimum fields:

- `instance`
- `action_bridge` optional
- `metadata`

Rules:

- runtime-owned task execution should populate `action_bridge` before step handlers run
- `metadata` should carry the current `runtime_context`, `profile_binding`, latest `preview_frame`, and latest health state

### `TaskActionBridge`

Minimum methods:

- `dispatch(command)`
- `tap(point)`
- `swipe(start, end, duration_ms)`
- `input_text(text)`
- `capture_preview()`
- `check_health()`

Rules:

- task packs may use this bridge for deterministic emulator interactions during headless execution
- bridge calls must flow through the runtime/emulator layer rather than importing GUI helpers or bypassing runtime context updates
- bridge calls should keep runtime context observability in sync for preview, health, and last action metadata

### `VisionMatch`

Minimum fields:

- `anchor_id`
- `confidence`
- `bbox`
- `source_image`

### `PreviewFrame`

Minimum fields:

- `frame_id`
- `instance_id`
- `image_path`
- `captured_at`
- `thumbnail_path` optional
- `source`
- `metadata`

### `StopCondition`

Minimum fields:

- `condition_id`
- `kind`
- `message`
- `enabled`
- `timeout_ms` optional
- `metadata`

Recommended kinds:

- `manual`
- `timeout`
- `health_check_failed`
- `vision_mismatch`

### `FailureSnapshotMetadata`

Minimum fields:

- `snapshot_id`
- `instance_id`
- `task_id`
- `run_id`
- `reason`
- `screenshot_path` optional
- `step_id` optional
- `preview_frame` optional
- `captured_at`
- `metadata`

### `CalibrationProfile`

Minimum fields:

- `calibration_id`
- `description`
- `capture_offset`
- `capture_scale`
- `crop_box` optional
- `anchor_overrides`
- `metadata`

### `InstanceProfileOverride`

Minimum fields:

- `instance_id`
- `adb_serial` optional
- `calibration_id` optional
- `capture_offset`
- `capture_scale` optional
- `notes`
- `metadata`

### `ProfileBinding`

Minimum fields:

- `profile_id`
- `display_name`
- `server_name`
- `character_name`
- `allowed_tasks`
- `calibration_id` optional
- `capture_offset`
- `capture_scale`
- `settings`
- `notes`
- `metadata`

### `InstanceRuntimeContext`

Minimum fields:

- `instance_id`
- `status`
- `queue_depth`
- `active_task_id` optional
- `active_run_id` optional
- `active_task_run` optional
- `last_task_run` optional
- `last_failed_task_run` optional
- `stop_requested`
- `health_check_ok` optional
- `profile_binding` optional
- `preview_frame` optional
- `failure_snapshot` optional
- `last_failure_snapshot` optional
- `metadata`

Rules:

- runtime-owned execution should update `active_task_run` while a task is running and move the finalized projection into `last_task_run` when the run finishes
- the latest non-manual failed or aborted run should remain available through `last_failed_task_run` until a newer failed run supersedes it
- `failure_snapshot` may clear after a successful retry, but `last_failure_snapshot` should preserve the latest failure signal for inspection surfaces

### `InstanceCommand`

Minimum fields:

- `command_id`
- `command_type`
- `instance_id`
- `payload`
- `requested_at`

Recommended command types:

- `refresh`
- `start_queue`
- `pause`
- `stop`
- `emergency_stop`
- `tap`
- `swipe`
- `input_text`

### `CommandRoute`

Minimum fields:

- `command_id`
- `command_type`
- `instance_id` optional
- `kind`
- `payload`
- `accepted`
- `message`

Recommended route kinds:

- `control`
- `global_control`
- `interaction`

### `CommandDispatchResult`

Minimum fields:

- `command_id`
- `command_type`
- `instance_ids`
- `status`
- `results`
- `message`

### `EmulatorAdapter`

Minimum methods:

- `capture_screenshot(instance)`
- `tap(instance, point)`
- `swipe(instance, start, end, duration_ms)`
- `input_text(instance, text)`
- `launch_app(instance, package_name)`
- `health_check(instance)`

### `RuntimeExecutionPath`

Minimum fields:

- `adapter`
- `command_executor`
- `health_checker`
- `preview_capture`

Rules:

- production runtime wiring may be bundled as one `RuntimeExecutionPath` so GUI and runtime code reuse the same adapter-backed services
- `command_executor`, `health_checker`, and `preview_capture` should all be built from the same emulator adapter instance

### `LiveRuntimeState`

Minimum fields:

- `revision`
- `refresh_state`
- `instance_count`
- `ready_count`
- `busy_count`
- `paused_count`
- `error_count`
- `disconnected_count`
- `queued_count`
- `failure_count`
- `instances`
- `selected_instance`

Rules:

- GUI-facing polling should prefer `LiveRuntimeState` or `LiveRuntimeInstanceSummary` over rebuilding a full `LiveRuntimeSnapshot` on every repaint
- `refresh_state` should expose whether a background rediscover or runtime refresh is pending or in flight
- `instances` should be lightweight summaries only; expensive work such as health checks and preview capture must happen in scheduled runtime refreshes, not during state reads
- selected or per-instance summaries should surface active step ids, last run status, last failure ids, and task-provided `failure_reason_id` / `outcome_code` signals when available without requiring GUI code to replay raw task events or parse fallback message strings

### `LiveRuntimeSession`

Minimum GUI-facing methods:

- `build_adb_live_runtime_session(...)`
- `get_live_state(instance_id=None)`
- `list_instance_summaries()`
- `get_instance_summary(instance_id)`
- `schedule_runtime_refresh(instance_id=None, run_health_check=True, capture_preview=False)`
- `schedule_rediscover(instance_id=None, refresh_runtime=False, run_health_check=True, capture_preview=False)`
- `connect_instance(instance, refresh_runtime=False, ...)`
- `disconnect_instance(instance_id, reason="")`
- `reconnect_instance(instance_id, rediscover=True, ...)`
- `rediscover_instances(...)`

Additional runtime/task integration methods:

- `register_task_factory(task_id, factory)`
- `has_task_factory(task_id)`
- `build_registered_task_spec(instance_id, task_id, metadata=None)`
- `enqueue_registered_task(instance_id, task_id, priority=100, ...)`

Rules:

- GUI threads should treat `schedule_*` methods as the non-blocking entry points for discovery and runtime inspection work
- GUI threads should read `get_live_state(...)` for cards, counters, selection, and refresh banners
- sync `poll()` / `refresh_runtime_contexts()` remain valid for tests and CLI-style tooling, but GUI integrations should not loop over them on the UI thread
- production GUI wiring should start from `build_adb_live_runtime_session(...)` instead of hand-building adapter/execution services
- runtime/task integration should prefer registered task factories over hard-coding task-pack imports inside `core` or `emulator`

### `RuntimeTaskFactoryRequest`

Minimum fields:

- `task_id`
- `instance`
- `runtime_context`
- `profile_binding` optional
- `adapter`
- `execution_path`
- `metadata`

Rules:

- runtime-owned registration points may expose this request to caller-owned task factories instead of importing task packs directly
- task factories may use `runtime_context`, `profile_binding`, and adapter-backed execution services to build task-specific `TaskSpec` instances
- task factory output should preserve the requested `task_id` on the returned `TaskSpec`

### `TaskRuntimeBuilderInput`

Minimum fields:

- `task_id`
- `pack_id`
- `manifest_path`
- `fixture_profile_paths`
- `required_anchors`
- `asset_requirement_ids`
- `runtime_requirement_ids`
- `calibration_requirement_ids`
- `foundation_requirement_ids`
- `metadata`

Rules:

- task implementation tracks should accept a `TaskRuntimeBuilderInput` rather than re-discovering pack metadata ad hoc
- GUI or runtime callers may use this as the stable boundary between foundations and implementation-specific builders

### `TaskReadinessReport`

Minimum fields:

- `task_id`
- `pack_id`
- `builder_readiness_state`
- `implementation_readiness_state`
- `builder_requirements`
- `implementation_requirements`
- `warning_requirements`
- `metadata`

Rules:

- GUI surfaces should render readiness from `TaskReadinessReport` instead of open-coding task-specific readiness heuristics
- warning requirements should stay non-blocking and should not be mixed into runtime or calibration blockers

### `TaskDisplayModel`

Minimum fields:

- `task_id`
- `display_name`
- `description`
- `status`
- `status_text`
- `status_summary`
- `steps`
- `failure_reason` optional
- `metadata`

Rules:

- product-facing task names, step labels, and failure reasons should be exposed through display metadata or a display model, not derived from raw task ids in GUI code
- task-specific display builders may exist per task pack, but GUI code should consume their normalized output

### `VisionToolingState`

Minimum fields:

- `workspace`
- `readiness`
- `preview`
- `match`
- `anchors`
- `calibration`
- `capture`
- `replay`
- `failure`
- `metadata`

Rules:

- vision/tooling layers should expose flattened selected-image, overlay-summary, threshold, and failure-explanation fields for GUI consumption
- GUI code should not rebuild overlay or calibration merge rules from nested raw payloads when these flattened surfaces already exist

### `RuntimeCoordinator`

Responsibilities:

- synchronize discovered instances into runtime contexts
- bind one `ProfileBinding` per instance
- dispatch operator commands to execution services
- orchestrate per-instance queues
- inject baseline stop conditions for manual stop and health failure
- keep preview frame and failure snapshot references on the runtime context

## 5. Event Names

Use predictable event names so logs and GUI wiring stay readable.

Recommended event names:

- `instance.updated`
- `instance.error`
- `instance.health_checked`
- `preview.captured`
- `command.executed`
- `task.queued`
- `task.started`
- `task.progress`
- `task.failure_snapshot`
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
- `emulator` may import `core`, `logs`
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
