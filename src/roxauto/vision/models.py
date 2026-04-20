from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from json import dumps, loads
from pathlib import Path
from typing import Any, Self

from roxauto.core.models import VisionMatch
from roxauto.core.time import utc_now
from roxauto.core.serde import to_primitive


class MatchStatus(str, Enum):
    MATCHED = "matched"
    MISSED = "missed"


class RecordingActionType(str, Enum):
    TAP = "tap"
    SWIPE = "swipe"
    INPUT_TEXT = "input_text"
    WAIT = "wait"
    CAPTURE = "capture"
    ANNOTATE = "annotate"


class StopConditionType(str, Enum):
    MANUAL_STOP = "manual_stop"
    TIMEOUT = "timeout"
    NO_MATCH = "no_match"
    HEALTH_CHECK_FAILED = "health_check_failed"
    RECOVERY_EXHAUSTED = "recovery_exhausted"


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value)
    return utc_now()


@dataclass(slots=True)
class AnchorSpec:
    anchor_id: str
    label: str
    template_path: str
    confidence_threshold: float = 0.85
    match_region: tuple[int, int, int, int] | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        region = data.get("match_region")
        return cls(
            anchor_id=str(data.get("anchor_id", "")),
            label=str(data.get("label", "")),
            template_path=str(data.get("template_path", "")),
            confidence_threshold=float(data.get("confidence_threshold", 0.85)),
            match_region=tuple(region) if region else None,
            description=str(data.get("description", "")),
            tags=[str(tag) for tag in data.get("tags", [])],
            metadata=dict(data.get("metadata", {})),
        )

    def resolved_template_path(self, repository_root: Path) -> Path:
        return repository_root / self.template_path


@dataclass(slots=True)
class TemplateRepositoryManifest:
    repository_id: str
    display_name: str
    version: str
    anchors: list[AnchorSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        anchors = [AnchorSpec.from_dict(entry) for entry in data.get("anchors", [])]
        return cls(
            repository_id=str(data.get("repository_id", "")),
            display_name=str(data.get("display_name", "")),
            version=str(data.get("version", "0.1.0")),
            anchors=anchors,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class CalibrationProfile:
    profile_id: str
    instance_id: str = ""
    emulator_name: str = "mumu"
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: int = 0
    offset_y: int = 0
    crop_region: tuple[int, int, int, int] | None = None
    anchor_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    def to_json(self) -> str:
        return dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        crop_region = data.get("crop_region")
        return cls(
            profile_id=str(data.get("profile_id", "")),
            instance_id=str(data.get("instance_id", "")),
            emulator_name=str(data.get("emulator_name", "mumu")),
            scale_x=float(data.get("scale_x", 1.0)),
            scale_y=float(data.get("scale_y", 1.0)),
            offset_x=int(data.get("offset_x", 0)),
            offset_y=int(data.get("offset_y", 0)),
            crop_region=tuple(crop_region) if crop_region else None,
            anchor_overrides={str(key): dict(value) for key, value in data.get("anchor_overrides", {}).items()},
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls.from_dict(loads(payload))


@dataclass(slots=True)
class RecordingAction:
    action_id: str
    action_type: RecordingActionType
    target: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_action_type = data.get("action_type", RecordingActionType.ANNOTATE.value)
        if isinstance(raw_action_type, RecordingActionType):
            action_type = raw_action_type
        else:
            action_type = RecordingActionType(str(raw_action_type))
        return cls(
            action_id=str(data.get("action_id", "")),
            action_type=action_type,
            target=str(data.get("target", "")),
            payload=dict(data.get("payload", {})),
            occurred_at=_parse_datetime(data.get("occurred_at")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class ReplayScript:
    script_id: str
    name: str
    version: str = "0.1.0"
    actions: list[RecordingAction] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    def to_json(self) -> str:
        return dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            script_id=str(data.get("script_id", "")),
            name=str(data.get("name", "")),
            version=str(data.get("version", "0.1.0")),
            actions=[RecordingAction.from_dict(entry) for entry in data.get("actions", [])],
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls.from_dict(loads(payload))

    def append(self, action: RecordingAction) -> None:
        self.actions.append(action)


@dataclass(slots=True)
class TemplateMatchResult:
    source_image: str
    candidates: list[VisionMatch] = field(default_factory=list)
    expected_anchor_id: str = ""
    threshold: float = 0.85
    status: MatchStatus = MatchStatus.MISSED
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def best_candidate(self) -> VisionMatch | None:
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda candidate: candidate.confidence)

    def matched_candidate(self) -> VisionMatch | None:
        candidate = self.best_candidate()
        if candidate is None:
            return None
        if self.expected_anchor_id and candidate.anchor_id != self.expected_anchor_id:
            return None
        if candidate.confidence < self.threshold:
            return None
        return candidate

    def is_match(self) -> bool:
        return self.status == MatchStatus.MATCHED and self.matched_candidate() is not None

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_status = data.get("status", MatchStatus.MISSED.value)
        if isinstance(raw_status, MatchStatus):
            status = raw_status
        else:
            status = MatchStatus(str(raw_status))
        candidates = [
            VisionMatch(
                anchor_id=str(entry.get("anchor_id", "")),
                confidence=float(entry.get("confidence", 0.0)),
                bbox=tuple(entry.get("bbox", (0, 0, 0, 0))),
                source_image=str(entry.get("source_image", "")),
            )
            for entry in data.get("candidates", [])
        ]
        return cls(
            source_image=str(data.get("source_image", "")),
            candidates=candidates,
            expected_anchor_id=str(data.get("expected_anchor_id", "")),
            threshold=float(data.get("threshold", 0.85)),
            status=status,
            message=str(data.get("message", "")),
            metadata=dict(data.get("metadata", {})),
        )
