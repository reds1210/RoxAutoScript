from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
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
from roxauto.core.models import (
    FailureSnapshotMetadata,
    InstanceRuntimeContext,
    InstanceState,
    InstanceStatus,
    PreviewFrame,
    ProfileBinding,
    TaskSpec,
    TaskRunTelemetry,
    TaskStepTelemetry,
)
from roxauto.core.queue import QueuedTask, TaskQueue
from roxauto.core.runtime import AuditSink, QueueRunResult, RuntimeCoordinator, RuntimeInspectionResult
from roxauto.core.time import utc_now
from roxauto.emulator.adapter import AdbTransport
from roxauto.emulator.discovery import discover_instances
from roxauto.emulator.execution import (
    EmulatorActionAdapter,
    RuntimeExecutionPath,
    build_adb_execution_path,
    build_runtime_execution_path,
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


@dataclass(slots=True, frozen=True)
class RuntimeTaskFactoryRequest:
    task_id: str
    instance: InstanceState
    runtime_context: InstanceRuntimeContext | None
    profile_binding: ProfileBinding | None
    adapter: EmulatorActionAdapter
    execution_path: RuntimeExecutionPath
    metadata: dict[str, Any] = field(default_factory=dict)


class RegisteredTaskFactory(Protocol):
    def __call__(self, request: RuntimeTaskFactoryRequest) -> TaskSpec:
        """Build one task spec from the current runtime/session state."""


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
    def last_failure_snapshot(self) -> FailureSnapshotMetadata | None:
        if self.context is None:
            return None
        return self.context.last_failure_snapshot

    @property
    def health_check_ok(self) -> bool | None:
        if self.context is None:
            return None
        return self.context.health_check_ok

    @property
    def active_task_run(self) -> TaskRunTelemetry | None:
        if self.context is None:
            return None
        return self.context.active_task_run

    @property
    def last_task_run(self) -> TaskRunTelemetry | None:
        if self.context is None:
            return None
        return self.context.last_task_run

    @property
    def last_failed_task_run(self) -> TaskRunTelemetry | None:
        if self.context is None:
            return None
        return self.context.last_failed_task_run


@dataclass(slots=True)
class LiveRuntimeSnapshot:
    captured_at: object = field(default_factory=utc_now)
    revision: int = 0
    last_sync_at: object | None = None
    last_discovery_at: object | None = None
    last_sync_ok: bool = True
    last_sync_error: str = ""
    last_command_result: CommandDispatchResult | None = None
    last_queue_result: QueueRunResult | None = None
    last_inspection_results: list[RuntimeInspectionResult] = field(default_factory=list)
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


@dataclass(slots=True, frozen=True)
class LiveRuntimeInstanceSummary:
    instance_id: str
    label: str
    adb_serial: str
    status: str
    last_seen_at: object
    queue_depth: int = 0
    active_task_id: str = ""
    active_run_id: str = ""
    active_step_id: str = ""
    active_step_status: str = ""
    active_step_anchor_id: str = ""
    active_step_failure_reason_id: str = ""
    active_step_outcome_code: str = ""
    stop_requested: bool = False
    health_check_ok: bool | None = None
    profile_id: str = ""
    profile_display_name: str = ""
    preview_image_path: str = ""
    failure_snapshot_id: str = ""
    failure_reason: str = ""
    failure_step_id: str = ""
    failure_anchor_id: str = ""
    failure_reason_id: str = ""
    failure_outcome_code: str = ""
    failure_inspection_attempt_count: int = 0
    last_task_id: str = ""
    last_run_id: str = ""
    last_run_status: str = ""
    last_step_count: int = 0
    last_completed_step_count: int = 0
    last_step_id: str = ""
    last_step_status: str = ""
    last_step_anchor_id: str = ""
    last_step_failure_reason_id: str = ""
    last_step_outcome_code: str = ""
    last_failure_snapshot_id: str = ""
    last_failure_reason: str = ""
    last_failure_step_id: str = ""
    last_failure_anchor_id: str = ""
    last_failure_reason_id: str = ""
    last_failure_outcome_code: str = ""
    last_failure_inspection_attempt_count: int = 0
    last_failed_task_id: str = ""
    last_failed_run_id: str = ""
    last_failed_run_status: str = ""
    last_failed_step_count: int = 0
    last_failed_completed_step_count: int = 0
    last_failed_step_id: str = ""
    last_failed_step_status: str = ""
    last_failed_step_anchor_id: str = ""
    last_failed_step_failure_reason_id: str = ""
    last_failed_step_outcome_code: str = ""


@dataclass(slots=True, frozen=True)
class LiveRuntimeTaskOutcomeSummary:
    task_id: str
    instance_id: str
    label: str = ""
    adb_serial: str = ""
    run_id: str = ""
    status: str = ""
    queue_id: str = ""
    attempt: int = 0
    step_count: int = 0
    completed_step_count: int = 0
    started_at: object | None = None
    finished_at: object | None = None
    final_step_id: str = ""
    final_step_status: str = ""
    failure_snapshot_id: str = ""
    stop_condition_kind: str = ""
    failure_reason_id: str = ""
    outcome_code: str = ""
    last_observed_state: str = ""
    workflow_mode: str = ""
    inspection_reason: str = ""
    anchor_id: str = ""
    expected_anchor_id: str = ""
    signal_anchor_ids: tuple[str, ...] = field(default_factory=tuple)
    matched_anchor_ids: tuple[str, ...] = field(default_factory=tuple)
    preview_image_path: str = ""
    source_image: str = ""


@dataclass(slots=True, frozen=True)
class LiveRuntimeTaskOutcomeReport:
    captured_at: object = field(default_factory=utc_now)
    task_id: str = ""
    instance_count: int = 0
    run_count: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    aborted_count: int = 0
    runs: tuple[LiveRuntimeTaskOutcomeSummary, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class LiveRuntimeRefreshState:
    operation: str = "idle"
    instance_id: str = ""
    rediscover: bool = False
    refresh_runtime: bool = False
    run_health_check: bool = True
    capture_preview: bool = False
    in_flight: bool = False
    pending: bool = False
    last_requested_at: object | None = None
    last_started_at: object | None = None
    last_finished_at: object | None = None
    last_error: str = ""
    last_completed_revision: int = 0


@dataclass(slots=True, frozen=True)
class LiveRuntimeState:
    captured_at: object = field(default_factory=utc_now)
    revision: int = 0
    refresh_state: LiveRuntimeRefreshState = field(default_factory=LiveRuntimeRefreshState)
    last_sync_at: object | None = None
    last_discovery_at: object | None = None
    last_sync_ok: bool = True
    last_sync_error: str = ""
    instance_count: int = 0
    ready_count: int = 0
    busy_count: int = 0
    paused_count: int = 0
    error_count: int = 0
    disconnected_count: int = 0
    queued_count: int = 0
    failure_count: int = 0
    last_command_type: str = ""
    last_command_status: str = ""
    last_queue_instance_id: str = ""
    last_queue_message: str = ""
    instances: tuple[LiveRuntimeInstanceSummary, ...] = field(default_factory=tuple)
    selected_instance: LiveRuntimeInstanceSummary | None = None

    def get_instance(self, instance_id: str) -> LiveRuntimeInstanceSummary | None:
        for item in self.instances:
            if item.instance_id == instance_id:
                return item
        return None


@dataclass(slots=True)
class _ScheduledRefreshRequest:
    operation: str
    instance_id: str | None = None
    rediscover: bool = False
    refresh_runtime: bool = False
    run_health_check: bool = True
    capture_preview: bool = False


class LiveRuntimeSession:
    def __init__(
        self,
        adapter: EmulatorActionAdapter | None = None,
        *,
        execution_path: RuntimeExecutionPath | None = None,
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
        self._last_sync_ok = True
        self._last_sync_error = ""
        self._last_command_result: CommandDispatchResult | None = None
        self._last_queue_result: QueueRunResult | None = None
        self._last_inspection_results: list[RuntimeInspectionResult] = []
        self._last_snapshot: LiveRuntimeSnapshot | None = None
        self._operation_lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._live_state_cache: LiveRuntimeState | None = None
        self._refresh_state = LiveRuntimeRefreshState()
        self._task_factories: dict[str, RegisteredTaskFactory] = {}
        self._background_condition = threading.Condition()
        self._background_request: _ScheduledRefreshRequest | None = None
        self._background_worker: threading.Thread | None = None
        self._background_shutdown = False
        self._background_in_flight = False
        if execution_path is not None and adapter is not None:
            raise ValueError("Provide either adapter or execution_path, not both")
        if execution_path is None:
            if adapter is None:
                raise ValueError("adapter or execution_path is required")
            execution_path = build_runtime_execution_path(
                adapter,
                event_bus=self._event_bus,
                audit_sink=self._audit_sink,
            )
        self._execution_path = execution_path
        self._coordinator = RuntimeCoordinator(
            command_executor=self._execution_path.command_executor,
            health_checker=self._execution_path.health_checker,
            preview_capture=self._execution_path.preview_capture,
            event_bus=self._event_bus,
            audit_sink=self._audit_sink,
        )
        self._subscribe_runtime_events()
        with self._operation_lock:
            self._publish_live_state_locked()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def adapter(self) -> EmulatorActionAdapter:
        return self._execution_path.adapter

    @property
    def execution_path(self) -> RuntimeExecutionPath:
        return self._execution_path

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
    def last_sync_ok(self) -> bool:
        return self._last_sync_ok

    @property
    def last_command_result(self) -> CommandDispatchResult | None:
        return self._last_command_result

    @property
    def last_queue_result(self) -> QueueRunResult | None:
        return self._last_queue_result

    @property
    def last_inspection_results(self) -> list[RuntimeInspectionResult]:
        return list(self._last_inspection_results)

    @property
    def last_snapshot(self) -> LiveRuntimeSnapshot:
        with self._operation_lock:
            if self._last_snapshot is None or self._last_snapshot.revision != self._revision:
                self._last_snapshot = self.snapshot(force_refresh=True)
            return self._last_snapshot

    @property
    def refresh_state(self) -> LiveRuntimeRefreshState:
        with self._state_lock:
            return self._refresh_state

    @property
    def last_live_state(self) -> LiveRuntimeState:
        return self.get_live_state()

    def discover(self) -> list[InstanceState]:
        with self._operation_lock:
            return list(self._discovery())

    def poll(
        self,
        instance_id: str | None = None,
        *,
        refresh_runtime: bool = False,
        run_health_check: bool = True,
        capture_preview: bool = True,
    ) -> LiveRuntimeSnapshot:
        with self._operation_lock:
            self.sync_instances()
            if refresh_runtime and self._last_sync_ok:
                self.refresh_runtime_contexts(
                    instance_id=instance_id,
                    run_health_check=run_health_check,
                    capture_preview=capture_preview,
                )
            return self.snapshot(instance_id=instance_id)

    def sync_instances(self, states: list[InstanceState] | None = None) -> list[InstanceState]:
        with self._operation_lock:
            before_revision = self._revision
            if states is None:
                try:
                    states = self.discover()
                except Exception as exc:
                    self._last_sync_at = utc_now()
                    self._last_sync_ok = False
                    self._last_sync_error = str(exc)
                    self._ensure_revision_changed(before_revision)
                    self._publish_live_state_locked()
                    return self._coordinator.registry.list_instances()
                self._last_discovery_at = utc_now()
            else:
                states = list(states)

            synced = self._coordinator.sync_instances(states)
            self._last_sync_at = utc_now()
            self._last_sync_ok = True
            self._last_sync_error = ""
            self._auto_bind_profiles(synced)
            self._ensure_revision_changed(before_revision)
            self._publish_live_state_locked()
            return synced

    def bind_profile(self, instance_id: str, binding: ProfileBinding) -> InstanceRuntimeContext:
        with self._operation_lock:
            before_revision = self._revision
            context = self._coordinator.bind_profile(instance_id, binding)
            self._ensure_revision_changed(before_revision)
            self._publish_live_state_locked()
            return context

    def register_task_factory(self, task_id: str, factory: RegisteredTaskFactory) -> None:
        normalized_task_id = self._normalize_registered_task_id(task_id)
        with self._operation_lock:
            self._task_factories[normalized_task_id] = factory

    def unregister_task_factory(self, task_id: str) -> None:
        normalized_task_id = self._normalize_registered_task_id(task_id)
        with self._operation_lock:
            self._task_factories.pop(normalized_task_id, None)

    def has_task_factory(self, task_id: str) -> bool:
        normalized_task_id = self._normalize_registered_task_id(task_id)
        with self._operation_lock:
            return normalized_task_id in self._task_factories

    def build_registered_task_spec(
        self,
        instance_id: str,
        task_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> TaskSpec:
        with self._operation_lock:
            return self._build_registered_task_spec_locked(
                instance_id=instance_id,
                task_id=task_id,
                metadata=metadata,
            )

    def enqueue(self, item: QueuedTask) -> QueuedTask:
        with self._operation_lock:
            before_revision = self._revision
            queued = self._coordinator.enqueue(item)
            self._ensure_revision_changed(before_revision)
            self._publish_live_state_locked()
            return queued

    def enqueue_registered_task(
        self,
        instance_id: str,
        task_id: str,
        *,
        priority: int = 100,
        builder_metadata: dict[str, Any] | None = None,
        queue_metadata: dict[str, Any] | None = None,
    ) -> QueuedTask:
        with self._operation_lock:
            before_revision = self._revision
            spec = self._build_registered_task_spec_locked(
                instance_id=instance_id,
                task_id=task_id,
                metadata=builder_metadata,
            )
            queued = self._coordinator.enqueue(
                QueuedTask(
                    instance_id=instance_id,
                    spec=spec,
                    priority=priority,
                    metadata=dict(queue_metadata or {}),
                )
            )
            self._ensure_revision_changed(before_revision)
            self._publish_live_state_locked()
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
        with self._operation_lock:
            before_revision = self._revision
            result = self._coordinator.dispatch_command(command)
            self._last_command_result = result
            if command.command_type == InstanceCommandType.START_QUEUE:
                self._store_last_queue_result_from_dispatch(result)
            elif command.command_type == InstanceCommandType.REFRESH:
                self._store_last_inspection_results_from_contexts(result.instance_ids)
            self._ensure_revision_changed(before_revision)
            self._publish_live_state_locked()
            return result

    def start_queue(self, instance_id: str) -> QueueRunResult:
        with self._operation_lock:
            before_revision = self._revision
            result = self._coordinator.start_queue(instance_id)
            self._last_queue_result = result
            self._ensure_revision_changed(before_revision)
            self._publish_live_state_locked()
            return result

    def refresh_runtime_contexts(
        self,
        instance_id: str | None = None,
        *,
        run_health_check: bool = True,
        capture_preview: bool = True,
    ) -> list[RuntimeInspectionResult]:
        with self._operation_lock:
            before_revision = self._revision
            if instance_id is None:
                results = self._coordinator.inspect_instances(
                    run_health_check=run_health_check,
                    capture_preview=capture_preview,
                )
            else:
                results = [
                    self._coordinator.inspect_instance(
                        instance_id,
                        run_health_check=run_health_check,
                        capture_preview=capture_preview,
                    )
                ]
            self._last_inspection_results = list(results)
            self._ensure_revision_changed(before_revision)
            self._publish_live_state_locked()
            return list(results)

    def get_runtime_context(self, instance_id: str) -> InstanceRuntimeContext | None:
        with self._operation_lock:
            return self._coordinator.get_runtime_context(instance_id)

    def list_runtime_contexts(self) -> list[InstanceRuntimeContext]:
        with self._operation_lock:
            return self._coordinator.list_runtime_contexts()

    def list_queue_items(self, instance_id: str | None = None) -> list[QueuedTask]:
        with self._operation_lock:
            return self._coordinator.queue.list_items(instance_id=instance_id)

    def get_instance_snapshot(self, instance_id: str) -> LiveRuntimeInstanceSnapshot | None:
        return self.snapshot(instance_id=instance_id).get_instance_snapshot(instance_id)

    def snapshot(
        self,
        instance_id: str | None = None,
        *,
        force_refresh: bool = False,
    ) -> LiveRuntimeSnapshot:
        with self._operation_lock:
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
                last_sync_ok=self._last_sync_ok,
                last_sync_error=self._last_sync_error,
                last_command_result=self._last_command_result,
                last_queue_result=self._last_queue_result,
                last_inspection_results=self._filter_inspection_results(instance_id=instance_id),
                instance_snapshots=self._build_instance_snapshots(instances, contexts, queue_items),
                instances=instances,
                contexts=contexts,
                queue_items=queue_items,
                recent_events=self._list_recent_events(instance_id=instance_id),
            )
            if instance_id is None:
                self._last_snapshot = snapshot
            return snapshot

    def get_live_state(self, instance_id: str | None = None) -> LiveRuntimeState:
        with self._state_lock:
            cached = self._live_state_cache
        if cached is None:
            with self._operation_lock:
                self._publish_live_state_locked()
            with self._state_lock:
                cached = self._live_state_cache
        if cached is None:
            return LiveRuntimeState(refresh_state=self.refresh_state)
        if instance_id is None:
            return cached
        return replace(
            cached,
            captured_at=utc_now(),
            selected_instance=cached.get_instance(instance_id),
        )

    def list_instance_summaries(self) -> list[LiveRuntimeInstanceSummary]:
        return list(self.get_live_state().instances)

    def get_instance_summary(self, instance_id: str) -> LiveRuntimeInstanceSummary | None:
        return self.get_live_state(instance_id=instance_id).selected_instance

    def list_task_run_summaries(
        self,
        task_id: str | None = None,
        *,
        instance_id: str | None = None,
    ) -> list[LiveRuntimeTaskOutcomeSummary]:
        with self._operation_lock:
            return self._list_task_run_summaries_locked(
                task_id=task_id,
                instance_id=instance_id,
            )

    def build_task_outcome_report(
        self,
        task_id: str,
        *,
        instance_id: str | None = None,
    ) -> LiveRuntimeTaskOutcomeReport:
        normalized_task_id = str(task_id).strip()
        if not normalized_task_id:
            raise ValueError("task_id is required")
        with self._operation_lock:
            latest_by_instance: dict[str, LiveRuntimeTaskOutcomeSummary] = {}
            for summary in self._list_task_run_summaries_locked(
                task_id=normalized_task_id,
                instance_id=instance_id,
            ):
                latest_by_instance[summary.instance_id] = summary
            for summary in self._list_context_task_outcome_summaries_locked(
                task_id=normalized_task_id,
                instance_id=instance_id,
            ):
                latest_by_instance.setdefault(summary.instance_id, summary)
            runs = tuple(
                sorted(
                    latest_by_instance.values(),
                    key=lambda item: item.instance_id,
                )
            )
            return LiveRuntimeTaskOutcomeReport(
                captured_at=utc_now(),
                task_id=normalized_task_id,
                instance_count=len(runs),
                run_count=len(runs),
                succeeded_count=sum(1 for item in runs if item.status == "succeeded"),
                failed_count=sum(1 for item in runs if item.status == "failed"),
                aborted_count=sum(1 for item in runs if item.status == "aborted"),
                runs=runs,
            )

    def connect_instance(
        self,
        instance: InstanceState,
        *,
        refresh_runtime: bool = False,
        run_health_check: bool = True,
        capture_preview: bool = False,
    ) -> LiveRuntimeInstanceSummary | None:
        with self._operation_lock:
            merged = self._merge_instance_states_locked(instance)
            self.sync_instances(merged)
            if refresh_runtime and self._last_sync_ok:
                self.refresh_runtime_contexts(
                    instance_id=instance.instance_id,
                    run_health_check=run_health_check,
                    capture_preview=capture_preview,
                )
        return self.get_instance_summary(instance.instance_id)

    def disconnect_instance(
        self,
        instance_id: str,
        *,
        reason: str = "",
    ) -> LiveRuntimeInstanceSummary | None:
        with self._operation_lock:
            instance = self._coordinator.registry.get(instance_id)
            if instance is None:
                raise KeyError(f"Unknown instance_id: {instance_id}")
            metadata = dict(instance.metadata)
            if reason:
                metadata["disconnect_reason"] = reason
            merged = self._merge_instance_states_locked(
                replace(
                    instance,
                    status=InstanceStatus.DISCONNECTED,
                    metadata=metadata,
                )
            )
            self.sync_instances(merged)
        return self.get_instance_summary(instance_id)

    def reconnect_instance(
        self,
        instance_id: str,
        *,
        rediscover: bool = True,
        refresh_runtime: bool = False,
        run_health_check: bool = True,
        capture_preview: bool = False,
    ) -> LiveRuntimeInstanceSummary | None:
        with self._operation_lock:
            instance = self._coordinator.registry.get(instance_id)
            if instance is None:
                raise KeyError(f"Unknown instance_id: {instance_id}")
            metadata = dict(instance.metadata)
            metadata["reconnect_requested_at"] = utc_now()
            merged = self._merge_instance_states_locked(
                replace(
                    instance,
                    status=InstanceStatus.CONNECTING,
                    metadata=metadata,
                )
            )
            self.sync_instances(merged)
            if rediscover:
                self.rediscover_instances(
                    instance_id=instance_id,
                    refresh_runtime=refresh_runtime,
                    run_health_check=run_health_check,
                    capture_preview=capture_preview,
                )
            elif refresh_runtime and self._last_sync_ok:
                self.refresh_runtime_contexts(
                    instance_id=instance_id,
                    run_health_check=run_health_check,
                    capture_preview=capture_preview,
                )
        return self.get_instance_summary(instance_id)

    def rediscover_instances(
        self,
        *,
        instance_id: str | None = None,
        refresh_runtime: bool = False,
        run_health_check: bool = True,
        capture_preview: bool = False,
    ) -> list[LiveRuntimeInstanceSummary]:
        with self._operation_lock:
            self.sync_instances()
            if (
                refresh_runtime
                and self._last_sync_ok
                and (instance_id is None or self._coordinator.registry.get(instance_id) is not None)
            ):
                self.refresh_runtime_contexts(
                    instance_id=instance_id,
                    run_health_check=run_health_check,
                    capture_preview=capture_preview,
                )
        return self.list_instance_summaries()

    def schedule_runtime_refresh(
        self,
        instance_id: str | None = None,
        *,
        run_health_check: bool = True,
        capture_preview: bool = False,
    ) -> LiveRuntimeRefreshState:
        return self._schedule_refresh(
            _ScheduledRefreshRequest(
                operation="runtime_refresh",
                instance_id=instance_id,
                refresh_runtime=True,
                run_health_check=run_health_check,
                capture_preview=capture_preview,
            )
        )

    def schedule_rediscover(
        self,
        *,
        instance_id: str | None = None,
        refresh_runtime: bool = False,
        run_health_check: bool = True,
        capture_preview: bool = False,
    ) -> LiveRuntimeRefreshState:
        return self._schedule_refresh(
            _ScheduledRefreshRequest(
                operation="rediscover",
                instance_id=instance_id,
                rediscover=True,
                refresh_runtime=refresh_runtime,
                run_health_check=run_health_check,
                capture_preview=capture_preview,
            )
        )

    def schedule_sync(self) -> LiveRuntimeRefreshState:
        return self.schedule_rediscover(refresh_runtime=False)

    def wait_for_background_idle(self, timeout_sec: float = 5.0) -> bool:
        timeout_sec = max(0.0, float(timeout_sec))
        end_monotonic = None
        if timeout_sec > 0.0:
            end_monotonic = time.monotonic() + timeout_sec
        with self._background_condition:
            while True:
                if self._background_request is None and not self._background_in_flight:
                    return True
                if end_monotonic is None:
                    return False
                remaining = end_monotonic - time.monotonic()
                if remaining <= 0:
                    return False
                self._background_condition.wait(timeout=remaining)

    def _schedule_refresh(self, request: _ScheduledRefreshRequest) -> LiveRuntimeRefreshState:
        self._ensure_background_worker()
        scheduled_at = utc_now()
        with self._background_condition:
            self._background_request = request
            self._background_condition.notify_all()
        self._set_refresh_state(
            replace(
                self.refresh_state,
                operation=request.operation,
                instance_id=request.instance_id or "",
                rediscover=request.rediscover,
                refresh_runtime=request.refresh_runtime,
                run_health_check=request.run_health_check,
                capture_preview=request.capture_preview,
                pending=True,
                last_requested_at=scheduled_at,
                last_error="",
            )
        )
        return self.refresh_state

    def _ensure_background_worker(self) -> None:
        with self._background_condition:
            if self._background_worker is not None and self._background_worker.is_alive():
                return
            self._background_shutdown = False
            self._background_worker = threading.Thread(
                target=self._background_worker_loop,
                name="roxauto-live-runtime-refresh",
                daemon=True,
            )
            self._background_worker.start()

    def _background_worker_loop(self) -> None:
        while True:
            with self._background_condition:
                while not self._background_shutdown and self._background_request is None:
                    self._background_condition.wait()
                if self._background_shutdown:
                    self._background_condition.notify_all()
                    return
                request = self._background_request
                self._background_request = None
                self._background_in_flight = True

            self._set_refresh_state(
                replace(
                    self.refresh_state,
                    operation=request.operation,
                    instance_id=request.instance_id or "",
                    rediscover=request.rediscover,
                    refresh_runtime=request.refresh_runtime,
                    run_health_check=request.run_health_check,
                    capture_preview=request.capture_preview,
                    in_flight=True,
                    pending=False,
                    last_started_at=utc_now(),
                    last_error="",
                )
            )

            error = ""
            try:
                if request.rediscover:
                    self.rediscover_instances(
                        instance_id=request.instance_id,
                        refresh_runtime=request.refresh_runtime,
                        run_health_check=request.run_health_check,
                        capture_preview=request.capture_preview,
                    )
                elif request.refresh_runtime:
                    with self._operation_lock:
                        if self._coordinator.registry.get(request.instance_id or "") is None and request.instance_id:
                            raise KeyError(f"Unknown instance_id: {request.instance_id}")
                    self.refresh_runtime_contexts(
                        instance_id=request.instance_id,
                        run_health_check=request.run_health_check,
                        capture_preview=request.capture_preview,
                    )
                else:
                    self.sync_instances()
                if request.rediscover and not self._last_sync_ok:
                    error = self._last_sync_error
            except Exception as exc:
                error = str(exc)

            with self._background_condition:
                has_pending = self._background_request is not None
                self._background_in_flight = has_pending
                self._background_condition.notify_all()
            self._set_refresh_state(
                replace(
                    self.refresh_state,
                    in_flight=False,
                    pending=has_pending,
                    last_finished_at=utc_now(),
                    last_error=error,
                    last_completed_revision=self._revision,
                )
            )
            with self._background_condition:
                self._background_condition.notify_all()

    def _set_refresh_state(self, state: LiveRuntimeRefreshState) -> None:
        with self._state_lock:
            self._refresh_state = state
            if self._live_state_cache is not None:
                self._live_state_cache = replace(
                    self._live_state_cache,
                    captured_at=utc_now(),
                    refresh_state=state,
                )

    def _publish_live_state_locked(self) -> LiveRuntimeState:
        instances = self._coordinator.registry.list_instances()
        status_counts = {
            InstanceStatus.READY.value: 0,
            InstanceStatus.BUSY.value: 0,
            InstanceStatus.PAUSED.value: 0,
            InstanceStatus.ERROR.value: 0,
            InstanceStatus.DISCONNECTED.value: 0,
        }
        summaries: list[LiveRuntimeInstanceSummary] = []
        queued_count = 0
        failure_count = 0
        for instance in instances:
            context = self._coordinator.get_runtime_context(instance.instance_id)
            if context is None:
                context = self._coordinator._sync_context_for_instance(instance)
            status_value = instance.status.value
            if status_value in status_counts:
                status_counts[status_value] += 1
            summary = self._build_instance_summary(instance, context)
            summaries.append(summary)
            queued_count += summary.queue_depth
            if summary.failure_snapshot_id:
                failure_count += 1
        queue_message = self._last_queue_result.message if self._last_queue_result is not None else ""
        state = LiveRuntimeState(
            captured_at=utc_now(),
            revision=self._revision,
            refresh_state=self.refresh_state,
            last_sync_at=self._last_sync_at,
            last_discovery_at=self._last_discovery_at,
            last_sync_ok=self._last_sync_ok,
            last_sync_error=self._last_sync_error,
            instance_count=len(summaries),
            ready_count=status_counts[InstanceStatus.READY.value],
            busy_count=status_counts[InstanceStatus.BUSY.value],
            paused_count=status_counts[InstanceStatus.PAUSED.value],
            error_count=status_counts[InstanceStatus.ERROR.value],
            disconnected_count=status_counts[InstanceStatus.DISCONNECTED.value],
            queued_count=queued_count,
            failure_count=failure_count,
            last_command_type=self._last_command_result.command_type.value if self._last_command_result is not None else "",
            last_command_status=self._last_command_result.status.value if self._last_command_result is not None else "",
            last_queue_instance_id=self._last_queue_result.instance_id if self._last_queue_result is not None else "",
            last_queue_message=queue_message,
            instances=tuple(summaries),
        )
        with self._state_lock:
            self._live_state_cache = state
        return state

    def _build_instance_summary(
        self,
        instance: InstanceState,
        context: InstanceRuntimeContext | None,
    ) -> LiveRuntimeInstanceSummary:
        profile_id = ""
        profile_display_name = ""
        preview_image_path = ""
        failure_snapshot_id = ""
        failure_reason = ""
        failure_step_id = ""
        failure_anchor_id = ""
        failure_reason_id = ""
        failure_outcome_code = ""
        failure_inspection_attempt_count = 0
        last_failure_snapshot_id = ""
        last_failure_reason = ""
        last_failure_step_id = ""
        last_failure_anchor_id = ""
        last_failure_reason_id = ""
        last_failure_outcome_code = ""
        last_failure_inspection_attempt_count = 0
        last_failed_task_id = ""
        last_failed_run_id = ""
        last_failed_run_status = ""
        last_failed_step_count = 0
        last_failed_completed_step_count = 0
        last_failed_step_id = ""
        last_failed_step_status = ""
        last_failed_step_anchor_id = ""
        last_failed_step_failure_reason_id = ""
        last_failed_step_outcome_code = ""
        queue_depth = 0
        active_task_id = ""
        active_run_id = ""
        active_step_id = ""
        active_step_status = ""
        active_step_anchor_id = ""
        active_step_failure_reason_id = ""
        active_step_outcome_code = ""
        last_task_id = ""
        last_run_id = ""
        last_run_status = ""
        last_step_count = 0
        last_completed_step_count = 0
        last_step_id = ""
        last_step_status = ""
        last_step_anchor_id = ""
        last_step_failure_reason_id = ""
        last_step_outcome_code = ""
        stop_requested = False
        health_check_ok = None
        if context is not None:
            queue_depth = context.queue_depth
            active_task_id = context.active_task_id or ""
            active_run_id = context.active_run_id or ""
            stop_requested = context.stop_requested
            health_check_ok = context.health_check_ok
            if context.active_task_run is not None:
                active_step_id = context.active_task_run.current_step_id
                if context.active_task_run.current_step_index >= 0:
                    active_step = context.active_task_run.steps[context.active_task_run.current_step_index]
                    active_step_status = active_step.status.value
                    active_step_anchor_id = self._read_step_anchor_id(active_step)
                    active_step_failure_reason_id = self._read_step_failure_reason_id(active_step)
                    active_step_outcome_code = self._read_step_outcome_code(active_step)
            if context.last_task_run is not None:
                last_task_id = context.last_task_run.task_id
                last_run_id = context.last_task_run.run_id
                last_run_status = context.last_task_run.status.value
                last_step_count = context.last_task_run.step_count
                last_completed_step_count = context.last_task_run.completed_step_count
                last_step = self._latest_projected_step(context.last_task_run)
                if last_step is not None:
                    last_step_id = last_step.step_id
                    last_step_status = last_step.status.value
                    last_step_anchor_id = self._read_step_anchor_id(last_step)
                    last_step_failure_reason_id = self._read_step_failure_reason_id(last_step)
                    last_step_outcome_code = self._read_step_outcome_code(last_step)
            if context.profile_binding is not None:
                profile_id = context.profile_binding.profile_id
                profile_display_name = context.profile_binding.display_name
            if context.preview_frame is not None:
                preview_image_path = context.preview_frame.image_path
            if context.failure_snapshot is not None:
                failure_snapshot_id = context.failure_snapshot.snapshot_id
                failure_reason = context.failure_snapshot.reason.value
                failure_step_id = context.failure_snapshot.step_id or ""
                failure_anchor_id = self._read_snapshot_metadata_value(
                    context.failure_snapshot,
                    "anchor_id",
                )
                failure_reason_id = self._read_snapshot_metadata_value(
                    context.failure_snapshot,
                    "failure_reason_id",
                )
                failure_outcome_code = self._read_snapshot_metadata_value(
                    context.failure_snapshot,
                    "outcome_code",
                )
                failure_inspection_attempt_count = self._read_snapshot_inspection_attempt_count(
                    context.failure_snapshot
                )
            if context.last_failure_snapshot is not None:
                last_failure_snapshot_id = context.last_failure_snapshot.snapshot_id
                last_failure_reason = context.last_failure_snapshot.reason.value
                last_failure_step_id = context.last_failure_snapshot.step_id or ""
                last_failure_anchor_id = self._read_snapshot_metadata_value(
                    context.last_failure_snapshot,
                    "anchor_id",
                )
                last_failure_reason_id = self._read_snapshot_metadata_value(
                    context.last_failure_snapshot,
                    "failure_reason_id",
                )
                last_failure_outcome_code = self._read_snapshot_metadata_value(
                    context.last_failure_snapshot,
                    "outcome_code",
                )
                last_failure_inspection_attempt_count = self._read_snapshot_inspection_attempt_count(
                    context.last_failure_snapshot
                )
            if context.last_failed_task_run is not None:
                last_failed_task_id = context.last_failed_task_run.task_id
                last_failed_run_id = context.last_failed_task_run.run_id
                last_failed_run_status = context.last_failed_task_run.status.value
                last_failed_step_count = context.last_failed_task_run.step_count
                last_failed_completed_step_count = context.last_failed_task_run.completed_step_count
                last_failed_step = self._latest_projected_step(context.last_failed_task_run)
                if last_failed_step is not None:
                    last_failed_step_id = last_failed_step.step_id
                    last_failed_step_status = last_failed_step.status.value
                    last_failed_step_anchor_id = self._read_step_anchor_id(last_failed_step)
                    last_failed_step_failure_reason_id = self._read_step_failure_reason_id(
                        last_failed_step
                    )
                    last_failed_step_outcome_code = self._read_step_outcome_code(last_failed_step)
        return LiveRuntimeInstanceSummary(
            instance_id=instance.instance_id,
            label=instance.label,
            adb_serial=instance.adb_serial,
            status=instance.status.value,
            last_seen_at=instance.last_seen_at,
            queue_depth=queue_depth,
            active_task_id=active_task_id,
            active_run_id=active_run_id,
            active_step_id=active_step_id,
            active_step_status=active_step_status,
            active_step_anchor_id=active_step_anchor_id,
            active_step_failure_reason_id=active_step_failure_reason_id,
            active_step_outcome_code=active_step_outcome_code,
            stop_requested=stop_requested,
            health_check_ok=health_check_ok,
            profile_id=profile_id,
            profile_display_name=profile_display_name,
            preview_image_path=preview_image_path,
            failure_snapshot_id=failure_snapshot_id,
            failure_reason=failure_reason,
            failure_step_id=failure_step_id,
            failure_anchor_id=failure_anchor_id,
            failure_reason_id=failure_reason_id,
            failure_outcome_code=failure_outcome_code,
            failure_inspection_attempt_count=failure_inspection_attempt_count,
            last_task_id=last_task_id,
            last_run_id=last_run_id,
            last_run_status=last_run_status,
            last_step_count=last_step_count,
            last_completed_step_count=last_completed_step_count,
            last_step_id=last_step_id,
            last_step_status=last_step_status,
            last_step_anchor_id=last_step_anchor_id,
            last_step_failure_reason_id=last_step_failure_reason_id,
            last_step_outcome_code=last_step_outcome_code,
            last_failure_snapshot_id=last_failure_snapshot_id,
            last_failure_reason=last_failure_reason,
            last_failure_step_id=last_failure_step_id,
            last_failure_anchor_id=last_failure_anchor_id,
            last_failure_reason_id=last_failure_reason_id,
            last_failure_outcome_code=last_failure_outcome_code,
            last_failure_inspection_attempt_count=last_failure_inspection_attempt_count,
            last_failed_task_id=last_failed_task_id,
            last_failed_run_id=last_failed_run_id,
            last_failed_run_status=last_failed_run_status,
            last_failed_step_count=last_failed_step_count,
            last_failed_completed_step_count=last_failed_completed_step_count,
            last_failed_step_id=last_failed_step_id,
            last_failed_step_status=last_failed_step_status,
            last_failed_step_anchor_id=last_failed_step_anchor_id,
            last_failed_step_failure_reason_id=last_failed_step_failure_reason_id,
            last_failed_step_outcome_code=last_failed_step_outcome_code,
        )

    def _latest_projected_step(self, telemetry: TaskRunTelemetry) -> TaskStepTelemetry | None:
        for step in reversed(telemetry.steps):
            if step.status.value != "pending":
                return step
        return None

    def _read_step_failure_reason_id(self, step: TaskStepTelemetry) -> str:
        if not isinstance(step.data, dict):
            return ""
        value = str(step.data.get("failure_reason_id", "")).strip()
        if value:
            return value
        outcome = step.data.get("step_outcome")
        if isinstance(outcome, dict):
            return str(outcome.get("failure_reason_id", "")).strip()
        return ""

    def _read_step_anchor_id(self, step: TaskStepTelemetry) -> str:
        if not isinstance(step.data, dict):
            return ""
        value = str(step.data.get("anchor_id", "")).strip()
        if value:
            return value
        runtime_step_spec = step.data.get("runtime_step_spec")
        if isinstance(runtime_step_spec, dict):
            return str(runtime_step_spec.get("anchor_id", "")).strip()
        return ""

    def _read_step_outcome_code(self, step: TaskStepTelemetry) -> str:
        if not isinstance(step.data, dict):
            return ""
        return str(step.data.get("outcome_code", "")).strip()

    def _read_snapshot_metadata_value(
        self,
        snapshot: FailureSnapshotMetadata,
        key: str,
    ) -> str:
        return str(snapshot.metadata.get(key, "")).strip()

    def _read_snapshot_inspection_attempt_count(
        self,
        snapshot: FailureSnapshotMetadata,
    ) -> int:
        attempts = snapshot.metadata.get("inspection_attempts")
        if not isinstance(attempts, list):
            return 0
        return len(attempts)

    def _list_task_run_summaries_locked(
        self,
        *,
        task_id: str | None,
        instance_id: str | None,
    ) -> list[LiveRuntimeTaskOutcomeSummary]:
        summaries: list[LiveRuntimeTaskOutcomeSummary] = []
        for event in self._list_recent_events(instance_id=instance_id):
            if event.name != EVENT_TASK_FINISHED:
                continue
            summary = self._task_outcome_summary_from_payload(event.payload.get("summary"))
            if summary is None:
                continue
            if task_id is not None and summary.task_id != str(task_id).strip():
                continue
            summaries.append(summary)
        return summaries

    def _list_context_task_outcome_summaries_locked(
        self,
        *,
        task_id: str,
        instance_id: str | None,
    ) -> list[LiveRuntimeTaskOutcomeSummary]:
        summaries: list[LiveRuntimeTaskOutcomeSummary] = []
        for context in self._coordinator.list_runtime_contexts():
            if instance_id is not None and context.instance_id != instance_id:
                continue
            candidates = (
                context.metadata.get("last_task_outcome_summary"),
                context.metadata.get("last_failed_task_outcome_summary"),
            )
            for candidate in candidates:
                summary = self._task_outcome_summary_from_payload(candidate)
                if summary is None or summary.task_id != task_id:
                    continue
                summaries.append(summary)
                break
        return summaries

    def _task_outcome_summary_from_payload(
        self,
        payload: Any,
    ) -> LiveRuntimeTaskOutcomeSummary | None:
        if not isinstance(payload, dict):
            return None
        task_id = str(payload.get("task_id", "")).strip()
        instance_id = str(payload.get("instance_id", "")).strip()
        if not task_id or not instance_id:
            return None
        return LiveRuntimeTaskOutcomeSummary(
            task_id=task_id,
            instance_id=instance_id,
            label=str(payload.get("instance_label", "")).strip(),
            adb_serial=str(payload.get("adb_serial", "")).strip(),
            run_id=str(payload.get("run_id", "")).strip(),
            status=str(payload.get("status", "")).strip(),
            queue_id=str(payload.get("queue_id", "")).strip(),
            attempt=self._int_or_zero(payload.get("attempt")),
            step_count=self._int_or_zero(payload.get("step_count")),
            completed_step_count=self._int_or_zero(payload.get("completed_step_count")),
            started_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            final_step_id=str(payload.get("final_step_id", "")).strip(),
            final_step_status=str(payload.get("final_step_status", "")).strip(),
            failure_snapshot_id=str(payload.get("failure_snapshot_id", "")).strip(),
            stop_condition_kind=str(payload.get("stop_condition_kind", "")).strip(),
            failure_reason_id=str(payload.get("failure_reason_id", "")).strip(),
            outcome_code=str(payload.get("outcome_code", "")).strip(),
            last_observed_state=str(payload.get("last_observed_state", "")).strip(),
            workflow_mode=str(payload.get("workflow_mode", "")).strip(),
            inspection_reason=str(payload.get("inspection_reason", "")).strip(),
            anchor_id=str(payload.get("anchor_id", "")).strip(),
            expected_anchor_id=str(payload.get("expected_anchor_id", "")).strip(),
            signal_anchor_ids=self._string_tuple(payload.get("signal_anchor_ids")),
            matched_anchor_ids=self._string_tuple(payload.get("matched_anchor_ids")),
            preview_image_path=str(payload.get("preview_image_path", "")).strip(),
            source_image=str(payload.get("source_image", "")).strip(),
        )

    def _string_tuple(self, value: Any) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        normalized = [str(item).strip() for item in value if str(item).strip()]
        return tuple(normalized)

    def _int_or_zero(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _merge_instance_states_locked(self, updated: InstanceState) -> list[InstanceState]:
        merged: list[InstanceState] = []
        replaced_existing = False
        for existing in self._coordinator.registry.list_instances():
            if existing.instance_id == updated.instance_id:
                merged.append(updated)
                replaced_existing = True
            else:
                merged.append(
                    replace(
                        existing,
                        metadata=dict(existing.metadata),
                    )
                )
        if not replaced_existing:
            merged.append(updated)
        return merged

    def _build_registered_task_spec_locked(
        self,
        *,
        instance_id: str,
        task_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TaskSpec:
        normalized_task_id = self._normalize_registered_task_id(task_id)
        factory = self._task_factories.get(normalized_task_id)
        if factory is None:
            raise KeyError(f"Unknown registered task factory: {normalized_task_id}")
        instance = self._coordinator.registry.get(instance_id)
        if instance is None:
            raise KeyError(f"Unknown instance_id: {instance_id}")
        context = self._coordinator.get_runtime_context(instance_id)
        if context is None:
            context = self._coordinator._sync_context_for_instance(instance)
        request = RuntimeTaskFactoryRequest(
            task_id=normalized_task_id,
            instance=instance,
            runtime_context=context,
            profile_binding=context.profile_binding if context is not None else None,
            adapter=self.adapter,
            execution_path=self.execution_path,
            metadata=dict(metadata or {}),
        )
        spec = factory(request)
        if spec.task_id != normalized_task_id:
            raise ValueError(
                "Registered task factory "
                f"{normalized_task_id} returned spec.task_id={spec.task_id}"
            )
        return spec

    def _normalize_registered_task_id(self, task_id: str) -> str:
        normalized_task_id = str(task_id).strip()
        if not normalized_task_id:
            raise ValueError("task_id is required")
        return normalized_task_id

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

    def _filter_inspection_results(
        self,
        *,
        instance_id: str | None = None,
    ) -> list[RuntimeInspectionResult]:
        if instance_id is None:
            return list(self._last_inspection_results)
        return [
            result
            for result in self._last_inspection_results
            if result.instance_id == instance_id
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

    def _store_last_inspection_results_from_contexts(self, instance_ids: list[str]) -> None:
        inspections: list[RuntimeInspectionResult] = []
        for instance_id in instance_ids:
            context = self._coordinator.get_runtime_context(instance_id)
            if context is None:
                continue
            inspections.append(
                RuntimeInspectionResult(
                    instance_id=instance_id,
                    status=context.status,
                    health_check_ok=context.health_check_ok,
                    health_check_message=str(context.metadata.get("last_health_check_message", "")),
                    preview_frame=context.preview_frame,
                    failure_snapshot=context.failure_snapshot,
                    metadata={"source": "dispatch.refresh"},
                )
            )
        if inspections:
            self._last_inspection_results = inspections

    def _ensure_revision_changed(self, previous_revision: int) -> None:
        if self._revision == previous_revision:
            self._touch()

    def _touch(self) -> None:
        self._revision += 1
        self._last_snapshot = None


def build_adb_live_runtime_session(
    *,
    adb_executable: Path | str | None = None,
    transport: AdbTransport | None = None,
    screenshot_dir: Path | str | None = None,
    command_timeout_sec: float = 10.0,
    screenshot_timeout_sec: float = 20.0,
    discovery: InstanceDiscovery | None = None,
    profile_resolver: ProfileResolver | None = None,
    event_bus: EventBus | None = None,
    audit_sink: AuditSink | None = None,
    max_recent_events: int = 100,
) -> LiveRuntimeSession:
    resolved_event_bus = event_bus or EventBus()
    execution_path = build_adb_execution_path(
        adb_executable=adb_executable,
        transport=transport,
        screenshot_dir=Path(screenshot_dir) if screenshot_dir is not None else None,
        command_timeout_sec=command_timeout_sec,
        screenshot_timeout_sec=screenshot_timeout_sec,
        event_bus=resolved_event_bus,
        audit_sink=audit_sink,
    )
    return LiveRuntimeSession(
        execution_path=execution_path,
        discovery=discovery,
        profile_resolver=profile_resolver,
        event_bus=resolved_event_bus,
        audit_sink=audit_sink,
        max_recent_events=max_recent_events,
    )
