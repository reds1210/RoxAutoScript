from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from roxauto.core.events import (
    EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
    EVENT_TASK_FINISHED,
    EVENT_TASK_PROGRESS,
    EVENT_TASK_STARTED,
    EventBus,
)
from roxauto.core.models import (
    FailureSnapshotMetadata,
    FailureSnapshotReason,
    InstanceState,
    PreviewFrame,
    StepStatus,
    StopCondition,
    StopConditionKind,
    TaskRun,
    TaskRunStatus,
    TaskSpec,
    TaskStepResult,
)
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
            self._capture_failure_snapshot(
                run=run,
                reason=FailureSnapshotReason.STOP_CONDITION,
                message=stop_condition.message or f"Stop condition triggered: {stop_condition.kind.value}",
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
