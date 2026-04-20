"""Emulator integration package."""

from roxauto.emulator.adapter import (
    AdbCommandError,
    AdbCommandResult,
    AdbEmulatorAdapter,
    AdbTransport,
    Coordinate,
    EmulatorAdapter,
    SubprocessAdbTransport,
)
from roxauto.emulator.execution import (
    ActionExecutor,
    CommandExecutionResult,
    CommandExecutionStatus,
    EmulatorActionAdapter,
    HealthCheckResult,
    HealthCheckService,
    ScreenshotCapturePipeline,
)
from roxauto.emulator.live_runtime import (
    LiveRuntimeEventRecord,
    LiveRuntimeInstanceSnapshot,
    LiveRuntimeSession,
    LiveRuntimeSnapshot,
)

__all__ = [
    "ActionExecutor",
    "AdbCommandError",
    "AdbCommandResult",
    "AdbEmulatorAdapter",
    "AdbTransport",
    "CommandExecutionResult",
    "CommandExecutionStatus",
    "Coordinate",
    "EmulatorActionAdapter",
    "EmulatorAdapter",
    "HealthCheckResult",
    "HealthCheckService",
    "LiveRuntimeEventRecord",
    "LiveRuntimeInstanceSnapshot",
    "LiveRuntimeSession",
    "LiveRuntimeSnapshot",
    "ScreenshotCapturePipeline",
    "SubprocessAdbTransport",
]

