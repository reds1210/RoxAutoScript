from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.models import (
    FailureSnapshotReason,
    InstanceState,
    InstanceStatus,
    StopCondition,
    StopConditionKind,
    TaskRunStatus,
    TaskSpec,
)
from roxauto.core.runtime import TaskExecutionContext, TaskRunner, TaskStep, step_failure, step_success


class RecordingAuditSink:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict[str, object]]] = []

    def write(self, name: str, payload: dict[str, object]) -> None:
        self.records.append((name, payload))


class TaskRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )
        self.context = TaskExecutionContext(instance=self.instance)

    def test_marks_success_when_all_steps_succeed(self) -> None:
        spec = TaskSpec(
            task_id="test.success",
            name="Test Success",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep("step-a", "First step", lambda ctx: step_success("step-a", "ok")),
                TaskStep("step-b", "Second step", lambda ctx: step_success("step-b", "ok")),
            ],
        )

        run = TaskRunner().run_task(spec=spec, context=self.context)

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(len(run.step_results), 2)

    def test_stops_after_failure_and_records_snapshot(self) -> None:
        sink = RecordingAuditSink()
        spec = TaskSpec(
            task_id="test.failure",
            name="Test Failure",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep("step-a", "First step", lambda ctx: step_failure("step-a", "bad")),
                TaskStep("step-b", "Second step", lambda ctx: step_success("step-b", "ok")),
            ],
        )

        run = TaskRunner(audit_sink=sink).run_task(spec=spec, context=self.context)

        self.assertEqual(run.status, TaskRunStatus.FAILED)
        self.assertEqual(len(run.step_results), 1)
        self.assertIsNotNone(run.failure_snapshot)
        self.assertEqual(run.failure_snapshot.reason, FailureSnapshotReason.STEP_FAILED)
        self.assertEqual(run.failure_snapshot.task_id, "test.failure")
        self.assertTrue(any(name == "task.failure_snapshot" for name, _ in sink.records))

    def test_manual_stop_condition_aborts_before_first_step(self) -> None:
        sink = RecordingAuditSink()
        spec = TaskSpec(
            task_id="test.stop",
            name="Test Stop",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep("step-a", "First step", lambda ctx: step_success("step-a", "should not run")),
            ],
            stop_conditions=[
                StopCondition(
                    condition_id="stop.manual",
                    kind=StopConditionKind.MANUAL,
                    message="operator requested stop",
                )
            ],
        )
        context = TaskExecutionContext(instance=self.instance, metadata={"stop_requested": True})

        run = TaskRunner(audit_sink=sink).run_task(spec=spec, context=context)

        self.assertEqual(run.status, TaskRunStatus.ABORTED)
        self.assertEqual(run.stop_condition.condition_id, "stop.manual")
        self.assertEqual(len(run.step_results), 0)
        self.assertIsNotNone(run.failure_snapshot)
        self.assertEqual(run.failure_snapshot.reason, FailureSnapshotReason.STOP_CONDITION)
        self.assertTrue(any(name == "task.failure_snapshot" for name, _ in sink.records))
