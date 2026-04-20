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


@dataclass(slots=True)
class InstanceState:
    instance_id: str
    label: str
    adb_serial: str
    status: InstanceStatus
    last_seen_at: object = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskSpec:
    task_id: str
    name: str
    version: str
    entry_state: str
    steps: list["TaskStep"]


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


@dataclass(slots=True)
class VisionMatch:
    anchor_id: str
    confidence: float
    bbox: tuple[int, int, int, int]
    source_image: str

