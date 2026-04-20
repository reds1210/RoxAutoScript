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
    TaskSpec,
    TaskStepResult,
)
from roxauto.core.queue import QueuedTask, TaskQueue
from roxauto.core.serde import to_primitive
from roxauto.core.time import utc_now


class AuditSink(Protocol):
    def write(self, name: str, payload: dict[str, Any]) -> None:
        """Persist an audit payload."""


@dataclass(slots=True)
class TaskExecutionContext:
    instance: InstanceState
    metadata: dict[str, Any] = field(default_factory=dict)


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
        self._event_bus.publish(
            EVENT_TASK_STARTED,
            {
                "run_id": run.run_id,
                "task_id": run.task_id,
                "instance_id": run.instance_id,
            },
        )
        self._write_audit(
            "task.started",
            {"run_id": run.run_id, "task_id": run.task_id, "instance_id": run.instance_id},
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
            self._finish_run(run)
            return run

        for step in spec.steps:
            try:
                result = step.handler(context)
                step_reason = None
            except Exception as exc:
                result = step_failure(step.step_id, f"Unhandled step exception: {exc}")
                step_reason = FailureSnapshotReason.STEP_EXCEPTION

            run.step_results.append(result)
            self._event_bus.publish(
                EVENT_TASK_PROGRESS,
                {
                    "run_id": run.run_id,
                    "step_id": result.step_id,
                    "status": result.status.value,
                    "message": result.message,
                },
            )
            self._write_audit(
                "task.step",
                {
                    "run_id": run.run_id,
                    "step_id": result.step_id,
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
                )
                run.finished_at = utc_now()
                self._finish_run(run)
                return run

        run.status = TaskRunStatus.SUCCEEDED
        run.finished_at = utc_now()
        self._finish_run(run)
        return run

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
            metadata={
                "message": message,
                "instance_label": context.instance.label,
            },
        )
        run.preview_frame = preview_frame
        run.failure_snapshot = snapshot
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

    def _finish_run(self, run: TaskRun) -> None:
        self._event_bus.publish(
            EVENT_TASK_FINISHED,
            {
                "run_id": run.run_id,
                "task_id": run.task_id,
                "instance_id": run.instance_id,
                "status": run.status.value,
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

        self._registry.transition_status(instance_id, InstanceStatus.BUSY, metadata={"queue_started": True})
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
        task_context = TaskExecutionContext(
            instance=instance,
            metadata={
                "queue_id": item.queue_id,
                "profile_binding": context.profile_binding,
                "runtime_context": context,
                "health_check_ok": context.health_check_ok,
                "health_check_message": context.metadata.get("last_health_check_message", ""),
                "preview_frame": context.preview_frame,
                "stop_requested": context.stop_requested,
            },
        )
        run = self._task_runner.run_task(
            spec=self._with_runtime_stop_conditions(item.spec),
            context=task_context,
        )
        context.active_run_id = run.run_id
        context.preview_frame = run.preview_frame or context.preview_frame
        context.failure_snapshot = run.failure_snapshot
        return run

    def _refresh_instance(self, instance: InstanceState, command: InstanceCommand) -> dict[str, Any]:
        context = self._require_context(instance.instance_id)
        health_result = self._check_instance_health(instance, None, command_id=command.command_id)
        self._update_health_context(
            context,
            health_result,
            command_id=command.command_id,
        )
        preview_frame = self._capture_preview_frame(instance, None, command_id=command.command_id)
        self._update_preview_context(
            context,
            preview_frame,
            command_id=command.command_id,
        )
        next_status = InstanceStatus.READY if health_result["healthy"] else InstanceStatus.ERROR
        self._registry.transition_status(
            instance.instance_id,
            next_status,
            metadata={"last_refresh_command_id": command.command_id},
            force=True,
        )
        context.status = next_status
        if health_result["healthy"]:
            self._clear_runtime_health_failure_snapshot(context)
        else:
            self._record_runtime_health_failure_snapshot(
                instance,
                context,
                message=health_result["message"] or "health check failed",
                command_id=command.command_id,
            )
        return {
            "instance_id": instance.instance_id,
            "healthy": health_result["healthy"],
            "preview_frame": preview_frame,
        }

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
    ) -> dict[str, Any]:
        if self._health_checker is None:
            return {"healthy": True, "message": "health checker unavailable"}
        result = self._health_checker.check(
            instance,
            metadata={
                "queue_id": item.queue_id if item is not None else None,
                "task_id": item.task_id if item is not None else None,
                "command_id": command_id,
            },
        )
        return {
            "healthy": bool(getattr(result, "healthy", True)),
            "message": getattr(result, "message", ""),
            "checked_at": getattr(result, "checked_at", utc_now()),
            "result": result,
        }

    def _capture_preview_frame(
        self,
        instance: InstanceState,
        item: QueuedTask | None,
        *,
        command_id: str | None = None,
    ) -> PreviewFrame | None:
        if self._preview_capture is None:
            return None
        try:
            return self._preview_capture.capture(
                instance,
                task_id=item.task_id if item is not None else None,
                metadata={
                    "queue_id": item.queue_id if item is not None else None,
                    "command_id": command_id,
                },
            )
        except Exception as exc:
            self._write_audit(
                "runtime.preview_capture_failed",
                {
                    "instance_id": instance.instance_id,
                    "task_id": item.task_id if item is not None else None,
                    "command_id": command_id,
                    "error": str(exc),
                },
            )
            return None

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

    def _update_health_context(
        self,
        context: InstanceRuntimeContext,
        result: dict[str, Any],
        *,
        task_id: str | None = None,
        queue_id: str | None = None,
        command_id: str | None = None,
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

    def _update_preview_context(
        self,
        context: InstanceRuntimeContext,
        preview_frame: PreviewFrame | None,
        *,
        task_id: str | None = None,
        queue_id: str | None = None,
        command_id: str | None = None,
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

    def _record_runtime_health_failure_snapshot(
        self,
        instance: InstanceState,
        context: InstanceRuntimeContext,
        *,
        message: str,
        command_id: str | None = None,
    ) -> FailureSnapshotMetadata:
        snapshot = FailureSnapshotMetadata(
            snapshot_id=str(uuid4()),
            instance_id=instance.instance_id,
            task_id="runtime.health_check",
            run_id=command_id or str(uuid4()),
            reason=FailureSnapshotReason.HEALTH_CHECK_FAILED,
            screenshot_path=context.preview_frame.image_path if context.preview_frame is not None else None,
            preview_frame=context.preview_frame,
            metadata={
                "message": message,
                "command_id": command_id,
                "instance_label": instance.label,
            },
        )
        context.failure_snapshot = snapshot
        context.metadata["last_failure_snapshot_id"] = snapshot.snapshot_id
        context.metadata["last_failure_reason"] = snapshot.reason.value
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

    def _clear_active_execution(self, context: InstanceRuntimeContext) -> None:
        context.active_task_id = None
        context.active_run_id = None
        context.metadata.pop("queue_id", None)

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
