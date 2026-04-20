from __future__ import annotations

import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import InstanceCommand, InstanceCommandType
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
        self.assertIs(session.last_queue_result, result)
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(adapter.screenshot_requests, 1)
        self.assertEqual(snapshot.instances[0].instance_id, "mumu-0")
        self.assertEqual(snapshot.contexts[0].instance_id, "mumu-0")
        self.assertEqual(snapshot.instance_snapshots[0].instance_id, "mumu-0")
        self.assertEqual(snapshot.instance_snapshots[0].profile_binding.profile_id, "main-account")
        self.assertGreaterEqual(len(snapshot.recent_events), 3)

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
        self.assertIs(session.last_command_result, dispatch)

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

        first_snapshot = session.poll()
        second_snapshot = session.poll()

        self.assertEqual(first_snapshot.instances[0].instance_id, "mumu-0")
        self.assertEqual(second_snapshot.instances[0].instance_id, "mumu-0")
        self.assertEqual(session.last_sync_error, "adb discovery unavailable")
        self.assertIsNotNone(second_snapshot.last_sync_at)
        self.assertGreater(second_snapshot.revision, first_snapshot.revision)

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
