from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import CommandDispatchStatus, InstanceCommand, InstanceCommandType
from roxauto.core.models import InstanceState, InstanceStatus, ProfileBinding, TaskRunStatus, TaskSpec
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import TaskStep, step_failure, step_success
from roxauto.emulator.adapter import AdbCommandError, AdbCommandResult, AdbEmulatorAdapter
from roxauto.emulator.live_runtime import LiveRuntimeSession, build_adb_live_runtime_session


class FakeAdapter:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy
        self.health_checks = 0
        self.screenshot_requests = 0
        self.taps: list[tuple[int, int]] = []
        self.swipes: list[tuple[tuple[int, int], tuple[int, int], int]] = []
        self.text_inputs: list[str] = []

    def capture_screenshot(self, instance: InstanceState) -> Path:
        self.screenshot_requests += 1
        return Path("captures") / f"{instance.instance_id}.png"

    def tap(self, instance: InstanceState, point: tuple[int, int]) -> None:
        self.taps.append(point)

    def swipe(
        self,
        instance: InstanceState,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        self.swipes.append((start, end, duration_ms))

    def input_text(self, instance: InstanceState, text: str) -> None:
        self.text_inputs.append(text)

    def launch_app(self, instance: InstanceState, package_name: str) -> None:
        return None

    def health_check(self, instance: InstanceState) -> bool:
        self.health_checks += 1
        return self.healthy


class BlockingAdapter(FakeAdapter):
    def __init__(self, healthy: bool = True) -> None:
        super().__init__(healthy=healthy)
        self.health_check_started = threading.Event()
        self.release_health_check = threading.Event()

    def health_check(self, instance: InstanceState) -> bool:
        self.health_check_started.set()
        if not self.release_health_check.wait(timeout=5.0):
            raise TimeoutError("background health check did not release")
        return super().health_check(instance)


class RecordingTransport:
    def __init__(self, responses: list[AdbCommandResult | Exception] | None = None) -> None:
        self._responses = list(responses or [])
        self.calls: list[dict[str, object]] = []

    def run(
        self,
        adb_serial: str,
        args,
        *,
        text: bool = True,
        timeout_sec: float | None = None,
        check: bool = True,
    ) -> AdbCommandResult:
        self.calls.append(
            {
                "adb_serial": adb_serial,
                "args": tuple(args),
                "text": text,
                "timeout_sec": timeout_sec,
                "check": check,
            }
        )
        if self._responses:
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return _result(adb_serial, tuple(args), stdout="" if text else b"")


class LiveRuntimeSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )

    def test_sync_instances_auto_binds_profile_and_runs_queue(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(
            adapter,
            discovery=lambda: [self.instance],
            profile_resolver=lambda instance: ProfileBinding(
                profile_id="main-account",
                display_name="Main Account",
                server_name="TW-1",
                character_name="Knight",
                allowed_tasks=["task.success"],
            )
            if instance.instance_id == "mumu-0"
            else None,
        )

        synced = session.sync_instances()
        session.enqueue(QueuedTask(instance_id="mumu-0", spec=self._success_spec(), priority=100))
        result = session.start_queue("mumu-0")
        context = session.get_runtime_context("mumu-0")
        snapshot = session.snapshot()

        self.assertEqual([instance.instance_id for instance in synced], ["mumu-0"])
        self.assertEqual(result.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(context.profile_binding.profile_id, "main-account")
        self.assertIsNotNone(context.preview_frame)
        self.assertIs(session.last_queue_result, result)
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(adapter.screenshot_requests, 1)
        self.assertEqual(snapshot.instances[0].instance_id, "mumu-0")
        self.assertEqual(snapshot.contexts[0].instance_id, "mumu-0")
        self.assertEqual(snapshot.instance_snapshots[0].instance_id, "mumu-0")
        self.assertEqual(snapshot.instance_snapshots[0].profile_binding.profile_id, "main-account")
        self.assertGreaterEqual(len(snapshot.recent_events), 3)

    def test_start_queue_task_step_uses_runtime_action_bridge_with_adapter(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()

        def handler(ctx):
            bridge = ctx.require_action_bridge()
            bridge.tap((40, 60), step_id="step-a", metadata={"source": "daily_ui.claim_rewards"})
            health = bridge.check_health(step_id="step-a", metadata={"source": "daily_ui.claim_rewards"})
            frame = bridge.capture_preview(step_id="step-a", metadata={"source": "daily_ui.claim_rewards"})
            return step_success(
                "step-a",
                "bridge ok",
                screenshot_path=frame.image_path if frame is not None else None,
                data={"health_ok": health.healthy},
            )

        session.enqueue(
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

        result = session.start_queue("mumu-0")
        context = session.get_runtime_context("mumu-0")

        self.assertEqual(result.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.taps, [(40, 60)])
        self.assertEqual(adapter.health_checks, 2)
        self.assertEqual(adapter.screenshot_requests, 2)
        self.assertTrue(result.runs[0].step_results[0].data["health_ok"])
        self.assertEqual(Path(result.runs[0].step_results[0].screenshot_path), Path("captures") / "mumu-0.png")
        self.assertEqual(context.metadata["last_task_action_type"], "tap")
        self.assertEqual(context.metadata["last_health_check_step_id"], "step-a")
        self.assertEqual(context.metadata["last_preview_step_id"], "step-a")

    def test_live_state_projects_runtime_owned_last_run_telemetry(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()
        session.enqueue(
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
                            "claim_reward",
                            "Claim reward",
                            lambda ctx: step_failure(
                                "claim_reward",
                                "tap had no effect",
                                data=_claim_rewards_failure_data(),
                            ),
                        ),
                    ],
                ),
                priority=100,
            )
        )

        result = session.start_queue("mumu-0")
        state = session.get_live_state(instance_id="mumu-0")

        self.assertEqual(result.runs[0].status, TaskRunStatus.FAILED)
        self.assertIsNotNone(state.selected_instance)
        self.assertEqual(state.selected_instance.last_task_id, "daily_ui.claim_rewards")
        self.assertEqual(state.selected_instance.last_run_status, "failed")
        self.assertEqual(state.selected_instance.last_step_count, 2)
        self.assertEqual(state.selected_instance.last_completed_step_count, 2)
        self.assertTrue(state.selected_instance.failure_snapshot_id)
        self.assertEqual(state.selected_instance.failure_step_id, "claim_reward")
        self.assertEqual(state.selected_instance.failure_reason_id, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.failure_outcome_code, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.failure_inspection_attempt_count, 2)
        self.assertEqual(state.selected_instance.last_step_id, "claim_reward")
        self.assertEqual(state.selected_instance.last_step_status, "failed")
        self.assertEqual(state.selected_instance.last_step_failure_reason_id, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.last_step_outcome_code, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.last_failure_snapshot_id, state.selected_instance.failure_snapshot_id)
        self.assertEqual(state.selected_instance.last_failure_reason, "step_failed")
        self.assertEqual(state.selected_instance.last_failure_step_id, "claim_reward")
        self.assertEqual(state.selected_instance.last_failure_reason_id, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.last_failure_outcome_code, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.last_failure_inspection_attempt_count, 2)
        self.assertEqual(state.selected_instance.last_failed_task_id, "daily_ui.claim_rewards")
        self.assertEqual(state.selected_instance.last_failed_run_status, "failed")
        self.assertEqual(state.selected_instance.last_failed_step_count, 2)
        self.assertEqual(state.selected_instance.last_failed_completed_step_count, 2)
        self.assertEqual(state.selected_instance.last_failed_step_id, "claim_reward")
        self.assertEqual(state.selected_instance.last_failed_step_status, "failed")
        self.assertEqual(
            state.selected_instance.last_failed_step_failure_reason_id,
            "claim_tap_no_effect",
        )
        self.assertEqual(state.selected_instance.last_failed_step_outcome_code, "claim_tap_no_effect")
        snapshot = session.get_instance_snapshot("mumu-0")
        self.assertIsNotNone(snapshot)
        self.assertIsNotNone(snapshot.last_failed_task_run)
        self.assertEqual(snapshot.last_failed_task_run.status.value, "failed")

    def test_live_state_preserves_last_failure_summary_after_successful_retry(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()

        failure_spec = TaskSpec(
            task_id="daily_ui.claim_rewards",
            name="Daily Reward Claim",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep("open_reward_panel", "Open reward panel", lambda ctx: step_success("open_reward_panel", "opened")),
                TaskStep(
                    "claim_reward",
                    "Claim reward",
                    lambda ctx: step_failure(
                        "claim_reward",
                        "tap had no effect",
                        data=_claim_rewards_failure_data(),
                    ),
                ),
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

        session.enqueue(QueuedTask(instance_id="mumu-0", spec=failure_spec, priority=100))
        session.start_queue("mumu-0")
        failed_state = session.get_live_state(instance_id="mumu-0")

        session.enqueue(QueuedTask(instance_id="mumu-0", spec=success_spec, priority=100))
        succeeded = session.start_queue("mumu-0")
        recovered_state = session.get_live_state(instance_id="mumu-0")

        self.assertIsNotNone(failed_state.selected_instance)
        self.assertTrue(failed_state.selected_instance.last_failure_snapshot_id)
        self.assertEqual(succeeded.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertIsNotNone(recovered_state.selected_instance)
        self.assertEqual(recovered_state.selected_instance.last_run_status, "succeeded")
        self.assertFalse(recovered_state.selected_instance.failure_snapshot_id)
        self.assertEqual(
            recovered_state.selected_instance.last_failure_snapshot_id,
            failed_state.selected_instance.last_failure_snapshot_id,
        )
        self.assertEqual(recovered_state.selected_instance.last_failure_reason, "step_failed")
        self.assertEqual(recovered_state.selected_instance.last_failure_reason_id, "claim_tap_no_effect")
        self.assertEqual(recovered_state.selected_instance.last_failure_outcome_code, "claim_tap_no_effect")
        self.assertEqual(recovered_state.selected_instance.last_failure_inspection_attempt_count, 2)
        self.assertEqual(recovered_state.selected_instance.last_failed_task_id, "daily_ui.claim_rewards")
        self.assertEqual(recovered_state.selected_instance.last_failed_run_status, "failed")
        self.assertEqual(recovered_state.selected_instance.last_failed_step_id, "claim_reward")
        self.assertEqual(
            recovered_state.selected_instance.last_failed_step_failure_reason_id,
            "claim_tap_no_effect",
        )
        snapshot = session.get_instance_snapshot("mumu-0")
        self.assertIsNotNone(snapshot)
        self.assertIsNotNone(snapshot.last_failed_task_run)
        self.assertEqual(snapshot.last_failed_task_run.steps[-1].step_id, "claim_reward")

    def test_reconnect_preserves_runtime_authority_for_last_run_and_failure_snapshot(self) -> None:
        adapter = FakeAdapter(healthy=True)
        discovered: dict[str, list[InstanceState]] = {"states": [self.instance]}
        session = LiveRuntimeSession(adapter, discovery=lambda: list(discovered["states"]))
        session.sync_instances()
        session.enqueue(
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
                            "claim_reward",
                            "Claim reward",
                            lambda ctx: step_failure(
                                "claim_reward",
                                "tap had no effect",
                                data=_claim_rewards_failure_data(),
                            ),
                        ),
                    ],
                ),
                priority=100,
            )
        )

        failed = session.start_queue("mumu-0")
        disconnected = session.disconnect_instance("mumu-0", reason="transport reset")
        reconnecting = session.reconnect_instance("mumu-0", rediscover=False)
        discovered["states"] = [
            InstanceState(
                instance_id="mumu-0",
                label="MuMu 0",
                adb_serial="127.0.0.1:16384",
                status=InstanceStatus.READY,
            )
        ]
        session.rediscover_instances()
        snapshot = session.get_instance_snapshot("mumu-0")
        state = session.get_live_state(instance_id="mumu-0")

        self.assertEqual(failed.runs[0].status, TaskRunStatus.FAILED)
        self.assertEqual(disconnected.status, "disconnected")
        self.assertEqual(reconnecting.status, "connecting")
        self.assertIsNotNone(snapshot)
        self.assertIsNotNone(snapshot.last_task_run)
        self.assertEqual(snapshot.last_task_run.status.value, "failed")
        self.assertEqual(snapshot.last_task_run.steps[-1].data["failure_reason_id"], "claim_tap_no_effect")
        self.assertIsNotNone(snapshot.last_failure_snapshot)
        self.assertEqual(snapshot.last_failure_snapshot.metadata["failure_reason_id"], "claim_tap_no_effect")
        self.assertIsNotNone(snapshot.last_failed_task_run)
        self.assertEqual(snapshot.last_failed_task_run.status.value, "failed")
        self.assertEqual(snapshot.last_failed_task_run.steps[-1].step_id, "claim_reward")
        self.assertIsNotNone(state.selected_instance)
        self.assertEqual(state.selected_instance.status, "ready")
        self.assertEqual(state.selected_instance.last_run_status, "failed")
        self.assertEqual(state.selected_instance.last_failure_reason_id, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.last_failure_outcome_code, "claim_tap_no_effect")
        self.assertEqual(state.selected_instance.last_failed_run_status, "failed")
        self.assertEqual(state.selected_instance.last_failed_step_id, "claim_reward")
        self.assertEqual(
            state.selected_instance.last_failed_step_failure_reason_id,
            "claim_tap_no_effect",
        )

    def test_build_registered_task_spec_uses_runtime_claim_rewards_context(self) -> None:
        adapter = FakeAdapter(healthy=True)
        observed: dict[str, object] = {}
        session = LiveRuntimeSession(
            adapter,
            discovery=lambda: [self.instance],
            profile_resolver=lambda instance: ProfileBinding(
                profile_id="claim-rewards-profile",
                display_name="Claim Rewards Profile",
                server_name="TW-1",
                character_name="Knight",
                allowed_tasks=["daily_ui.claim_rewards"],
            ),
        )
        session.sync_instances()
        session.refresh_runtime_contexts(instance_id="mumu-0", capture_preview=True)

        def factory(request):
            observed["task_id"] = request.task_id
            observed["profile_id"] = request.profile_binding.profile_id if request.profile_binding is not None else ""
            observed["health_check_ok"] = (
                request.runtime_context.health_check_ok if request.runtime_context is not None else None
            )
            observed["preview_image_path"] = (
                request.runtime_context.preview_frame.image_path
                if request.runtime_context is not None and request.runtime_context.preview_frame is not None
                else ""
            )
            observed["metadata"] = dict(request.metadata)
            self.assertIs(request.adapter, adapter)
            self.assertIs(request.execution_path.adapter, adapter)
            return TaskSpec(
                task_id=request.task_id,
                name="Daily Reward Claim",
                version="0.1.0",
                entry_state="ready",
                steps=[TaskStep("step-a", "Registered task build", lambda ctx: step_success("step-a", "ok"))],
                metadata={"factory_metadata": dict(request.metadata)},
            )

        session.register_task_factory("daily_ui.claim_rewards", factory)

        spec = session.build_registered_task_spec(
            "mumu-0",
            "daily_ui.claim_rewards",
            metadata={"workflow_mode": "claimable"},
        )

        self.assertTrue(session.has_task_factory("daily_ui.claim_rewards"))
        self.assertEqual(observed["task_id"], "daily_ui.claim_rewards")
        self.assertEqual(observed["profile_id"], "claim-rewards-profile")
        self.assertTrue(observed["health_check_ok"])
        self.assertEqual(observed["preview_image_path"], str(Path("captures") / "mumu-0.png"))
        self.assertEqual(observed["metadata"], {"workflow_mode": "claimable"})
        self.assertEqual(spec.metadata["factory_metadata"]["workflow_mode"], "claimable")

    def test_enqueue_registered_task_runs_claim_rewards_through_runtime_path(self) -> None:
        adapter = FakeAdapter(healthy=True)
        factory_calls: list[dict[str, object]] = []
        session = LiveRuntimeSession(
            adapter,
            discovery=lambda: [self.instance],
            profile_resolver=lambda instance: ProfileBinding(
                profile_id="claim-rewards-profile",
                display_name="Claim Rewards Profile",
                server_name="TW-1",
                character_name="Knight",
                allowed_tasks=["daily_ui.claim_rewards"],
            ),
        )
        session.sync_instances()

        def factory(request):
            factory_calls.append(dict(request.metadata))
            workflow_mode = str(request.metadata.get("workflow_mode", ""))
            return TaskSpec(
                task_id=request.task_id,
                name="Daily Reward Claim",
                version="0.1.0",
                entry_state="ready",
                steps=[
                    TaskStep(
                        "step-a",
                        "Uses registered runtime task builder",
                        lambda ctx: step_success(
                            "step-a",
                            ctx.metadata["profile_binding"].profile_id,
                            data={"workflow_mode": workflow_mode},
                        ),
                    )
                ],
                metadata={"workflow_mode": workflow_mode},
            )

        session.register_task_factory("daily_ui.claim_rewards", factory)

        queued = session.enqueue_registered_task(
            "mumu-0",
            "daily_ui.claim_rewards",
            priority=240,
            builder_metadata={"workflow_mode": "claimable"},
            queue_metadata={"operator_workflow": "claim_rewards"},
        )
        result = session.start_queue("mumu-0")
        context = session.get_runtime_context("mumu-0")

        self.assertEqual(factory_calls, [{"workflow_mode": "claimable"}])
        self.assertEqual(queued.task_id, "daily_ui.claim_rewards")
        self.assertEqual(queued.priority, 240)
        self.assertEqual(queued.metadata["operator_workflow"], "claim_rewards")
        self.assertEqual(result.runs[0].task_id, "daily_ui.claim_rewards")
        self.assertEqual(result.runs[0].status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(result.runs[0].step_results[0].message, "claim-rewards-profile")
        self.assertEqual(result.runs[0].step_results[0].data["workflow_mode"], "claimable")
        self.assertEqual(context.metadata["last_run_status"], TaskRunStatus.SUCCEEDED.value)

    def test_build_registered_task_spec_rejects_task_id_mismatch(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()
        session.register_task_factory(
            "daily_ui.claim_rewards",
            lambda request: TaskSpec(
                task_id="daily_ui.guild_check_in",
                name="Wrong Task",
                version="0.1.0",
                entry_state="ready",
                steps=[],
            ),
        )

        with self.assertRaisesRegex(ValueError, "returned spec.task_id=daily_ui.guild_check_in"):
            session.build_registered_task_spec("mumu-0", "daily_ui.claim_rewards")

    def test_schedule_runtime_refresh_updates_live_state_without_blocking_ui_reads(self) -> None:
        adapter = BlockingAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()

        scheduled = session.schedule_runtime_refresh(instance_id="mumu-0", capture_preview=True)

        self.assertTrue(scheduled.pending or scheduled.in_flight)
        self.assertTrue(adapter.health_check_started.wait(timeout=1.0))

        started = time.monotonic()
        live_state = session.get_live_state(instance_id="mumu-0")
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.2)
        self.assertIsNotNone(live_state.selected_instance)
        self.assertIn(live_state.refresh_state.operation, {"runtime_refresh", "idle"})
        self.assertTrue(live_state.refresh_state.pending or live_state.refresh_state.in_flight)

        adapter.release_health_check.set()

        self.assertTrue(session.wait_for_background_idle(timeout_sec=2.0))
        final_state = session.get_live_state(instance_id="mumu-0")

        self.assertFalse(final_state.refresh_state.in_flight)
        self.assertFalse(final_state.refresh_state.pending)
        self.assertEqual(final_state.selected_instance.instance_id, "mumu-0")
        self.assertTrue(final_state.selected_instance.health_check_ok)
        self.assertEqual(final_state.selected_instance.preview_image_path, str(Path("captures") / "mumu-0.png"))
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(adapter.screenshot_requests, 1)

    def test_connect_disconnect_reconnect_and_rediscover_surfaces_update_live_state(self) -> None:
        adapter = FakeAdapter(healthy=True)
        discovered: dict[str, list[InstanceState]] = {"states": []}
        session = LiveRuntimeSession(adapter, discovery=lambda: list(discovered["states"]))

        connected = session.connect_instance(self.instance)
        self.assertIsNotNone(connected)
        self.assertEqual(connected.status, "ready")
        self.assertEqual(session.get_live_state().instance_count, 1)

        disconnected = session.disconnect_instance("mumu-0", reason="operator requested")
        self.assertIsNotNone(disconnected)
        self.assertEqual(disconnected.status, "disconnected")
        self.assertEqual(session.get_live_state(instance_id="mumu-0").selected_instance.status, "disconnected")

        reconnecting = session.reconnect_instance("mumu-0", rediscover=False)
        self.assertIsNotNone(reconnecting)
        self.assertEqual(reconnecting.status, "connecting")

        discovered["states"] = [
            InstanceState(
                instance_id="mumu-0",
                label="MuMu 0",
                adb_serial="127.0.0.1:16384",
                status=InstanceStatus.READY,
            )
        ]
        summaries = session.rediscover_instances()
        refreshed = session.get_instance_summary("mumu-0")

        self.assertEqual(len(summaries), 1)
        self.assertIsNotNone(refreshed)
        self.assertEqual(refreshed.status, "ready")
        self.assertEqual(session.get_live_state().disconnected_count, 0)

    def test_build_adb_live_runtime_session_wires_production_refresh_preview_and_failure_path(self) -> None:
        transport = RecordingTransport(
            responses=[
                _result(self.instance.adb_serial, ("get-state",), stdout="device\n"),
                _result(self.instance.adb_serial, ("shell", "echo", "health_check"), stdout="not_ok\n"),
                _result(self.instance.adb_serial, ("exec-out", "screencap", "-p"), stdout=b"png-bytes"),
            ]
        )
        with TemporaryDirectory() as temp_dir:
            session = build_adb_live_runtime_session(
                transport=transport,
                screenshot_dir=Path(temp_dir),
                discovery=lambda: [self.instance],
            )
            session.sync_instances()

            dispatch = session.refresh("mumu-0")
            context = session.get_runtime_context("mumu-0")

            self.assertIsInstance(session.adapter, AdbEmulatorAdapter)
            self.assertIs(session.execution_path.adapter, session.adapter)
            self.assertEqual(dispatch.status, CommandDispatchStatus.COMPLETED)
            self.assertFalse(context.health_check_ok)
            self.assertIsNotNone(context.preview_frame)
            self.assertIsNotNone(context.failure_snapshot)
            self.assertEqual(context.failure_snapshot.task_id, "runtime.health_check")
            self.assertEqual(Path(context.preview_frame.image_path).suffix, ".png")
            self.assertEqual(
                [call["args"] for call in transport.calls],
                [
                    ("get-state",),
                    ("shell", "echo", "health_check"),
                    ("exec-out", "screencap", "-p"),
                ],
            )

    def test_build_adb_live_runtime_session_supports_background_rediscover_for_gui_state(self) -> None:
        transport = RecordingTransport(
            responses=[
                _result(self.instance.adb_serial, ("get-state",), stdout="device\n"),
                _result(self.instance.adb_serial, ("shell", "echo", "health_check"), stdout="health_check\n"),
                _result(self.instance.adb_serial, ("exec-out", "screencap", "-p"), stdout=b"png-bytes"),
            ]
        )
        with TemporaryDirectory() as temp_dir:
            session = build_adb_live_runtime_session(
                transport=transport,
                screenshot_dir=Path(temp_dir),
                discovery=lambda: [self.instance],
            )

            scheduled = session.schedule_rediscover(
                instance_id="mumu-0",
                refresh_runtime=True,
                capture_preview=True,
            )

            self.assertTrue(scheduled.pending or scheduled.in_flight)
            self.assertTrue(session.wait_for_background_idle(timeout_sec=2.0))

            live_state = session.get_live_state(instance_id="mumu-0")

            self.assertEqual(live_state.instance_count, 1)
            self.assertTrue(live_state.last_sync_ok)
            self.assertFalse(live_state.refresh_state.in_flight)
            self.assertEqual(live_state.selected_instance.instance_id, "mumu-0")
            self.assertTrue(live_state.selected_instance.health_check_ok)
            self.assertTrue(live_state.selected_instance.preview_image_path.endswith(".png"))
            self.assertEqual(
                [call["args"] for call in transport.calls],
                [
                    ("get-state",),
                    ("shell", "echo", "health_check"),
                    ("exec-out", "screencap", "-p"),
                ],
            )

    def test_build_adb_live_runtime_session_supports_task_failure_snapshot_for_first_task_path(self) -> None:
        failed_tap = _result(
            self.instance.adb_serial,
            ("shell", "input", "tap", "40", "60"),
            stdout="",
            stderr="tap failed",
            returncode=1,
        )
        transport = RecordingTransport(
            responses=[
                _result(self.instance.adb_serial, ("get-state",), stdout="device\n"),
                _result(self.instance.adb_serial, ("shell", "echo", "health_check"), stdout="health_check\n"),
                _result(self.instance.adb_serial, ("exec-out", "screencap", "-p"), stdout=b"png-bytes"),
                AdbCommandError(failed_tap),
            ]
        )
        with TemporaryDirectory() as temp_dir:
            session = build_adb_live_runtime_session(
                transport=transport,
                screenshot_dir=Path(temp_dir),
                discovery=lambda: [self.instance],
            )
            session.sync_instances()

            def handler(ctx):
                ctx.require_action_bridge().tap((40, 60), step_id="step-a", metadata={"source": "daily_ui.claim_rewards"})
                return step_success("step-a", "unreachable")

            session.enqueue(
                QueuedTask(
                    instance_id="mumu-0",
                    spec=TaskSpec(
                        task_id="daily_ui.claim_rewards",
                        name="Daily Reward Claim",
                        version="0.1.0",
                        entry_state="ready",
                        steps=[TaskStep("step-a", "Triggers adb-backed failure path", handler)],
                    ),
                    priority=100,
                )
            )

            result = session.start_queue("mumu-0")
            context = session.get_runtime_context("mumu-0")

            self.assertEqual(result.runs[0].status, TaskRunStatus.FAILED)
            self.assertEqual(result.runs[0].failure_snapshot.reason.value, "step_exception")
            self.assertIn("ADB command failed", result.runs[0].step_results[0].message)
            self.assertIsNotNone(result.runs[0].failure_snapshot.preview_frame)
            self.assertIsNotNone(context.preview_frame)
            self.assertIsNotNone(context.failure_snapshot)
            self.assertEqual(context.failure_snapshot.task_id, "daily_ui.claim_rewards")
            self.assertEqual(context.metadata["last_health_check_task_id"], "daily_ui.claim_rewards")
            self.assertEqual(
                [call["args"] for call in transport.calls],
                [
                    ("get-state",),
                    ("shell", "echo", "health_check"),
                    ("exec-out", "screencap", "-p"),
                    ("shell", "input", "tap", "40", "60"),
                ],
            )

    def test_refresh_uses_integrated_health_and_preview_services(self) -> None:
        adapter = FakeAdapter(healthy=False)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()

        dispatch = session.refresh("mumu-0")
        context = session.get_runtime_context("mumu-0")
        snapshot = session.snapshot()

        self.assertEqual(dispatch.instance_ids, ["mumu-0"])
        self.assertFalse(context.health_check_ok)
        self.assertIsNotNone(context.preview_frame)
        self.assertIsNotNone(context.failure_snapshot)
        self.assertEqual(context.failure_snapshot.task_id, "runtime.health_check")
        self.assertIs(session.last_command_result, dispatch)
        self.assertEqual([item.instance_id for item in snapshot.last_inspection_results], ["mumu-0"])

    def test_sync_instances_captures_profile_resolver_error_without_stopping_runtime(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(
            adapter,
            discovery=lambda: [self.instance],
            profile_resolver=lambda instance: (_ for _ in ()).throw(ValueError("ambiguous profile binding")),
        )

        synced = session.sync_instances()
        context = session.get_runtime_context("mumu-0")

        self.assertEqual(len(synced), 1)
        self.assertIsNone(context.profile_binding)
        self.assertEqual(context.metadata["profile_resolver_error"], "ambiguous profile binding")

    def test_poll_preserves_last_snapshot_and_surfaces_discovery_error(self) -> None:
        adapter = FakeAdapter(healthy=True)
        discovery_calls = {"count": 0}

        def discovery() -> list[InstanceState]:
            discovery_calls["count"] += 1
            if discovery_calls["count"] == 1:
                return [self.instance]
            raise RuntimeError("adb discovery unavailable")

        session = LiveRuntimeSession(adapter, discovery=discovery)

        first_snapshot = session.poll(refresh_runtime=True)
        second_snapshot = session.poll(refresh_runtime=True)

        self.assertEqual(first_snapshot.instances[0].instance_id, "mumu-0")
        self.assertEqual(second_snapshot.instances[0].instance_id, "mumu-0")
        self.assertEqual(session.last_sync_error, "adb discovery unavailable")
        self.assertFalse(second_snapshot.last_sync_ok)
        self.assertIsNotNone(second_snapshot.last_sync_at)
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(adapter.screenshot_requests, 1)
        self.assertGreater(second_snapshot.revision, first_snapshot.revision)

    def test_poll_refreshes_runtime_contexts_and_tracks_last_inspection_results(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])

        snapshot = session.poll(refresh_runtime=True)

        self.assertTrue(snapshot.last_sync_ok)
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(adapter.screenshot_requests, 1)
        self.assertEqual(len(snapshot.last_inspection_results), 1)
        self.assertEqual(snapshot.last_inspection_results[0].instance_id, "mumu-0")
        self.assertTrue(snapshot.last_inspection_results[0].health_check_ok)
        self.assertEqual(Path(snapshot.get_instance_snapshot("mumu-0").preview_frame.image_path), Path("captures") / "mumu-0.png")

    def test_refresh_runtime_contexts_supports_per_instance_filtering(self) -> None:
        second = InstanceState(
            instance_id="mumu-1",
            label="MuMu 1",
            adb_serial="127.0.0.1:16448",
            status=InstanceStatus.READY,
        )
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance, second])
        session.sync_instances()

        results = session.refresh_runtime_contexts(instance_id="mumu-1")
        filtered = session.snapshot(instance_id="mumu-1")

        self.assertEqual([result.instance_id for result in results], ["mumu-1"])
        self.assertEqual([result.instance_id for result in filtered.last_inspection_results], ["mumu-1"])
        self.assertEqual([item.instance_id for item in filtered.instance_snapshots], ["mumu-1"])

    def test_snapshot_filters_per_instance_and_tracks_recent_events(self) -> None:
        second = InstanceState(
            instance_id="mumu-1",
            label="MuMu 1",
            adb_serial="127.0.0.1:16448",
            status=InstanceStatus.READY,
        )
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance, second], max_recent_events=3)

        session.sync_instances()
        session.enqueue(QueuedTask(instance_id="mumu-0", spec=self._success_spec(), priority=100))
        session.enqueue(QueuedTask(instance_id="mumu-1", spec=self._success_spec(), priority=90))
        session.refresh("mumu-0")

        filtered = session.snapshot(instance_id="mumu-0")
        live_instance = session.get_instance_snapshot("mumu-0")

        self.assertEqual([instance.instance_id for instance in filtered.instances], ["mumu-0"])
        self.assertEqual([context.instance_id for context in filtered.contexts], ["mumu-0"])
        self.assertEqual([item.instance_id for item in filtered.queue_items], ["mumu-0"])
        self.assertEqual(filtered.instance_snapshots[0].queue_depth, 1)
        self.assertIsNotNone(live_instance)
        self.assertEqual(live_instance.instance_id, "mumu-0")
        self.assertLessEqual(len(filtered.recent_events), 3)
        self.assertTrue(all(not event.instance_id or event.instance_id == "mumu-0" for event in filtered.recent_events))

    def test_dispatch_command_updates_last_command_result_without_queue_result(self) -> None:
        adapter = FakeAdapter(healthy=True)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()

        result = session.dispatch_command(
            InstanceCommand(
                command_type=InstanceCommandType.INPUT_TEXT,
                instance_id="mumu-0",
                payload={"text": "hello"},
            )
        )
        snapshot = session.snapshot()

        self.assertIs(session.last_command_result, result)
        self.assertIsNone(session.last_queue_result)
        self.assertEqual(adapter.text_inputs, ["hello"])
        self.assertIs(snapshot.last_command_result, result)
        self.assertEqual(snapshot.get_instance_snapshot("mumu-0").instance_id, "mumu-0")

    @staticmethod
    def _success_spec() -> TaskSpec:
        return TaskSpec(
            task_id="task.success",
            name="Success Task",
            version="0.1.0",
            entry_state="ready",
            steps=[
                TaskStep(
                    "step-a",
                    "Uses bound profile",
                    lambda ctx: step_success("step-a", ctx.metadata["profile_binding"].profile_id),
                )
            ],
        )


def _result(
    adb_serial: str,
    args: tuple[str, ...],
    *,
    stdout: str | bytes,
    stderr: str | bytes = "",
    returncode: int = 0,
) -> AdbCommandResult:
    return AdbCommandResult(
        adb_serial=adb_serial,
        args=args,
        command=("adb", "-s", adb_serial, *args),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _claim_rewards_failure_data() -> dict[str, object]:
    return {
        "failure_reason_id": "claim_tap_no_effect",
        "outcome_code": "claim_tap_no_effect",
        "inspection_attempts": [
            {
                "attempt": 1,
                "state": "claimable",
                "screenshot_path": "captures/mumu-0.png",
            },
            {
                "attempt": 2,
                "state": "claimable",
                "screenshot_path": "captures/mumu-0.png",
            },
        ],
        "step_outcome": {
            "kind": "verification_failed",
            "failure_reason_id": "claim_tap_no_effect",
        },
        "task_action": {
            "action": "tap_claim_reward",
            "status": "executed",
        },
        "telemetry": {
            "inspection": {
                "workflow_mode": "claimable",
                "expected_panel_states": ["claimed", "confirm_required"],
            }
        },
    }
