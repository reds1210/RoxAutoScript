from __future__ import annotations

import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.app.runtime_bridge import OperatorConsoleRuntimeBridge


class OperatorConsoleRuntimeBridgeTests(unittest.TestCase):
    def test_refresh_syncs_runtime_context_and_seeds_queue(self) -> None:
        bridge = OperatorConsoleRuntimeBridge(
            workspace_root=Path(__file__).resolve().parents[2],
            doctor_report_provider=lambda: _doctor_report(instance_count=1),
        )

        snapshot = bridge.refresh()
        context = bridge.get_runtime_context("mumu-0")
        event_names = [event.name for event in bridge.events()]

        self.assertEqual(snapshot.instance_count, 1)
        self.assertEqual(snapshot.instances[0].status, "ready")
        self.assertEqual(len(bridge.queue_items("mumu-0")), 2)
        self.assertIsNotNone(context)
        self.assertTrue(context.health_check_ok)
        self.assertIsNotNone(context.preview_frame)
        self.assertIn("instance.health_checked", event_names)
        self.assertIn("preview.captured", event_names)
        self.assertIn("operator.refresh.completed", event_names)

    def test_start_queue_dispatch_drains_seeded_work_and_records_events(self) -> None:
        bridge = OperatorConsoleRuntimeBridge(
            workspace_root=Path(__file__).resolve().parents[2],
            doctor_report_provider=lambda: _doctor_report(instance_count=1),
        )
        bridge.refresh()

        dispatch = bridge.dispatch_manual_action("start_queue", instance_id="mumu-0")
        queue_run = dispatch.results[0]
        context = bridge.get_runtime_context("mumu-0")
        event_names = [event.name for event in bridge.events()]

        self.assertEqual(len(queue_run.runs), 2)
        self.assertEqual(len(bridge.queue_items("mumu-0")), 0)
        self.assertEqual(context.metadata["last_run_status"], "succeeded")
        self.assertIn("task.started", event_names)
        self.assertIn("task.finished", event_names)
        self.assertIn("command.executed", event_names)
        self.assertIn("operator.command.dispatched", event_names)

    def test_emergency_stop_reflects_global_stop_state(self) -> None:
        bridge = OperatorConsoleRuntimeBridge(
            workspace_root=Path(__file__).resolve().parents[2],
            doctor_report_provider=lambda: _doctor_report(instance_count=2),
        )
        bridge.refresh()

        bridge.dispatch_manual_action("emergency_stop")

        self.assertTrue(bridge.global_emergency_stop_active())
        self.assertTrue(bridge.get_runtime_context("mumu-0").stop_requested)
        self.assertTrue(bridge.get_runtime_context("mumu-1").stop_requested)


def _doctor_report(*, instance_count: int) -> dict[str, object]:
    instances = []
    for index in range(instance_count):
        instances.append(
            {
                "instance_id": f"mumu-{index}",
                "label": f"MuMu {index}",
                "adb_serial": f"127.0.0.1:{16384 + index * 32}",
                "status": "ready",
                "metadata": {"server": f"TW-{index + 1}"},
            }
        )
    return {
        "packages": {"PySide6": True, "adbutils": True, "cv2": False},
        "adb": {"path": "C:/platform-tools/adb.exe", "instances_found": len(instances)},
        "instances": instances,
    }
