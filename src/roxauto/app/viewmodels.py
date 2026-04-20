from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from roxauto.core.models import VisionMatch
from roxauto.vision import (
    AnchorRepository,
    CalibrationProfile,
    MatchStatus,
    ReplayScript,
    TemplateMatchResult,
)


@dataclass(slots=True)
class InstanceCardView:
    instance_id: str
    label: str
    adb_serial: str
    status: str
    last_seen_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConsoleSnapshot:
    adb_path: str
    instance_count: int
    packages: dict[str, bool]
    instances: list[InstanceCardView]

    @property
    def available_runtime_features(self) -> list[str]:
        enabled: list[str] = []
        for package_name, installed in self.packages.items():
            if installed:
                enabled.append(package_name)
        return enabled


@dataclass(slots=True)
class TemplateAnchorView:
    anchor_id: str
    label: str
    template_path: str
    confidence_threshold: float
    match_region: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    override_summary: str = ""


@dataclass(slots=True)
class PreviewPaneView:
    repository_id: str
    source_image: str
    selected_anchor_id: str
    match_status: str
    confidence: float
    message: str
    candidate_summaries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CalibrationPaneView:
    profile_id: str
    instance_id: str
    emulator_name: str
    scale_summary: str
    offset_summary: str
    crop_region: str
    anchor_rows: list[TemplateAnchorView] = field(default_factory=list)


@dataclass(slots=True)
class RecordingActionView:
    action_id: str
    action_type: str
    target: str
    payload_summary: str
    occurred_at: str


@dataclass(slots=True)
class RecordingPaneView:
    script_id: str
    name: str
    version: str
    action_count: int
    action_rows: list[RecordingActionView] = field(default_factory=list)


@dataclass(slots=True)
class AnchorInspectionView:
    repository_id: str
    display_name: str
    version: str
    anchor_rows: list[TemplateAnchorView] = field(default_factory=list)
    selected_anchor_id: str = ""
    selected_anchor_summary: str = ""


@dataclass(slots=True)
class FailureInspectionView:
    source_image: str
    status: str
    message: str
    best_candidate_summary: str
    candidate_summaries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VisionWorkspaceSnapshot:
    repository_root: str
    preview: PreviewPaneView
    calibration: CalibrationPaneView
    recording: RecordingPaneView
    anchors: AnchorInspectionView
    failure: FailureInspectionView


def _format_region(region: tuple[int, int, int, int] | None) -> str:
    if not region:
        return "n/a"
    return f"{region[0]},{region[1]},{region[2]},{region[3]}"


def _format_payload_summary(payload: dict[str, Any]) -> str:
    if not payload:
        return "{}"
    parts = [f"{key}={value!r}" for key, value in sorted(payload.items())]
    return ", ".join(parts)


def _format_match(match: VisionMatch) -> str:
    return f"{match.anchor_id} | confidence={match.confidence:.3f} | bbox={match.bbox} | source={match.source_image}"


def _anchor_view(repository: AnchorRepository | None, anchor_id: str, override_summary: str = "") -> TemplateAnchorView:
    if repository is None or not anchor_id:
        return TemplateAnchorView(
            anchor_id=anchor_id,
            label="",
            template_path="",
            confidence_threshold=0.0,
            match_region="n/a",
            override_summary=override_summary,
        )
    anchor = repository.get_anchor(anchor_id)
    return TemplateAnchorView(
        anchor_id=anchor.anchor_id,
        label=anchor.label,
        template_path=anchor.template_path,
        confidence_threshold=anchor.confidence_threshold,
        match_region=_format_region(anchor.match_region),
        tags=list(anchor.tags),
        description=anchor.description,
        override_summary=override_summary,
    )


def _default_selected_anchor_id(repository: AnchorRepository | None, match_result: TemplateMatchResult | None) -> str:
    if match_result and match_result.expected_anchor_id:
        return match_result.expected_anchor_id
    if repository is not None:
        anchors = repository.list_anchors()
        if anchors:
            return anchors[0].anchor_id
    return ""


def build_console_snapshot(report: dict[str, Any]) -> ConsoleSnapshot:
    adb = report.get("adb", {})
    packages = dict(report.get("packages", {}))
    instances = [
        InstanceCardView(
            instance_id=str(instance.get("instance_id", "")),
            label=str(instance.get("label", "")),
            adb_serial=str(instance.get("adb_serial", "")),
            status=str(instance.get("status", "")),
            last_seen_at=str(instance.get("last_seen_at", "")),
            metadata=dict(instance.get("metadata", {})),
        )
        for instance in report.get("instances", [])
    ]
    return ConsoleSnapshot(
        adb_path=str(adb.get("path") or "not found"),
        instance_count=int(adb.get("instances_found") or len(instances)),
        packages=packages,
        instances=instances,
    )


def build_vision_workspace_snapshot(
    *,
    repository: AnchorRepository | None = None,
    calibration_profile: CalibrationProfile | None = None,
    replay_script: ReplayScript | None = None,
    match_result: TemplateMatchResult | None = None,
    source_image: str = "",
    failure_message: str = "",
) -> VisionWorkspaceSnapshot:
    repository_root = str(repository.root) if repository is not None else ""
    anchors = repository.list_anchors() if repository is not None else []
    selected_anchor_id = _default_selected_anchor_id(repository, match_result)

    anchor_rows = [
        _anchor_view(
            repository,
            anchor.anchor_id,
            override_summary=(
                _format_payload_summary(calibration_profile.anchor_overrides.get(anchor.anchor_id, {}))
                if calibration_profile is not None
                else ""
            ),
        )
        for anchor in anchors
    ]

    if match_result is not None:
        best_candidate = match_result.best_candidate()
        candidate_summaries = [_format_match(candidate) for candidate in match_result.candidates]
        preview = PreviewPaneView(
            repository_id=repository.repository_id if repository is not None else "",
            source_image=match_result.source_image or source_image,
            selected_anchor_id=selected_anchor_id,
            match_status=match_result.status.value,
            confidence=best_candidate.confidence if best_candidate is not None else 0.0,
            message=match_result.message,
            candidate_summaries=candidate_summaries,
        )
        failure = FailureInspectionView(
            source_image=match_result.source_image or source_image,
            status=match_result.status.value,
            message=match_result.message or failure_message,
            best_candidate_summary=_format_match(best_candidate) if best_candidate is not None else "no candidate",
            candidate_summaries=candidate_summaries,
        )
    else:
        preview = PreviewPaneView(
            repository_id=repository.repository_id if repository is not None else "",
            source_image=source_image,
            selected_anchor_id=selected_anchor_id,
            match_status=MatchStatus.MISSED.value,
            confidence=0.0,
            message=failure_message or "Preview pipeline not connected yet.",
            candidate_summaries=[],
        )
        failure = FailureInspectionView(
            source_image=source_image,
            status=MatchStatus.MISSED.value,
            message=failure_message or "No failure snapshot available.",
            best_candidate_summary="no candidate",
            candidate_summaries=[],
        )

    calibration = CalibrationPaneView(
        profile_id=calibration_profile.profile_id if calibration_profile is not None else "default",
        instance_id=calibration_profile.instance_id if calibration_profile is not None else "",
        emulator_name=calibration_profile.emulator_name if calibration_profile is not None else "mumu",
        scale_summary=(
            f"{calibration_profile.scale_x:.2f} x {calibration_profile.scale_y:.2f}"
            if calibration_profile is not None
            else "1.00 x 1.00"
        ),
        offset_summary=(
            f"{calibration_profile.offset_x}, {calibration_profile.offset_y}"
            if calibration_profile is not None
            else "0, 0"
        ),
        crop_region=_format_region(calibration_profile.crop_region) if calibration_profile is not None else "n/a",
        anchor_rows=anchor_rows,
    )

    recording_actions: list[RecordingActionView] = []
    if replay_script is not None:
        recording_actions = [
            RecordingActionView(
                action_id=action.action_id,
                action_type=action.action_type.value,
                target=action.target,
                payload_summary=_format_payload_summary(action.payload),
                occurred_at=action.occurred_at.isoformat(),
            )
            for action in replay_script.actions
        ]
    recording = RecordingPaneView(
        script_id=replay_script.script_id if replay_script is not None else "sample.script",
        name=replay_script.name if replay_script is not None else "Sample recording",
        version=replay_script.version if replay_script is not None else "0.1.0",
        action_count=len(recording_actions),
        action_rows=recording_actions,
    )

    selected_anchor_summary = ""
    if repository is not None and selected_anchor_id:
        try:
            selected_anchor = repository.get_anchor(selected_anchor_id)
            override_summary = _format_payload_summary(
                calibration_profile.anchor_overrides.get(selected_anchor.anchor_id, {})
            ) if calibration_profile is not None else ""
            selected_anchor_summary = (
                f"{selected_anchor.label} | template={selected_anchor.template_path} | "
                f"threshold={selected_anchor.confidence_threshold:.2f} | "
                f"region={_format_region(selected_anchor.match_region)} | "
                f"override={override_summary or 'none'}"
            )
        except KeyError:
            selected_anchor_summary = "selected anchor not found"

    anchors_view = AnchorInspectionView(
        repository_id=repository.repository_id if repository is not None else "",
        display_name=repository.display_name if repository is not None else "No template repository loaded",
        version=repository.manifest.version if repository is not None else "0.0.0",
        anchor_rows=anchor_rows,
        selected_anchor_id=selected_anchor_id,
        selected_anchor_summary=selected_anchor_summary,
    )

    return VisionWorkspaceSnapshot(
        repository_root=repository_root,
        preview=preview,
        calibration=calibration,
        recording=recording,
        anchors=anchors_view,
        failure=failure,
    )
