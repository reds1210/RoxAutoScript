from __future__ import annotations

from typing import Iterable

from roxauto.core.events import EVENT_INSTANCE_UPDATED, EventBus
from roxauto.core.models import InstanceState, InstanceStatus


class InstanceRegistry:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus or EventBus()
        self._instances: dict[str, InstanceState] = {}

    def sync(self, states: Iterable[InstanceState]) -> list[InstanceState]:
        synced: list[InstanceState] = []
        for state in states:
            self._instances[state.instance_id] = state
            synced.append(state)
            self._event_bus.publish(
                EVENT_INSTANCE_UPDATED,
                {
                    "instance_id": state.instance_id,
                    "label": state.label,
                    "status": state.status.value,
                },
            )
        return synced

    def list_instances(self) -> list[InstanceState]:
        return [self._instances[key] for key in sorted(self._instances)]

    def get(self, instance_id: str) -> InstanceState | None:
        return self._instances.get(instance_id)

    def update_status(self, instance_id: str, status: InstanceStatus) -> InstanceState | None:
        instance = self._instances.get(instance_id)
        if instance is None:
            return None
        instance.status = status
        self._event_bus.publish(
            EVENT_INSTANCE_UPDATED,
            {
                "instance_id": instance.instance_id,
                "label": instance.label,
                "status": instance.status.value,
            },
        )
        return instance

