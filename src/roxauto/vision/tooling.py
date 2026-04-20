from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from roxauto.core.serde import to_primitive
from roxauto.core.time import utc_now
from roxauto.vision.models import (
    CalibrationProfile,
    CaptureArtifact,
    CaptureArtifactKind,
    CaptureSession,
    CropRegion,
    FailureInspectionRecord,
    MatchStatus,
    ReplayScript,
    ReplayViewerState,
    TemplateMatchResult,
)
from roxauto.vision.repository import AnchorRepository
from roxauto.vision.services import build_replay_view
from roxauto.vision.validation import (
    TemplateRepositoryValidationReport,
    TemplateValidationIssue,
    validate_template_repository,
    validate_template_workspace,
)


@dataclass(slots=True)
class AnchorInspectionRow:
    anchor_id: str
    label: str
    template_path: str
    resolved_template_path: str
    asset_exists: bool
    confidence_threshold: float
    effective_confidence_threshold: float
    match_region: tuple[int, int, int, int] | None = None
    effective_match_region: tuple[int, int, int, int] | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    override: dict[str, Any] = field(default_factory=dict)
    issue_codes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class TemplateRepositoryCatalogEntry:
    repository_id: str
    display_name: str
    version: str
    repository_root: str
    anchor_count: int
    is_valid: bool
    error_count: int = 0
    warning_count: int = 0
    issues: list[TemplateValidationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class TemplateWorkspaceCatalog:
    templates_root: str
    repositories: list[TemplateRepositoryCatalogEntry] = field(default_factory=list)
    selected_repository_id: str = ""
    selected_repository: TemplateRepositoryCatalogEntry | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class CaptureArtifactView:
    artifact_id: str
    kind: CaptureArtifactKind
    image_path: str
    source_image: str = ""
    crop_region: CropRegion | None = None
    created_at: object = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class CaptureInspectorState:
    session_id: str
    instance_id: str
    source_image: str
    selected_anchor_id: str = ""
    crop_region: CropRegion | None = None
    artifact_count: int = 0
    selected_artifact_id: str = ""
    selected_artifact: CaptureArtifactView | None = None
    artifacts: list[CaptureArtifactView] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class MatchCandidateView:
    anchor_id: str
    confidence: float
    bbox: tuple[int, int, int, int]
    source_image: str
    is_expected: bool = False
    is_best: bool = False
    passed_threshold: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class MatchInspectorState:
    repository_id: str
    source_image: str
    expected_anchor_id: str = ""
    status: MatchStatus = MatchStatus.MISSED
    threshold: float = 0.85
    message: str = ""
    matched_candidate: MatchCandidateView | None = None
    best_candidate: MatchCandidateView | None = None
    candidates: list[MatchCandidateView] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class AnchorInspectorState:
    repository_id: str
    display_name: str
    version: str
    repository_root: str
    selected_anchor_id: str = ""
    selected_anchor: AnchorInspectionRow | None = None
    anchors: list[AnchorInspectionRow] = field(default_factory=list)
    issues: list[TemplateValidationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class CalibrationInspectorState:
    profile_id: str
    instance_id: str
    emulator_name: str
    scale_x: float
    scale_y: float
    offset_x: int
    offset_y: int
    crop_region: CropRegion | None = None
    selected_anchor_id: str = ""
    selected_anchor: AnchorInspectionRow | None = None
    anchors: list[AnchorInspectionRow] = field(default_factory=list)
    capture_session_id: str = ""
    artifact_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class FailureInspectorState:
    failure_id: str
    instance_id: str
    screenshot_path: str
    preview_image_path: str = ""
    anchor_id: str = ""
    status: MatchStatus = MatchStatus.MISSED
    message: str = ""
    selected_anchor: AnchorInspectionRow | None = None
    best_candidate: MatchCandidateView | None = None
    candidates: list[MatchCandidateView] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class VisionToolingState:
    workspace: TemplateWorkspaceCatalog
    match: MatchInspectorState
    anchors: AnchorInspectorState
    calibration: CalibrationInspectorState
    capture: CaptureInspectorState
    replay: ReplayViewerState
    failure: FailureInspectorState
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


def build_template_workspace_catalog(
    templates_root: Path | str,
    *,
    selected_repository_id: str = "",
) -> TemplateWorkspaceCatalog:
    validation = validate_template_workspace(templates_root)
    repositories_by_id = {
        repository.repository_id: repository
        for repository in AnchorRepository.discover(templates_root)
    }
    entries: list[TemplateRepositoryCatalogEntry] = []
    for report in validation.reports:
        resolved_repository_id = report.repository_id or Path(report.repository_root).name
        loaded_repository = repositories_by_id.get(resolved_repository_id)
        entries.append(
            TemplateRepositoryCatalogEntry(
                repository_id=resolved_repository_id,
                display_name=(
                    report.display_name
                    or (loaded_repository.display_name if loaded_repository is not None else "")
                    or resolved_repository_id
                ),
                version=loaded_repository.version if loaded_repository is not None else str(report.metadata.get("version", "")),
                repository_root=report.repository_root,
                anchor_count=report.anchor_count,
                is_valid=report.is_valid,
                error_count=report.error_count,
                warning_count=report.warning_count,
                issues=list(report.issues),
                metadata=dict(report.metadata),
            )
        )
    selected_entry = _select_repository_entry(entries, selected_repository_id)

    return TemplateWorkspaceCatalog(
        templates_root=str(templates_root),
        repositories=entries,
        selected_repository_id=selected_entry.repository_id if selected_entry is not None else "",
        selected_repository=selected_entry,
        metadata=dict(validation.metadata),
    )


def build_anchor_inspector(
    repository: AnchorRepository | None = None,
    *,
    validation_report: TemplateRepositoryValidationReport | None = None,
    calibration_profile: CalibrationProfile | None = None,
    selected_anchor_id: str = "",
) -> AnchorInspectorState:
    if repository is None:
        return AnchorInspectorState(
            repository_id="",
            display_name="",
            version="",
            repository_root="",
            issues=list(validation_report.issues) if validation_report is not None else [],
        )

    if validation_report is None:
        validation_report = validate_template_repository(repository)

    issue_map = _anchor_issue_map(validation_report.issues)
    rows = [
        _build_anchor_row(
            repository,
            anchor_id=anchor_id,
            calibration_profile=calibration_profile,
            issue_codes=issue_map.get(anchor_id, []),
        )
        for anchor_id in repository.list_anchor_ids()
    ]
    selected_row = _select_anchor_row(rows, selected_anchor_id)

    return AnchorInspectorState(
        repository_id=repository.repository_id,
        display_name=repository.display_name,
        version=repository.version,
        repository_root=str(repository.root),
        selected_anchor_id=selected_row.anchor_id if selected_row is not None else "",
        selected_anchor=selected_row,
        anchors=rows,
        issues=list(validation_report.issues),
        metadata={
            "anchor_count": len(rows),
            "error_count": validation_report.error_count,
            "warning_count": validation_report.warning_count,
        },
    )


def build_calibration_inspector(
    *,
    repository: AnchorRepository | None = None,
    calibration_profile: CalibrationProfile | None = None,
    capture_session: CaptureSession | None = None,
    validation_report: TemplateRepositoryValidationReport | None = None,
    selected_anchor_id: str = "",
) -> CalibrationInspectorState:
    anchor_state = build_anchor_inspector(
        repository,
        validation_report=validation_report,
        calibration_profile=calibration_profile,
        selected_anchor_id=selected_anchor_id or (capture_session.selected_anchor_id if capture_session else ""),
    )
    resolved_profile = calibration_profile or CalibrationProfile(profile_id="default")

    return CalibrationInspectorState(
        profile_id=resolved_profile.profile_id,
        instance_id=resolved_profile.instance_id,
        emulator_name=resolved_profile.emulator_name,
        scale_x=resolved_profile.scale_x,
        scale_y=resolved_profile.scale_y,
        offset_x=resolved_profile.offset_x,
        offset_y=resolved_profile.offset_y,
        crop_region=CropRegion.from_value(resolved_profile.crop_region),
        selected_anchor_id=anchor_state.selected_anchor_id,
        selected_anchor=anchor_state.selected_anchor,
        anchors=anchor_state.anchors,
        capture_session_id=capture_session.session_id if capture_session is not None else "",
        artifact_count=len(capture_session.artifacts) if capture_session is not None else 0,
        metadata=dict(resolved_profile.metadata),
    )


def build_capture_inspector(
    session: CaptureSession | None = None,
    *,
    selected_artifact_id: str = "",
) -> CaptureInspectorState:
    if session is None:
        return CaptureInspectorState(session_id="", instance_id="", source_image="")

    artifact_views = [_build_capture_artifact_view(artifact) for artifact in session.artifacts]
    selected_artifact = _select_artifact_view(artifact_views, selected_artifact_id)

    return CaptureInspectorState(
        session_id=session.session_id,
        instance_id=session.instance_id,
        source_image=session.source_image,
        selected_anchor_id=session.selected_anchor_id,
        crop_region=session.crop_region,
        artifact_count=len(artifact_views),
        selected_artifact_id=selected_artifact.artifact_id if selected_artifact is not None else "",
        selected_artifact=selected_artifact,
        artifacts=artifact_views,
        metadata=dict(session.metadata),
    )


def build_match_inspector(
    *,
    repository: AnchorRepository | None = None,
    match_result: TemplateMatchResult | None = None,
    source_image: str = "",
    message: str = "",
) -> MatchInspectorState:
    if match_result is None:
        return MatchInspectorState(
            repository_id=repository.repository_id if repository is not None else "",
            source_image=source_image,
            status=MatchStatus.MISSED,
            message=message or "Preview pipeline not connected yet.",
        )

    best_candidate = match_result.best_candidate()
    matched_candidate = match_result.matched_candidate()
    candidates = [
        MatchCandidateView(
            anchor_id=candidate.anchor_id,
            confidence=candidate.confidence,
            bbox=candidate.bbox,
            source_image=candidate.source_image,
            is_expected=bool(match_result.expected_anchor_id) and candidate.anchor_id == match_result.expected_anchor_id,
            is_best=best_candidate is not None
            and candidate.anchor_id == best_candidate.anchor_id
            and candidate.bbox == best_candidate.bbox,
            passed_threshold=candidate.confidence >= match_result.threshold,
        )
        for candidate in match_result.candidates
    ]

    return MatchInspectorState(
        repository_id=repository.repository_id if repository is not None else "",
        source_image=match_result.source_image or source_image,
        expected_anchor_id=match_result.expected_anchor_id,
        status=match_result.status,
        threshold=match_result.threshold,
        message=match_result.message or message,
        matched_candidate=_find_candidate_view(candidates, matched_candidate),
        best_candidate=_find_candidate_view(candidates, best_candidate),
        candidates=candidates,
        metadata=dict(match_result.metadata),
    )


def build_failure_inspector(
    failure_record: FailureInspectionRecord | None = None,
    *,
    repository: AnchorRepository | None = None,
    calibration_profile: CalibrationProfile | None = None,
    validation_report: TemplateRepositoryValidationReport | None = None,
    message: str = "",
) -> FailureInspectorState:
    if failure_record is None:
        return FailureInspectorState(
            failure_id="",
            instance_id="",
            screenshot_path="",
            status=MatchStatus.MISSED,
            message=message or "No failure snapshot available.",
        )

    match_state = build_match_inspector(
        repository=repository,
        match_result=failure_record.match_result,
        source_image=failure_record.screenshot_path,
        message=failure_record.message or message,
    )
    anchor_state = build_anchor_inspector(
        repository,
        validation_report=validation_report,
        calibration_profile=calibration_profile,
        selected_anchor_id=failure_record.anchor_id,
    )

    return FailureInspectorState(
        failure_id=failure_record.failure_id,
        instance_id=failure_record.instance_id,
        screenshot_path=failure_record.screenshot_path,
        preview_image_path=failure_record.preview_image_path,
        anchor_id=failure_record.anchor_id,
        status=match_state.status,
        message=failure_record.message or match_state.message or message,
        selected_anchor=anchor_state.selected_anchor,
        best_candidate=match_state.best_candidate,
        candidates=match_state.candidates,
        metadata=dict(failure_record.metadata),
    )


def build_vision_tooling_state(
    *,
    templates_root: Path | str | None = None,
    repository: AnchorRepository | None = None,
    calibration_profile: CalibrationProfile | None = None,
    capture_session: CaptureSession | None = None,
    replay_script: ReplayScript | None = None,
    match_result: TemplateMatchResult | None = None,
    failure_record: FailureInspectionRecord | None = None,
    validation_report: TemplateRepositoryValidationReport | None = None,
    selected_repository_id: str = "",
    selected_anchor_id: str = "",
    selected_action_id: str = "",
    selected_artifact_id: str = "",
    source_image: str = "",
    failure_message: str = "",
) -> VisionToolingState:
    workspace = _build_workspace_for_state(
        templates_root=templates_root,
        repository=repository,
        selected_repository_id=selected_repository_id,
    )
    repository = _resolve_repository_for_state(
        templates_root=templates_root,
        repository=repository,
        workspace=workspace,
    )
    if validation_report is None and repository is not None:
        validation_report = validate_template_repository(repository)

    replay = (
        build_replay_view(replay_script, selected_action_id=selected_action_id)
        if replay_script is not None
        else ReplayViewerState(
            script_id="",
            script_name="",
            version="0.1.0",
            total_actions=0,
            selected_action_id="",
            actions=[],
            metadata={},
        )
    )

    match_state = build_match_inspector(
        repository=repository,
        match_result=match_result,
        source_image=source_image,
        message=failure_message,
    )
    anchors = build_anchor_inspector(
        repository,
        validation_report=validation_report,
        calibration_profile=calibration_profile,
        selected_anchor_id=selected_anchor_id
        or match_state.expected_anchor_id
        or (capture_session.selected_anchor_id if capture_session is not None else ""),
    )
    calibration = build_calibration_inspector(
        repository=repository,
        calibration_profile=calibration_profile,
        capture_session=capture_session,
        validation_report=validation_report,
        selected_anchor_id=anchors.selected_anchor_id,
    )
    capture = build_capture_inspector(
        capture_session,
        selected_artifact_id=selected_artifact_id,
    )
    failure = build_failure_inspector(
        failure_record,
        repository=repository,
        calibration_profile=calibration_profile,
        validation_report=validation_report,
        message=failure_message,
    )

    return VisionToolingState(
        workspace=workspace,
        match=match_state,
        anchors=anchors,
        calibration=calibration,
        capture=capture,
        replay=replay,
        failure=failure,
        metadata={
            "repository_id": repository.repository_id if repository is not None else "",
            "selected_action_id": replay.selected_action_id,
            "selected_artifact_id": capture.selected_artifact_id,
        },
    )


def _build_anchor_row(
    repository: AnchorRepository,
    *,
    anchor_id: str,
    calibration_profile: CalibrationProfile | None = None,
    issue_codes: list[str] | None = None,
) -> AnchorInspectionRow:
    anchor = repository.get_anchor(anchor_id)
    override = _anchor_override(calibration_profile, anchor_id)
    effective_threshold = _effective_confidence_threshold(anchor.confidence_threshold, override)
    effective_match_region = _effective_match_region(anchor.match_region, override)
    resolved_path = repository.resolve_asset_path(anchor_id)

    return AnchorInspectionRow(
        anchor_id=anchor.anchor_id,
        label=anchor.label,
        template_path=anchor.template_path,
        resolved_template_path=str(resolved_path),
        asset_exists=resolved_path.exists(),
        confidence_threshold=anchor.confidence_threshold,
        effective_confidence_threshold=effective_threshold,
        match_region=anchor.match_region,
        effective_match_region=effective_match_region,
        description=anchor.description,
        tags=list(anchor.tags),
        override=override,
        issue_codes=list(issue_codes or []),
        metadata=dict(anchor.metadata),
    )


def _anchor_issue_map(
    issues: list[TemplateValidationIssue],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for issue in issues:
        if not issue.anchor_id:
            continue
        result.setdefault(issue.anchor_id, []).append(issue.code)
    return result


def _build_capture_artifact_view(artifact: CaptureArtifact) -> CaptureArtifactView:
    return CaptureArtifactView(
        artifact_id=artifact.artifact_id,
        kind=artifact.kind,
        image_path=artifact.image_path,
        source_image=artifact.source_image,
        crop_region=artifact.crop_region,
        created_at=artifact.created_at,
        metadata=dict(artifact.metadata),
    )


def _build_workspace_for_state(
    *,
    templates_root: Path | str | None,
    repository: AnchorRepository | None,
    selected_repository_id: str,
) -> TemplateWorkspaceCatalog:
    if templates_root is not None:
        return build_template_workspace_catalog(
            templates_root,
            selected_repository_id=selected_repository_id or (repository.repository_id if repository is not None else ""),
        )

    if repository is None:
        return TemplateWorkspaceCatalog(templates_root="", repositories=[], selected_repository_id="")

    entry = TemplateRepositoryCatalogEntry(
        repository_id=repository.repository_id,
        display_name=repository.display_name,
        version=repository.version,
        repository_root=str(repository.root),
        anchor_count=len(repository.list_anchors()),
        is_valid=True,
        metadata={"manifest_path": str(repository.manifest_path)},
    )
    return TemplateWorkspaceCatalog(
        templates_root=str(repository.root.parent),
        repositories=[entry],
        selected_repository_id=repository.repository_id,
        selected_repository=entry,
    )


def _resolve_repository_for_state(
    *,
    templates_root: Path | str | None,
    repository: AnchorRepository | None,
    workspace: TemplateWorkspaceCatalog,
) -> AnchorRepository | None:
    if repository is not None:
        return repository
    if templates_root is None:
        return None

    selected_entry = workspace.selected_repository
    if selected_entry is None or not selected_entry.is_valid:
        return None

    for candidate in AnchorRepository.discover(templates_root):
        if candidate.repository_id == selected_entry.repository_id:
            return candidate
    return None


def _effective_confidence_threshold(
    default_threshold: float,
    override: dict[str, Any],
) -> float:
    raw_value = override.get("confidence_threshold")
    if raw_value is None:
        return default_threshold
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default_threshold


def _effective_match_region(
    match_region: tuple[int, int, int, int] | None,
    override: dict[str, Any],
) -> tuple[int, int, int, int] | None:
    if "match_region" not in override:
        return match_region
    region = CropRegion.from_value(override.get("match_region"))
    return region.to_tuple() if region is not None else match_region


def _anchor_override(
    calibration_profile: CalibrationProfile | None,
    anchor_id: str,
) -> dict[str, Any]:
    if calibration_profile is None:
        return {}
    return dict(calibration_profile.anchor_overrides.get(anchor_id, {}))


def _select_repository_entry(
    entries: list[TemplateRepositoryCatalogEntry],
    selected_repository_id: str,
) -> TemplateRepositoryCatalogEntry | None:
    for entry in entries:
        if entry.repository_id == selected_repository_id:
            return entry
    for entry in entries:
        if entry.is_valid:
            return entry
    return entries[0] if entries else None


def _select_anchor_row(
    rows: list[AnchorInspectionRow],
    selected_anchor_id: str,
) -> AnchorInspectionRow | None:
    for row in rows:
        if row.anchor_id == selected_anchor_id:
            return row
    return rows[0] if rows else None


def _select_artifact_view(
    artifacts: list[CaptureArtifactView],
    selected_artifact_id: str,
) -> CaptureArtifactView | None:
    for artifact in artifacts:
        if artifact.artifact_id == selected_artifact_id:
            return artifact
    return artifacts[0] if artifacts else None


def _find_candidate_view(
    candidates: list[MatchCandidateView],
    match_candidate: Any,
) -> MatchCandidateView | None:
    if match_candidate is None:
        return None
    for candidate in candidates:
        if (
            candidate.anchor_id == match_candidate.anchor_id
            and candidate.bbox == match_candidate.bbox
            and candidate.source_image == match_candidate.source_image
        ):
            return candidate
    return None
