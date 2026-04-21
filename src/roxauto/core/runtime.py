from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from roxauto.core.commands import (
    CommandDispatchResult,
    CommandDispatchStatus,
    InstanceCommand,
    InstanceCommandType,
)
from roxauto.core.events import (
    EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
    EVENT_TASK_FINISHED,
    EVENT_TASK_PROGRESS,
    EVENT_TASK_STARTED,
    EventBus,
)
from roxauto.core.instance_registry import InstanceRegistry
from roxauto.core.models import (
    FailureSnapshotMetadata,
    FailureSnapshotReason,
    InstanceState,
    InstanceRuntimeContext,
    InstanceStatus,
    PreviewFrame,
    ProfileBinding,
    StepStatus,
    StopCondition,
    StopConditionKind,
    TaskRun,
    TaskRunStatus,
    TaskRunTelemetry,
    TaskSpec,
    TaskStepTelemetry,
    TaskStepTelemetryStatus,
    TaskStepResult,
)
from roxauto.core.queue import QueuedTask, TaskQueue
from roxauto.core.serde import to_primitive
from roxauto.core.time import utc_now


class AuditSink(Protocol):
    def write(self, name: str, payload: dict[str, Any]) -> None:
        """Persist an audit payload."""


@dataclass(slots=True)
class TaskActionDispatchResult:
    command_id: str
    command_type: InstanceCommandType
    instance_id: str
    status: str
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskHealthCheckResult:
    instance_id: str
    healthy: bool
    message: str = ""
    checked_at: object = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskActionBridge(Protocol):
    instance_id: str
    task_id: str
    queue_id: str | None

    def dispatch(
        self,
        command: InstanceCommand,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        """Dispatch one task-scoped runtime command."""

    def tap(
        self,
        point: tuple[int, int],
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        """Tap one coordinate through the runtime command path."""

    def swipe(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        *,
        duration_ms: int = 250,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        """Swipe through the runtime command path."""

    def input_text(
        self,
        text: str,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        """Input text through the runtime command path."""

    def capture_preview(
        self,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PreviewFrame | None:
        """Capture one preview frame within the current task run."""

    def check_health(
        self,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskHealthCheckResult:
        """Run one task-scoped health check and sync runtime state."""


@dataclass(slots=True)
class TaskExecutionContext:
    instance: InstanceState
    action_bridge: TaskActionBridge | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def require_action_bridge(self) -> TaskActionBridge:
        if self.action_bridge is None:
            raise RuntimeError("task action bridge is unavailable")
        return self.action_bridge


class StepHandler(Protocol):
    def __call__(self, context: TaskExecutionContext) -> TaskStepResult:
        """Run a task step and return its result."""


class PreviewCaptureService(Protocol):
    def capture(
        self,
        instance: InstanceState,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        thumbnail_path: Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PreviewFrame:
        """Capture a preview frame for one runtime event."""


class HealthCheckService(Protocol):
    def check(self, instance: InstanceState, *, metadata: dict[str, Any] | None = None) -> Any:
        """Run one health check for an instance."""


class CommandExecutor(Protocol):
    def execute(self, instance: InstanceState, command: InstanceCommand) -> Any:
        """Dispatch one command through the execution layer."""


@dataclass(slots=True)
class TaskStep:
    step_id: str
    description: str
    handler: StepHandler


def step_success(
    step_id: str,
    message: str,
    screenshot_path: str | Path | None = None,
    data: dict[str, Any] | None = None,
) -> TaskStepResult:
    return TaskStepResult(
        step_id=step_id,
        status=StepStatus.SUCCEEDED,
        message=message,
        screenshot_path=str(screenshot_path) if screenshot_path else None,
        data=data or {},
    )


def step_failure(
    step_id: str,
    message: str,
    screenshot_path: str | Path | None = None,
    data: dict[str, Any] | None = None,
) -> TaskStepResult:
    return TaskStepResult(
        step_id=step_id,
        status=StepStatus.FAILED,
        message=message,
        screenshot_path=str(screenshot_path) if screenshot_path else None,
        data=data or {},
    )


@dataclass(slots=True)
class QueueRunResult:
    instance_id: str
    runs: list[TaskRun] = field(default_factory=list)
    remaining_queue_depth: int = 0
    stopped: bool = False
    message: str = ""
    started_at: object = field(default_factory=utc_now)
    finished_at: object | None = None


@dataclass(slots=True)
class RuntimeInspectionResult:
    instance_id: str
    status: InstanceStatus
    health_check_ok: bool | None
    health_check_message: str = ""
    preview_frame: PreviewFrame | None = None
    failure_snapshot: FailureSnapshotMetadata | None = None
    inspected_at: object = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _RuntimeTaskActionBridge:
    coordinator: RuntimeCoordinator
    instance: InstanceState
    runtime_context: InstanceRuntimeContext
    task_id: str
    queue_id: str | None
    task_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def instance_id(self) -> str:
        return self.instance.instance_id

    def __post_init__(self) -> None:
        self._sync_task_metadata()

    def dispatch(
        self,
        command: InstanceCommand,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        if command.instance_id and command.instance_id != self.instance.instance_id:
            raise ValueError(
                f"Task action bridge is bound to {self.instance.instance_id}, not {command.instance_id}"
            )
        bound_command = replace(command, instance_id=self.instance.instance_id)
        if self.coordinator._command_executor is None:
            result = TaskActionDispatchResult(
                command_id=bound_command.command_id,
                command_type=bound_command.command_type,
                instance_id=self.instance.instance_id,
                status=CommandDispatchStatus.REJECTED.value,
                message="command executor unavailable",
                payload=dict(bound_command.payload),
                metadata=self._result_metadata(step_id=step_id, metadata=metadata),
            )
        else:
            raw_result = self.coordinator._command_executor.execute(self.instance, bound_command)
            result = self._normalize_dispatch_result(
                bound_command,
                raw_result,
                step_id=step_id,
                metadata=metadata,
            )
        self.runtime_context.metadata["last_task_action_command_id"] = result.command_id
        self.runtime_context.metadata["last_task_action_type"] = result.command_type.value
        self.runtime_context.metadata["last_task_action_status"] = result.status
        self.runtime_context.metadata["last_task_action_message"] = result.message
        if step_id is not None:
            self.runtime_context.metadata["last_task_action_step_id"] = step_id
        self.task_metadata["last_task_action"] = result
        self._sync_task_metadata()
        return result

    def tap(
        self,
        point: tuple[int, int],
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        return self.dispatch(
            InstanceCommand(
                command_type=InstanceCommandType.TAP,
                instance_id=self.instance.instance_id,
                payload={"point": point},
            ),
            step_id=step_id,
            metadata=metadata,
        )

    def swipe(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        *,
        duration_ms: int = 250,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        return self.dispatch(
            InstanceCommand(
                command_type=InstanceCommandType.SWIPE,
                instance_id=self.instance.instance_id,
                payload={"start": start, "end": end, "duration_ms": duration_ms},
            ),
            step_id=step_id,
            metadata=metadata,
        )

    def input_text(
        self,
        text: str,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskActionDispatchResult:
        return self.dispatch(
            InstanceCommand(
                command_type=InstanceCommandType.INPUT_TEXT,
                instance_id=self.instance.instance_id,
                payload={"text": text},
            ),
            step_id=step_id,
            metadata=metadata,
        )

    def capture_preview(
        self,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PreviewFrame | None:
        preview_frame = self.coordinator._capture_preview_frame(
            self.instance,
            None,
            task_id=self.task_id,
            queue_id=self.queue_id,
            step_id=step_id,
            metadata=metadata,
        )
        self.coordinator._update_preview_context(
            self.runtime_context,
            preview_frame,
            task_id=self.task_id,
            queue_id=self.queue_id,
            step_id=step_id,
        )
        self.task_metadata["last_task_preview_frame"] = preview_frame
        self._sync_task_metadata()
        return preview_frame

    def check_health(
        self,
        *,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskHealthCheckResult:
        health_result = self.coordinator._check_instance_health(
            self.instance,
            None,
            task_id=self.task_id,
            queue_id=self.queue_id,
            step_id=step_id,
            metadata=metadata,
        )
        self.coordinator._update_health_context(
            self.runtime_context,
            health_result,
            task_id=self.task_id,
            queue_id=self.queue_id,
            step_id=step_id,
        )
        if health_result["healthy"]:
            self.coordinator._clear_runtime_health_failure_snapshot(self.runtime_context)
        else:
            self.coordinator._record_runtime_health_failure_snapshot(
                self.instance,
                self.runtime_context,
                message=str(health_result["message"] or "health check failed"),
            )
        next_status = self.coordinator._derive_inspection_status(
            self.instance,
            self.runtime_context,
            health_result["healthy"],
        )
        if self.instance.status != next_status:
            self.coordinator._registry.transition_status(self.instance.instance_id, next_status, force=True)
            self.instance = self.coordinator._require_instance(self.instance.instance_id)
        self.runtime_context.status = next_status
        result = TaskHealthCheckResult(
            instance_id=self.instance.instance_id,
            healthy=bool(health_result["healthy"]),
            message=str(health_result["message"]),
            checked_at=health_result["checked_at"],
            metadata=self._result_metadata(step_id=step_id, metadata=metadata),
        )
        self.task_metadata["last_task_health_check"] = result
        self._sync_task_metadata()
        return result

    def _normalize_dispatch_result(
        self,
        command: InstanceCommand,
        raw_result: Any,
        *,
        step_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> TaskActionDispatchResult:
        status = self.coordinator._normalize_result_status(raw_result) or "executed"
        if isinstance(raw_result, dict):
            message = str(raw_result.get("message", ""))
            payload = dict(raw_result.get("payload", {})) if isinstance(raw_result.get("payload"), dict) else {}
        else:
            message = str(getattr(raw_result, "message", ""))
            raw_payload = getattr(raw_result, "payload", None)
            payload = dict(raw_payload) if isinstance(raw_payload, dict) else {}
        if not payload:
            payload = dict(command.payload)
        return TaskActionDispatchResult(
            command_id=command.command_id,
            command_type=command.command_type,
            instance_id=self.instance.instance_id,
            status=status,
            message=message,
            payload=payload,
            metadata=self._result_metadata(step_id=step_id, metadata=metadata),
        )

    def _result_metadata(
        self,
        *,
        step_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        result_metadata = {
            "task_id": self.task_id,
            "queue_id": self.queue_id,
        }
        if step_id is not None:
            result_metadata["step_id"] = step_id
        if metadata:
            result_metadata.update(dict(metadata))
        return result_metadata

    def _sync_task_metadata(self) -> None:
        self.task_metadata["action_bridge"] = self
        self.task_metadata["task_id"] = self.task_id
        self.task_metadata["queue_id"] = self.queue_id
        self.task_metadata["profile_binding"] = self.runtime_context.profile_binding
        self.task_metadata["runtime_context"] = self.runtime_context
        self.task_metadata["active_task_run"] = self.runtime_context.active_task_run
        self.task_metadata["last_task_run"] = self.runtime_context.last_task_run
        self.task_metadata["health_check_ok"] = self.runtime_context.health_check_ok
        self.task_metadata["health_check_message"] = str(
            self.runtime_context.metadata.get("last_health_check_message", "")
        )
        self.task_metadata["preview_frame"] = self.runtime_context.preview_frame
        self.task_metadata["failure_snapshot"] = self.runtime_context.failure_snapshot
        self.task_metadata["last_failure_snapshot"] = self.runtime_context.last_failure_snapshot
        self.task_metadata["stop_requested"] = self.runtime_context.stop_requested


class TaskRunner:
    def __init__(self, event_bus: EventBus | None = None, audit_sink: AuditSink | None = None) -> None:
        self._event_bus = event_bus or EventBus()
        self._audit_sink = audit_sink

    def run_task(self, spec: TaskSpec, context: TaskExecutionContext) -> TaskRun:
        run = TaskRun(
            run_id=str(uuid4()),
            instance_id=context.instance.instance_id,
            task_id=spec.task_id,
            status=TaskRunStatus.RUNNING,
        )
        context.metadata["run_id"] = run.run_id
        context.metadata["task_id"] = run.task_id
        runtime_context = self._runtime_context(context)
        queue_id = str(context.metadata.get("queue_id") or "")
        attempt = self._next_attempt(runtime_context, run.task_id)
        if isinstance(runtime_context, InstanceRuntimeContext):
            runtime_context.active_run_id = run.run_id
        self._start_run_telemetry(
            spec=spec,
            run=run,
            context=context,
            queue_id=queue_id,
            attempt=attempt,
        )
        self._event_bus.publish(
            EVENT_TASK_STARTED,
            {
                "run_id": run.run_id,
                "task_id": run.task_id,
                "instance_id": run.instance_id,
                "queue_id": queue_id,
                "attempt": attempt,
                "step_count": len(spec.steps),
            },
        )
        self._write_audit(
            "task.started",
            {
                "run_id": run.run_id,
                "task_id": run.task_id,
                "instance_id": run.instance_id,
                "queue_id": queue_id,
                "attempt": attempt,
                "step_count": len(spec.steps),
            },
        )

        stop_condition = self._evaluate_stop_conditions(spec, context, run)
        if stop_condition is not None:
            run.status = TaskRunStatus.ABORTED
            run.stop_condition = stop_condition
            failure_reason = FailureSnapshotReason.STOP_CONDITION
            failure_message = stop_condition.message or f"Stop condition triggered: {stop_condition.kind.value}"
            if stop_condition.kind == StopConditionKind.HEALTH_CHECK_FAILED:
                failure_reason = FailureSnapshotReason.HEALTH_CHECK_FAILED
                failure_message = str(context.metadata.get("health_check_message") or failure_message)
            self._capture_failure_snapshot(
                run=run,
                reason=failure_reason,
                message=failure_message,
                step_id=None,
                context=context,
            )
            run.finished_at = utc_now()
            context.metadata["run_status"] = run.status.value
            self._finalize_run_telemetry(run=run, context=context)
            self._finish_run(run, context=context)
            return run

        for step_index, step in enumerate(spec.steps):
            self._mark_step_running(
                step=step,
                step_index=step_index,
                context=context,
            )
            try:
                result = step.handler(context)
                step_reason = None
            except Exception as exc:
                result = step_failure(step.step_id, f"Unhandled step exception: {exc}")
                step_reason = FailureSnapshotReason.STEP_EXCEPTION

            run.step_results.append(result)
            self._apply_step_result(
                step=step,
                step_index=step_index,
                result=result,
                context=context,
            )
            self._event_bus.publish(
                EVENT_TASK_PROGRESS,
                {
                    "run_id": run.run_id,
                    "task_id": run.task_id,
                    "instance_id": run.instance_id,
                    "queue_id": queue_id,
                    "attempt": attempt,
                    "step_id": result.step_id,
                    "step_index": step_index,
                    "step_count": len(spec.steps),
                    "status": result.status.value,
                    "message": result.message,
                    "screenshot_path": result.screenshot_path,
                },
            )
            self._write_audit(
                "task.step",
                {
                    "run_id": run.run_id,
                    "task_id": run.task_id,
                    "instance_id": run.instance_id,
                    "queue_id": queue_id,
                    "attempt": attempt,
                    "step_id": result.step_id,
                    "step_index": step_index,
                    "step_count": len(spec.steps),
                    "status": result.status.value,
                    "message": result.message,
                    "screenshot_path": result.screenshot_path,
                },
            )

            if result.status == StepStatus.FAILED:
                run.status = TaskRunStatus.FAILED
                self._capture_failure_snapshot(
                    run=run,
                    reason=step_reason or FailureSnapshotReason.STEP_FAILED,
                    message=result.message,
                    step_id=result.step_id,
                    context=context,
                    screenshot_path=result.screenshot_path,
                    step_result=result,
                )
                run.finished_at = utc_now()
                context.metadata["run_status"] = run.status.value
                self._finalize_run_telemetry(run=run, context=context)
                self._finish_run(run, context=context)
                return run

        run.status = TaskRunStatus.SUCCEEDED
        run.finished_at = utc_now()
        context.metadata["run_status"] = run.status.value
        self._finalize_run_telemetry(run=run, context=context)
        self._finish_run(run, context=context)
        return run

    def _runtime_context(self, context: TaskExecutionContext) -> InstanceRuntimeContext | None:
        runtime_context = context.metadata.get("runtime_context")
        if isinstance(runtime_context, InstanceRuntimeContext):
            return runtime_context
        return None

    def _next_attempt(self, runtime_context: InstanceRuntimeContext | None, task_id: str) -> int:
        if runtime_context is None:
            return 1
        attempts = runtime_context.metadata.get("task_attempts")
        if not isinstance(attempts, dict):
            attempts = {}
            runtime_context.metadata["task_attempts"] = attempts
        attempt = int(attempts.get(task_id, 0)) + 1
        attempts[task_id] = attempt
        return attempt

    def _start_run_telemetry(
        self,
        *,
        spec: TaskSpec,
        run: TaskRun,
        context: TaskExecutionContext,
        queue_id: str,
        attempt: int,
    ) -> None:
        runtime_context = self._runtime_context(context)
        preview_frame = context.metadata.get("preview_frame")
        telemetry = TaskRunTelemetry(
            task_id=run.task_id,
            run_id=run.run_id,
            status=TaskRunStatus.RUNNING,
            step_count=len(spec.steps),
            queue_id=queue_id,
            attempt=attempt,
            steps=[
                TaskStepTelemetry(
                    step_id=step.step_id,
                    description=step.description,
                )
                for step in spec.steps
            ],
            preview_frame=preview_frame if isinstance(preview_frame, PreviewFrame) else None,
            metadata={
                "entry_state": spec.entry_state,
                "task_name": spec.name,
                "queue_id": queue_id,
            },
        )
        context.metadata["task_attempt"] = attempt
        context.metadata["current_step_id"] = ""
        context.metadata["current_step_index"] = -1
        context.metadata["task_run_telemetry"] = telemetry
        if runtime_context is not None:
            runtime_context.active_task_run = telemetry

    def _mark_step_running(
        self,
        *,
        step: TaskStep,
        step_index: int,
        context: TaskExecutionContext,
    ) -> None:
        telemetry = self._active_run_telemetry(context)
        started_at = utc_now()
        context.metadata["current_step_id"] = step.step_id
        context.metadata["current_step_index"] = step_index
        if telemetry is None or step_index >= len(telemetry.steps):
            return
        step_telemetry = telemetry.steps[step_index]
        step_telemetry.status = TaskStepTelemetryStatus.RUNNING
        step_telemetry.message = ""
        step_telemetry.started_at = step_telemetry.started_at or started_at
        step_telemetry.finished_at = None
        telemetry.current_step_id = step.step_id
        telemetry.current_step_index = step_index
        telemetry.last_updated_at = started_at

    def _apply_step_result(
        self,
        *,
        step: TaskStep,
        step_index: int,
        result: TaskStepResult,
        context: TaskExecutionContext,
    ) -> None:
        telemetry = self._active_run_telemetry(context)
        finished_at = utc_now()
        if telemetry is None or step_index >= len(telemetry.steps):
            return
        step_telemetry = telemetry.steps[step_index]
        step_telemetry.status = self._telemetry_status_for_result(result)
        step_telemetry.message = result.message
        step_telemetry.screenshot_path = result.screenshot_path
        step_telemetry.finished_at = finished_at
        step_telemetry.started_at = step_telemetry.started_at or finished_at
        step_telemetry.data = dict(result.data)
        telemetry.completed_step_count = sum(
            1
            for item in telemetry.steps
            if item.status
            in {
                TaskStepTelemetryStatus.SUCCEEDED,
                TaskStepTelemetryStatus.FAILED,
                TaskStepTelemetryStatus.SKIPPED,
            }
        )
        telemetry.current_step_id = step.step_id if result.status == StepStatus.FAILED else ""
        telemetry.current_step_index = step_index if result.status == StepStatus.FAILED else -1
        preview_frame = context.metadata.get("preview_frame")
        telemetry.preview_frame = preview_frame if isinstance(preview_frame, PreviewFrame) else telemetry.preview_frame
        telemetry.last_updated_at = finished_at
        context.metadata["task_run_telemetry"] = telemetry

    def _telemetry_status_for_result(self, result: TaskStepResult) -> TaskStepTelemetryStatus:
        if result.status == StepStatus.SUCCEEDED:
            return TaskStepTelemetryStatus.SUCCEEDED
        if result.status == StepStatus.SKIPPED:
            return TaskStepTelemetryStatus.SKIPPED
        return TaskStepTelemetryStatus.FAILED

    def _active_run_telemetry(self, context: TaskExecutionContext) -> TaskRunTelemetry | None:
        runtime_context = self._runtime_context(context)
        if runtime_context is not None and runtime_context.active_task_run is not None:
            return runtime_context.active_task_run
        telemetry = context.metadata.get("task_run_telemetry")
        if isinstance(telemetry, TaskRunTelemetry):
            return telemetry
        return None

    def _finalize_run_telemetry(self, *, run: TaskRun, context: TaskExecutionContext) -> None:
        runtime_context = self._runtime_context(context)
        telemetry = self._active_run_telemetry(context)
        if telemetry is None:
            return
        finished_at = run.finished_at or utc_now()
        telemetry.status = run.status
        telemetry.finished_at = finished_at
        telemetry.current_step_id = ""
        telemetry.current_step_index = -1
        telemetry.completed_step_count = sum(
            1
            for item in telemetry.steps
            if item.status
            in {
                TaskStepTelemetryStatus.SUCCEEDED,
                TaskStepTelemetryStatus.FAILED,
                TaskStepTelemetryStatus.SKIPPED,
            }
        )
        telemetry.preview_frame = run.preview_frame or telemetry.preview_frame
        telemetry.failure_snapshot = run.failure_snapshot
        telemetry.stop_condition = run.stop_condition
        telemetry.last_updated_at = finished_at
        cloned = self._clone_run_telemetry(telemetry)
        context.metadata["task_run_telemetry"] = cloned
        context.metadata["last_task_run"] = cloned
        context.metadata["current_step_id"] = ""
        context.metadata["current_step_index"] = -1
        if runtime_context is not None:
            runtime_context.last_task_run = cloned
            runtime_context.active_task_run = None
            if run.failure_snapshot is not None:
                runtime_context.last_failure_snapshot = run.failure_snapshot
            context.metadata["last_failure_snapshot"] = runtime_context.last_failure_snapshot

    def _clone_run_telemetry(self, telemetry: TaskRunTelemetry) -> TaskRunTelemetry:
        return replace(
            telemetry,
            steps=[
                replace(step, data=dict(step.data))
                for step in telemetry.steps
            ],
            metadata=dict(telemetry.metadata),
        )

    def _collect_stop_conditions(self, spec: TaskSpec) -> list[StopCondition]:
        conditions: list[StopCondition] = []
        if spec.manifest is not None:
            conditions.extend(spec.manifest.stop_conditions)
        conditions.extend(spec.stop_conditions)
        unique: dict[str, StopCondition] = {}
        for condition in conditions:
            unique[condition.condition_id] = condition
        return list(unique.values())

    def _evaluate_stop_conditions(
        self,
        spec: TaskSpec,
        context: TaskExecutionContext,
        run: TaskRun,
    ) -> StopCondition | None:
        for condition in self._collect_stop_conditions(spec):
            if not condition.enabled:
                continue
            if condition.kind == StopConditionKind.MANUAL:
                if context.metadata.get("stop_requested"):
                    return condition
            elif condition.kind == StopConditionKind.TIMEOUT:
                if condition.timeout_ms is None:
                    continue
                elapsed_ms = (utc_now() - run.started_at).total_seconds() * 1000.0
                if elapsed_ms >= condition.timeout_ms:
                    return condition
            elif condition.kind == StopConditionKind.HEALTH_CHECK_FAILED:
                if context.metadata.get("health_check_ok") is False:
                    return condition
            elif condition.kind == StopConditionKind.VISION_MISMATCH:
                if context.metadata.get("vision_match_ok") is False:
                    return condition
        return None

    def _capture_failure_snapshot(
        self,
        run: TaskRun,
        reason: FailureSnapshotReason,
        message: str,
        step_id: str | None,
        context: TaskExecutionContext,
        screenshot_path: str | None = None,
        step_result: TaskStepResult | None = None,
    ) -> FailureSnapshotMetadata:
        preview_frame = self._resolve_preview_frame(context, run, screenshot_path)
        snapshot = FailureSnapshotMetadata(
            snapshot_id=str(uuid4()),
            instance_id=run.instance_id,
            task_id=run.task_id,
            run_id=run.run_id,
            reason=reason,
            screenshot_path=screenshot_path or (preview_frame.image_path if preview_frame else None),
            step_id=step_id,
            preview_frame=preview_frame,
            metadata=self._build_failure_snapshot_metadata(
                message=message,
                context=context,
                step_result=step_result,
            ),
        )
        run.preview_frame = preview_frame
        run.failure_snapshot = snapshot
        if preview_frame is not None:
            context.metadata["preview_frame"] = preview_frame
        context.metadata["failure_snapshot"] = snapshot
        telemetry = self._active_run_telemetry(context)
        if telemetry is not None:
            telemetry.preview_frame = preview_frame or telemetry.preview_frame
            telemetry.failure_snapshot = snapshot
            telemetry.last_updated_at = utc_now()
        payload = {
            "run_id": snapshot.run_id,
            "task_id": snapshot.task_id,
            "instance_id": snapshot.instance_id,
            "snapshot": snapshot,
        }
        self._event_bus.publish(
            EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
            {
                "run_id": snapshot.run_id,
                "task_id": snapshot.task_id,
                "instance_id": snapshot.instance_id,
                "snapshot_id": snapshot.snapshot_id,
                "reason": snapshot.reason.value,
            },
        )
        self._write_audit("task.failure_snapshot", payload)
        return snapshot

    def _build_failure_snapshot_metadata(
        self,
        *,
        message: str,
        context: TaskExecutionContext,
        step_result: TaskStepResult | None,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "message": message,
            "instance_label": context.instance.label,
        }
        metadata.update(self._project_step_failure_metadata(step_result))
        return metadata

    def _project_step_failure_metadata(
        self,
        step_result: TaskStepResult | None,
    ) -> dict[str, Any]:
        if step_result is None or not isinstance(step_result.data, dict) or not step_result.data:
            return {}
        step_data = to_primitive(step_result.data)
        if not isinstance(step_data, dict):
            return {}

        projected: dict[str, Any] = {
            "step_data": step_data,
        }
        step_outcome = step_data.get("step_outcome")
        if isinstance(step_outcome, dict) and step_outcome:
            projected["step_outcome"] = dict(step_outcome)
        task_action = step_data.get("task_action")
        if isinstance(task_action, dict) and task_action:
            projected["task_action"] = dict(task_action)
        inspection_attempts = step_data.get("inspection_attempts")
        if isinstance(inspection_attempts, list) and inspection_attempts:
            projected["inspection_attempts"] = list(inspection_attempts)
        telemetry = step_data.get("telemetry")
        if isinstance(telemetry, dict):
            inspection = telemetry.get("inspection")
            if isinstance(inspection, dict) and inspection:
                projected["inspection"] = dict(inspection)

        failure_reason_id = str(step_data.get("failure_reason_id", "")).strip()
        if not failure_reason_id and isinstance(step_outcome, dict):
            failure_reason_id = str(step_outcome.get("failure_reason_id", "")).strip()
        if failure_reason_id:
            projected["failure_reason_id"] = failure_reason_id

        outcome_code = str(step_data.get("outcome_code", "")).strip()
        if outcome_code:
            projected["outcome_code"] = outcome_code
        return projected

    def _resolve_preview_frame(
        self,
        context: TaskExecutionContext,
        run: TaskRun,
        screenshot_path: str | None,
    ) -> PreviewFrame | None:
        preview_frame = context.metadata.get("preview_frame")
        if isinstance(preview_frame, PreviewFrame):
            return preview_frame
        if screenshot_path is None:
            return None
        return PreviewFrame(
            frame_id=str(uuid4()),
            instance_id=run.instance_id,
            image_path=screenshot_path,
            source="task.failure_snapshot",
            metadata={"task_id": run.task_id, "run_id": run.run_id},
        )

    def _finish_run(self, run: TaskRun, *, context: TaskExecutionContext | None = None) -> None:
        runtime_context = self._runtime_context(context) if context is not None else None
        telemetry = runtime_context.last_task_run if runtime_context is not None else None
        self._event_bus.publish(
            EVENT_TASK_FINISHED,
            {
                "run_id": run.run_id,
                "task_id": run.task_id,
                "instance_id": run.instance_id,
                "status": run.status.value,
                "queue_id": telemetry.queue_id if telemetry is not None else "",
                "attempt": telemetry.attempt if telemetry is not None else None,
                "step_count": telemetry.step_count if telemetry is not None else len(run.step_results),
                "completed_step_count": (
                    telemetry.completed_step_count if telemetry is not None else len(run.step_results)
                ),
                "failure_snapshot_id": (
                    run.failure_snapshot.snapshot_id if run.failure_snapshot is not None else ""
                ),
            },
        )
        self._write_audit(
            "task.finished",
            {
                "run_id": run.run_id,
                "task_id": run.task_id,
                "instance_id": run.instance_id,
                "status": run.status.value,
                "stop_condition": run.stop_condition,
                "failure_snapshot": run.failure_snapshot,
                "telemetry": telemetry,
            },
        )

    def _write_audit(self, name: str, payload: dict[str, Any]) -> None:
        if self._audit_sink is not None:
            self._audit_sink.write(name, payload)


class RuntimeCoordinator:
    def __init__(
        self,
        *,
        registry: InstanceRegistry | None = None,
        queue: TaskQueue | None = None,
        task_runner: TaskRunner | None = None,
        command_executor: CommandExecutor | None = None,
        health_checker: HealthCheckService | None = None,
        preview_capture: PreviewCaptureService | None = None,
        event_bus: EventBus | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._event_bus = event_bus or EventBus()
        self._audit_sink = audit_sink
        self._registry = registry or InstanceRegistry(event_bus=self._event_bus)
        self._queue = queue or TaskQueue(event_bus=self._event_bus)
        self._task_runner = task_runner or TaskRunner(event_bus=self._event_bus, audit_sink=self._audit_sink)
        self._command_executor = command_executor
        self._health_checker = health_checker
        self._preview_capture = preview_capture
        self._contexts: dict[str, InstanceRuntimeContext] = {}

    @property
    def registry(self) -> InstanceRegistry:
        return self._registry

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def queue(self) -> TaskQueue:
        return self._queue

    def sync_instances(self, states: list[InstanceState]) -> list[InstanceState]:
        synced = self._registry.sync(states)
        for instance in self._registry.list_instances():
            self._sync_context_for_instance(instance)
        return synced

    def get_runtime_context(self, instance_id: str) -> InstanceRuntimeContext | None:
        context = self._contexts.get(instance_id)
        if context is None:
            return None
        instance = self._registry.get(instance_id)
        if instance is not None:
            context.status = instance.status
        context.queue_depth = self._queue.size(instance_id)
        return context

    def list_runtime_contexts(self) -> list[InstanceRuntimeContext]:
        return [
            self._sync_context_for_instance(instance)
            for instance in self._registry.list_instances()
        ]

    def inspect_instance(
        self,
        instance_id: str,
        *,
        run_health_check: bool = True,
        capture_preview: bool = True,
        command_id: str | None = None,
    ) -> RuntimeInspectionResult:
        instance = self._require_instance(instance_id)
        context = self._require_context(instance_id)
        return self._inspect_runtime_instance(
            instance,
            context,
            run_health_check=run_health_check,
            capture_preview=capture_preview,
            command_id=command_id,
        )

    def inspect_instances(
        self,
        instance_ids: list[str] | None = None,
        *,
        run_health_check: bool = True,
        capture_preview: bool = True,
        command_id: str | None = None,
    ) -> list[RuntimeInspectionResult]:
        if instance_ids is None:
            targets = self._registry.list_instances()
        else:
            targets = [self._require_instance(instance_id) for instance_id in instance_ids]
        return [
            self._inspect_runtime_instance(
                instance,
                self._require_context(instance.instance_id),
                run_health_check=run_health_check,
                capture_preview=capture_preview,
                command_id=command_id,
            )
            for instance in targets
        ]

    def bind_profile(self, instance_id: str, binding: ProfileBinding) -> InstanceRuntimeContext:
        context = self._require_context(instance_id)
        context.profile_binding = binding
        context.metadata["profile_id"] = binding.profile_id
        context.metadata["calibration_id"] = binding.calibration_id
        instance = self._require_instance(instance_id)
        instance.metadata["profile_id"] = binding.profile_id
        instance.metadata["calibration_id"] = binding.calibration_id
        self._write_audit(
            "runtime.profile_bound",
            {
                "instance_id": instance_id,
                "profile_binding": binding,
            },
        )
        return context

    def enqueue(self, item: QueuedTask) -> QueuedTask:
        queued = self._queue.enqueue(item)
        context = self._require_context(item.instance_id)
        context.queue_depth = self._queue.size(item.instance_id)
        return queued

    def dispatch_command(self, command: InstanceCommand) -> CommandDispatchResult:
        try:
            targets = self._resolve_targets(command)
        except (KeyError, ValueError) as exc:
            message = exc.args[0] if exc.args else str(exc)
            return CommandDispatchResult(
                command_id=command.command_id,
                command_type=command.command_type,
                status=CommandDispatchStatus.REJECTED,
                message=str(message),
            )
        if not targets:
            return CommandDispatchResult(
                command_id=command.command_id,
                command_type=command.command_type,
                status=CommandDispatchStatus.REJECTED,
                message="no target instances available",
            )

        results: list[Any] = []
        for instance in targets:
            if command.command_type == InstanceCommandType.REFRESH:
                results.append(self._refresh_instance(instance, command))
                continue
            if command.command_type == InstanceCommandType.START_QUEUE:
                results.append(self.start_queue(instance.instance_id))
                continue
            results.append(self._handle_control_or_interaction(instance, command))

        rejected_count = sum(
            1
            for result in results
            if self._normalize_result_status(result) == CommandDispatchStatus.REJECTED.value
        )
        if rejected_count == len(results):
            status = CommandDispatchStatus.REJECTED
        elif rejected_count:
            status = CommandDispatchStatus.PARTIAL
        else:
            status = CommandDispatchStatus.COMPLETED
        dispatch_result = CommandDispatchResult(
            command_id=command.command_id,
            command_type=command.command_type,
            instance_ids=[instance.instance_id for instance in targets],
            status=status,
            results=results,
            message=f"{command.command_type.value} dispatched to {len(targets)} instance(s)",
        )
        self._write_audit(
            "runtime.command_dispatched",
            {
                "command": command,
                "dispatch_result": dispatch_result,
            },
        )
        return dispatch_result

    def start_queue(self, instance_id: str) -> QueueRunResult:
        context = self._require_context(instance_id)
        instance = self._require_instance(instance_id)
        context.stop_requested = False
        context.queue_depth = self._queue.size(instance_id)
        result = QueueRunResult(instance_id=instance_id, remaining_queue_depth=context.queue_depth)
        if context.queue_depth == 0:
            self._clear_active_execution(context)
            self._registry.transition_status(instance_id, InstanceStatus.READY, force=True)
            context.status = InstanceStatus.READY
            result.message = "queue empty"
            result.finished_at = utc_now()
            return result

        self._registry.transition_status(
            instance_id,
            InstanceStatus.BUSY,
            metadata={"queue_started": True, "queue_retry": instance.status == InstanceStatus.ERROR},
            force=instance.status == InstanceStatus.ERROR,
        )
        while True:
            context.queue_depth = self._queue.size(instance_id)
            if context.stop_requested:
                result.stopped = True
                result.message = "queue paused by operator"
                break
            item = self._queue.dequeue(instance_id)
            if item is None:
                result.message = "queue drained"
                break
            context.queue_depth = self._queue.size(instance_id)
            run = self._run_task_item(instance, context, item)
            result.runs.append(run)
            context.metadata["last_run_id"] = run.run_id
            context.metadata["last_run_status"] = run.status.value
            self._clear_active_execution(context)
            context.queue_depth = self._queue.size(instance_id)
            if run.status != TaskRunStatus.SUCCEEDED:
                result.message = f"queue stopped after {run.status.value}"
                break

        result.remaining_queue_depth = self._queue.size(instance_id)
        result.finished_at = utc_now()
        self._finalize_queue_status(instance_id, context, result)
        self._write_audit(
            "runtime.queue_completed",
            {
                "instance_id": instance_id,
                "queue_run": result,
            },
        )
        return result

    def _run_task_item(self, instance: InstanceState, context: InstanceRuntimeContext, item: QueuedTask) -> TaskRun:
        self._prepare_task_attempt_context(context)
        context.active_task_id = item.task_id
        context.metadata["queue_id"] = item.queue_id
        health_result = self._check_instance_health(instance, item)
        self._update_health_context(
            context,
            health_result,
            queue_id=item.queue_id,
            task_id=item.task_id,
        )
        preview_frame = self._capture_preview_frame(instance, item)
        self._update_preview_context(
            context,
            preview_frame,
            queue_id=item.queue_id,
            task_id=item.task_id,
        )
        task_metadata = {
            "queue_id": item.queue_id,
            "profile_binding": context.profile_binding,
            "runtime_context": context,
            "health_check_ok": context.health_check_ok,
            "health_check_message": context.metadata.get("last_health_check_message", ""),
            "preview_frame": context.preview_frame,
            "failure_snapshot": context.failure_snapshot,
            "stop_requested": context.stop_requested,
        }
        action_bridge = _RuntimeTaskActionBridge(
            self,
            instance,
            context,
            task_id=item.task_id,
            queue_id=item.queue_id,
            task_metadata=task_metadata,
        )
        task_context = TaskExecutionContext(
            instance=instance,
            action_bridge=action_bridge,
            metadata=task_metadata,
        )
        run = self._task_runner.run_task(
            spec=self._with_runtime_stop_conditions(item.spec),
            context=task_context,
        )
        context.active_run_id = run.run_id
        if context.last_task_run is not None and context.last_task_run.preview_frame is not None:
            context.preview_frame = context.last_task_run.preview_frame
        else:
            context.preview_frame = run.preview_frame or context.preview_frame
        context.failure_snapshot = run.failure_snapshot
        if run.failure_snapshot is not None:
            context.last_failure_snapshot = run.failure_snapshot
        return run

    def _refresh_instance(self, instance: InstanceState, command: InstanceCommand) -> dict[str, Any]:
        inspection = self.inspect_instance(
            instance.instance_id,
            run_health_check=True,
            capture_preview=True,
            command_id=command.command_id,
        )
        context = self._require_context(instance.instance_id)
        next_status = InstanceStatus.READY if inspection.health_check_ok else InstanceStatus.ERROR
        self._registry.transition_status(
            instance.instance_id,
            next_status,
            metadata={"last_refresh_command_id": command.command_id},
            force=True,
        )
        context.status = next_status
        return {
            "instance_id": instance.instance_id,
            "healthy": inspection.health_check_ok,
            "preview_frame": inspection.preview_frame,
            "failure_snapshot": inspection.failure_snapshot,
        }

    def _inspect_runtime_instance(
        self,
        instance: InstanceState,
        context: InstanceRuntimeContext,
        *,
        run_health_check: bool,
        capture_preview: bool,
        command_id: str | None = None,
    ) -> RuntimeInspectionResult:
        if instance.status == InstanceStatus.DISCONNECTED:
            synced_context = self._sync_context_for_instance(instance)
            return RuntimeInspectionResult(
                instance_id=instance.instance_id,
                status=synced_context.status,
                health_check_ok=synced_context.health_check_ok,
                health_check_message=str(synced_context.metadata.get("last_health_check_message", "")),
                preview_frame=synced_context.preview_frame,
                failure_snapshot=synced_context.failure_snapshot,
                metadata={
                    "command_id": command_id,
                    "capture_preview": capture_preview,
                    "run_health_check": run_health_check,
                    "skipped": "disconnected",
                },
            )

        if run_health_check:
            health_result = self._check_instance_health(instance, None, command_id=command_id)
            self._update_health_context(
                context,
                health_result,
                command_id=command_id,
            )
        else:
            health_result = {
                "healthy": context.health_check_ok,
                "message": context.metadata.get("last_health_check_message", ""),
                "checked_at": context.metadata.get("last_health_check_at"),
            }

        if capture_preview:
            preview_frame = self._capture_preview_frame(instance, None, command_id=command_id)
            self._update_preview_context(
                context,
                preview_frame,
                command_id=command_id,
            )
        preview_frame = context.preview_frame
        if run_health_check:
            if health_result["healthy"]:
                self._clear_runtime_health_failure_snapshot(context)
            else:
                self._record_runtime_health_failure_snapshot(
                    instance,
                    context,
                    message=str(health_result["message"] or "health check failed"),
                    command_id=command_id,
                )

        next_status = self._derive_inspection_status(instance, context, health_result["healthy"])
        if instance.status != next_status:
            self._registry.transition_status(instance.instance_id, next_status, force=True)
            instance = self._require_instance(instance.instance_id)
        context.status = next_status
        return RuntimeInspectionResult(
            instance_id=instance.instance_id,
            status=next_status,
            health_check_ok=context.health_check_ok,
            health_check_message=str(context.metadata.get("last_health_check_message", "")),
            preview_frame=preview_frame,
            failure_snapshot=context.failure_snapshot,
            metadata={
                "command_id": command_id,
                "capture_preview": capture_preview,
                "run_health_check": run_health_check,
            },
        )

    def _derive_inspection_status(
        self,
        instance: InstanceState,
        context: InstanceRuntimeContext,
        health_check_ok: bool | None,
    ) -> InstanceStatus:
        if instance.status == InstanceStatus.DISCONNECTED:
            return InstanceStatus.DISCONNECTED
        if health_check_ok is False:
            return InstanceStatus.ERROR
        if instance.status == InstanceStatus.CONNECTING:
            return InstanceStatus.CONNECTING
        if context.stop_requested or instance.status == InstanceStatus.PAUSED:
            return InstanceStatus.PAUSED
        if context.active_task_id or context.active_run_id or instance.status == InstanceStatus.BUSY:
            return InstanceStatus.BUSY
        if health_check_ok is None and instance.status == InstanceStatus.ERROR:
            return InstanceStatus.ERROR
        return InstanceStatus.READY

    def _handle_control_or_interaction(self, instance: InstanceState, command: InstanceCommand) -> Any:
        context = self._require_context(instance.instance_id)
        if command.command_type in {
            InstanceCommandType.PAUSE,
            InstanceCommandType.STOP,
            InstanceCommandType.EMERGENCY_STOP,
        }:
            context.stop_requested = True
            self._registry.transition_status(instance.instance_id, InstanceStatus.PAUSED, force=True)
            context.status = InstanceStatus.PAUSED
        elif command.command_type == InstanceCommandType.START_QUEUE:
            context.stop_requested = False

        if self._command_executor is None:
            return {
                "instance_id": instance.instance_id,
                "status": "routed",
                "message": f"{command.command_type.value} handled without command executor",
            }
        return self._command_executor.execute(instance, command)

    def _check_instance_health(
        self,
        instance: InstanceState,
        item: QueuedTask | None,
        *,
        command_id: str | None = None,
        task_id: str | None = None,
        queue_id: str | None = None,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        effective_queue_id = item.queue_id if item is not None else queue_id
        effective_task_id = item.task_id if item is not None else task_id
        request_metadata = {
            "queue_id": effective_queue_id,
            "task_id": effective_task_id,
            "command_id": command_id,
        }
        if step_id is not None:
            request_metadata["step_id"] = step_id
        if metadata:
            request_metadata.update(dict(metadata))
        if self._health_checker is None:
            return {
                "healthy": True,
                "message": "health checker unavailable",
                "checked_at": utc_now(),
                "result": None,
                "metadata": request_metadata,
            }
        result = self._health_checker.check(
            instance,
            metadata=request_metadata,
        )
        return {
            "healthy": bool(getattr(result, "healthy", True)),
            "message": getattr(result, "message", ""),
            "checked_at": getattr(result, "checked_at", utc_now()),
            "result": result,
            "metadata": request_metadata,
        }

    def _capture_preview_frame(
        self,
        instance: InstanceState,
        item: QueuedTask | None,
        *,
        command_id: str | None = None,
        task_id: str | None = None,
        queue_id: str | None = None,
        step_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PreviewFrame | None:
        effective_queue_id = item.queue_id if item is not None else queue_id
        effective_task_id = item.task_id if item is not None else task_id
        capture_metadata = {
            "queue_id": effective_queue_id,
            "command_id": command_id,
        }
        if step_id is not None:
            capture_metadata["step_id"] = step_id
        if metadata:
            capture_metadata.update(dict(metadata))
        if self._preview_capture is None:
            return None
        try:
            return self._preview_capture.capture(
                instance,
                run_id=self._active_run_id_for_instance(instance.instance_id),
                task_id=effective_task_id,
                metadata=capture_metadata,
            )
        except Exception as exc:
            self._write_audit(
                "runtime.preview_capture_failed",
                {
                    "instance_id": instance.instance_id,
                    "task_id": effective_task_id,
                    "command_id": command_id,
                    "step_id": step_id,
                    "error": str(exc),
                },
            )
            return None

    def _active_run_id_for_instance(self, instance_id: str) -> str | None:
        context = self._contexts.get(instance_id)
        if context is None or context.active_run_id is None:
            return None
        return str(context.active_run_id)

    def _with_runtime_stop_conditions(self, spec: TaskSpec) -> TaskSpec:
        stop_conditions = list(spec.stop_conditions)
        kinds = {condition.kind for condition in stop_conditions}
        if StopConditionKind.MANUAL not in kinds:
            stop_conditions.append(
                StopCondition(
                    condition_id=f"{spec.task_id}.runtime.manual_stop",
                    kind=StopConditionKind.MANUAL,
                    message="operator requested stop",
                )
            )
        if StopConditionKind.HEALTH_CHECK_FAILED not in kinds:
            stop_conditions.append(
                StopCondition(
                    condition_id=f"{spec.task_id}.runtime.health_check",
                    kind=StopConditionKind.HEALTH_CHECK_FAILED,
                    message="instance health check failed",
                )
            )
        return replace(spec, stop_conditions=stop_conditions)

    def _finalize_queue_status(
        self,
        instance_id: str,
        context: InstanceRuntimeContext,
        result: QueueRunResult,
    ) -> None:
        self._clear_active_execution(context)
        if result.stopped or context.stop_requested:
            self._registry.transition_status(instance_id, InstanceStatus.PAUSED, force=True)
            context.status = InstanceStatus.PAUSED
            return
        last_run = result.runs[-1] if result.runs else None
        if last_run is None:
            self._registry.transition_status(instance_id, InstanceStatus.READY, force=True)
            context.status = InstanceStatus.READY
            return
        next_status = self._status_from_run(last_run)
        self._registry.transition_status(instance_id, next_status, force=True)
        context.status = next_status

    def _status_from_run(self, run: TaskRun) -> InstanceStatus:
        if run.status == TaskRunStatus.SUCCEEDED:
            return InstanceStatus.READY
        if run.status == TaskRunStatus.ABORTED and run.stop_condition is not None:
            if run.stop_condition.kind == StopConditionKind.MANUAL:
                return InstanceStatus.PAUSED
            if run.stop_condition.kind == StopConditionKind.HEALTH_CHECK_FAILED:
                return InstanceStatus.ERROR
        return InstanceStatus.ERROR

    def _resolve_targets(self, command: InstanceCommand) -> list[InstanceState]:
        if command.instance_id:
            return [self._require_instance(command.instance_id)]
        if command.command_type in {InstanceCommandType.REFRESH, InstanceCommandType.EMERGENCY_STOP}:
            return self._registry.list_instances()
        raise ValueError(f"{command.command_type.value} requires an instance_id")

    def _require_instance(self, instance_id: str) -> InstanceState:
        instance = self._registry.get(instance_id)
        if instance is None:
            raise KeyError(f"Unknown instance_id: {instance_id}")
        return instance

    def _require_context(self, instance_id: str) -> InstanceRuntimeContext:
        context = self._contexts.get(instance_id)
        if context is None:
            raise KeyError(f"Unknown runtime context for instance_id: {instance_id}")
        return context

    def _sync_context_for_instance(self, instance: InstanceState) -> InstanceRuntimeContext:
        context = self._contexts.get(instance.instance_id)
        metadata = {"label": instance.label, "adb_serial": instance.adb_serial}
        if context is None:
            context = InstanceRuntimeContext(
                instance_id=instance.instance_id,
                status=instance.status,
                queue_depth=self._queue.size(instance.instance_id),
                metadata=metadata,
            )
            self._contexts[instance.instance_id] = context
        else:
            context.status = instance.status
            context.queue_depth = self._queue.size(instance.instance_id)
            context.metadata.update(metadata)
        if instance.status == InstanceStatus.DISCONNECTED:
            self._clear_active_execution(context)
            context.health_check_ok = None
        return context

    def _prepare_task_attempt_context(self, context: InstanceRuntimeContext) -> None:
        if context.failure_snapshot is not None:
            context.last_failure_snapshot = context.failure_snapshot
        context.failure_snapshot = None
        context.active_task_run = None
        context.metadata.pop("current_step_id", None)
        context.metadata.pop("current_step_index", None)
        context.metadata.pop("task_run_telemetry", None)
        context.metadata.pop("failure_snapshot", None)

    def _update_health_context(
        self,
        context: InstanceRuntimeContext,
        result: dict[str, Any],
        *,
        task_id: str | None = None,
        queue_id: str | None = None,
        command_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        context.health_check_ok = result["healthy"]
        context.metadata["last_health_check_ok"] = result["healthy"]
        context.metadata["last_health_check_message"] = result["message"]
        context.metadata["last_health_check_at"] = result["checked_at"]
        if task_id is not None:
            context.metadata["last_health_check_task_id"] = task_id
        if queue_id is not None:
            context.metadata["last_health_check_queue_id"] = queue_id
        if command_id is not None:
            context.metadata["last_health_check_command_id"] = command_id
        if step_id is not None:
            context.metadata["last_health_check_step_id"] = step_id
        if context.active_task_run is not None:
            context.active_task_run.metadata["last_health_check_message"] = result["message"]
            context.active_task_run.metadata["last_health_check_ok"] = result["healthy"]
            context.active_task_run.last_updated_at = utc_now()

    def _update_preview_context(
        self,
        context: InstanceRuntimeContext,
        preview_frame: PreviewFrame | None,
        *,
        task_id: str | None = None,
        queue_id: str | None = None,
        command_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        if preview_frame is None:
            return
        context.preview_frame = preview_frame
        context.metadata["last_preview_frame_id"] = preview_frame.frame_id
        context.metadata["last_preview_image_path"] = preview_frame.image_path
        if task_id is not None:
            context.metadata["last_preview_task_id"] = task_id
        if queue_id is not None:
            context.metadata["last_preview_queue_id"] = queue_id
        if command_id is not None:
            context.metadata["last_preview_command_id"] = command_id
        if step_id is not None:
            context.metadata["last_preview_step_id"] = step_id
        if context.active_task_run is not None:
            context.active_task_run.preview_frame = preview_frame
            context.active_task_run.last_updated_at = utc_now()

    def _record_runtime_health_failure_snapshot(
        self,
        instance: InstanceState,
        context: InstanceRuntimeContext,
        *,
        message: str,
        command_id: str | None = None,
    ) -> FailureSnapshotMetadata:
        existing = context.failure_snapshot
        preview_image_path = context.preview_frame.image_path if context.preview_frame is not None else None
        if existing is not None and existing.task_id == "runtime.health_check":
            snapshot = existing
            changed = (
                snapshot.metadata.get("message") != message
                or (
                    command_id is not None
                    and snapshot.metadata.get("command_id") != command_id
                )
            )
            snapshot.run_id = command_id or snapshot.run_id
            snapshot.reason = FailureSnapshotReason.HEALTH_CHECK_FAILED
            snapshot.screenshot_path = preview_image_path
            snapshot.preview_frame = context.preview_frame
            snapshot.captured_at = utc_now()
            snapshot.metadata.update(
                {
                    "message": message,
                    "command_id": command_id,
                    "instance_label": instance.label,
                }
            )
        else:
            snapshot = FailureSnapshotMetadata(
                snapshot_id=str(uuid4()),
                instance_id=instance.instance_id,
                task_id="runtime.health_check",
                run_id=command_id or str(uuid4()),
                reason=FailureSnapshotReason.HEALTH_CHECK_FAILED,
                screenshot_path=preview_image_path,
                preview_frame=context.preview_frame,
                metadata={
                    "message": message,
                    "command_id": command_id,
                    "instance_label": instance.label,
                },
            )
            changed = True
        context.failure_snapshot = snapshot
        context.last_failure_snapshot = snapshot
        context.metadata["last_failure_snapshot_id"] = snapshot.snapshot_id
        context.metadata["last_failure_reason"] = snapshot.reason.value
        if context.active_task_run is not None:
            context.active_task_run.failure_snapshot = snapshot
            context.active_task_run.preview_frame = context.preview_frame
            context.active_task_run.last_updated_at = utc_now()
        if changed:
            self._event_bus.publish(
                EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
                {
                    "run_id": snapshot.run_id,
                    "task_id": snapshot.task_id,
                    "instance_id": snapshot.instance_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "reason": snapshot.reason.value,
                },
            )
            self._write_audit(
                "task.failure_snapshot",
                {
                    "run_id": snapshot.run_id,
                    "task_id": snapshot.task_id,
                    "instance_id": snapshot.instance_id,
                    "snapshot": snapshot,
                },
            )
        return snapshot

    def _clear_runtime_health_failure_snapshot(self, context: InstanceRuntimeContext) -> None:
        snapshot = context.failure_snapshot
        if snapshot is None or snapshot.task_id != "runtime.health_check":
            return
        context.failure_snapshot = None
        if context.active_task_run is not None and context.active_task_run.failure_snapshot is snapshot:
            context.active_task_run.failure_snapshot = None
            context.active_task_run.last_updated_at = utc_now()

    def _clear_active_execution(self, context: InstanceRuntimeContext) -> None:
        context.active_task_id = None
        context.active_run_id = None
        context.active_task_run = None
        context.metadata.pop("queue_id", None)
        context.metadata.pop("current_step_id", None)
        context.metadata.pop("current_step_index", None)

    def _normalize_result_status(self, result: Any) -> str | None:
        if isinstance(result, dict):
            status = result.get("status")
        else:
            status = getattr(result, "status", None)
        if status is None:
            return None
        return str(getattr(status, "value", status))

    def _write_audit(self, name: str, payload: dict[str, Any]) -> None:
        if self._audit_sink is None:
            return
        self._audit_sink.write(name, to_primitive(payload))
