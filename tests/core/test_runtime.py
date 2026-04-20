from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.models import InstanceState, InstanceStatus, TaskRunStatus, TaskSpec
from roxauto.core.runtime import TaskExecutionContext, TaskRunner, TaskStep, step_failure, step_success


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

    def test_stops_after_failure(self) -> None:
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

        run = TaskRunner().run_task(spec=spec, context=self.context)

        self.assertEqual(run.status, TaskRunStatus.FAILED)
        self.assertEqual(len(run.step_results), 1)
