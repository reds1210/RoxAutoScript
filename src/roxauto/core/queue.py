from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
from uuid import uuid4

from roxauto.core.events import EVENT_TASK_QUEUED, EventBus
from roxauto.core.models import TaskSpec
from roxauto.core.time import utc_now


@dataclass(slots=True)
class QueuedTask:
    instance_id: str
    spec: TaskSpec
    priority: int = 100
    metadata: dict[str, object] = field(default_factory=dict)
    queue_id: str = field(default_factory=lambda: str(uuid4()))
    enqueued_at: object = field(default_factory=utc_now)

    @property
    def task_id(self) -> str:
        return self.spec.task_id


class TaskQueue:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus or EventBus()
        self._items: list[QueuedTask] = []

    def enqueue(self, item: QueuedTask) -> QueuedTask:
        self._items.append(item)
        self._items.sort(key=lambda queued: (-queued.priority, str(queued.enqueued_at), queued.queue_id))
        self._event_bus.publish(
            EVENT_TASK_QUEUED,
            {
                "queue_id": item.queue_id,
                "instance_id": item.instance_id,
                "task_id": item.task_id,
                "priority": item.priority,
            },
        )
        return item

    def extend(self, items: Iterable[QueuedTask]) -> list[QueuedTask]:
        queued_items = [self.enqueue(item) for item in items]
        return queued_items

    def dequeue(self, instance_id: str | None = None) -> QueuedTask | None:
        if not self._items:
            return None
        if instance_id is None:
            return self._items.pop(0)
        for index, item in enumerate(self._items):
            if item.instance_id == instance_id:
                return self._items.pop(index)
        return None

    def peek(self, instance_id: str | None = None) -> QueuedTask | None:
        if instance_id is None:
            return self._items[0] if self._items else None
        for item in self._items:
            if item.instance_id == instance_id:
                return item
        return None

    def list_items(self, instance_id: str | None = None) -> list[QueuedTask]:
        if instance_id is None:
            return list(self._items)
        return [item for item in self._items if item.instance_id == instance_id]

    def __len__(self) -> int:
        return len(self._items)
