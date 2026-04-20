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


class CaptureArtifactKind(str, Enum):
    SCREENSHOT = "screenshot"
    CROP = "crop"
    ANNOTATION = "annotation"


class InspectionOverlayKind(str, Enum):
    CROP_REGION = "crop_region"
    EXPECTED_ANCHOR = "expected_anchor"
    MATCH_CANDIDATE = "match_candidate"
    MATCHED_ANCHOR = "matched_anchor"
    FAILURE_FOCUS = "failure_focus"
    CAPTURE_ARTIFACT = "capture_artifact"


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
class CropRegion:
    x: int
    y: int
    width: int
    height: int

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_value(cls, value: Any) -> Self | None:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(
                x=int(value.get("x", 0)),
                y=int(value.get("y", 0)),
                width=int(value.get("width", 0)),
                height=int(value.get("height", 0)),
            )
        if isinstance(value, (list, tuple)) and len(value) == 4:
            return cls(
                x=int(value[0]),
                y=int(value[1]),
                width=int(value[2]),
                height=int(value[3]),
            )
        raise ValueError(f"Unsupported crop region value: {value!r}")


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
class CalibrationOverrideResolution:
    anchor_id: str
    profile_id: str = ""
    base_confidence_threshold: float = 0.85
    effective_confidence_threshold: float = 0.85
    base_match_region: tuple[int, int, int, int] | None = None
    effective_match_region: tuple[int, int, int, int] | None = None
    capture_crop_region: CropRegion | None = None
    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: int = 0
    offset_y: int = 0
    override: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            anchor_id=str(data.get("anchor_id", "")),
            profile_id=str(data.get("profile_id", "")),
            base_confidence_threshold=float(data.get("base_confidence_threshold", 0.85)),
            effective_confidence_threshold=float(data.get("effective_confidence_threshold", 0.85)),
            base_match_region=tuple(data.get("base_match_region")) if data.get("base_match_region") else None,
            effective_match_region=tuple(data.get("effective_match_region")) if data.get("effective_match_region") else None,
            capture_crop_region=CropRegion.from_value(data.get("capture_crop_region")),
            scale_x=float(data.get("scale_x", 1.0)),
            scale_y=float(data.get("scale_y", 1.0)),
            offset_x=int(data.get("offset_x", 0)),
            offset_y=int(data.get("offset_y", 0)),
            override=dict(data.get("override", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class CaptureArtifact:
    artifact_id: str
    kind: CaptureArtifactKind
    image_path: str
    source_image: str = ""
    crop_region: CropRegion | None = None
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_kind = data.get("kind", CaptureArtifactKind.SCREENSHOT.value)
        if isinstance(raw_kind, CaptureArtifactKind):
            kind = raw_kind
        else:
            kind = CaptureArtifactKind(str(raw_kind))
        return cls(
            artifact_id=str(data.get("artifact_id", "")),
            kind=kind,
            image_path=str(data.get("image_path", "")),
            source_image=str(data.get("source_image", "")),
            crop_region=CropRegion.from_value(data.get("crop_region")),
            created_at=_parse_datetime(data.get("created_at")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class CaptureSession:
    session_id: str
    instance_id: str
    source_image: str
    selected_anchor_id: str = ""
    crop_region: CropRegion | None = None
    artifacts: list[CaptureArtifact] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    def to_json(self) -> str:
        return dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            session_id=str(data.get("session_id", "")),
            instance_id=str(data.get("instance_id", "")),
            source_image=str(data.get("source_image", "")),
            selected_anchor_id=str(data.get("selected_anchor_id", "")),
            crop_region=CropRegion.from_value(data.get("crop_region")),
            artifacts=[CaptureArtifact.from_dict(entry) for entry in data.get("artifacts", [])],
            created_at=_parse_datetime(data.get("created_at")),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls.from_dict(loads(payload))

    def append_artifact(self, artifact: CaptureArtifact) -> None:
        self.artifacts.append(artifact)


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
class InspectionOverlay:
    overlay_id: str
    kind: InspectionOverlayKind
    label: str
    region: CropRegion | None = None
    stroke_color: str = "#33c3ff"
    fill_color: str = ""
    stroke_style: str = "solid"
    line_width: int = 2
    is_selected: bool = False
    is_expected: bool = False
    is_match: bool = False
    is_warning: bool = False
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_kind = data.get("kind", InspectionOverlayKind.MATCH_CANDIDATE.value)
        if isinstance(raw_kind, InspectionOverlayKind):
            kind = raw_kind
        else:
            kind = InspectionOverlayKind(str(raw_kind))
        return cls(
            overlay_id=str(data.get("overlay_id", "")),
            kind=kind,
            label=str(data.get("label", "")),
            region=CropRegion.from_value(data.get("region")),
            stroke_color=str(data.get("stroke_color", "#33c3ff")),
            fill_color=str(data.get("fill_color", "")),
            stroke_style=str(data.get("stroke_style", "solid")),
            line_width=int(data.get("line_width", 2)),
            is_selected=bool(data.get("is_selected", False)),
            is_expected=bool(data.get("is_expected", False)),
            is_match=bool(data.get("is_match", False)),
            is_warning=bool(data.get("is_warning", False)),
            confidence=float(data.get("confidence")) if data.get("confidence") is not None else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class ImageInspectionState:
    inspection_id: str
    image_path: str
    source_image: str = ""
    selected_overlay_id: str = ""
    selected_overlay: InspectionOverlay | None = None
    overlays: list[InspectionOverlay] = field(default_factory=list)
    overlay_count: int = 0
    selected_overlay_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_selected_overlay = data.get("selected_overlay")
        if isinstance(raw_selected_overlay, InspectionOverlay):
            selected_overlay = raw_selected_overlay
        elif isinstance(raw_selected_overlay, dict):
            selected_overlay = InspectionOverlay.from_dict(raw_selected_overlay)
        else:
            selected_overlay = None
        return cls(
            inspection_id=str(data.get("inspection_id", "")),
            image_path=str(data.get("image_path", "")),
            source_image=str(data.get("source_image", "")),
            selected_overlay_id=str(data.get("selected_overlay_id", "")),
            selected_overlay=selected_overlay,
            overlays=[InspectionOverlay.from_dict(entry) for entry in data.get("overlays", [])],
            overlay_count=int(data.get("overlay_count", 0)),
            selected_overlay_summary=str(data.get("selected_overlay_summary", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class ReplayActionView:
    action_id: str
    label: str
    action_type: RecordingActionType
    occurred_at: datetime
    payload_summary: str = ""
    is_selected: bool = False
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
            label=str(data.get("label", "")),
            action_type=action_type,
            occurred_at=_parse_datetime(data.get("occurred_at")),
            payload_summary=str(data.get("payload_summary", "")),
            is_selected=bool(data.get("is_selected", False)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class ReplayViewerState:
    script_id: str
    script_name: str
    version: str = "0.1.0"
    total_actions: int = 0
    selected_action_id: str = ""
    actions: list[ReplayActionView] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            script_id=str(data.get("script_id", "")),
            script_name=str(data.get("script_name", "")),
            version=str(data.get("version", "0.1.0")),
            total_actions=int(data.get("total_actions", 0)),
            selected_action_id=str(data.get("selected_action_id", "")),
            actions=[ReplayActionView.from_dict(entry) for entry in data.get("actions", [])],
            metadata=dict(data.get("metadata", {})),
        )


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
        if self.expected_anchor_id:
            matching_candidates = [
                candidate for candidate in self.candidates if candidate.anchor_id == self.expected_anchor_id
            ]
            candidate = max(matching_candidates, key=lambda item: item.confidence, default=None)
        else:
            candidate = self.best_candidate()
        if candidate is None:
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


@dataclass(slots=True)
class FailureInspectionRecord:
    failure_id: str
    instance_id: str
    screenshot_path: str
    anchor_id: str = ""
    preview_image_path: str = ""
    match_result: TemplateMatchResult | None = None
    message: str = ""
    recorded_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_match_result = data.get("match_result")
        if isinstance(raw_match_result, TemplateMatchResult):
            match_result = raw_match_result
        elif isinstance(raw_match_result, dict):
            match_result = TemplateMatchResult.from_dict(raw_match_result)
        else:
            match_result = None
        return cls(
            failure_id=str(data.get("failure_id", "")),
            instance_id=str(data.get("instance_id", "")),
            screenshot_path=str(data.get("screenshot_path", "")),
            anchor_id=str(data.get("anchor_id", "")),
            preview_image_path=str(data.get("preview_image_path", "")),
            match_result=match_result,
            message=str(data.get("message", "")),
            recorded_at=_parse_datetime(data.get("recorded_at")),
            metadata=dict(data.get("metadata", {})),
        )

    def best_candidate(self) -> VisionMatch | None:
        if self.match_result is None:
            return None
        return self.match_result.best_candidate()
