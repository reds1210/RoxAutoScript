from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from roxauto.core.time import utc_now

EVENT_INSTANCE_UPDATED = "instance.updated"
EVENT_INSTANCE_ERROR = "instance.error"
EVENT_INSTANCE_HEALTH_CHECKED = "instance.health_checked"
EVENT_PREVIEW_CAPTURED = "preview.captured"
EVENT_TASK_QUEUED = "task.queued"
EVENT_TASK_STARTED = "task.started"
EVENT_TASK_PROGRESS = "task.progress"
EVENT_TASK_FAILURE_SNAPSHOT_RECORDED = "task.failure_snapshot"
EVENT_FAILURE_SNAPSHOT_RECORDED = EVENT_TASK_FAILURE_SNAPSHOT_RECORDED
EVENT_TASK_FINISHED = "task.finished"
EVENT_ALERT_RAISED = "alert.raised"


@dataclass(slots=True)
class AppEvent:
    name: str
    payload: dict[str, Any]
    emitted_at: object = field(default_factory=utc_now)


EventHandler = Callable[[AppEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    def publish(self, event_name: str, payload: dict[str, Any]) -> AppEvent:
        event = AppEvent(name=event_name, payload=payload)
        for handler in self._handlers.get(event_name, []):
            handler(event)
        return event

