from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from roxauto.app.viewmodels import (
    ConsoleSnapshot,
    build_console_snapshot_from_runtime,
    build_manual_control_command,
)
from roxauto.core.commands import CommandDispatchResult, InstanceCommand, InstanceCommandType
from roxauto.core.events import (
    AppEvent,
    EVENT_ALERT_RAISED,
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
    InstanceRuntimeContext,
    InstanceState,
    InstanceStatus,
    ProfileBinding,
    StopCondition,
    StopConditionKind,
    TaskManifest,
    TaskSpec,
)
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import RuntimeCoordinator, TaskExecutionContext, TaskStep, step_success
from roxauto.core.time import utc_now
from roxauto.doctor import build_doctor_report
from roxauto.emulator.execution import ActionExecutor, HealthCheckService, ScreenshotCapturePipeline


_CAPTURED_EVENT_NAMES = [
    EVENT_INSTANCE_UPDATED,
    EVENT_INSTANCE_ERROR,
    EVENT_INSTANCE_HEALTH_CHECKED,
    EVENT_PREVIEW_CAPTURED,
    EVENT_TASK_QUEUED,
    EVENT_TASK_STARTED,
    EVENT_TASK_PROGRESS,
    EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
    EVENT_TASK_FINISHED,
    EVENT_ALERT_RAISED,
    "command.executed",
    "operator.command.dispatched",
    "operator.refresh.completed",
]


class _DemoEmulatorAdapter:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._capture_counts: dict[str, int] = defaultdict(int)

    def capture_screenshot(self, instance: InstanceState) -> Path:
        self._capture_counts[instance.instance_id] += 1
        filename = f"{instance.instance_id}-{self._capture_counts[instance.instance_id]}.png"
        return self._workspace_root / "runtime_logs" / "previews" / filename

    def tap(self, instance: InstanceState, point: tuple[int, int]) -> None:
        instance.metadata["last_tap"] = point

    def swipe(
        self,
        instance: InstanceState,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        instance.metadata["last_swipe"] = {
            "start": start,
            "end": end,
            "duration_ms": duration_ms,
        }

    def input_text(self, instance: InstanceState, text: str) -> None:
        instance.metadata["last_text"] = text

    def health_check(self, instance: InstanceState) -> bool:
        return instance.status != InstanceStatus.DISCONNECTED


class OperatorConsoleRuntimeBridge:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        doctor_report_provider: Callable[[], dict[str, object]] | None = None,
        max_events: int = 200,
    ) -> None:
        self._workspace_root = workspace_root or Path(__file__).resolve().parents[3]
        self._doctor_report_provider = doctor_report_provider or build_doctor_report
        self._max_events = max_events
        self._adb_path = "not found"
        self._packages: dict[str, bool] = {}
        self._seeded_instances: set[str] = set()
        self._events: list[AppEvent] = []
        self._event_bus = EventBus()
        self._subscribe_events()

        adapter = _DemoEmulatorAdapter(self._workspace_root)
        self._coordinator = RuntimeCoordinator(
            event_bus=self._event_bus,
            command_executor=ActionExecutor(adapter, event_bus=self._event_bus),
            health_checker=HealthCheckService(adapter, event_bus=self._event_bus),
            preview_capture=ScreenshotCapturePipeline(adapter, event_bus=self._event_bus),
        )

    @property
    def coordinator(self) -> RuntimeCoordinator:
        return self._coordinator

    def refresh(self) -> ConsoleSnapshot:
        report = self._doctor_report_provider()
        adb = report.get("adb", {})
        self._adb_path = str(adb.get("path") or "not found")
        self._packages = dict(report.get("packages", {}))

        discovered_states = [self._coerce_instance_state(raw) for raw in report.get("instances", [])]
        existing_ids = {instance.instance_id for instance in self._coordinator.registry.list_instances()}
        discovered_ids = {state.instance_id for state in discovered_states}

        if discovered_states:
            self._coordinator.sync_instances(discovered_states)

        for missing_id in sorted(existing_ids - discovered_ids):
            self._coordinator.registry.transition_status(
                missing_id,
                InstanceStatus.DISCONNECTED,
                metadata={"last_refresh_missing": True},
                force=True,
            )

        for state in discovered_states:
            self._ensure_profile_binding(state)
            self._ensure_seed_queue(state)
            self._coordinator.dispatch_command(
                InstanceCommand(
                    command_type=InstanceCommandType.REFRESH,
                    instance_id=state.instance_id,
                )
            )

        self._event_bus.publish(
            "operator.refresh.completed",
            {
                "message": f"Runtime refresh completed for {len(discovered_states)} instance(s).",
                "status": "completed",
                "instance_count": len(discovered_states),
            },
        )
        return self.snapshot()

    def snapshot(self) -> ConsoleSnapshot:
        return build_console_snapshot_from_runtime(
            self._coordinator.registry.list_instances(),
            adb_path=self._adb_path,
            packages=self._packages,
            runtime_contexts=self.runtime_contexts(),
        )

    def runtime_contexts(self) -> dict[str, InstanceRuntimeContext | None]:
        return {
            instance.instance_id: self._coordinator.get_runtime_context(instance.instance_id)
            for instance in self._coordinator.registry.list_instances()
        }

    def get_runtime_context(self, instance_id: str) -> InstanceRuntimeContext | None:
        return self._coordinator.get_runtime_context(instance_id)

    def queue_items(self, instance_id: str | None = None) -> list[QueuedTask]:
        return self._coordinator.queue.list_items(instance_id=instance_id)

    def events(self) -> list[AppEvent]:
        return list(self._events)

    def global_emergency_stop_active(self) -> bool:
        contexts = [context for context in self.runtime_contexts().values() if context is not None]
        return bool(contexts) and all(context.stop_requested for context in contexts)

    def dispatch_manual_action(
        self,
        action_key: str,
        *,
        instance_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> CommandDispatchResult:
        command = build_manual_control_command(
            action_key,
            instance_id=instance_id,
            payload=payload,
        )
        result = self._coordinator.dispatch_command(command)
        self._event_bus.publish(
            "operator.command.dispatched",
            {
                "command_id": command.command_id,
                "command_type": command.command_type.value,
                "instance_id": instance_id,
                "instance_ids": list(result.instance_ids),
                "status": result.status.value,
                "message": result.message,
            },
        )
        if command.command_type == InstanceCommandType.START_QUEUE:
            self._event_bus.publish(
                "command.executed",
                {
                    "command_id": command.command_id,
                    "command_type": command.command_type.value,
                    "instance_id": instance_id,
                    "route_kind": "control",
                    "status": result.status.value,
                    "message": result.message,
                },
            )
        return result

    def _subscribe_events(self) -> None:
        for event_name in _CAPTURED_EVENT_NAMES:
            self._event_bus.subscribe(event_name, self._record_event)

    def _record_event(self, event: AppEvent) -> None:
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

    def _coerce_instance_state(self, raw: object) -> InstanceState:
        if isinstance(raw, InstanceState):
            return raw
        if not isinstance(raw, dict):
            raise TypeError(f"Unsupported instance payload: {type(raw)!r}")
        status_value = raw.get("status", InstanceStatus.READY)
        try:
            status = status_value if isinstance(status_value, InstanceStatus) else InstanceStatus(str(status_value))
        except ValueError:
            status = InstanceStatus.READY
        return InstanceState(
            instance_id=str(raw.get("instance_id", "")),
            label=str(raw.get("label", "")),
            adb_serial=str(raw.get("adb_serial", "")),
            status=status,
            last_seen_at=raw.get("last_seen_at") or utc_now(),
            metadata=dict(raw.get("metadata", {})),
        )

    def _ensure_profile_binding(self, state: InstanceState) -> None:
        context = self._coordinator.get_runtime_context(state.instance_id)
        if context is not None and context.profile_binding is not None:
            return
        self._coordinator.bind_profile(
            state.instance_id,
            ProfileBinding(
                profile_id=f"profile.{state.instance_id}",
                display_name=f"{state.label} Profile",
                server_name=str(state.metadata.get("server", "unassigned")),
                character_name=str(state.metadata.get("character_name", state.label)),
                allowed_tasks=[
                    f"sample.{state.instance_id}.preview",
                    f"sample.{state.instance_id}.audit",
                ],
                calibration_id=f"calibration.{state.instance_id}",
            ),
        )

    def _ensure_seed_queue(self, state: InstanceState) -> None:
        if state.instance_id in self._seeded_instances:
            return
        self._coordinator.enqueue(
            QueuedTask(
                instance_id=state.instance_id,
                spec=self._build_sample_spec(state, task_index=0),
                priority=100,
                metadata={"source": "app.runtime_bridge"},
            )
        )
        self._coordinator.enqueue(
            QueuedTask(
                instance_id=state.instance_id,
                spec=self._build_sample_spec(state, task_index=1),
                priority=90,
                metadata={"source": "app.runtime_bridge"},
            )
        )
        self._seeded_instances.add(state.instance_id)

    def _build_sample_spec(self, state: InstanceState, *, task_index: int) -> TaskSpec:
        task_id = f"sample.{state.instance_id}.{task_index}"
        task_name = "Preview Sync" if task_index == 0 else "Audit Sweep"
        manifest = TaskManifest(
            task_id=task_id,
            name=task_name,
            version="0.1.0",
            requires=["preview", "health_check"],
            recovery_policy="abort",
            stop_conditions=[
                StopCondition(
                    condition_id=f"{task_id}.manual_stop",
                    kind=StopConditionKind.MANUAL,
                    message="operator requested stop",
                )
            ],
            metadata={"source": "operator_console"},
        )
        return TaskSpec(
            task_id=task_id,
            name=task_name,
            version="0.1.0",
            entry_state="ready",
            manifest=manifest,
            steps=[
                TaskStep(
                    step_id="collect-runtime-context",
                    description="Expose runtime context to the operator console.",
                    handler=self._step_handler(task_name),
                )
            ],
            metadata={"source": "operator_console"},
        )

    def _step_handler(self, task_name: str) -> Callable[[TaskExecutionContext], object]:
        def handler(context: TaskExecutionContext) -> object:
            preview_frame = context.metadata.get("preview_frame")
            preview_path = getattr(preview_frame, "image_path", "n/a")
            profile_binding = context.metadata.get("profile_binding")
            profile_id = getattr(profile_binding, "profile_id", "unbound")
            return step_success(
                "collect-runtime-context",
                f"{task_name} completed for {context.instance.instance_id} "
                f"(profile={profile_id}, preview={preview_path})",
            )

        return handler
