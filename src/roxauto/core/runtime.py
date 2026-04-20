from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from roxauto.core.events import EVENT_TASK_FINISHED, EVENT_TASK_PROGRESS, EVENT_TASK_STARTED, EventBus
from roxauto.core.models import (
    InstanceState,
    StepStatus,
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

        for step in spec.steps:
            try:
                result = step.handler(context)
            except Exception as exc:
                result = step_failure(step.step_id, f"Unhandled step exception: {exc}")

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
                run.finished_at = utc_now()
                self._finish_run(run)
                return run

        run.status = TaskRunStatus.SUCCEEDED
        run.finished_at = utc_now()
        self._finish_run(run)
        return run

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
            },
        )

    def _write_audit(self, name: str, payload: dict[str, Any]) -> None:
        if self._audit_sink is not None:
            self._audit_sink.write(name, payload)

