from __future__ import annotations

from typing import Iterable

from roxauto.core.events import EVENT_INSTANCE_UPDATED, EventBus
from roxauto.core.models import InstanceState, InstanceStatus
from roxauto.core.time import utc_now


_ALLOWED_STATUS_TRANSITIONS: dict[InstanceStatus, set[InstanceStatus]] = {
    InstanceStatus.DISCONNECTED: {InstanceStatus.DISCONNECTED, InstanceStatus.CONNECTING, InstanceStatus.READY, InstanceStatus.ERROR},
    InstanceStatus.CONNECTING: {InstanceStatus.CONNECTING, InstanceStatus.READY, InstanceStatus.ERROR, InstanceStatus.DISCONNECTED},
    InstanceStatus.READY: {InstanceStatus.READY, InstanceStatus.BUSY, InstanceStatus.PAUSED, InstanceStatus.ERROR, InstanceStatus.DISCONNECTED},
    InstanceStatus.BUSY: {InstanceStatus.BUSY, InstanceStatus.READY, InstanceStatus.PAUSED, InstanceStatus.ERROR, InstanceStatus.DISCONNECTED},
    InstanceStatus.PAUSED: {InstanceStatus.PAUSED, InstanceStatus.READY, InstanceStatus.BUSY, InstanceStatus.ERROR, InstanceStatus.DISCONNECTED},
    InstanceStatus.ERROR: {InstanceStatus.ERROR, InstanceStatus.CONNECTING, InstanceStatus.READY, InstanceStatus.DISCONNECTED},
}


class InstanceStateTransitionError(ValueError):
    """Raised when a runtime attempts an invalid instance status transition."""


class InstanceRegistry:
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus or EventBus()
        self._instances: dict[str, InstanceState] = {}

    def sync(self, states: Iterable[InstanceState]) -> list[InstanceState]:
        synced: list[InstanceState] = []
        seen_instance_ids: set[str] = set()
        for state in states:
            seen_instance_ids.add(state.instance_id)
            existing = self._instances.get(state.instance_id)
            if existing is None:
                synced_state = state
                self._instances[state.instance_id] = synced_state
            else:
                existing.label = state.label
                existing.adb_serial = state.adb_serial
                existing.status = state.status
                existing.last_seen_at = state.last_seen_at
                existing.metadata.update(state.metadata)
                synced_state = existing
            synced.append(synced_state)
            self._event_bus.publish(
                EVENT_INSTANCE_UPDATED,
                {
                    "instance_id": synced_state.instance_id,
                    "label": synced_state.label,
                    "status": synced_state.status.value,
                },
            )
        for instance_id in sorted(set(self._instances) - seen_instance_ids):
            instance = self._instances[instance_id]
            if instance.status == InstanceStatus.DISCONNECTED:
                continue
            instance.status = InstanceStatus.DISCONNECTED
            instance.last_seen_at = utc_now()
            self._event_bus.publish(
                EVENT_INSTANCE_UPDATED,
                {
                    "instance_id": instance.instance_id,
                    "label": instance.label,
                    "status": instance.status.value,
                },
            )
        return synced

    def list_instances(self) -> list[InstanceState]:
        return [self._instances[key] for key in sorted(self._instances)]

    def get(self, instance_id: str) -> InstanceState | None:
        return self._instances.get(instance_id)

    def update_status(self, instance_id: str, status: InstanceStatus) -> InstanceState | None:
        return self.transition_status(instance_id, status)

    def transition_status(
        self,
        instance_id: str,
        status: InstanceStatus,
        *,
        metadata: dict[str, object] | None = None,
        force: bool = False,
    ) -> InstanceState | None:
        instance = self._instances.get(instance_id)
        if instance is None:
            return None
        allowed = _ALLOWED_STATUS_TRANSITIONS.get(instance.status, set())
        if not force and status not in allowed:
            raise InstanceStateTransitionError(
                f"Invalid transition for {instance_id}: {instance.status.value} -> {status.value}"
            )
        instance.status = status
        instance.last_seen_at = utc_now()
        if metadata:
            instance.metadata.update(metadata)
        self._event_bus.publish(
            EVENT_INSTANCE_UPDATED,
            {
                "instance_id": instance.instance_id,
                "label": instance.label,
                "status": instance.status.value,
            },
        )
        return instance

