from __future__ import annotations

import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import InstanceCommand, InstanceCommandType
from roxauto.core.models import InstanceState, InstanceStatus, PreviewFrame
from roxauto.emulator.execution import (
    ActionExecutor,
    CommandExecutionStatus,
    EmulatorActionAdapter,
    HealthCheckService,
    ScreenshotCapturePipeline,
)


class RecordingAuditSink:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict[str, object]]] = []

    def write(self, name: str, payload: dict[str, object]) -> None:
        self.records.append((name, payload))


class FakeAdapter:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy
        self.taps: list[tuple[int, int]] = []
        self.swipes: list[tuple[tuple[int, int], tuple[int, int], int]] = []
        self.text_inputs: list[str] = []
        self.health_checks = 0
        self.screenshot_requests = 0

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


class EmulatorExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )

    def test_screenshot_pipeline_emits_preview_frame_audit(self) -> None:
        adapter = FakeAdapter()
        sink = RecordingAuditSink()
        pipeline = ScreenshotCapturePipeline(adapter, audit_sink=sink)

        frame = pipeline.capture(self.instance, run_id="run-1", task_id="task-1")

        self.assertIsInstance(frame, PreviewFrame)
        self.assertEqual(Path(frame.image_path), Path("captures") / "mumu-0.png")
        self.assertEqual(adapter.screenshot_requests, 1)
        self.assertEqual(sink.records[0][0], "preview.captured")
        self.assertEqual(Path(sink.records[0][1]["preview_frame"].image_path), Path("captures") / "mumu-0.png")

    def test_action_executor_routes_commands_to_adapter(self) -> None:
        adapter = FakeAdapter()
        sink = RecordingAuditSink()
        executor = ActionExecutor(adapter, audit_sink=sink)

        tap_result = executor.execute(
            self.instance,
            InstanceCommand(
                command_type=InstanceCommandType.TAP,
                instance_id=self.instance.instance_id,
                payload={"point": [12, 34]},
            ),
        )
        refresh_result = executor.execute(
            self.instance,
            InstanceCommand(
                command_type=InstanceCommandType.REFRESH,
            ),
        )

        self.assertTrue(isinstance(adapter, EmulatorActionAdapter))
        self.assertEqual(adapter.taps, [(12, 34)])
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(tap_result.status, CommandExecutionStatus.EXECUTED)
        self.assertEqual(refresh_result.status, CommandExecutionStatus.ROUTED)
        self.assertEqual(sink.records[0][0], "command.executed")

    def test_health_check_service_records_structured_result(self) -> None:
        adapter = FakeAdapter(healthy=False)
        sink = RecordingAuditSink()
        service = HealthCheckService(adapter, audit_sink=sink)

        result = service.check(self.instance, metadata={"source": "manual"})

        self.assertFalse(result.healthy)
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(sink.records[0][0], "instance.health_check")
        self.assertEqual(sink.records[0][1]["metadata"]["source"], "manual")
