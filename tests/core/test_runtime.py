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
from roxauto.emulator.execution import CommandExecutionStatus


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


class FakeSelectiveCommandExecutor:
    def __init__(self, rejected_instance_ids: set[str] | None = None) -> None:
        self.rejected_instance_ids = rejected_instance_ids or set()

    def execute(self, instance: InstanceState, command: InstanceCommand) -> object:
        status = (
            CommandExecutionStatus.REJECTED
            if instance.instance_id in self.rejected_instance_ids
            else CommandExecutionStatus.EXECUTED
        )
        return type(
            "CommandExecutionResult",
            (),
            {
                "instance_id": instance.instance_id,
                "command_type": command.command_type.value,
                "status": status,
                "message": status.value,
            },
        )()


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

    def test_start_queue_injects_task_action_bridge_for_task_steps(self) -> None:
        queue = TaskQueue()
        executor = FakeCommandExecutor()
        coordinator = RuntimeCoordinator(
            queue=queue,
            task_runner=TaskRunner(),
            command_executor=executor,
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])

        def handler(ctx: TaskExecutionContext):
            bridge = ctx.require_action_bridge()
            self.assertIs(ctx.metadata["action_bridge"], bridge)
            action = bridge.tap((12, 34), step_id="step-a", metadata={"source": "daily_ui.claim_rewards"})
            health = bridge.check_health(step_id="step-a", metadata={"source": "daily_ui.claim_rewards"})
            frame = bridge.capture_preview(step_id="step-a", metadata={"source": "daily_ui.claim_rewards"})
            self.assertEqual(ctx.metadata["preview_frame"].frame_id, frame.frame_id)
            return step_success(
                "step-a",
                action.message or action.status,
                screenshot_path=frame.image_path if frame is not None else None,
                data={
                    "action_status": action.status,
                    "health_ok": health.healthy,
                    "preview_frame_id": frame.frame_id if frame is not None else "",
                },
            )

        coordinator.enqueue(
            QueuedTask(
                instance_id="mumu-0",
                spec=TaskSpec(
                    task_id="daily_ui.claim_rewards",
                    name="Daily Reward Claim",
                    version="0.1.0",
                    entry_state="ready",
                    steps=[TaskStep("step-a", "Uses runtime action bridge", handler)],
                ),
                priority=100,
            )
        )

        result = coordinator.start_queue("mumu-0")
        context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(result.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(executor.executed, [("mumu-0", "tap")])
        self.assertEqual(result.runs[0].step_results[0].data["action_status"], "executed")
        self.assertTrue(result.runs[0].step_results[0].data["health_ok"])
        self.assertEqual(result.runs[0].step_results[0].screenshot_path, "captures/mumu-0.png")
        self.assertIsNotNone(context.preview_frame)
        self.assertEqual(context.metadata["last_task_action_type"], "tap")
        self.assertEqual(context.metadata["last_task_action_status"], "executed")
        self.assertEqual(context.metadata["last_health_check_step_id"], "step-a")
        self.assertEqual(context.metadata["last_preview_step_id"], "step-a")

    def test_start_queue_exposes_running_step_telemetry_inside_task_handler(self) -> None:
        coordinator = RuntimeCoordinator(
            queue=TaskQueue(),
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])

        def handler(ctx: TaskExecutionContext):
            runtime_context = ctx.metadata["runtime_context"]
            active_run = runtime_context.active_task_run
            self.assertIsNotNone(active_run)
            self.assertEqual(active_run.current_step_id, "step-a")
            self.assertEqual(active_run.current_step_index, 0)
            self.assertEqual(active_run.steps[0].status.value, "running")
            return step_success("step-a", "running telemetry is visible")

        coordinator.enqueue(
            QueuedTask(
                instance_id="mumu-0",
                spec=TaskSpec(
                    task_id="daily_ui.claim_rewards",
                    name="Daily Reward Claim",
                    version="0.1.0",
                    entry_state="ready",
                    steps=[TaskStep("step-a", "Runtime telemetry", handler)],
                ),
                priority=100,
            )
        )

        result = coordinator.start_queue("mumu-0")
        context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(result.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertIsNone(context.active_task_run)
        self.assertIsNotNone(context.last_task_run)
        self.assertEqual(context.last_task_run.steps[0].status.value, "succeeded")
        self.assertEqual(context.last_task_run.completed_step_count, 1)

    def test_start_queue_projects_runtime_owned_step_and_run_telemetry(self) -> None:
        coordinator = RuntimeCoordinator(
            queue=TaskQueue(),
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])
        coordinator.enqueue(
            QueuedTask(
                instance_id="mumu-0",
                spec=TaskSpec(
                    task_id="daily_ui.claim_rewards",
                    name="Daily Reward Claim",
                    version="0.1.0",
                    entry_state="ready",
                    steps=[
                        TaskStep("open_reward_panel", "Open reward panel", lambda ctx: step_success("open_reward_panel", "opened")),
                        TaskStep(
                            "verify_claim_affordance",
                            "Verify claim affordance",
                            lambda ctx: step_failure(
                                "verify_claim_affordance",
                                "claim affordance missing",
                                screenshot_path="captures/failure.png",
                                data={
                                    "failure_reason_id": "claim_state_ambiguous",
                                    "outcome_code": "claim_state_ambiguous",
                                    "inspection_attempts": [
                                        {
                                            "attempt": 1,
                                            "state": "unavailable",
                                            "screenshot_path": "captures/failure.png",
                                        }
                                    ],
                                    "step_outcome": {
                                        "kind": "verification_failed",
                                        "failure_reason_id": "claim_state_ambiguous",
                                    },
                                    "task_action": {
                                        "action": "inspect_reward_panel",
                                        "status": "skipped",
                                    },
                                    "telemetry": {
                                        "inspection": {
                                            "workflow_mode": "ambiguous",
                                            "expected_panel_states": ["claimable", "claimed"],
                                        }
                                    },
                                },
                            ),
                        ),
                    ],
                ),
                priority=100,
            )
        )

        result = coordinator.start_queue("mumu-0")
        context = coordinator.get_runtime_context("mumu-0")
        telemetry = context.last_task_run

        self.assertEqual(result.runs[0].status, TaskRunStatus.FAILED)
        self.assertIsNotNone(telemetry)
        self.assertEqual(telemetry.task_id, "daily_ui.claim_rewards")
        self.assertEqual(telemetry.status, TaskRunStatus.FAILED)
        self.assertEqual(telemetry.step_count, 2)
        self.assertEqual(telemetry.completed_step_count, 2)
        self.assertEqual([item.step_id for item in telemetry.steps], ["open_reward_panel", "verify_claim_affordance"])
        self.assertEqual([item.status.value for item in telemetry.steps], ["succeeded", "failed"])
        self.assertEqual(telemetry.steps[1].message, "claim affordance missing")
        self.assertEqual(telemetry.steps[1].screenshot_path, "captures/failure.png")
        self.assertEqual(telemetry.steps[1].data["failure_reason_id"], "claim_state_ambiguous")
        self.assertEqual(telemetry.steps[1].data["outcome_code"], "claim_state_ambiguous")
        self.assertIsNotNone(telemetry.preview_frame)
        self.assertIsNotNone(telemetry.failure_snapshot)
        self.assertEqual(telemetry.failure_snapshot.snapshot_id, result.runs[0].failure_snapshot.snapshot_id)
        self.assertEqual(
            telemetry.failure_snapshot.metadata["failure_reason_id"],
            "claim_state_ambiguous",
        )
        self.assertEqual(
            telemetry.failure_snapshot.metadata["outcome_code"],
            "claim_state_ambiguous",
        )
        self.assertEqual(
            telemetry.failure_snapshot.metadata["inspection_attempts"][0]["state"],
            "unavailable",
        )
        self.assertEqual(
            telemetry.failure_snapshot.metadata["step_outcome"]["kind"],
            "verification_failed",
        )
        self.assertEqual(
            telemetry.failure_snapshot.metadata["task_action"]["status"],
            "skipped",
        )
        self.assertEqual(
            telemetry.failure_snapshot.metadata["inspection"]["workflow_mode"],
            "ambiguous",
        )
        self.assertEqual(
            telemetry.failure_snapshot.metadata["step_data"]["failure_reason_id"],
            "claim_state_ambiguous",
        )
        self.assertEqual(context.failure_snapshot.snapshot_id, result.runs[0].failure_snapshot.snapshot_id)
        self.assertEqual(context.last_failure_snapshot.snapshot_id, result.runs[0].failure_snapshot.snapshot_id)

    def test_retry_keeps_last_failure_snapshot_stable_after_successful_rerun(self) -> None:
        coordinator = RuntimeCoordinator(
            queue=TaskQueue(),
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])

        failure_spec = TaskSpec(
            task_id="daily_ui.claim_rewards",
            name="Daily Reward Claim",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep("open_reward_panel", "Open reward panel", lambda ctx: step_success("open_reward_panel", "opened")),
                TaskStep("claim_reward", "Claim reward", lambda ctx: step_failure("claim_reward", "tap had no effect")),
            ],
        )
        success_spec = TaskSpec(
            task_id="daily_ui.claim_rewards",
            name="Daily Reward Claim",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep("open_reward_panel", "Open reward panel", lambda ctx: step_success("open_reward_panel", "opened")),
                TaskStep("claim_reward", "Claim reward", lambda ctx: step_success("claim_reward", "claimed")),
            ],
        )

        coordinator.enqueue(QueuedTask(instance_id="mumu-0", spec=failure_spec, priority=100))
        failed = coordinator.start_queue("mumu-0")
        failed_context = coordinator.get_runtime_context("mumu-0")
        first_failure_snapshot = failed_context.failure_snapshot

        coordinator.enqueue(QueuedTask(instance_id="mumu-0", spec=success_spec, priority=100))
        succeeded = coordinator.start_queue("mumu-0")
        recovered_context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(failed.runs[0].status, TaskRunStatus.FAILED)
        self.assertIsNotNone(first_failure_snapshot)
        self.assertEqual(succeeded.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertIsNone(recovered_context.failure_snapshot)
        self.assertIsNotNone(recovered_context.last_failure_snapshot)
        self.assertEqual(recovered_context.last_failure_snapshot.snapshot_id, first_failure_snapshot.snapshot_id)
        self.assertIsNotNone(recovered_context.last_task_run)
        self.assertEqual(recovered_context.last_task_run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(recovered_context.last_task_run.attempt, 2)
        self.assertEqual([item.status.value for item in recovered_context.last_task_run.steps], ["succeeded", "succeeded"])

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
        self.assertEqual(context.metadata["last_health_check_message"], "healthy")
        self.assertEqual(context.metadata["last_preview_command_id"], dispatch.command_id)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.READY)

    def test_inspect_instance_preserves_busy_status_for_active_runtime(self) -> None:
        coordinator = RuntimeCoordinator(
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])
        coordinator.registry.transition_status("mumu-0", InstanceStatus.BUSY, force=True)
        context = coordinator.get_runtime_context("mumu-0")
        context.active_task_id = "task.success"

        inspection = coordinator.inspect_instance("mumu-0")

        self.assertEqual(inspection.status, InstanceStatus.BUSY)
        self.assertTrue(inspection.health_check_ok)
        self.assertIsNotNone(inspection.preview_frame)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.BUSY)

    def test_inspect_instance_skips_device_calls_for_disconnected_instances(self) -> None:
        checker = FakeHealthChecker(healthy=True)
        preview_capture = FakePreviewCapture()
        coordinator = RuntimeCoordinator(
            task_runner=TaskRunner(),
            health_checker=checker,
            preview_capture=preview_capture,
        )
        coordinator.sync_instances([self.instance])
        coordinator.sync_instances([])

        inspection = coordinator.inspect_instance("mumu-0")

        self.assertEqual(inspection.status, InstanceStatus.DISCONNECTED)
        self.assertEqual(checker.calls, 0)
        self.assertEqual(preview_capture.calls, 0)
        self.assertEqual(inspection.metadata["skipped"], "disconnected")

    def test_inspect_instance_reuses_runtime_health_failure_snapshot_during_polling(self) -> None:
        sink = RecordingAuditSink()
        coordinator = RuntimeCoordinator(
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=False),
            preview_capture=FakePreviewCapture(),
            audit_sink=sink,
        )
        coordinator.sync_instances([self.instance])

        first = coordinator.inspect_instance("mumu-0")
        second = coordinator.inspect_instance("mumu-0")

        self.assertFalse(first.health_check_ok)
        self.assertFalse(second.health_check_ok)
        self.assertIsNotNone(first.failure_snapshot)
        self.assertIsNotNone(second.failure_snapshot)
        self.assertEqual(first.failure_snapshot.snapshot_id, second.failure_snapshot.snapshot_id)
        self.assertEqual(
            sum(1 for name, _ in sink.records if name == "task.failure_snapshot"),
            1,
        )
        self.assertEqual(second.failure_snapshot.preview_frame.frame_id, "frame-2")

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

    def test_dispatch_command_rejects_unknown_instance(self) -> None:
        coordinator = RuntimeCoordinator(task_runner=TaskRunner())
        coordinator.sync_instances([self.instance])

        dispatch = coordinator.dispatch_command(
            InstanceCommand(
                command_type=InstanceCommandType.STOP,
                instance_id="missing-instance",
            )
        )

        self.assertEqual(dispatch.status, CommandDispatchStatus.REJECTED)
        self.assertIn("Unknown instance_id", dispatch.message)

    def test_dispatch_command_marks_partial_when_one_target_is_rejected(self) -> None:
        second = InstanceState(
            instance_id="mumu-1",
            label="MuMu 1",
            adb_serial="127.0.0.1:16448",
            status=InstanceStatus.READY,
        )
        coordinator = RuntimeCoordinator(
            task_runner=TaskRunner(),
            command_executor=FakeSelectiveCommandExecutor(rejected_instance_ids={"mumu-1"}),
        )
        coordinator.sync_instances([self.instance, second])

        dispatch = coordinator.dispatch_command(InstanceCommand(command_type=InstanceCommandType.EMERGENCY_STOP))

        self.assertEqual(dispatch.status, CommandDispatchStatus.PARTIAL)
        self.assertEqual(dispatch.instance_ids, ["mumu-0", "mumu-1"])

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
        self.assertIsNotNone(run.failure_snapshot)
        self.assertEqual(run.failure_snapshot.reason, FailureSnapshotReason.HEALTH_CHECK_FAILED)
        self.assertEqual(run.failure_snapshot.metadata["message"], "health check failed")
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.ERROR)
        self.assertIsNotNone(context.failure_snapshot)
        self.assertEqual(context.metadata["last_health_check_message"], "health check failed")

    def test_start_queue_clears_active_execution_after_completion(self) -> None:
        coordinator = RuntimeCoordinator(
            queue=TaskQueue(),
            task_runner=TaskRunner(),
            health_checker=FakeHealthChecker(healthy=True),
            preview_capture=FakePreviewCapture(),
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
            ),
        )
        coordinator.enqueue(QueuedTask(instance_id="mumu-0", spec=self._success_spec(), priority=100))

        result = coordinator.start_queue("mumu-0")
        context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(result.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertIsNone(context.active_task_id)
        self.assertIsNone(context.active_run_id)
        self.assertNotIn("queue_id", context.metadata)
        self.assertEqual(context.metadata["last_run_id"], result.runs[0].run_id)
        self.assertEqual(context.metadata["last_run_status"], TaskRunStatus.SUCCEEDED.value)

    def test_sync_instances_marks_missing_runtime_contexts_disconnected(self) -> None:
        coordinator = RuntimeCoordinator(task_runner=TaskRunner())
        coordinator.sync_instances([self.instance])

        coordinator.sync_instances([])
        contexts = coordinator.list_runtime_contexts()

        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0].instance_id, "mumu-0")
        self.assertEqual(contexts[0].status, InstanceStatus.DISCONNECTED)

    def test_refresh_failure_records_runtime_health_snapshot_and_recovery_clears_it(self) -> None:
        checker = FakeHealthChecker(healthy=False)
        coordinator = RuntimeCoordinator(
            task_runner=TaskRunner(),
            health_checker=checker,
            preview_capture=FakePreviewCapture(),
        )
        coordinator.sync_instances([self.instance])

        failed_refresh = coordinator.dispatch_command(
            InstanceCommand(
                command_type=InstanceCommandType.REFRESH,
                instance_id="mumu-0",
            )
        )
        failed_context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(failed_refresh.status, CommandDispatchStatus.COMPLETED)
        self.assertFalse(failed_context.health_check_ok)
        self.assertIsNotNone(failed_context.preview_frame)
        self.assertIsNotNone(failed_context.failure_snapshot)
        self.assertEqual(failed_context.failure_snapshot.task_id, "runtime.health_check")
        self.assertEqual(failed_context.failure_snapshot.reason, FailureSnapshotReason.HEALTH_CHECK_FAILED)
        self.assertEqual(failed_context.metadata["last_health_check_command_id"], failed_refresh.command_id)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.ERROR)

        checker.healthy = True
        recovered_refresh = coordinator.dispatch_command(
            InstanceCommand(
                command_type=InstanceCommandType.REFRESH,
                instance_id="mumu-0",
            )
        )
        recovered_context = coordinator.get_runtime_context("mumu-0")

        self.assertEqual(recovered_refresh.status, CommandDispatchStatus.COMPLETED)
        self.assertTrue(recovered_context.health_check_ok)
        self.assertIsNone(recovered_context.failure_snapshot)
        self.assertEqual(coordinator.registry.get("mumu-0").status, InstanceStatus.READY)
