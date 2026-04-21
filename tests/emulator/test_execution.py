from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import InstanceCommand, InstanceCommandType
from roxauto.core.models import InstanceState, InstanceStatus, PreviewFrame
from roxauto.emulator.adapter import AdbCommandResult, AdbEmulatorAdapter
from roxauto.emulator.execution import (
    ActionExecutor,
    CommandExecutionStatus,
    EmulatorActionAdapter,
    HealthCheckService,
    RuntimeExecutionPath,
    ScreenshotCapturePipeline,
    build_adb_execution_path,
    build_runtime_execution_path,
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

    def test_build_runtime_execution_path_reuses_one_adapter_for_all_services(self) -> None:
        adapter = FakeAdapter(healthy=True)
        path = build_runtime_execution_path(adapter)

        self.assertIsInstance(path, RuntimeExecutionPath)
        self.assertIs(path.adapter, adapter)

        tap_result = path.command_executor.execute(
            self.instance,
            InstanceCommand(
                command_type=InstanceCommandType.TAP,
                instance_id=self.instance.instance_id,
                payload={"point": (9, 18)},
            ),
        )
        health_result = path.health_checker.check(self.instance)
        preview_frame = path.preview_capture.capture(self.instance)

        self.assertEqual(tap_result.status, CommandExecutionStatus.EXECUTED)
        self.assertEqual(adapter.taps, [(9, 18)])
        self.assertTrue(health_result.healthy)
        self.assertEqual(Path(preview_frame.image_path), Path("captures") / "mumu-0.png")
        self.assertEqual(adapter.health_checks, 1)
        self.assertEqual(adapter.screenshot_requests, 1)

    def test_build_adb_execution_path_wires_real_adapter_with_shared_services(self) -> None:
        transport = RecordingTransport(
            responses=[
                _result(self.instance.adb_serial, ("shell", "input", "text", "hello"), stdout=""),
                _result(self.instance.adb_serial, ("get-state",), stdout="device\n"),
                _result(self.instance.adb_serial, ("shell", "echo", "health_check"), stdout="health_check\n"),
                _result(self.instance.adb_serial, ("exec-out", "screencap", "-p"), stdout=b"png-bytes"),
            ]
        )
        with TemporaryDirectory() as temp_dir:
            path = build_adb_execution_path(transport=transport, screenshot_dir=Path(temp_dir))

            self.assertIsInstance(path.adapter, AdbEmulatorAdapter)

            command_result = path.command_executor.execute(
                self.instance,
                InstanceCommand(
                    command_type=InstanceCommandType.INPUT_TEXT,
                    instance_id=self.instance.instance_id,
                    payload={"text": "hello"},
                ),
            )
            health_result = path.health_checker.check(self.instance)
            preview_frame = path.preview_capture.capture(self.instance)

            self.assertEqual(command_result.status, CommandExecutionStatus.EXECUTED)
            self.assertTrue(health_result.healthy)
            self.assertEqual(Path(preview_frame.image_path).suffix, ".png")
            self.assertEqual(
                [call["args"] for call in transport.calls],
                [
                    ("shell", "input", "text", "hello"),
                    ("get-state",),
                    ("shell", "echo", "health_check"),
                    ("exec-out", "screencap", "-p"),
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
