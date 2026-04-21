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
    RuntimeExecutionPath,
    ScreenshotCapturePipeline,
    build_adb_execution_path,
    build_runtime_execution_path,
)
from roxauto.emulator.live_runtime import (
    LiveRuntimeEventRecord,
    LiveRuntimeInstanceSnapshot,
    LiveRuntimeSession,
    LiveRuntimeSnapshot,
    build_adb_live_runtime_session,
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
    "RuntimeExecutionPath",
    "ScreenshotCapturePipeline",
    "SubprocessAdbTransport",
    "build_adb_execution_path",
    "build_adb_live_runtime_session",
    "build_runtime_execution_path",
]

