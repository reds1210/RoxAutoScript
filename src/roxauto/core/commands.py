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
