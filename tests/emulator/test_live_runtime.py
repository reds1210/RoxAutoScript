from __future__ import annotations

import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.core.models import InstanceState, InstanceStatus, ProfileBinding, TaskRunStatus, TaskSpec
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import TaskStep, step_success
from roxauto.emulator.live_runtime import LiveRuntimeSession


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

    def health_check(self, instance: InstanceState) -> bool:
        self.health_checks += 1
        return self.healthy


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
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(adapter.screenshot_requests, 1)
        self.assertEqual(snapshot.instances[0].instance_id, "mumu-0")
        self.assertEqual(snapshot.contexts[0].instance_id, "mumu-0")

    def test_refresh_uses_integrated_health_and_preview_services(self) -> None:
        adapter = FakeAdapter(healthy=False)
        session = LiveRuntimeSession(adapter, discovery=lambda: [self.instance])
        session.sync_instances()

        dispatch = session.refresh("mumu-0")
        context = session.get_runtime_context("mumu-0")

        self.assertEqual(dispatch.instance_ids, ["mumu-0"])
        self.assertFalse(context.health_check_ok)
        self.assertIsNotNone(context.preview_frame)
        self.assertIsNotNone(context.failure_snapshot)
        self.assertEqual(context.failure_snapshot.task_id, "runtime.health_check")

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
