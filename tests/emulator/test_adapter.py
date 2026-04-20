from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.core.models import InstanceState, InstanceStatus
from roxauto.emulator.adapter import AdbCommandError, AdbCommandResult, AdbEmulatorAdapter


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


class AdbEmulatorAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )

    def test_capture_screenshot_materializes_png_from_exec_out(self) -> None:
        transport = RecordingTransport(
            responses=[
                _result(
                    self.instance.adb_serial,
                    ("exec-out", "screencap", "-p"),
                    stdout=b"png-bytes",
                )
            ]
        )
        with TemporaryDirectory() as temp_dir:
            adapter = AdbEmulatorAdapter(transport=transport, screenshot_dir=Path(temp_dir))

            image_path = adapter.capture_screenshot(self.instance)

            self.assertTrue(image_path.exists())
            self.assertEqual(image_path.read_bytes(), b"png-bytes")
            self.assertEqual(
                transport.calls[0]["args"],
                ("exec-out", "screencap", "-p"),
            )
            self.assertFalse(bool(transport.calls[0]["text"]))

    def test_actions_route_through_consistent_adb_input_commands(self) -> None:
        transport = RecordingTransport()
        adapter = AdbEmulatorAdapter(transport=transport, screenshot_dir=Path.cwd())

        adapter.tap(self.instance, (12, 34))
        adapter.swipe(self.instance, (1, 2), (30, 40), duration_ms=600)
        adapter.input_text(self.instance, "hello world")
        adapter.launch_app(self.instance, "com.example.game")

        self.assertEqual(
            [call["args"] for call in transport.calls],
            [
                ("shell", "input", "tap", "12", "34"),
                ("shell", "input", "swipe", "1", "2", "30", "40", "600"),
                ("shell", "input", "text", "hello%sworld"),
                (
                    "shell",
                    "monkey",
                    "-p",
                    "com.example.game",
                    "-c",
                    "android.intent.category.LAUNCHER",
                    "1",
                ),
            ],
        )

    def test_health_check_requires_device_state_and_probe_echo(self) -> None:
        healthy_transport = RecordingTransport(
            responses=[
                _result(self.instance.adb_serial, ("get-state",), stdout="device\n"),
                _result(self.instance.adb_serial, ("shell", "echo", "health_check"), stdout="health_check\n"),
            ]
        )
        unhealthy_transport = RecordingTransport(
            responses=[
                _result(self.instance.adb_serial, ("get-state",), stdout="offline\n"),
            ]
        )

        healthy_adapter = AdbEmulatorAdapter(transport=healthy_transport, screenshot_dir=Path.cwd())
        unhealthy_adapter = AdbEmulatorAdapter(transport=unhealthy_transport, screenshot_dir=Path.cwd())

        self.assertTrue(healthy_adapter.health_check(self.instance))
        self.assertFalse(unhealthy_adapter.health_check(self.instance))

    def test_health_check_returns_false_on_adb_command_error(self) -> None:
        failed_result = _result(self.instance.adb_serial, ("get-state",), stdout="", stderr="device missing", returncode=1)
        transport = RecordingTransport(responses=[AdbCommandError(failed_result)])
        adapter = AdbEmulatorAdapter(transport=transport, screenshot_dir=Path.cwd())

        self.assertFalse(adapter.health_check(self.instance))


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
