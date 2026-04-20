from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from roxauto.core.time import utc_now


class InstanceCommandType(str, Enum):
    REFRESH = "refresh"
    START_QUEUE = "start_queue"
    PAUSE = "pause"
    STOP = "stop"
    EMERGENCY_STOP = "emergency_stop"
    TAP = "tap"
    SWIPE = "swipe"
    INPUT_TEXT = "input_text"


@dataclass(slots=True)
class InstanceCommand:
    command_type: InstanceCommandType
    instance_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    command_id: str = field(default_factory=lambda: str(uuid4()))
    requested_at: object = field(default_factory=utc_now)


class CommandRouteKind(str, Enum):
    CONTROL = "control"
    GLOBAL_CONTROL = "global_control"
    INTERACTION = "interaction"


@dataclass(slots=True)
class CommandRoute:
    command_id: str
    command_type: InstanceCommandType
    instance_id: str | None
    kind: CommandRouteKind
    payload: dict[str, Any] = field(default_factory=dict)
    accepted: bool = True
    message: str = ""
    routed_at: object = field(default_factory=utc_now)


class CommandRoutingError(ValueError):
    """Raised when a command cannot be normalized into an executable route."""


class CommandRouter:
    def route(self, command: InstanceCommand) -> CommandRoute:
        if command.command_type == InstanceCommandType.REFRESH:
            return self._route_global(command, "refresh requested")
        if command.command_type == InstanceCommandType.EMERGENCY_STOP:
            return self._route_global(command, "emergency stop requested")
        if command.command_type in {
            InstanceCommandType.START_QUEUE,
            InstanceCommandType.PAUSE,
            InstanceCommandType.STOP,
        }:
            instance_id = self._require_instance_id(command)
            return CommandRoute(
                command_id=command.command_id,
                command_type=command.command_type,
                instance_id=instance_id,
                kind=CommandRouteKind.CONTROL,
                payload={},
                message=f"{command.command_type.value} routed to runtime",
            )
        if command.command_type == InstanceCommandType.TAP:
            instance_id = self._require_instance_id(command)
            point = self._parse_point(command.payload)
            return CommandRoute(
                command_id=command.command_id,
                command_type=command.command_type,
                instance_id=instance_id,
                kind=CommandRouteKind.INTERACTION,
                payload={"point": point},
                message=f"tap {point[0]},{point[1]}",
            )
        if command.command_type == InstanceCommandType.SWIPE:
            instance_id = self._require_instance_id(command)
            start, end, duration_ms = self._parse_swipe(command.payload)
            return CommandRoute(
                command_id=command.command_id,
                command_type=command.command_type,
                instance_id=instance_id,
                kind=CommandRouteKind.INTERACTION,
                payload={"start": start, "end": end, "duration_ms": duration_ms},
                message=f"swipe {start[0]},{start[1]}->{end[0]},{end[1]}",
            )
        if command.command_type == InstanceCommandType.INPUT_TEXT:
            instance_id = self._require_instance_id(command)
            text = self._parse_text(command.payload)
            return CommandRoute(
                command_id=command.command_id,
                command_type=command.command_type,
                instance_id=instance_id,
                kind=CommandRouteKind.INTERACTION,
                payload={"text": text},
                message="input text routed",
            )
        raise CommandRoutingError(f"Unsupported command type: {command.command_type.value}")

    def _route_global(self, command: InstanceCommand, message: str) -> CommandRoute:
        kind = CommandRouteKind.GLOBAL_CONTROL if command.instance_id is None else CommandRouteKind.CONTROL
        return CommandRoute(
            command_id=command.command_id,
            command_type=command.command_type,
            instance_id=command.instance_id,
            kind=kind,
            payload=dict(command.payload),
            message=message,
        )

    def _require_instance_id(self, command: InstanceCommand) -> str:
        if not command.instance_id:
            raise CommandRoutingError(f"{command.command_type.value} requires an instance_id")
        return command.instance_id

    def _parse_point(self, payload: dict[str, Any]) -> tuple[int, int]:
        if "point" in payload:
            point = payload["point"]
            if isinstance(point, (list, tuple)) and len(point) == 2:
                return int(point[0]), int(point[1])
            raise CommandRoutingError("tap payload point must contain two coordinates")
        if "x" in payload and "y" in payload:
            return int(payload["x"]), int(payload["y"])
        raise CommandRoutingError("tap payload must define point or x/y")

    def _parse_swipe(self, payload: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int], int]:
        if "start" not in payload or "end" not in payload:
            raise CommandRoutingError("swipe payload must define start and end")
        start = self._parse_coordinate(payload["start"], "start")
        end = self._parse_coordinate(payload["end"], "end")
        duration_ms = int(payload.get("duration_ms", 250))
        return start, end, duration_ms

    def _parse_coordinate(self, value: Any, label: str) -> tuple[int, int]:
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return int(value[0]), int(value[1])
        raise CommandRoutingError(f"swipe payload {label} must contain two coordinates")

    def _parse_text(self, payload: dict[str, Any]) -> str:
        if "text" not in payload:
            raise CommandRoutingError("input_text payload must define text")
        return str(payload["text"])
