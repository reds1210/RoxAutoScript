from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import CommandDispatchStatus, InstanceCommand, InstanceCommandType
from roxauto.core.models import (
    FailureSnapshotReason,
    InstanceState,
    InstanceStatus,
    ProfileBinding,
    StopCondition,
    StopConditionKind,
    TaskRunStatus,
    TaskSpec,
)
from roxauto.core.queue import QueuedTask, TaskQueue
from roxauto.core.runtime import (
    RuntimeCoordinator,
    TaskExecutionContext,
    TaskRunner,
    TaskStep,
    step_failure,
    step_success,
)


class RecordingAuditSink:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict[str, object]]] = []

    def write(self, name: str, payload: dict[str, object]) -> None:
        self.records.append((name, payload))


class FakeCommandExecutor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, str]] = []

    def execute(self, instance: InstanceState, command: InstanceCommand) -> dict[str, str]:
        self.executed.append((instance.instance_id, command.command_type.value))
        return {
            "instance_id": instance.instance_id,
            "status": "executed",
            "command_type": command.command_type.value,
        }


class FakeHealthChecker:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy
        self.calls = 0

    def check(self, instance: InstanceState, *, metadata: dict[str, object] | None = None) -> object:
        self.calls += 1
        return type(
            "HealthResult",
            (),
            {
                "instance_id": instance.instance_id,
                "healthy": self.healthy,
                "message": "healthy" if self.healthy else "health check failed",
                "metadata": metadata or {},
            },
        )()


class FakePreviewCapture:
    def __init__(self) -> None:
        self.calls = 0

    def capture(
        self,
        instance: InstanceState,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        thumbnail_path: object | None = None,
        metadata: dict[str, object] | None = None,
    ) -> object:
        from roxauto.core.models import PreviewFrame

        self.calls += 1
        return PreviewFrame(
            frame_id=f"frame-{self.calls}",
            instance_id=instance.instance_id,
            image_path=f"captures/{instance.instance_id}.png",
            metadata={"task_id": task_id, **(metadata or {})},
        )


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


class RuntimeCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )

    def _success_spec(self) -> TaskSpec:
        return TaskSpec(
            task_id="task.success",
            name="Success Task",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep(
                    "step-a",
                    "Uses runtime metadata",
                    lambda ctx: step_success("step-a", ctx.metadata["profile_binding"].profile_id),
                )
            ],
        )

    def test_start_queue_binds_profile_and_records_preview(self) -> None:
        sink = RecordingAuditSink()
        queue = TaskQueue()
        coordinator = RuntimeCoordinator(
            queue=queue,
            task_runner=TaskRunner(audit_sink=sink),
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
            audit_sink=sink,
        )
        coordinator.sync_instances([self.instance])
        coordinator.bind_profile(
            "mumu-0",
            ProfileBinding(
                profile_id="main-account",
                display_name="Main Account",
                server_name="TW-1",
                character_name="Knight",
                allowed_tasks=["task.success"],
                calibration_id="calib-main",
            ),
        )
        coordinator.enqueue(QueuedTask(instance_id="mumu-0", spec=self._success_spec(), priority=100))

        result = coordinator.start_queue("mumu-0")
        context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(len(result.runs), 1)
        self.assertEqual(result.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertIsNotNone(context)
        self.assertEqual(context.profile_binding.profile_id, "main-account")
        self.assertIsNotNone(context.preview_frame)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.READY)
        self.assertTrue(any(name == "runtime.profile_bound" for name, _ in sink.records))
        self.assertTrue(any(name == "runtime.queue_completed" for name, _ in sink.records))

    def test_dispatch_refresh_updates_runtime_context(self) -> None:
        coordinator = RuntimeCoordinator(
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])

        dispatch = coordinator.dispatch_command(InstanceCommand(command_type=InstanceCommandType.REFRESH))
        context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(dispatch.status, CommandDispatchStatus.COMPLETED)
        self.assertEqual(dispatch.instance_ids, ["mumu-0"])
        self.assertTrue(context.health_check_ok)
        self.assertIsNotNone(context.preview_frame)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.READY)

    def test_dispatch_stop_and_emergency_stop_pause_instances(self) -> None:
        second = InstanceState(
            instance_id="mumu-1",
            label="MuMu 1",
            adb_serial="127.0.0.1:16448",
            status=InstanceStatus.READY,
        )
        executor = FakeCommandExecutor()
        coordinator = RuntimeCoordinator(
            task_runner=TaskRunner(),
            command_executor=executor,
        )
        coordinator.sync_instances([self.instance, second])

        coordinator.dispatch_command(
            InstanceCommand(
                command_type=InstanceCommandType.STOP,
                instance_id="mumu-0",
            )
        )
        coordinator.dispatch_command(InstanceCommand(command_type=InstanceCommandType.EMERGENCY_STOP))

        self.assertTrue(coordinator.get_runtime_context("mumu-0").stop_requested)
        self.assertTrue(coordinator.get_runtime_context("mumu-1").stop_requested)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.PAUSED)
        self.assertEqual(coordinator.registry.get("mumu-1").status, InstanceStatus.PAUSED)
        self.assertIn(("mumu-0", "stop"), executor.executed)
        self.assertIn(("mumu-1", "emergency_stop"), executor.executed)

    def test_start_queue_aborts_when_health_check_fails(self) -> None:
        queue = TaskQueue()
        coordinator = RuntimeCoordinator(
            queue=queue,
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=False),
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])
        coordinator.enqueue(QueuedTask(instance_id="mumu-0", spec=self._success_spec(), priority=100))

        result = coordinator.start_queue("mumu-0")
        run = result.runs[0]
        context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(run.status, TaskRunStatus.ABORTED)
        self.assertIsNotNone(run.stop_condition)
        self.assertEqual(run.stop_condition.kind, StopConditionKind.HEALTH_CHECK_FAILED)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.ERROR)
        self.assertIsNotNone(context.failure_snapshot)
