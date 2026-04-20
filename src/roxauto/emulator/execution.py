from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from roxauto.core.commands import (
    CommandRoute,
    CommandRouteKind,
    CommandRouter,
    InstanceCommand,
    InstanceCommandType,
)
from roxauto.core.events import (
    EVENT_COMMAND_EXECUTED,
    EVENT_INSTANCE_ERROR,
    EVENT_INSTANCE_HEALTH_CHECKED,
    EVENT_PREVIEW_CAPTURED,
)
from roxauto.core.models import InstanceState, PreviewFrame
from roxauto.core.runtime import AuditSink
from roxauto.core.time import utc_now
from roxauto.emulator.adapter import EmulatorAdapter
from roxauto.logs.audit import write_preview_audit


class ScreenshotProvider(Protocol):
    def capture_screenshot(self, instance: InstanceState) -> Path:
        """Capture the current framebuffer for one emulator instance."""


class InteractionAdapter(Protocol):
    def tap(self, instance: InstanceState, point: tuple[int, int]) -> None:
        """Tap one screen coordinate."""

    def swipe(self, instance: InstanceState, start: tuple[int, int], end: tuple[int, int], duration_ms: int = 250) -> None:
        """Swipe between two screen coordinates."""

    def input_text(self, instance: InstanceState, text: str) -> None:
        """Send text input into the active control."""

    def health_check(self, instance: InstanceState) -> bool:
        """Return whether the instance is healthy enough to accept actions."""


@runtime_checkable
class EmulatorActionAdapter(EmulatorAdapter, ScreenshotProvider, InteractionAdapter, Protocol):
    """Stable execution-side adapter contract for production and fallback adapters."""


class CommandExecutionStatus(str, Enum):
    EXECUTED = "executed"
    ROUTED = "routed"
    REJECTED = "rejected"


@dataclass(slots=True)
class CommandExecutionResult:
    command_id: str
    command_type: InstanceCommandType
    instance_id: str | None
    route_kind: CommandRouteKind
    status: CommandExecutionStatus
    message: str
    executed_at: object = field(default_factory=utc_now)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HealthCheckResult:
    instance_id: str
    healthy: bool
    checked_at: object = field(default_factory=utc_now)
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ScreenshotCapturePipeline:
    def __init__(
        self,
        adapter: ScreenshotProvider,
        event_bus: Any | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._adapter = adapter
        self._event_bus = event_bus
        self._audit_sink = audit_sink

    def capture(
        self,
        instance: InstanceState,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        thumbnail_path: Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PreviewFrame:
        image_path = self._adapter.capture_screenshot(instance)
        frame = PreviewFrame(
            frame_id=str(uuid4()),
            instance_id=instance.instance_id,
            image_path=str(image_path),
            thumbnail_path=str(thumbnail_path) if thumbnail_path is not None else None,
            metadata=metadata or {},
        )
        if self._event_bus is not None:
            self._event_bus.publish(
                EVENT_PREVIEW_CAPTURED,
                {
                    "instance_id": instance.instance_id,
                    "run_id": run_id,
                    "task_id": task_id,
                    "frame_id": frame.frame_id,
                    "image_path": frame.image_path,
                },
            )
        if self._audit_sink is not None:
            write_preview_audit(
                self._audit_sink,
                frame,
                run_id=run_id,
                task_id=task_id,
                metadata=metadata,
            )
        return frame


class ActionExecutor:
    def __init__(
        self,
        adapter: EmulatorActionAdapter,
        router: CommandRouter | None = None,
        event_bus: Any | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._adapter = adapter
        self._router = router or CommandRouter()
        self._event_bus = event_bus
        self._audit_sink = audit_sink

    def execute(self, instance: InstanceState, command: InstanceCommand) -> CommandExecutionResult:
        route = self._router.route(command)
        return self.execute_route(instance, route)

    def execute_route(self, instance: InstanceState, route: CommandRoute) -> CommandExecutionResult:
        if route.kind == CommandRouteKind.GLOBAL_CONTROL:
            if route.command_type == InstanceCommandType.REFRESH:
                healthy = self._adapter.health_check(instance)
                message = "refresh routed and health checked" if healthy else "refresh routed but health check failed"
                return self._record_result(route, instance.instance_id, CommandExecutionStatus.ROUTED, message)
            return self._record_result(route, instance.instance_id, CommandExecutionStatus.ROUTED, route.message)

        if route.command_type == InstanceCommandType.TAP:
            self._adapter.tap(instance, route.payload["point"])
        elif route.command_type == InstanceCommandType.SWIPE:
            self._adapter.swipe(
                instance,
                route.payload["start"],
                route.payload["end"],
                route.payload["duration_ms"],
            )
        elif route.command_type == InstanceCommandType.INPUT_TEXT:
            self._adapter.input_text(instance, route.payload["text"])
        else:
            return self._record_result(route, instance.instance_id, CommandExecutionStatus.ROUTED, route.message)

        return self._record_result(route, instance.instance_id, CommandExecutionStatus.EXECUTED, route.message)

    def _record_result(
        self,
        route: CommandRoute,
        instance_id: str | None,
        status: CommandExecutionStatus,
        message: str,
    ) -> CommandExecutionResult:
        result = CommandExecutionResult(
            command_id=route.command_id,
            command_type=route.command_type,
            instance_id=instance_id,
            route_kind=route.kind,
            status=status,
            message=message,
            payload=dict(route.payload),
        )
        if self._audit_sink is not None:
            self._audit_sink.write(
                "command.executed",
                {
                    "command_id": result.command_id,
                    "command_type": result.command_type.value,
                    "instance_id": result.instance_id,
                    "route_kind": result.route_kind.value,
                    "status": result.status.value,
                    "message": result.message,
                    "payload": result.payload,
                },
            )
        if self._event_bus is not None:
            self._event_bus.publish(
                EVENT_COMMAND_EXECUTED,
                {
                    "command_id": result.command_id,
                    "command_type": result.command_type.value,
                    "instance_id": result.instance_id,
                    "route_kind": result.route_kind.value,
                    "status": result.status.value,
                },
            )
        return result


class HealthCheckService:
    def __init__(
        self,
        adapter: InteractionAdapter,
        event_bus: Any | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._adapter = adapter
        self._event_bus = event_bus
        self._audit_sink = audit_sink

    def check(self, instance: InstanceState, *, metadata: dict[str, Any] | None = None) -> HealthCheckResult:
        healthy = self._adapter.health_check(instance)
        result = HealthCheckResult(
            instance_id=instance.instance_id,
            healthy=healthy,
            message="healthy" if healthy else "health check failed",
            metadata=metadata or {},
        )
        if self._event_bus is not None:
            self._event_bus.publish(
                EVENT_INSTANCE_HEALTH_CHECKED,
                {
                    "instance_id": result.instance_id,
                    "healthy": result.healthy,
                    "checked_at": result.checked_at,
                    "message": result.message,
                },
            )
            if not healthy:
                self._event_bus.publish(
                    EVENT_INSTANCE_ERROR,
                    {
                        "instance_id": result.instance_id,
                        "message": result.message,
                    },
                )
        if self._audit_sink is not None:
            self._audit_sink.write(
                "instance.health_check",
                {
                    "instance_id": result.instance_id,
                    "healthy": result.healthy,
                    "checked_at": result.checked_at,
                    "message": result.message,
                    "metadata": result.metadata,
                },
            )
        return result
