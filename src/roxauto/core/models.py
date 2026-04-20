from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from roxauto.core.time import utc_now

if TYPE_CHECKING:
    from roxauto.core.runtime import TaskStep


class InstanceStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"


class TaskRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


class StepStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class StopConditionKind(str, Enum):
    MANUAL = "manual"
    TIMEOUT = "timeout"
    HEALTH_CHECK_FAILED = "health_check_failed"
    VISION_MISMATCH = "vision_mismatch"


class FailureSnapshotReason(str, Enum):
    STEP_FAILED = "step_failed"
    STEP_EXCEPTION = "step_exception"
    STOP_CONDITION = "stop_condition"
    HEALTH_CHECK_FAILED = "health_check_failed"


@dataclass(slots=True)
class PreviewFrame:
    frame_id: str
    instance_id: str
    image_path: str
    captured_at: object = field(default_factory=utc_now)
    thumbnail_path: str | None = None
    source: str = "emulator.capture_screenshot"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StopCondition:
    condition_id: str
    kind: StopConditionKind
    message: str = ""
    enabled: bool = True
    timeout_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskManifest:
    task_id: str
    name: str
    version: str
    requires: list[str] = field(default_factory=list)
    entry_condition: str = ""
    success_condition: str = ""
    failure_condition: str = ""
    recovery_policy: str = "abort"
    stop_conditions: list[StopCondition] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FailureSnapshotMetadata:
    snapshot_id: str
    instance_id: str
    task_id: str
    run_id: str
    reason: FailureSnapshotReason
    screenshot_path: str | None = None
    step_id: str | None = None
    preview_frame: PreviewFrame | None = None
    captured_at: object = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProfileBinding:
    profile_id: str
    display_name: str
    server_name: str
    character_name: str
    allowed_tasks: list[str] = field(default_factory=list)
    calibration_id: str | None = None
    capture_offset: tuple[int, int] = (0, 0)
    capture_scale: float = 1.0
    settings: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InstanceState:
    instance_id: str
    label: str
    adb_serial: str
    status: InstanceStatus
    last_seen_at: object = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InstanceRuntimeContext:
    instance_id: str
    status: InstanceStatus
    queue_depth: int = 0
    active_task_id: str | None = None
    active_run_id: str | None = None
    stop_requested: bool = False
    health_check_ok: bool | None = None
    profile_binding: ProfileBinding | None = None
    preview_frame: PreviewFrame | None = None
    failure_snapshot: FailureSnapshotMetadata | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskSpec:
    task_id: str
    name: str
    version: str
    entry_state: str
    steps: list["TaskStep"]
    manifest: TaskManifest | None = None
    stop_conditions: list[StopCondition] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskStepResult:
    step_id: str
    status: StepStatus
    message: str
    screenshot_path: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskRun:
    run_id: str
    instance_id: str
    task_id: str
    status: TaskRunStatus
    started_at: object = field(default_factory=utc_now)
    finished_at: object | None = None
    step_results: list[TaskStepResult] = field(default_factory=list)
    stop_condition: StopCondition | None = None
    failure_snapshot: FailureSnapshotMetadata | None = None
    preview_frame: PreviewFrame | None = None


@dataclass(slots=True)
class VisionMatch:
    anchor_id: str
    confidence: float
    bbox: tuple[int, int, int, int]
    source_image: str

