from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from roxauto.core.commands import CommandDispatchResult, InstanceCommand, InstanceCommandType
from roxauto.core.events import (
    AppEvent,
    EVENT_ALERT_RAISED,
    EVENT_COMMAND_EXECUTED,
    EVENT_INSTANCE_ERROR,
    EVENT_INSTANCE_HEALTH_CHECKED,
    EVENT_INSTANCE_UPDATED,
    EVENT_PREVIEW_CAPTURED,
    EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
    EVENT_TASK_FINISHED,
    EVENT_TASK_PROGRESS,
    EVENT_TASK_QUEUED,
    EVENT_TASK_STARTED,
    EventBus,
)
from roxauto.core.models import InstanceRuntimeContext, InstanceState, PreviewFrame, ProfileBinding
from roxauto.core.queue import QueuedTask, TaskQueue
from roxauto.core.runtime import AuditSink, QueueRunResult, RuntimeCoordinator
from roxauto.core.time import utc_now
from roxauto.emulator.discovery import discover_instances
from roxauto.emulator.execution import (
    ActionExecutor,
    EmulatorActionAdapter,
    HealthCheckService,
    ScreenshotCapturePipeline,
)

_RUNTIME_EVENT_NAMES = (
    EVENT_INSTANCE_UPDATED,
    EVENT_INSTANCE_ERROR,
    EVENT_INSTANCE_HEALTH_CHECKED,
    EVENT_PREVIEW_CAPTURED,
    EVENT_COMMAND_EXECUTED,
    EVENT_TASK_QUEUED,
    EVENT_TASK_STARTED,
    EVENT_TASK_PROGRESS,
    EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
    EVENT_TASK_FINISHED,
    EVENT_ALERT_RAISED,
)


class InstanceDiscovery(Protocol):
    def __call__(self) -> list[InstanceState]:
        """Return the current discovered runtime instances."""


class ProfileResolver(Protocol):
    def __call__(self, instance: InstanceState) -> ProfileBinding | None:
        """Return one runtime profile binding for the instance when available."""


@dataclass(slots=True)
class LiveRuntimeEventRecord:
    sequence_id: int
    name: str
    emitted_at: object
    instance_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LiveRuntimeInstanceSnapshot:
    instance_id: str
    instance: InstanceState
    context: InstanceRuntimeContext | None = None
    queue_items: list[QueuedTask] = field(default_factory=list)

    @property
    def queue_depth(self) -> int:
        if self.context is not None:
            return self.context.queue_depth
        return len(self.queue_items)

    @property
    def profile_binding(self) -> ProfileBinding | None:
        if self.context is None:
            return None
        return self.context.profile_binding

    @property
    def preview_frame(self) -> PreviewFrame | None:
        if self.context is None:
            return None
        return self.context.preview_frame

    @property
    def failure_snapshot(self):
        if self.context is None:
            return None
        return self.context.failure_snapshot

    @property
    def health_check_ok(self) -> bool | None:
        if self.context is None:
            return None
        return self.context.health_check_ok


@dataclass(slots=True)
class LiveRuntimeSnapshot:
    captured_at: object = field(default_factory=utc_now)
    revision: int = 0
    last_sync_at: object | None = None
    last_discovery_at: object | None = None
    last_sync_error: str = ""
    last_command_result: CommandDispatchResult | None = None
    last_queue_result: QueueRunResult | None = None
    instance_snapshots: list[LiveRuntimeInstanceSnapshot] = field(default_factory=list)
    instances: list[InstanceState] = field(default_factory=list)
    contexts: list[InstanceRuntimeContext] = field(default_factory=list)
    queue_items: list[QueuedTask] = field(default_factory=list)
    recent_events: list[LiveRuntimeEventRecord] = field(default_factory=list)

    def get_instance_snapshot(self, instance_id: str) -> LiveRuntimeInstanceSnapshot | None:
        for item in self.instance_snapshots:
            if item.instance_id == instance_id:
                return item
        return None


class LiveRuntimeSession:
    def __init__(
        self,
        adapter: EmulatorActionAdapter,
        *,
        discovery: InstanceDiscovery | None = None,
        profile_resolver: ProfileResolver | None = None,
        event_bus: EventBus | None = None,
        audit_sink: AuditSink | None = None,
        max_recent_events: int = 100,
    ) -> None:
        self._event_bus = event_bus or EventBus()
        self._audit_sink = audit_sink
        self._discovery = discovery or discover_instances
        self._profile_resolver = profile_resolver
        self._max_recent_events = max(1, int(max_recent_events))
        self._recent_events: list[LiveRuntimeEventRecord] = []
        self._event_sequence = 0
        self._revision = 0
        self._last_sync_at: object | None = None
        self._last_discovery_at: object | None = None
        self._last_sync_error = ""
        self._last_command_result: CommandDispatchResult | None = None
        self._last_queue_result: QueueRunResult | None = None
        self._last_snapshot: LiveRuntimeSnapshot | None = None
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
        self._subscribe_runtime_events()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def coordinator(self) -> RuntimeCoordinator:
        return self._coordinator

    @property
    def queue(self) -> TaskQueue:
        return self._coordinator.queue

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def last_sync_at(self) -> object | None:
        return self._last_sync_at

    @property
    def last_discovery_at(self) -> object | None:
        return self._last_discovery_at

    @property
    def last_sync_error(self) -> str:
        return self._last_sync_error

    @property
    def last_command_result(self) -> CommandDispatchResult | None:
        return self._last_command_result

    @property
    def last_queue_result(self) -> QueueRunResult | None:
        return self._last_queue_result

    @property
    def last_snapshot(self) -> LiveRuntimeSnapshot:
        if self._last_snapshot is None or self._last_snapshot.revision != self._revision:
            self._last_snapshot = self.snapshot(force_refresh=True)
        return self._last_snapshot

    def discover(self) -> list[InstanceState]:
        return list(self._discovery())

    def poll(self) -> LiveRuntimeSnapshot:
        self.sync_instances()
        return self.snapshot()

    def sync_instances(self, states: list[InstanceState] | None = None) -> list[InstanceState]:
        before_revision = self._revision
        if states is None:
            try:
                states = self.discover()
            except Exception as exc:
                self._last_sync_at = utc_now()
                self._last_sync_error = str(exc)
                self._ensure_revision_changed(before_revision)
                return self._coordinator.registry.list_instances()
            self._last_discovery_at = utc_now()
        else:
            states = list(states)

        synced = self._coordinator.sync_instances(states)
        self._last_sync_at = utc_now()
        self._last_sync_error = ""
        self._auto_bind_profiles(synced)
        self._ensure_revision_changed(before_revision)
        return synced

    def bind_profile(self, instance_id: str, binding: ProfileBinding) -> InstanceRuntimeContext:
        before_revision = self._revision
        context = self._coordinator.bind_profile(instance_id, binding)
        self._ensure_revision_changed(before_revision)
        return context

    def enqueue(self, item: QueuedTask) -> QueuedTask:
        before_revision = self._revision
        queued = self._coordinator.enqueue(item)
        self._ensure_revision_changed(before_revision)
        return queued

    def enqueue_many(self, items: list[QueuedTask]) -> list[QueuedTask]:
        return [self.enqueue(item) for item in items]

    def refresh(self, instance_id: str | None = None) -> CommandDispatchResult:
        return self.dispatch_command(
            InstanceCommand(
                command_type=InstanceCommandType.REFRESH,
                instance_id=instance_id,
            )
        )

    def dispatch_command(self, command: InstanceCommand) -> CommandDispatchResult:
        before_revision = self._revision
        result = self._coordinator.dispatch_command(command)
        self._last_command_result = result
        if command.command_type == InstanceCommandType.START_QUEUE:
            self._store_last_queue_result_from_dispatch(result)
        self._ensure_revision_changed(before_revision)
        return result

    def start_queue(self, instance_id: str) -> QueueRunResult:
        before_revision = self._revision
        result = self._coordinator.start_queue(instance_id)
        self._last_queue_result = result
        self._ensure_revision_changed(before_revision)
        return result

    def get_runtime_context(self, instance_id: str) -> InstanceRuntimeContext | None:
        return self._coordinator.get_runtime_context(instance_id)

    def list_runtime_contexts(self) -> list[InstanceRuntimeContext]:
        return self._coordinator.list_runtime_contexts()

    def list_queue_items(self, instance_id: str | None = None) -> list[QueuedTask]:
        return self._coordinator.queue.list_items(instance_id=instance_id)

    def get_instance_snapshot(self, instance_id: str) -> LiveRuntimeInstanceSnapshot | None:
        return self.snapshot(instance_id=instance_id).get_instance_snapshot(instance_id)

    def snapshot(
        self,
        instance_id: str | None = None,
        *,
        force_refresh: bool = False,
    ) -> LiveRuntimeSnapshot:
        if (
            instance_id is None
            and not force_refresh
            and self._last_snapshot is not None
            and self._last_snapshot.revision == self._revision
        ):
            return self._last_snapshot

        instances = self._coordinator.registry.list_instances()
        contexts = self.list_runtime_contexts()
        queue_items = self.list_queue_items()
        if instance_id is not None:
            instances = [instance for instance in instances if instance.instance_id == instance_id]
            contexts = [context for context in contexts if context.instance_id == instance_id]
            queue_items = [item for item in queue_items if item.instance_id == instance_id]

        snapshot = LiveRuntimeSnapshot(
            captured_at=utc_now(),
            revision=self._revision,
            last_sync_at=self._last_sync_at,
            last_discovery_at=self._last_discovery_at,
            last_sync_error=self._last_sync_error,
            last_command_result=self._last_command_result,
            last_queue_result=self._last_queue_result,
            instance_snapshots=self._build_instance_snapshots(instances, contexts, queue_items),
            instances=instances,
            contexts=contexts,
            queue_items=queue_items,
            recent_events=self._list_recent_events(instance_id=instance_id),
        )
        if instance_id is None:
            self._last_snapshot = snapshot
        return snapshot

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

    def _build_instance_snapshots(
        self,
        instances: list[InstanceState],
        contexts: list[InstanceRuntimeContext],
        queue_items: list[QueuedTask],
    ) -> list[LiveRuntimeInstanceSnapshot]:
        context_map = {context.instance_id: context for context in contexts}
        queue_map: dict[str, list[QueuedTask]] = {}
        for item in queue_items:
            queue_map.setdefault(item.instance_id, []).append(item)
        return [
            LiveRuntimeInstanceSnapshot(
                instance_id=instance.instance_id,
                instance=instance,
                context=context_map.get(instance.instance_id),
                queue_items=list(queue_map.get(instance.instance_id, [])),
            )
            for instance in instances
        ]

    def _subscribe_runtime_events(self) -> None:
        for event_name in _RUNTIME_EVENT_NAMES:
            self._event_bus.subscribe(event_name, self._record_event)

    def _record_event(self, event: AppEvent) -> None:
        self._event_sequence += 1
        self._recent_events.append(
            LiveRuntimeEventRecord(
                sequence_id=self._event_sequence,
                name=event.name,
                emitted_at=event.emitted_at,
                instance_id=str(event.payload.get("instance_id", "")),
                payload=dict(event.payload),
            )
        )
        if len(self._recent_events) > self._max_recent_events:
            self._recent_events = self._recent_events[-self._max_recent_events :]
        self._touch()

    def _list_recent_events(self, *, instance_id: str | None = None) -> list[LiveRuntimeEventRecord]:
        if instance_id is None:
            return list(self._recent_events)
        return [
            event
            for event in self._recent_events
            if not event.instance_id or event.instance_id == instance_id
        ]

    def _store_last_queue_result_from_dispatch(self, dispatch_result: CommandDispatchResult) -> None:
        for result in dispatch_result.results:
            if isinstance(result, QueueRunResult):
                self._last_queue_result = result
                return

    def _ensure_revision_changed(self, previous_revision: int) -> None:
        if self._revision == previous_revision:
            self._touch()

    def _touch(self) -> None:
        self._revision += 1
        self._last_snapshot = None
