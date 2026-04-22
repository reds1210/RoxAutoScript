from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable
from uuid import uuid4

from roxauto.core.models import InstanceState
from roxauto.core.time import utc_now
from roxauto.emulator.discovery import find_adb_executable


Coordinate = tuple[int, int]


@runtime_checkable
class EmulatorAdapter(Protocol):
    """Stable interface expected by runtime, GUI, and task packs."""

    def capture_screenshot(self, instance: InstanceState) -> Path:
        """Capture the current framebuffer for one emulator instance."""

    def tap(self, instance: InstanceState, point: Coordinate) -> None:
        """Tap one screen coordinate."""

    def swipe(self, instance: InstanceState, start: Coordinate, end: Coordinate, duration_ms: int = 250) -> None:
        """Swipe between two screen coordinates."""

    def input_text(self, instance: InstanceState, text: str) -> None:
        """Send text input into the active control."""

    def launch_app(self, instance: InstanceState, package_name: str) -> None:
        """Launch one Android package on the target instance."""

    def health_check(self, instance: InstanceState) -> bool:
        """Return whether the instance is healthy enough to accept actions."""


@dataclass(slots=True)
class AdbCommandResult:
    adb_serial: str
    args: tuple[str, ...]
    command: tuple[str, ...]
    returncode: int
    stdout: str | bytes = ""
    stderr: str | bytes = ""
    executed_at: object = field(default_factory=utc_now)


class AdbCommandError(RuntimeError):
    def __init__(self, result: AdbCommandResult) -> None:
        self.result = result
        stderr = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else str(result.stderr)
        message = f"ADB command failed for {result.adb_serial}: {' '.join(result.command)}"
        if stderr.strip():
            message = f"{message} | stderr={stderr.strip()}"
        super().__init__(message)


class AdbTransport(Protocol):
    def run(
        self,
        adb_serial: str,
        args: Sequence[str],
        *,
        text: bool = True,
        timeout_sec: float | None = None,
        check: bool = True,
    ) -> AdbCommandResult:
        """Run one adb command for a target serial."""


class SubprocessAdbTransport:
    def __init__(self, adb_executable: Path | str | None = None, *, default_timeout_sec: float = 10.0) -> None:
        resolved = Path(adb_executable) if adb_executable is not None else find_adb_executable()
        if resolved is None:
            raise FileNotFoundError("adb executable not found")
        self._adb_executable = resolved
        self._default_timeout_sec = default_timeout_sec

    @property
    def adb_executable(self) -> Path:
        return self._adb_executable

    def run(
        self,
        adb_serial: str,
        args: Sequence[str],
        *,
        text: bool = True,
        timeout_sec: float | None = None,
        check: bool = True,
    ) -> AdbCommandResult:
        normalized_args = tuple(str(arg) for arg in args)
        command = (str(self._adb_executable), "-s", adb_serial, *normalized_args)
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=text,
            check=False,
            timeout=self._default_timeout_sec if timeout_sec is None else timeout_sec,
        )
        result = AdbCommandResult(
            adb_serial=adb_serial,
            args=normalized_args,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout if completed.stdout is not None else ("" if text else b""),
            stderr=completed.stderr if completed.stderr is not None else ("" if text else b""),
        )
        if check and completed.returncode != 0:
            raise AdbCommandError(result)
        return result


class AdbEmulatorAdapter:
    def __init__(
        self,
        *,
        adb_executable: Path | str | None = None,
        transport: AdbTransport | None = None,
        screenshot_dir: Path | None = None,
        command_timeout_sec: float = 10.0,
        screenshot_timeout_sec: float = 20.0,
    ) -> None:
        self._command_timeout_sec = command_timeout_sec
        self._screenshot_timeout_sec = screenshot_timeout_sec
        self._transport = transport or SubprocessAdbTransport(
            adb_executable=adb_executable,
            default_timeout_sec=command_timeout_sec,
        )
        self._screenshot_dir = screenshot_dir or (Path(tempfile.gettempdir()) / "roxauto" / "captures")
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

    @property
    def screenshot_dir(self) -> Path:
        return self._screenshot_dir

    def capture_screenshot(self, instance: InstanceState) -> Path:
        result = self._run(instance, ("exec-out", "screencap", "-p"), text=False, timeout_sec=self._screenshot_timeout_sec)
        image_bytes = result.stdout if isinstance(result.stdout, bytes) else str(result.stdout).encode("utf-8")
        target = self._screenshot_dir / f"{instance.instance_id}-{uuid4().hex}.png"
        target.write_bytes(image_bytes)
        return target

    def tap(self, instance: InstanceState, point: Coordinate) -> None:
        self._run(instance, ("shell", "input", "tap", str(int(point[0])), str(int(point[1]))))

    def swipe(self, instance: InstanceState, start: Coordinate, end: Coordinate, duration_ms: int = 250) -> None:
        self._run(
            instance,
            (
                "shell",
                "input",
                "swipe",
                str(int(start[0])),
                str(int(start[1])),
                str(int(end[0])),
                str(int(end[1])),
                str(int(duration_ms)),
            ),
        )

    def input_text(self, instance: InstanceState, text: str) -> None:
        self._run(instance, ("shell", "input", "text", _encode_input_text(text)))

    def launch_app(self, instance: InstanceState, package_name: str) -> None:
        self._run(
            instance,
            (
                "shell",
                "monkey",
                "-p",
                package_name,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ),
        )

    def health_check(self, instance: InstanceState) -> bool:
        try:
            state_result = self._run(instance, ("get-state",), text=True)
            state = state_result.stdout.strip() if isinstance(state_result.stdout, str) else state_result.stdout.decode("utf-8", errors="replace").strip()
            if state != "device":
                return False
            probe_result = self._run(instance, ("shell", "echo", "health_check"), text=True)
            probe_output = probe_result.stdout.strip() if isinstance(probe_result.stdout, str) else probe_result.stdout.decode("utf-8", errors="replace").strip()
            return probe_output == "health_check"
        except (AdbCommandError, OSError, subprocess.TimeoutExpired):
            return False

    def _run(
        self,
        instance: InstanceState,
        args: Sequence[str],
        *,
        text: bool = True,
        timeout_sec: float | None = None,
    ) -> AdbCommandResult:
        return self._transport.run(
            instance.adb_serial,
            args,
            text=text,
            timeout_sec=self._command_timeout_sec if timeout_sec is None else timeout_sec,
            check=True,
        )


def _encode_input_text(value: str) -> str:
    replacements: dict[str, str] = {
        " ": "%s",
        '"': '\\"',
        "'": "\\'",
        "&": "\\&",
        "|": "\\|",
        "<": "\\<",
        ">": "\\>",
        "(": "\\(",
        ")": "\\)",
        ";": "\\;",
        "$": "\\$",
    }
    encoded = []
    for char in value:
        encoded.append(replacements.get(char, char))
    return "".join(encoded)
