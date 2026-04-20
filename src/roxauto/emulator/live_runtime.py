from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from roxauto.core.commands import InstanceCommand, InstanceCommandType
from roxauto.core.events import EventBus
from roxauto.core.models import InstanceRuntimeContext, InstanceState, ProfileBinding
from roxauto.core.queue import QueuedTask, TaskQueue
from roxauto.core.runtime import AuditSink, RuntimeCoordinator
from roxauto.emulator.discovery import discover_instances
from roxauto.emulator.execution import (
    ActionExecutor,
    EmulatorActionAdapter,
    HealthCheckService,
    ScreenshotCapturePipeline,
)


class InstanceDiscovery(Protocol):
    def __call__(self) -> list[InstanceState]:
        """Return the current discovered runtime instances."""


class ProfileResolver(Protocol):
    def __call__(self, instance: InstanceState) -> ProfileBinding | None:
        """Return one runtime profile binding for the instance when available."""


@dataclass(slots=True)
class LiveRuntimeSnapshot:
    instances: list[InstanceState] = field(default_factory=list)
    contexts: list[InstanceRuntimeContext] = field(default_factory=list)
    queue_items: list[QueuedTask] = field(default_factory=list)


class LiveRuntimeSession:
    def __init__(
        self,
        adapter: EmulatorActionAdapter,
        *,
        discovery: InstanceDiscovery | None = None,
        profile_resolver: ProfileResolver | None = None,
        event_bus: EventBus | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._event_bus = event_bus or EventBus()
        self._audit_sink = audit_sink
        self._discovery = discovery or discover_instances
        self._profile_resolver = profile_resolver
        self._coordinator = RuntimeCoordinator(
            command_executor=ActionExecutor(
                adapter,
                event_bus=self._event_bus,
                audit_sink=self._audit_sink,
            ),
            health_checker=HealthCheckService(
                adapter,
                event_bus=self._event_bus,
                audit_sink=self._audit_sink,
            ),
            preview_capture=ScreenshotCapturePipeline(
                adapter,
                event_bus=self._event_bus,
                audit_sink=self._audit_sink,
            ),
            event_bus=self._event_bus,
            audit_sink=self._audit_sink,
        )

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def coordinator(self) -> RuntimeCoordinator:
        return self._coordinator

    @property
    def queue(self) -> TaskQueue:
        return self._coordinator.queue

    def discover(self) -> list[InstanceState]:
        return list(self._discovery())

    def sync_instances(self, states: list[InstanceState] | None = None) -> list[InstanceState]:
        synced = self._coordinator.sync_instances(states if states is not None else self.discover())
        self._auto_bind_profiles(synced)
        return synced

    def bind_profile(self, instance_id: str, binding: ProfileBinding) -> InstanceRuntimeContext:
        return self._coordinator.bind_profile(instance_id, binding)

    def enqueue(self, item: QueuedTask) -> QueuedTask:
        return self._coordinator.enqueue(item)

    def enqueue_many(self, items: list[QueuedTask]) -> list[QueuedTask]:
        return [self.enqueue(item) for item in items]

    def refresh(self, instance_id: str | None = None):
        return self.dispatch_command(
            InstanceCommand(
                command_type=InstanceCommandType.REFRESH,
                instance_id=instance_id,
            )
        )

    def dispatch_command(self, command: InstanceCommand):
        return self._coordinator.dispatch_command(command)

    def start_queue(self, instance_id: str):
        return self._coordinator.start_queue(instance_id)

    def get_runtime_context(self, instance_id: str) -> InstanceRuntimeContext | None:
        return self._coordinator.get_runtime_context(instance_id)

    def list_runtime_contexts(self) -> list[InstanceRuntimeContext]:
        return self._coordinator.list_runtime_contexts()

    def list_queue_items(self, instance_id: str | None = None) -> list[QueuedTask]:
        return self._coordinator.queue.list_items(instance_id=instance_id)

    def snapshot(self, instance_id: str | None = None) -> LiveRuntimeSnapshot:
        return LiveRuntimeSnapshot(
            instances=self._coordinator.registry.list_instances(),
            contexts=self.list_runtime_contexts(),
            queue_items=self.list_queue_items(instance_id=instance_id),
        )

    def _auto_bind_profiles(self, states: list[InstanceState]) -> None:
        if self._profile_resolver is None:
            return
        for instance in states:
            context = self._coordinator.get_runtime_context(instance.instance_id)
            if context is None or context.profile_binding is not None:
                continue
            try:
                binding = self._profile_resolver(instance)
            except Exception as exc:
                context.metadata["profile_resolver_error"] = str(exc)
                continue
            if binding is None:
                continue
            context.metadata.pop("profile_resolver_error", None)
            self._coordinator.bind_profile(instance.instance_id, binding)
