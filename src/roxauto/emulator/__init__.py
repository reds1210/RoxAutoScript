"""Emulator integration package."""

from roxauto.emulator.adapter import Coordinate, EmulatorAdapter
from roxauto.emulator.execution import (
    ActionExecutor,
    CommandExecutionResult,
    CommandExecutionStatus,
    EmulatorActionAdapter,
    HealthCheckResult,
    HealthCheckService,
    ScreenshotCapturePipeline,
)

__all__ = [
    "ActionExecutor",
    "CommandExecutionResult",
    "CommandExecutionStatus",
    "Coordinate",
    "EmulatorActionAdapter",
    "EmulatorAdapter",
    "HealthCheckResult",
    "HealthCheckService",
    "ScreenshotCapturePipeline",
]

