from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from roxauto.core.models import InstanceState


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
