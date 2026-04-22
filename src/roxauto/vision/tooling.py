from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from roxauto.core.models import VisionMatch
from roxauto.core.serde import to_primitive
from roxauto.core.time import utc_now
from roxauto.vision.models import (
    AnchorAssetProvenanceKind,
    AnchorCurationProfile,
    AnchorCurationReference,
    AnchorCurationStatus,
    CalibrationOverrideResolution,
    CalibrationProfile,
    CaptureArtifact,
    CaptureArtifactKind,
    CaptureSession,
    CropRegion,
    FailureInspectionRecord,
    ImageInspectionState,
    InspectionOverlay,
    InspectionOverlayKind,
    MatchStatus,
    ReplayScript,
    ReplayViewerState,
    TemplateMatchResult,
)
from roxauto.vision.repository import AnchorRepository
from roxauto.vision.services import (
    build_image_inspection_state,
    build_match_result,
    build_replay_view,
    resolve_calibration_override,
)
from roxauto.vision.validation import (
    VisionWorkspaceReadinessReport,
    TemplateRepositoryValidationReport,
    TemplateValidationIssue,
    build_vision_workspace_readiness_report,
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
    curation_status: AnchorCurationStatus | None = None
    curation_reference_count: int = 0
    provenance_kind: AnchorAssetProvenanceKind | None = None
    provenance_summary: str = ""
    curation_summary: str = ""
    curation_profile: AnchorCurationProfile | None = None
    calibration_resolution: CalibrationOverrideResolution | None = None
    overlay: InspectionOverlay | None = None
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
    repository_count: int = 0
    total_error_count: int = 0
    total_warning_count: int = 0
    valid_repository_ids: list[str] = field(default_factory=list)
    invalid_repository_ids: list[str] = field(default_factory=list)
    readiness: VisionWorkspaceReadinessReport | None = None
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
    file_exists: bool = False
    is_selected: bool = False
    inspection: ImageInspectionState | None = None
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
    available_artifact_ids: list[str] = field(default_factory=list)
    artifact_kind_counts: dict[str, int] = field(default_factory=dict)
    selected_artifact_summary: str = ""
    source_inspection: ImageInspectionState | None = None
    selected_artifact_inspection: ImageInspectionState | None = None
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
    expected_anchor_label: str = ""
    status: MatchStatus = MatchStatus.MISSED
    threshold: float = 0.85
    message: str = ""
    candidate_count: int = 0
    matched_candidate: MatchCandidateView | None = None
    best_candidate: MatchCandidateView | None = None
    candidates: list[MatchCandidateView] = field(default_factory=list)
    matched_candidate_summary: str = ""
    best_candidate_summary: str = ""
    calibration_resolution: CalibrationOverrideResolution | None = None
    inspection: ImageInspectionState | None = None
    selected_image_path: str = ""
    selected_source_image: str = ""
    selected_overlay: InspectionOverlay | None = None
    selected_overlay_summary: str = ""
    selected_region: CropRegion | None = None
    selected_region_summary: str = ""
    golden_catalog_path: str = ""
    selected_golden_id: str = ""
    selected_golden_image_path: str = ""
    selected_template_path: str = ""
    selected_reference_id: str = ""
    selected_reference_kind: str = ""
    selected_reference_image_path: str = ""
    reference_ids: list[str] = field(default_factory=list)
    reference_image_paths: list[str] = field(default_factory=list)
    live_reference_count: int = 0
    live_reference_ids: list[str] = field(default_factory=list)
    live_reference_image_paths: list[str] = field(default_factory=list)
    supporting_capture_count: int = 0
    supporting_capture_ids: list[str] = field(default_factory=list)
    supporting_capture_image_paths: list[str] = field(default_factory=list)
    supporting_capture_evidence_roles: list[str] = field(default_factory=list)
    supporting_capture_failure_cases: list[str] = field(default_factory=list)
    live_supporting_capture_count: int = 0
    live_supporting_capture_ids: list[str] = field(default_factory=list)
    curation_status: AnchorCurationStatus | None = None
    provenance_kind: AnchorAssetProvenanceKind | None = None
    provenance_summary: str = ""
    curation_summary: str = ""
    failure_case: str = ""
    failure_explanation: str = ""
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
    available_anchor_ids: list[str] = field(default_factory=list)
    selected_anchor_summary: str = ""
    selected_overlay: InspectionOverlay | None = None
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
    scale_summary: str = ""
    offset_summary: str = ""
    crop_summary: str = ""
    override_count: int = 0
    selected_resolution: CalibrationOverrideResolution | None = None
    resolutions: list[CalibrationOverrideResolution] = field(default_factory=list)
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
    candidate_count: int = 0
    best_candidate_summary: str = ""
    calibration_resolution: CalibrationOverrideResolution | None = None
    inspection: ImageInspectionState | None = None
    claim_rewards: ClaimRewardsInspectorState | None = None
    focus_check_id: str = ""
    focus_check_label: str = ""
    focus_stage: str = ""
    selected_threshold: float | None = None
    selected_image_path: str = ""
    selected_source_image: str = ""
    selected_overlay: InspectionOverlay | None = None
    selected_overlay_summary: str = ""
    selected_region: CropRegion | None = None
    selected_region_summary: str = ""
    selected_anchor_label: str = ""
    golden_catalog_path: str = ""
    selected_golden_id: str = ""
    selected_golden_image_path: str = ""
    selected_template_path: str = ""
    selected_reference_id: str = ""
    selected_reference_kind: str = ""
    selected_reference_image_path: str = ""
    reference_ids: list[str] = field(default_factory=list)
    reference_image_paths: list[str] = field(default_factory=list)
    live_reference_count: int = 0
    live_reference_ids: list[str] = field(default_factory=list)
    live_reference_image_paths: list[str] = field(default_factory=list)
    supporting_capture_count: int = 0
    supporting_capture_ids: list[str] = field(default_factory=list)
    supporting_capture_image_paths: list[str] = field(default_factory=list)
    supporting_capture_evidence_roles: list[str] = field(default_factory=list)
    supporting_capture_failure_cases: list[str] = field(default_factory=list)
    live_supporting_capture_count: int = 0
    live_supporting_capture_ids: list[str] = field(default_factory=list)
    curation_status: AnchorCurationStatus | None = None
    provenance_kind: AnchorAssetProvenanceKind | None = None
    provenance_summary: str = ""
    curation_summary: str = ""
    failure_case: str = ""
    failure_explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class ClaimRewardsCheckState:
    check_id: str
    label: str
    anchor_id: str
    anchor_label: str = ""
    stage: str = ""
    status: MatchStatus = MatchStatus.MISSED
    threshold: float = 0.85
    message: str = ""
    candidate_count: int = 0
    matched_candidate: MatchCandidateView | None = None
    best_candidate: MatchCandidateView | None = None
    candidates: list[MatchCandidateView] = field(default_factory=list)
    matched_candidate_summary: str = ""
    best_candidate_summary: str = ""
    calibration_resolution: CalibrationOverrideResolution | None = None
    inspection: ImageInspectionState | None = None
    is_selected: bool = False
    selected_image_path: str = ""
    selected_source_image: str = ""
    selected_overlay: InspectionOverlay | None = None
    selected_overlay_summary: str = ""
    selected_region: CropRegion | None = None
    selected_region_summary: str = ""
    golden_catalog_path: str = ""
    selected_golden_id: str = ""
    selected_golden_image_path: str = ""
    selected_template_path: str = ""
    selected_reference_id: str = ""
    selected_reference_kind: str = ""
    selected_reference_image_path: str = ""
    reference_ids: list[str] = field(default_factory=list)
    reference_image_paths: list[str] = field(default_factory=list)
    live_reference_count: int = 0
    live_reference_ids: list[str] = field(default_factory=list)
    live_reference_image_paths: list[str] = field(default_factory=list)
    supporting_capture_count: int = 0
    supporting_capture_ids: list[str] = field(default_factory=list)
    supporting_capture_image_paths: list[str] = field(default_factory=list)
    supporting_capture_evidence_roles: list[str] = field(default_factory=list)
    supporting_capture_failure_cases: list[str] = field(default_factory=list)
    live_supporting_capture_count: int = 0
    live_supporting_capture_ids: list[str] = field(default_factory=list)
    curation_status: AnchorCurationStatus | None = None
    provenance_kind: AnchorAssetProvenanceKind | None = None
    provenance_summary: str = ""
    curation_summary: str = ""
    failure_case: str = ""
    failure_explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class ClaimRewardsInspectorState:
    task_id: str
    current_check_id: str = ""
    selected_check_id: str = ""
    selected_check: ClaimRewardsCheckState | None = None
    checks: list[ClaimRewardsCheckState] = field(default_factory=list)
    available_check_ids: list[str] = field(default_factory=list)
    check_count: int = 0
    matched_check_count: int = 0
    missing_check_count: int = 0
    selected_anchor_id: str = ""
    selected_stage: str = ""
    selected_threshold: float | None = None
    selected_image_path: str = ""
    selected_source_image: str = ""
    selected_overlay: InspectionOverlay | None = None
    selected_overlay_summary: str = ""
    selected_region: CropRegion | None = None
    selected_region_summary: str = ""
    selected_anchor_label: str = ""
    golden_catalog_path: str = ""
    selected_golden_id: str = ""
    selected_golden_image_path: str = ""
    selected_template_path: str = ""
    selected_reference_id: str = ""
    selected_reference_kind: str = ""
    selected_reference_image_path: str = ""
    reference_ids: list[str] = field(default_factory=list)
    reference_image_paths: list[str] = field(default_factory=list)
    live_reference_count: int = 0
    live_reference_ids: list[str] = field(default_factory=list)
    live_reference_image_paths: list[str] = field(default_factory=list)
    supporting_capture_count: int = 0
    supporting_capture_ids: list[str] = field(default_factory=list)
    supporting_capture_image_paths: list[str] = field(default_factory=list)
    supporting_capture_evidence_roles: list[str] = field(default_factory=list)
    supporting_capture_failure_cases: list[str] = field(default_factory=list)
    live_supporting_capture_count: int = 0
    live_supporting_capture_ids: list[str] = field(default_factory=list)
    selected_curation_status: AnchorCurationStatus | None = None
    selected_provenance_kind: AnchorAssetProvenanceKind | None = None
    selected_provenance_summary: str = ""
    selected_curation_summary: str = ""
    selected_failure_case: str = ""
    selected_check_summary: str = ""
    workflow_summary: str = ""
    failure_explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))


@dataclass(slots=True)
class VisionToolingState:
    workspace: TemplateWorkspaceCatalog
    readiness: VisionWorkspaceReadinessReport | None
    preview: ImageInspectionState | None
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
    asset_inventory_path: Path | str | None = None,
) -> TemplateWorkspaceCatalog:
    validation = validate_template_workspace(templates_root)
    readiness = (
        build_vision_workspace_readiness_report(templates_root, asset_inventory_path)
        if asset_inventory_path is not None
        else None
    )
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
        repository_count=len(entries),
        total_error_count=validation.error_count,
        total_warning_count=validation.warning_count,
        valid_repository_ids=list(validation.valid_repository_ids),
        invalid_repository_ids=list(validation.invalid_repository_ids),
        readiness=readiness,
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
        available_anchor_ids=[row.anchor_id for row in rows],
        selected_anchor_summary=_anchor_summary(selected_row),
        selected_overlay=selected_row.overlay if selected_row is not None else None,
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
        scale_summary=f"{resolved_profile.scale_x:.2f} x {resolved_profile.scale_y:.2f}",
        offset_summary=f"{resolved_profile.offset_x}, {resolved_profile.offset_y}",
        crop_summary=_format_region(CropRegion.from_value(resolved_profile.crop_region)),
        override_count=len(resolved_profile.anchor_overrides),
        selected_resolution=selected_row.calibration_resolution if (selected_row := anchor_state.selected_anchor) is not None else None,
        resolutions=[
            row.calibration_resolution
            for row in anchor_state.anchors
            if row.calibration_resolution is not None
        ],
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
    if selected_artifact is not None:
        artifact_views = [
            _mark_artifact_selection(artifact, selected_artifact.artifact_id)
            for artifact in artifact_views
        ]
        selected_artifact = next(
            artifact for artifact in artifact_views if artifact.artifact_id == selected_artifact.artifact_id
        )

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
        available_artifact_ids=[artifact.artifact_id for artifact in artifact_views],
        artifact_kind_counts=_artifact_kind_counts(artifact_views),
        selected_artifact_summary=_capture_artifact_summary(selected_artifact),
        source_inspection=build_image_inspection_state(
            inspection_id=f"{session.session_id}:source",
            image_path=session.source_image,
            source_image=session.source_image,
            capture_session=session,
            selected_overlay_id=f"{session.session_id}:crop",
            metadata={"session_id": session.session_id, "kind": "capture_source"},
        ),
        selected_artifact_inspection=(
            selected_artifact.inspection if selected_artifact is not None else None
        ),
        metadata=dict(session.metadata),
    )


def build_match_inspector(
    *,
    repository: AnchorRepository | None = None,
    match_result: TemplateMatchResult | None = None,
    calibration_profile: CalibrationProfile | None = None,
    source_image: str = "",
    message: str = "",
) -> MatchInspectorState:
    expected_anchor_id = match_result.expected_anchor_id if match_result is not None else ""
    selected_anchor = _selected_anchor(repository, expected_anchor_id)
    curation = _selected_anchor_curation(
        repository=repository,
        expected_anchor_id=expected_anchor_id,
    )
    selected_template_path = _selected_template_path(repository, expected_anchor_id)
    golden_catalog_path = _golden_catalog_path(repository)
    selected_golden_id = _selected_golden_id(repository, expected_anchor_id)
    selected_golden_image_path = _selected_golden_image_path(repository, expected_anchor_id)
    selected_reference_id = _selected_reference_id(repository, expected_anchor_id)
    selected_reference_kind = _selected_reference_kind(repository, expected_anchor_id)
    selected_reference_image_path = _selected_reference_image_path(repository, expected_anchor_id)
    reference_ids = _reference_ids(repository, expected_anchor_id)
    reference_image_paths = _reference_image_paths(repository, expected_anchor_id)
    live_reference_ids = _live_reference_ids(repository, expected_anchor_id)
    live_reference_image_paths = _live_reference_image_paths(repository, expected_anchor_id)
    supporting_capture_ids = _supporting_capture_ids(repository, expected_anchor_id)
    supporting_capture_image_paths = _supporting_capture_image_paths(repository, expected_anchor_id)
    supporting_capture_evidence_roles = _supporting_capture_evidence_roles(repository, expected_anchor_id)
    supporting_capture_failure_cases = _supporting_capture_failure_cases(repository, expected_anchor_id)
    live_supporting_capture_ids = _live_supporting_capture_ids(repository, expected_anchor_id)
    calibration_resolution = _resolve_selected_calibration(
        repository=repository,
        calibration_profile=calibration_profile,
        expected_anchor_id=expected_anchor_id,
    )
    if match_result is None:
        inspection = build_image_inspection_state(
            inspection_id="preview:empty",
            image_path=source_image,
            source_image=source_image,
            calibration=calibration_resolution,
            metadata={"kind": "preview"},
        )
        return MatchInspectorState(
            repository_id=repository.repository_id if repository is not None else "",
            source_image=source_image,
            expected_anchor_label=selected_anchor.label if selected_anchor is not None else "",
            status=MatchStatus.MISSED,
            message=message or "Preview pipeline not connected yet.",
            calibration_resolution=calibration_resolution,
            inspection=inspection,
            selected_image_path=_inspection_image_path(inspection, fallback=source_image),
            selected_source_image=_inspection_source_image(inspection, fallback=source_image),
            selected_overlay=inspection.selected_overlay,
            selected_overlay_summary=inspection.selected_overlay_summary,
            selected_region=_selected_region(
                inspection,
                calibration_resolution=calibration_resolution,
                fallback=selected_anchor.match_region if selected_anchor is not None else None,
            ),
            selected_region_summary=_format_region(
                _selected_region(
                    inspection,
                    calibration_resolution=calibration_resolution,
                    fallback=selected_anchor.match_region if selected_anchor is not None else None,
                )
            ),
            golden_catalog_path=golden_catalog_path,
            selected_golden_id=selected_golden_id,
            selected_golden_image_path=selected_golden_image_path,
            selected_template_path=selected_template_path,
            selected_reference_id=selected_reference_id,
            selected_reference_kind=selected_reference_kind,
            selected_reference_image_path=selected_reference_image_path,
            reference_ids=reference_ids,
            reference_image_paths=reference_image_paths,
            live_reference_count=len(live_reference_ids),
            live_reference_ids=live_reference_ids,
            live_reference_image_paths=live_reference_image_paths,
            supporting_capture_count=len(supporting_capture_ids),
            supporting_capture_ids=supporting_capture_ids,
            supporting_capture_image_paths=supporting_capture_image_paths,
            supporting_capture_evidence_roles=supporting_capture_evidence_roles,
            supporting_capture_failure_cases=supporting_capture_failure_cases,
            live_supporting_capture_count=len(live_supporting_capture_ids),
            live_supporting_capture_ids=live_supporting_capture_ids,
            curation_status=curation.status if curation is not None else None,
            provenance_kind=curation.provenance_kind if curation is not None else None,
            provenance_summary=_provenance_summary(curation),
            curation_summary=_curation_summary(curation),
            failure_case=_failure_case(curation),
            failure_explanation=_match_failure_explanation(
                anchor_id=expected_anchor_id,
                anchor_label=selected_anchor.label if selected_anchor is not None else "",
                threshold=calibration_resolution.effective_confidence_threshold if calibration_resolution is not None else None,
                message=message or "Preview pipeline not connected yet.",
                status=MatchStatus.MISSED,
                best_candidate=None,
                candidate_count=0,
                image_path=_inspection_image_path(inspection, fallback=source_image),
                template_path=selected_template_path,
                reference_image_path=selected_reference_image_path,
                curation=curation,
            ),
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
    matched_candidate_view = _find_candidate_view(candidates, matched_candidate)
    best_candidate_view = _find_candidate_view(candidates, best_candidate)
    inspection = build_image_inspection_state(
        inspection_id=f"match:{match_result.expected_anchor_id or 'preview'}",
        image_path=match_result.source_image or source_image,
        source_image=source_image or match_result.source_image,
        match_result=match_result,
        calibration=calibration_resolution,
        metadata={"kind": "match_preview"},
    )

    return MatchInspectorState(
        repository_id=repository.repository_id if repository is not None else "",
        source_image=match_result.source_image or source_image,
        expected_anchor_id=match_result.expected_anchor_id,
        expected_anchor_label=selected_anchor.label if selected_anchor is not None else "",
        status=match_result.status,
        threshold=match_result.threshold,
        message=match_result.message or message,
        candidate_count=len(candidates),
        matched_candidate=matched_candidate_view,
        best_candidate=best_candidate_view,
        candidates=candidates,
        matched_candidate_summary=_candidate_summary(matched_candidate_view),
        best_candidate_summary=_candidate_summary(best_candidate_view),
        calibration_resolution=calibration_resolution,
        inspection=inspection,
        selected_image_path=_inspection_image_path(inspection, fallback=match_result.source_image or source_image),
        selected_source_image=_inspection_source_image(inspection, fallback=source_image or match_result.source_image),
        selected_overlay=inspection.selected_overlay,
        selected_overlay_summary=inspection.selected_overlay_summary,
        selected_region=_selected_region(
            inspection,
            calibration_resolution=calibration_resolution,
            fallback=selected_anchor.match_region if selected_anchor is not None else None,
        ),
        selected_region_summary=_format_region(
            _selected_region(
                inspection,
                calibration_resolution=calibration_resolution,
                fallback=selected_anchor.match_region if selected_anchor is not None else None,
            )
        ),
        golden_catalog_path=golden_catalog_path,
        selected_golden_id=selected_golden_id,
        selected_golden_image_path=selected_golden_image_path,
        selected_template_path=selected_template_path,
        selected_reference_id=selected_reference_id,
        selected_reference_kind=selected_reference_kind,
        selected_reference_image_path=selected_reference_image_path,
        reference_ids=reference_ids,
        reference_image_paths=reference_image_paths,
        live_reference_count=len(live_reference_ids),
        live_reference_ids=live_reference_ids,
        live_reference_image_paths=live_reference_image_paths,
        supporting_capture_count=len(supporting_capture_ids),
        supporting_capture_ids=supporting_capture_ids,
        supporting_capture_image_paths=supporting_capture_image_paths,
        supporting_capture_evidence_roles=supporting_capture_evidence_roles,
        supporting_capture_failure_cases=supporting_capture_failure_cases,
        live_supporting_capture_count=len(live_supporting_capture_ids),
        live_supporting_capture_ids=live_supporting_capture_ids,
        curation_status=curation.status if curation is not None else None,
        provenance_kind=curation.provenance_kind if curation is not None else None,
        provenance_summary=_provenance_summary(curation),
        curation_summary=_curation_summary(curation),
        failure_case=_failure_case(curation),
        failure_explanation=_match_failure_explanation(
            anchor_id=match_result.expected_anchor_id,
            anchor_label=selected_anchor.label if selected_anchor is not None else "",
            threshold=match_result.threshold,
            message=match_result.message or message,
            status=match_result.status,
            best_candidate=best_candidate_view,
            candidate_count=len(candidates),
            image_path=_inspection_image_path(inspection, fallback=match_result.source_image or source_image),
            template_path=selected_template_path,
            reference_image_path=selected_reference_image_path,
            curation=curation,
        ),
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
            curation_summary="",
            failure_explanation=message or "No failure snapshot available.",
        )

    match_state = build_match_inspector(
        repository=repository,
        match_result=failure_record.match_result,
        calibration_profile=calibration_profile,
        source_image=failure_record.screenshot_path,
        message=failure_record.message or message,
    )
    anchor_state = build_anchor_inspector(
        repository,
        validation_report=validation_report,
        calibration_profile=calibration_profile,
        selected_anchor_id=failure_record.anchor_id,
    )
    resolved_anchor_id = failure_record.anchor_id
    calibration_resolution = match_state.calibration_resolution or _resolve_selected_calibration(
        repository=repository,
        calibration_profile=calibration_profile,
        expected_anchor_id=resolved_anchor_id,
    )
    claim_rewards = _build_claim_rewards_inspector(
        failure_record=failure_record,
        repository=repository,
        calibration_profile=calibration_profile,
    )
    selected_claim_check = claim_rewards.selected_check if claim_rewards is not None else None
    failure_best_candidate = match_state.best_candidate
    failure_candidates = match_state.candidates
    failure_candidate_count = len(match_state.candidates)
    failure_best_summary = match_state.best_candidate_summary
    failure_status = match_state.status
    failure_inspection = build_image_inspection_state(
        inspection_id=f"failure:{failure_record.failure_id}",
        image_path=failure_record.preview_image_path or failure_record.screenshot_path,
        source_image=failure_record.screenshot_path,
        match_result=failure_record.match_result,
        calibration=calibration_resolution,
        metadata={"kind": "failure_inspection", "failure_id": failure_record.failure_id},
    )
    failure_message = failure_record.message or match_state.message or message
    focus_check_id = ""
    focus_check_label = ""
    focus_stage = ""
    selected_threshold = match_state.threshold if match_state.threshold else None
    selected_image_path = _inspection_image_path(
        failure_inspection,
        fallback=failure_record.preview_image_path or failure_record.screenshot_path,
    )
    selected_source_image = _inspection_source_image(
        failure_inspection,
        fallback=failure_record.screenshot_path,
    )
    selected_overlay = failure_inspection.selected_overlay
    selected_overlay_summary = failure_inspection.selected_overlay_summary
    selected_region = match_state.selected_region
    selected_region_summary = match_state.selected_region_summary
    selected_anchor_label = match_state.expected_anchor_label
    golden_catalog_path = match_state.golden_catalog_path
    selected_golden_id = match_state.selected_golden_id
    selected_golden_image_path = match_state.selected_golden_image_path
    selected_template_path = match_state.selected_template_path
    selected_reference_id = match_state.selected_reference_id
    selected_reference_kind = match_state.selected_reference_kind
    selected_reference_image_path = match_state.selected_reference_image_path
    reference_ids = list(match_state.reference_ids)
    reference_image_paths = list(match_state.reference_image_paths)
    live_reference_count = match_state.live_reference_count
    live_reference_ids = list(match_state.live_reference_ids)
    live_reference_image_paths = list(match_state.live_reference_image_paths)
    supporting_capture_count = match_state.supporting_capture_count
    supporting_capture_ids = list(match_state.supporting_capture_ids)
    supporting_capture_image_paths = list(match_state.supporting_capture_image_paths)
    supporting_capture_evidence_roles = list(match_state.supporting_capture_evidence_roles)
    supporting_capture_failure_cases = list(match_state.supporting_capture_failure_cases)
    live_supporting_capture_count = match_state.live_supporting_capture_count
    live_supporting_capture_ids = list(match_state.live_supporting_capture_ids)
    curation_status = match_state.curation_status
    provenance_kind = match_state.provenance_kind
    provenance_summary = match_state.provenance_summary
    curation_summary = match_state.curation_summary
    failure_case = match_state.failure_case
    failure_explanation = _match_failure_explanation(
        anchor_id=resolved_anchor_id,
        anchor_label=selected_anchor_label,
        threshold=selected_threshold,
        message=failure_message,
        status=failure_status,
        best_candidate=failure_best_candidate,
        candidate_count=failure_candidate_count,
        image_path=selected_image_path,
        template_path=selected_template_path,
        reference_image_path=selected_reference_image_path,
        curation=_selected_anchor_curation(repository=repository, expected_anchor_id=resolved_anchor_id),
    )

    if selected_claim_check is not None:
        focus_check_id = selected_claim_check.check_id
        focus_check_label = selected_claim_check.label
        focus_stage = selected_claim_check.stage
        if not resolved_anchor_id:
            resolved_anchor_id = selected_claim_check.anchor_id
        if calibration_resolution is None:
            calibration_resolution = selected_claim_check.calibration_resolution
        if (
            failure_record.match_result is None
            or not match_state.candidates
            or (failure_record.match_result.expected_anchor_id and not match_state.best_candidate)
        ):
            failure_status = selected_claim_check.status
            failure_best_candidate = selected_claim_check.best_candidate
            failure_candidates = list(selected_claim_check.candidates)
            if selected_claim_check.inspection is not None:
                failure_inspection = selected_claim_check.inspection
            failure_candidate_count = selected_claim_check.candidate_count
            failure_best_summary = selected_claim_check.best_candidate_summary
        if not failure_message:
            failure_message = selected_claim_check.message
        selected_threshold = selected_claim_check.threshold
        selected_image_path = selected_claim_check.selected_image_path
        selected_source_image = selected_claim_check.selected_source_image
        selected_overlay = selected_claim_check.selected_overlay
        selected_overlay_summary = selected_claim_check.selected_overlay_summary
        selected_region = selected_claim_check.selected_region
        selected_region_summary = selected_claim_check.selected_region_summary
        selected_anchor_label = selected_claim_check.anchor_label
        golden_catalog_path = selected_claim_check.golden_catalog_path
        selected_golden_id = selected_claim_check.selected_golden_id
        selected_golden_image_path = selected_claim_check.selected_golden_image_path
        selected_template_path = selected_claim_check.selected_template_path
        selected_reference_id = selected_claim_check.selected_reference_id
        selected_reference_kind = selected_claim_check.selected_reference_kind
        selected_reference_image_path = selected_claim_check.selected_reference_image_path
        reference_ids = list(selected_claim_check.reference_ids)
        reference_image_paths = list(selected_claim_check.reference_image_paths)
        live_reference_count = selected_claim_check.live_reference_count
        live_reference_ids = list(selected_claim_check.live_reference_ids)
        live_reference_image_paths = list(selected_claim_check.live_reference_image_paths)
        supporting_capture_count = selected_claim_check.supporting_capture_count
        supporting_capture_ids = list(selected_claim_check.supporting_capture_ids)
        supporting_capture_image_paths = list(selected_claim_check.supporting_capture_image_paths)
        supporting_capture_evidence_roles = list(selected_claim_check.supporting_capture_evidence_roles)
        supporting_capture_failure_cases = list(selected_claim_check.supporting_capture_failure_cases)
        live_supporting_capture_count = selected_claim_check.live_supporting_capture_count
        live_supporting_capture_ids = list(selected_claim_check.live_supporting_capture_ids)
        curation_status = selected_claim_check.curation_status
        provenance_kind = selected_claim_check.provenance_kind
        provenance_summary = selected_claim_check.provenance_summary
        curation_summary = selected_claim_check.curation_summary
        failure_case = selected_claim_check.failure_case
        failure_explanation = selected_claim_check.failure_explanation or failure_explanation

    return FailureInspectorState(
        failure_id=failure_record.failure_id,
        instance_id=failure_record.instance_id,
        screenshot_path=failure_record.screenshot_path,
        preview_image_path=failure_record.preview_image_path,
        anchor_id=resolved_anchor_id,
        status=failure_status,
        message=failure_message,
        selected_anchor=anchor_state.selected_anchor,
        best_candidate=failure_best_candidate,
        candidates=failure_candidates,
        candidate_count=failure_candidate_count,
        best_candidate_summary=failure_best_summary,
        calibration_resolution=calibration_resolution,
        inspection=failure_inspection,
        claim_rewards=claim_rewards,
        focus_check_id=focus_check_id,
        focus_check_label=focus_check_label,
        focus_stage=focus_stage,
        selected_threshold=selected_threshold,
        selected_image_path=selected_image_path,
        selected_source_image=selected_source_image,
        selected_overlay=selected_overlay,
        selected_overlay_summary=selected_overlay_summary,
        selected_region=selected_region,
        selected_region_summary=selected_region_summary,
        selected_anchor_label=selected_anchor_label,
        golden_catalog_path=golden_catalog_path,
        selected_golden_id=selected_golden_id,
        selected_golden_image_path=selected_golden_image_path,
        selected_template_path=selected_template_path,
        selected_reference_id=selected_reference_id,
        selected_reference_kind=selected_reference_kind,
        selected_reference_image_path=selected_reference_image_path,
        reference_ids=reference_ids,
        reference_image_paths=reference_image_paths,
        live_reference_count=live_reference_count,
        live_reference_ids=live_reference_ids,
        live_reference_image_paths=live_reference_image_paths,
        supporting_capture_count=supporting_capture_count,
        supporting_capture_ids=supporting_capture_ids,
        supporting_capture_image_paths=supporting_capture_image_paths,
        supporting_capture_evidence_roles=supporting_capture_evidence_roles,
        supporting_capture_failure_cases=supporting_capture_failure_cases,
        live_supporting_capture_count=live_supporting_capture_count,
        live_supporting_capture_ids=live_supporting_capture_ids,
        curation_status=curation_status,
        provenance_kind=provenance_kind,
        provenance_summary=provenance_summary,
        curation_summary=curation_summary,
        failure_case=failure_case,
        failure_explanation=failure_explanation,
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
    asset_inventory_path: Path | str | None = None,
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
        asset_inventory_path=asset_inventory_path,
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
        calibration_profile=calibration_profile,
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
        readiness=workspace.readiness,
        preview=match_state.inspection,
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
            "workspace_ready_blocking_count": workspace.readiness.blocking_count if workspace.readiness is not None else 0,
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
    curation = repository.get_anchor_curation(anchor_id)
    calibration_resolution = resolve_calibration_override(
        anchor=anchor,
        calibration_profile=calibration_profile,
    )
    override = dict(calibration_resolution.override)
    effective_threshold = calibration_resolution.effective_confidence_threshold
    effective_match_region = calibration_resolution.effective_match_region
    resolved_path = repository.resolve_asset_path(anchor_id)
    overlay = _overlay_for_anchor_row(anchor, calibration_resolution)

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
        curation_status=curation.status if curation is not None else None,
        curation_reference_count=curation.reference_count if curation is not None else 0,
        provenance_kind=curation.provenance_kind if curation is not None else None,
        provenance_summary=_provenance_summary(curation),
        curation_summary=_curation_summary(curation),
        curation_profile=curation,
        calibration_resolution=calibration_resolution,
        overlay=overlay,
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
        file_exists=_path_exists(artifact.image_path),
        inspection=build_image_inspection_state(
            inspection_id=f"artifact:{artifact.artifact_id}",
            image_path=artifact.image_path,
            source_image=artifact.source_image or artifact.image_path,
            selected_overlay_id=f"{artifact.artifact_id}:artifact",
            metadata={"artifact_id": artifact.artifact_id, "kind": artifact.kind.value},
        )
        if artifact.crop_region is None
        else build_image_inspection_state(
            inspection_id=f"artifact:{artifact.artifact_id}",
            image_path=artifact.image_path,
            source_image=artifact.source_image or artifact.image_path,
            capture_session=CaptureSession(
                session_id=f"artifact-session:{artifact.artifact_id}",
                instance_id="",
                source_image=artifact.image_path,
                crop_region=artifact.crop_region,
                metadata={"artifact_id": artifact.artifact_id},
            ),
            selected_overlay_id=f"artifact-session:{artifact.artifact_id}:crop",
            metadata={"artifact_id": artifact.artifact_id, "kind": artifact.kind.value},
        ),
        created_at=artifact.created_at,
        metadata=dict(artifact.metadata),
    )


def _build_workspace_for_state(
    *,
    templates_root: Path | str | None,
    repository: AnchorRepository | None,
    selected_repository_id: str,
    asset_inventory_path: Path | str | None,
) -> TemplateWorkspaceCatalog:
    if templates_root is not None:
        return build_template_workspace_catalog(
            templates_root,
            selected_repository_id=selected_repository_id or (repository.repository_id if repository is not None else ""),
            asset_inventory_path=asset_inventory_path,
        )

    if repository is None:
        return TemplateWorkspaceCatalog(
            templates_root="",
            repositories=[],
            selected_repository_id="",
            repository_count=0,
            total_error_count=0,
            total_warning_count=0,
            valid_repository_ids=[],
            invalid_repository_ids=[],
        )

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
        repository_count=1,
        total_error_count=0,
        total_warning_count=0,
        valid_repository_ids=[repository.repository_id],
        invalid_repository_ids=[],
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


def _format_region(region: CropRegion | tuple[int, int, int, int] | None) -> str:
    resolved_region = CropRegion.from_value(region)
    if resolved_region is None:
        return "n/a"
    x, y, width, height = resolved_region.to_tuple()
    return f"{x},{y},{width},{height}"


def _anchor_summary(anchor: AnchorInspectionRow | None) -> str:
    if anchor is None:
        return ""
    summary = (
        f"{anchor.label or anchor.anchor_id} | template={anchor.template_path} | "
        f"threshold={anchor.effective_confidence_threshold:.2f} | "
        f"region={_format_region(anchor.effective_match_region)} | "
        f"issues={','.join(anchor.issue_codes) or 'none'}"
    )
    if anchor.provenance_summary:
        summary += f" | provenance={anchor.provenance_summary}"
    if anchor.curation_summary:
        summary += f" | curation={anchor.curation_summary}"
    return summary


def _artifact_kind_counts(
    artifacts: list[CaptureArtifactView],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for artifact in artifacts:
        key = artifact.kind.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def _capture_artifact_summary(artifact: CaptureArtifactView | None) -> str:
    if artifact is None:
        return ""
    return (
        f"{artifact.kind.value} | path={artifact.image_path} | "
        f"crop={_format_region(artifact.crop_region)} | "
        f"exists={'yes' if artifact.file_exists else 'no'}"
    )


def _mark_artifact_selection(
    artifact: CaptureArtifactView,
    selected_artifact_id: str,
) -> CaptureArtifactView:
    return CaptureArtifactView(
        artifact_id=artifact.artifact_id,
        kind=artifact.kind,
        image_path=artifact.image_path,
        source_image=artifact.source_image,
        crop_region=artifact.crop_region,
        file_exists=artifact.file_exists,
        is_selected=artifact.artifact_id == selected_artifact_id,
        inspection=artifact.inspection,
        created_at=artifact.created_at,
        metadata=dict(artifact.metadata),
    )


def _candidate_summary(candidate: MatchCandidateView | None) -> str:
    if candidate is None:
        return "no candidate"
    return (
        f"{candidate.anchor_id} | confidence={candidate.confidence:.3f} | "
        f"bbox={candidate.bbox} | source={candidate.source_image}"
    )


def _inspection_image_path(inspection: ImageInspectionState | None, *, fallback: str = "") -> str:
    if inspection is None:
        return fallback
    return inspection.image_path or fallback


def _inspection_source_image(inspection: ImageInspectionState | None, *, fallback: str = "") -> str:
    if inspection is None:
        return fallback
    return inspection.source_image or fallback


def _selected_region(
    inspection: ImageInspectionState | None,
    *,
    calibration_resolution: CalibrationOverrideResolution | None = None,
    fallback: CropRegion | tuple[int, int, int, int] | None = None,
) -> CropRegion | None:
    if inspection is not None and inspection.selected_overlay is not None:
        overlay_region = CropRegion.from_value(inspection.selected_overlay.region)
        if overlay_region is not None:
            return overlay_region
    if calibration_resolution is not None:
        calibration_region = CropRegion.from_value(calibration_resolution.effective_match_region)
        if calibration_region is not None:
            return calibration_region
    return CropRegion.from_value(fallback)


def _selected_anchor_curation(
    *,
    repository: AnchorRepository | None,
    expected_anchor_id: str,
) -> AnchorCurationProfile | None:
    if repository is None or not expected_anchor_id or not repository.has_anchor(expected_anchor_id):
        return None
    return repository.get_anchor_curation(expected_anchor_id)


def _selected_anchor(repository: AnchorRepository | None, anchor_id: str):
    if repository is None or not anchor_id or not repository.has_anchor(anchor_id):
        return None
    return repository.get_anchor(anchor_id)


def _selected_template_path(repository: AnchorRepository | None, anchor_id: str) -> str:
    anchor = _selected_anchor(repository, anchor_id)
    if anchor is None:
        return ""
    return str(repository.resolve_asset_path(anchor_id))


def _selected_reference(
    repository: AnchorRepository | None,
    anchor_id: str,
) -> AnchorCurationReference | None:
    if repository is None or not anchor_id or not repository.has_anchor(anchor_id):
        return None
    return repository.get_primary_curation_reference(anchor_id)


def _selected_reference_id(repository: AnchorRepository | None, anchor_id: str) -> str:
    reference = _selected_reference(repository, anchor_id)
    return str(reference.reference_id) if reference is not None else ""


def _selected_reference_kind(repository: AnchorRepository | None, anchor_id: str) -> str:
    reference = _selected_reference(repository, anchor_id)
    return str(reference.kind) if reference is not None else ""


def _selected_reference_image_path(repository: AnchorRepository | None, anchor_id: str) -> str:
    if repository is None or not anchor_id or not repository.has_anchor(anchor_id):
        return ""
    resolved_path = repository.resolve_curation_reference_path(anchor_id)
    return str(resolved_path) if resolved_path is not None else ""


def _golden_catalog_path(repository: AnchorRepository | None) -> str:
    if repository is None:
        return ""
    resolved_path = repository.resolve_claim_rewards_catalog_path()
    return str(resolved_path) if resolved_path is not None else ""


def _selected_golden_id(repository: AnchorRepository | None, anchor_id: str) -> str:
    if repository is None or not anchor_id:
        return ""
    golden = repository.get_claim_rewards_anchor_golden(anchor_id)
    return golden.golden_id if golden is not None else ""


def _selected_golden_image_path(repository: AnchorRepository | None, anchor_id: str) -> str:
    if repository is None or not anchor_id:
        return ""
    resolved_path = repository.resolve_claim_rewards_golden_image_path(anchor_id)
    return str(resolved_path) if resolved_path is not None else ""


def _reference_ids(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    if repository is None or not anchor_id or not repository.has_anchor(anchor_id):
        return []
    return [
        str(reference.reference_id)
        for reference in repository.list_curation_references(anchor_id)
        if str(reference.reference_id)
    ]


def _reference_image_paths(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    if repository is None or not anchor_id or not repository.has_anchor(anchor_id):
        return []
    return [str(path) for path in repository.resolve_curation_reference_paths(anchor_id)]


def _is_live_reference(reference: AnchorCurationReference | None) -> bool:
    if reference is None:
        return False
    kind = str(reference.kind or "").strip().lower()
    if "live" in kind:
        return True
    return bool(reference.metadata.get("live_capture", False))


def _live_reference_ids(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    if repository is None or not anchor_id or not repository.has_anchor(anchor_id):
        return []
    return [
        str(reference.reference_id)
        for reference in repository.list_curation_references(anchor_id)
        if str(reference.reference_id) and _is_live_reference(reference)
    ]


def _live_reference_image_paths(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    if repository is None or not anchor_id or not repository.has_anchor(anchor_id):
        return []
    return [
        str(repository.resolve_repository_path(reference.image_path))
        for reference in repository.list_curation_references(anchor_id)
        if reference.image_path and _is_live_reference(reference)
    ]


def _supporting_captures(repository: AnchorRepository | None, anchor_id: str) -> list[Any]:
    if repository is None or not anchor_id:
        return []
    return list(repository.list_claim_rewards_supporting_captures(anchor_id))


def _supporting_capture_ids(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    return [capture.capture_id for capture in _supporting_captures(repository, anchor_id) if capture.capture_id]


def _supporting_capture_image_paths(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    if repository is None or not anchor_id:
        return []
    return [
        str(path)
        for path in repository.resolve_claim_rewards_supporting_capture_paths(anchor_id)
    ]


def _supporting_capture_evidence_roles(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    return [
        capture.evidence_role
        for capture in _supporting_captures(repository, anchor_id)
        if capture.evidence_role
    ]


def _supporting_capture_failure_cases(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    return [
        capture.failure_case
        for capture in _supporting_captures(repository, anchor_id)
        if capture.failure_case
    ]


def _live_supporting_capture_ids(repository: AnchorRepository | None, anchor_id: str) -> list[str]:
    return [
        capture.capture_id
        for capture in _supporting_captures(repository, anchor_id)
        if capture.capture_id and bool(capture.live_capture)
    ]


def _curation_summary(curation: AnchorCurationProfile | None) -> str:
    if curation is None:
        return ""
    parts = [curation.status.value]
    if curation.provenance_kind is not None:
        parts.append(f"provenance={curation.provenance_kind.value}")
    if curation.provenance is not None and curation.provenance.locale:
        parts.append(f"locale={curation.provenance.locale}")
    if curation.provenance is not None and curation.provenance.source:
        parts.append(f"source={curation.provenance.source}")
    if curation.scene_id:
        parts.append(f"scene={curation.scene_id}")
    if curation.variant_id:
        parts.append(f"variant={curation.variant_id}")
    parts.append(f"refs={curation.reference_count}")
    parts.append(f"live_refs={len([reference for reference in curation.references if _is_live_reference(reference)])}")
    if curation.intent_id:
        parts.append(f"intent={curation.intent_id}")
    return " | ".join(parts)


def _provenance_summary(curation: AnchorCurationProfile | None) -> str:
    if curation is None:
        return ""
    return curation.provenance_summary


def _failure_case(curation: AnchorCurationProfile | None) -> str:
    if curation is None:
        return ""
    return str(curation.metadata.get("failure_case", "")).strip()


def _append_curation_note(message: str, curation: AnchorCurationProfile | None) -> str:
    normalized_message = message.strip()
    if curation is None:
        return normalized_message
    note = ""
    if curation.status != AnchorCurationStatus.CURATED:
        note = f"Template curation status: {_curation_summary(curation)}."
    elif curation.provenance_kind == AnchorAssetProvenanceKind.CURATED_STAND_IN:
        note = (
            "Template baseline is a curated stand-in"
            + (f" ({_provenance_summary(curation)})" if _provenance_summary(curation) else "")
            + "."
        )
    if not note:
        return normalized_message
    if not normalized_message:
        return note
    if note.lower() in normalized_message.lower():
        return normalized_message
    return f"{normalized_message} {note}".strip()


def _append_template_context(
    message: str,
    *,
    template_path: str,
    reference_image_path: str,
) -> str:
    normalized_message = message.strip()
    suffix_parts: list[str] = []
    if template_path:
        suffix_parts.append(f"template={template_path}")
    if reference_image_path:
        suffix_parts.append(f"reference={reference_image_path}")
    if not suffix_parts:
        return normalized_message
    suffix = " | ".join(suffix_parts)
    if suffix in normalized_message:
        return normalized_message
    return f"{normalized_message} [{suffix}]".strip()


def _match_failure_explanation(
    *,
    anchor_id: str,
    anchor_label: str,
    threshold: float | None,
    message: str,
    status: MatchStatus,
    best_candidate: MatchCandidateView | None,
    candidate_count: int,
    image_path: str,
    template_path: str,
    reference_image_path: str,
    curation: AnchorCurationProfile | None,
) -> str:
    normalized_anchor_id = anchor_id or "anchor"
    normalized_anchor_label = anchor_label or normalized_anchor_id
    normalized_message = message.strip()
    if status == MatchStatus.MATCHED:
        if normalized_message:
            return _append_curation_note(normalized_message, curation)
        if best_candidate is not None:
            base = (
                f"{normalized_anchor_label} ({normalized_anchor_id}) matched on {image_path or 'current image'} "
                f"at {best_candidate.confidence:.3f} with threshold {threshold:.3f}."
            ) if threshold is not None else f"{normalized_anchor_id} matched at {best_candidate.confidence:.3f}."
        else:
            base = f"{normalized_anchor_label} ({normalized_anchor_id}) matched."
        return _append_curation_note(
            _append_template_context(base, template_path=template_path, reference_image_path=reference_image_path),
            curation,
        )

    detail = ""
    if best_candidate is None and candidate_count == 0:
        detail = (
            f"No candidates were found for {normalized_anchor_label} ({normalized_anchor_id}) on "
            f"{image_path or 'current image'}"
            + (f" at threshold {threshold:.3f}." if threshold is not None else ".")
        )
    elif best_candidate is not None and best_candidate.anchor_id != normalized_anchor_id:
        detail = (
            f"Expected {normalized_anchor_label} ({normalized_anchor_id}) on {image_path or 'current image'}, "
            f"but best candidate was "
            f"{best_candidate.anchor_id} at {best_candidate.confidence:.3f}."
        )
    elif best_candidate is not None and threshold is not None and not best_candidate.passed_threshold:
        detail = (
            f"{normalized_anchor_label} ({normalized_anchor_id}) on {image_path or 'current image'} "
            f"peaked at {best_candidate.confidence:.3f}, "
            f"below threshold {threshold:.3f}."
        )
    elif best_candidate is not None:
        detail = (
            f"{normalized_anchor_label} ({normalized_anchor_id}) on {image_path or 'current image'} "
            "did not produce a passing match."
        )
    else:
        detail = f"{normalized_anchor_label} ({normalized_anchor_id}) did not match."

    if not normalized_message:
        return _append_curation_note(
            _append_template_context(detail, template_path=template_path, reference_image_path=reference_image_path),
            curation,
        )
    if detail.lower() in normalized_message.lower():
        return _append_curation_note(
            _append_template_context(normalized_message, template_path=template_path, reference_image_path=reference_image_path),
            curation,
        )
    return _append_curation_note(
        _append_template_context(
            f"{normalized_message} {detail}".strip(),
            template_path=template_path,
            reference_image_path=reference_image_path,
        ),
        curation,
    )


def _claim_rewards_check_summary(check: ClaimRewardsCheckState | None) -> str:
    if check is None:
        return ""
    summary = (
        f"{check.label} | anchor={check.anchor_id} | threshold={check.threshold:.3f} | "
        f"image={check.selected_image_path or 'n/a'} | message={check.message or 'n/a'}"
    )
    if check.selected_region_summary:
        summary += f" | region={check.selected_region_summary}"
    if check.selected_golden_id:
        summary += f" | golden_id={check.selected_golden_id}"
    if check.selected_reference_id:
        summary += f" | reference_id={check.selected_reference_id}"
    if check.live_reference_count:
        summary += f" | live_refs={check.live_reference_count}"
    if check.supporting_capture_count:
        summary += f" | supporting={check.supporting_capture_count}"
    if check.provenance_summary:
        summary += f" | provenance={check.provenance_summary}"
    if check.curation_summary:
        summary += f" | curation={check.curation_summary}"
    if check.failure_case:
        summary += f" | failure_case={check.failure_case}"
    return summary


def _claim_rewards_workflow_summary(checks: list[ClaimRewardsCheckState], *, current_check_id: str) -> str:
    if not checks:
        return ""
    parts = [f"current={current_check_id or checks[0].check_id}"]
    parts.append(f"matched={sum(1 for check in checks if check.status == MatchStatus.MATCHED)}")
    parts.append(f"missing={sum(1 for check in checks if check.status != MatchStatus.MATCHED)}")
    return " | ".join(parts)


def _mark_claim_rewards_check_selection(
    check: ClaimRewardsCheckState,
    selected_check_id: str,
) -> ClaimRewardsCheckState:
    return ClaimRewardsCheckState(
        check_id=check.check_id,
        label=check.label,
        anchor_id=check.anchor_id,
        anchor_label=check.anchor_label,
        stage=check.stage,
        status=check.status,
        threshold=check.threshold,
        message=check.message,
        candidate_count=check.candidate_count,
        matched_candidate=check.matched_candidate,
        best_candidate=check.best_candidate,
        candidates=list(check.candidates),
        matched_candidate_summary=check.matched_candidate_summary,
        best_candidate_summary=check.best_candidate_summary,
        calibration_resolution=check.calibration_resolution,
        inspection=check.inspection,
        is_selected=check.check_id == selected_check_id,
        selected_image_path=check.selected_image_path,
        selected_source_image=check.selected_source_image,
        selected_overlay=check.selected_overlay,
        selected_overlay_summary=check.selected_overlay_summary,
        selected_region=check.selected_region,
        selected_region_summary=check.selected_region_summary,
        golden_catalog_path=check.golden_catalog_path,
        selected_golden_id=check.selected_golden_id,
        selected_golden_image_path=check.selected_golden_image_path,
        selected_template_path=check.selected_template_path,
        selected_reference_id=check.selected_reference_id,
        selected_reference_kind=check.selected_reference_kind,
        selected_reference_image_path=check.selected_reference_image_path,
        reference_ids=list(check.reference_ids),
        reference_image_paths=list(check.reference_image_paths),
        live_reference_count=check.live_reference_count,
        live_reference_ids=list(check.live_reference_ids),
        live_reference_image_paths=list(check.live_reference_image_paths),
        supporting_capture_count=check.supporting_capture_count,
        supporting_capture_ids=list(check.supporting_capture_ids),
        supporting_capture_image_paths=list(check.supporting_capture_image_paths),
        supporting_capture_evidence_roles=list(check.supporting_capture_evidence_roles),
        supporting_capture_failure_cases=list(check.supporting_capture_failure_cases),
        live_supporting_capture_count=check.live_supporting_capture_count,
        live_supporting_capture_ids=list(check.live_supporting_capture_ids),
        curation_status=check.curation_status,
        provenance_kind=check.provenance_kind,
        provenance_summary=check.provenance_summary,
        curation_summary=check.curation_summary,
        failure_case=check.failure_case,
        failure_explanation=check.failure_explanation,
        metadata=dict(check.metadata),
    )


def _build_claim_rewards_inspector(
    *,
    failure_record: FailureInspectionRecord,
    repository: AnchorRepository | None,
    calibration_profile: CalibrationProfile | None,
) -> ClaimRewardsInspectorState | None:
    if repository is None or repository.repository_id != "daily_ui":
        return None

    task_support = _claim_rewards_task_support(repository)
    if not task_support:
        return None

    claim_metadata = failure_record.metadata.get("claim_rewards")
    if not isinstance(claim_metadata, dict):
        return None

    current_check_id = str(claim_metadata.get("current_check_id") or "")
    selected_check_id = str(claim_metadata.get("selected_check_id") or current_check_id)
    check_payloads = dict(claim_metadata.get("checks", {})) if isinstance(claim_metadata.get("checks", {}), dict) else {}
    checks: list[ClaimRewardsCheckState] = []

    for check_id in [str(item) for item in task_support.get("required_anchor_roles", []) if str(item)]:
        anchor = _find_task_anchor_by_role(repository, task_id="daily_ui.claim_rewards", role=check_id)
        if anchor is None:
            continue
        payload = check_payloads.get(check_id, {})
        if not isinstance(payload, dict):
            payload = {}
        stage = str(payload.get("stage") or anchor.metadata.get("stage") or "")
        golden_catalog_path = _golden_catalog_path(repository)
        selected_golden_id = _selected_golden_id(repository, anchor.anchor_id)
        selected_golden_image_path = _selected_golden_image_path(repository, anchor.anchor_id)
        selected_template_path = _selected_template_path(repository, anchor.anchor_id)
        selected_reference_image_path = _selected_reference_image_path(repository, anchor.anchor_id)
        supporting_capture_ids = _supporting_capture_ids(repository, anchor.anchor_id)
        supporting_capture_image_paths = _supporting_capture_image_paths(repository, anchor.anchor_id)
        supporting_capture_evidence_roles = _supporting_capture_evidence_roles(repository, anchor.anchor_id)
        supporting_capture_failure_cases = _supporting_capture_failure_cases(repository, anchor.anchor_id)
        live_supporting_capture_ids = _live_supporting_capture_ids(repository, anchor.anchor_id)
        calibration_resolution = resolve_calibration_override(
            anchor=anchor,
            calibration_profile=calibration_profile,
        )
        source_image = str(
            payload.get("source_image")
            or failure_record.preview_image_path
            or failure_record.screenshot_path
        )
        match_result = build_match_result(
            source_image=source_image,
            candidates=_vision_matches_from_payload(payload.get("candidates")),
            expected_anchor=anchor,
            threshold=_float_or_default(
                payload.get("threshold"),
                default=calibration_resolution.effective_confidence_threshold,
            ),
            message=str(payload.get("message") or ""),
        )
        match_state = build_match_inspector(
            repository=repository,
            match_result=match_result,
            calibration_profile=calibration_profile,
            source_image=source_image,
            message=str(payload.get("message") or ""),
        )
        checks.append(
            ClaimRewardsCheckState(
                check_id=check_id,
                label=str(payload.get("label") or anchor.label or check_id.replace("_", " ")),
                anchor_id=anchor.anchor_id,
                anchor_label=anchor.label,
                stage=stage,
                status=match_state.status,
                threshold=match_state.threshold,
                message=match_state.message,
                candidate_count=match_state.candidate_count,
                matched_candidate=match_state.matched_candidate,
                best_candidate=match_state.best_candidate,
                candidates=list(match_state.candidates),
                matched_candidate_summary=match_state.matched_candidate_summary,
                best_candidate_summary=match_state.best_candidate_summary,
                calibration_resolution=match_state.calibration_resolution,
                inspection=match_state.inspection,
                selected_image_path=match_state.selected_image_path,
                selected_source_image=match_state.selected_source_image,
                selected_overlay=match_state.selected_overlay,
                selected_overlay_summary=match_state.selected_overlay_summary,
                selected_region=match_state.selected_region,
                selected_region_summary=match_state.selected_region_summary,
                golden_catalog_path=golden_catalog_path,
                selected_golden_id=selected_golden_id,
                selected_golden_image_path=selected_golden_image_path,
                selected_template_path=selected_template_path,
                selected_reference_id=match_state.selected_reference_id,
                selected_reference_kind=match_state.selected_reference_kind,
                selected_reference_image_path=selected_reference_image_path,
                reference_ids=list(match_state.reference_ids),
                reference_image_paths=list(match_state.reference_image_paths),
                live_reference_count=match_state.live_reference_count,
                live_reference_ids=list(match_state.live_reference_ids),
                live_reference_image_paths=list(match_state.live_reference_image_paths),
                supporting_capture_count=len(supporting_capture_ids),
                supporting_capture_ids=supporting_capture_ids,
                supporting_capture_image_paths=supporting_capture_image_paths,
                supporting_capture_evidence_roles=supporting_capture_evidence_roles,
                supporting_capture_failure_cases=supporting_capture_failure_cases,
                live_supporting_capture_count=len(live_supporting_capture_ids),
                live_supporting_capture_ids=live_supporting_capture_ids,
                curation_status=match_state.curation_status,
                provenance_kind=match_state.provenance_kind,
                provenance_summary=match_state.provenance_summary,
                curation_summary=match_state.curation_summary,
                failure_case=match_state.failure_case,
                failure_explanation=match_state.failure_explanation,
                metadata={**dict(anchor.metadata), **dict(payload.get("metadata", {}))},
            )
        )

    if not checks:
        return None

    selected_check = _select_claim_rewards_check(checks, selected_check_id or current_check_id)
    selected_check_id_value = selected_check.check_id if selected_check is not None else ""
    checks = [
        _mark_claim_rewards_check_selection(check, selected_check_id_value)
        for check in checks
    ]
    selected_check = next(
        (check for check in checks if check.check_id == selected_check_id_value),
        None,
    )
    return ClaimRewardsInspectorState(
        task_id="daily_ui.claim_rewards",
        current_check_id=current_check_id or selected_check_id_value,
        selected_check_id=selected_check_id_value,
        selected_check=selected_check,
        checks=checks,
        available_check_ids=[check.check_id for check in checks],
        check_count=len(checks),
        matched_check_count=sum(1 for check in checks if check.status == MatchStatus.MATCHED),
        missing_check_count=sum(1 for check in checks if check.status != MatchStatus.MATCHED),
        selected_anchor_id=selected_check.anchor_id if selected_check is not None else "",
        selected_stage=selected_check.stage if selected_check is not None else "",
        selected_threshold=selected_check.threshold if selected_check is not None else None,
        selected_image_path=selected_check.selected_image_path if selected_check is not None else "",
        selected_source_image=selected_check.selected_source_image if selected_check is not None else "",
        selected_overlay=selected_check.selected_overlay if selected_check is not None else None,
        selected_overlay_summary=selected_check.selected_overlay_summary if selected_check is not None else "",
        selected_region=selected_check.selected_region if selected_check is not None else None,
        selected_region_summary=selected_check.selected_region_summary if selected_check is not None else "",
        selected_anchor_label=selected_check.anchor_label if selected_check is not None else "",
        golden_catalog_path=selected_check.golden_catalog_path if selected_check is not None else "",
        selected_golden_id=selected_check.selected_golden_id if selected_check is not None else "",
        selected_golden_image_path=selected_check.selected_golden_image_path if selected_check is not None else "",
        selected_template_path=selected_check.selected_template_path if selected_check is not None else "",
        selected_reference_id=selected_check.selected_reference_id if selected_check is not None else "",
        selected_reference_kind=selected_check.selected_reference_kind if selected_check is not None else "",
        selected_reference_image_path=selected_check.selected_reference_image_path if selected_check is not None else "",
        reference_ids=list(selected_check.reference_ids) if selected_check is not None else [],
        reference_image_paths=list(selected_check.reference_image_paths) if selected_check is not None else [],
        live_reference_count=selected_check.live_reference_count if selected_check is not None else 0,
        live_reference_ids=list(selected_check.live_reference_ids) if selected_check is not None else [],
        live_reference_image_paths=list(selected_check.live_reference_image_paths) if selected_check is not None else [],
        supporting_capture_count=selected_check.supporting_capture_count if selected_check is not None else 0,
        supporting_capture_ids=list(selected_check.supporting_capture_ids) if selected_check is not None else [],
        supporting_capture_image_paths=list(selected_check.supporting_capture_image_paths) if selected_check is not None else [],
        supporting_capture_evidence_roles=list(selected_check.supporting_capture_evidence_roles) if selected_check is not None else [],
        supporting_capture_failure_cases=list(selected_check.supporting_capture_failure_cases) if selected_check is not None else [],
        live_supporting_capture_count=selected_check.live_supporting_capture_count if selected_check is not None else 0,
        live_supporting_capture_ids=list(selected_check.live_supporting_capture_ids) if selected_check is not None else [],
        selected_curation_status=selected_check.curation_status if selected_check is not None else None,
        selected_provenance_kind=selected_check.provenance_kind if selected_check is not None else None,
        selected_provenance_summary=selected_check.provenance_summary if selected_check is not None else "",
        selected_curation_summary=selected_check.curation_summary if selected_check is not None else "",
        selected_failure_case=selected_check.failure_case if selected_check is not None else "",
        selected_check_summary=_claim_rewards_check_summary(selected_check),
        workflow_summary=_claim_rewards_workflow_summary(checks, current_check_id=current_check_id),
        failure_explanation=selected_check.failure_explanation if selected_check is not None else "",
        metadata={key: value for key, value in claim_metadata.items() if key != "checks"},
    )


def _claim_rewards_task_support(repository: AnchorRepository) -> dict[str, Any]:
    task_support = repository.manifest.metadata.get("task_support", {})
    if not isinstance(task_support, dict):
        return {}
    support = task_support.get("daily_ui.claim_rewards", {})
    return dict(support) if isinstance(support, dict) else {}


def _find_task_anchor_by_role(
    repository: AnchorRepository,
    *,
    task_id: str,
    role: str,
):
    for anchor in repository.list_anchors():
        metadata = dict(anchor.metadata)
        raw_task_ids = metadata.get("task_ids", [])
        task_ids = [str(metadata.get("task_id", ""))] if metadata.get("task_id") else []
        if isinstance(raw_task_ids, list):
            task_ids.extend(str(item) for item in raw_task_ids if str(item))
        if task_id in task_ids and str(metadata.get("inspection_role", "")) == role:
            return anchor
    return None


def _vision_matches_from_payload(value: Any) -> list[VisionMatch]:
    if not isinstance(value, list):
        return []
    matches: list[VisionMatch] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        bbox = entry.get("bbox", (0, 0, 0, 0))
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            bbox = (0, 0, 0, 0)
        matches.append(
            VisionMatch(
                anchor_id=str(entry.get("anchor_id", "")),
                confidence=float(entry.get("confidence", 0.0)),
                bbox=tuple(int(item) for item in bbox),
                source_image=str(entry.get("source_image", "")),
            )
        )
    return matches


def _select_claim_rewards_check(
    checks: list[ClaimRewardsCheckState],
    selected_check_id: str,
) -> ClaimRewardsCheckState | None:
    for check in checks:
        if check.check_id == selected_check_id:
            return check
    for check in checks:
        if check.status != MatchStatus.MATCHED:
            return check
    return checks[0] if checks else None


def _path_exists(value: str) -> bool:
    if not value:
        return False
    if "://" in value:
        return False
    return Path(value).exists()


def _float_or_default(value: Any, *, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_selected_calibration(
    *,
    repository: AnchorRepository | None,
    calibration_profile: CalibrationProfile | None,
    expected_anchor_id: str,
) -> CalibrationOverrideResolution | None:
    if calibration_profile is None and not expected_anchor_id:
        return None

    anchor = None
    if repository is not None and expected_anchor_id and repository.has_anchor(expected_anchor_id):
        anchor = repository.get_anchor(expected_anchor_id)

    resolution = resolve_calibration_override(
        anchor=anchor,
        anchor_id=expected_anchor_id,
        calibration_profile=calibration_profile,
    )
    if (
        not resolution.anchor_id
        and not resolution.profile_id
        and resolution.capture_crop_region is None
        and not resolution.override
    ):
        return None
    return resolution


def _overlay_for_anchor_row(
    anchor: Any,
    calibration_resolution: CalibrationOverrideResolution,
) -> InspectionOverlay | None:
    region = CropRegion.from_value(
        calibration_resolution.effective_match_region or anchor.match_region
    )
    if region is None:
        return None
    return InspectionOverlay(
        overlay_id=f"{anchor.anchor_id}:anchor",
        kind=InspectionOverlayKind.EXPECTED_ANCHOR,
        label=f"anchor:{anchor.anchor_id}",
        region=region,
        stroke_color="#ffb02e",
        stroke_style="dashed" if calibration_resolution.override else "solid",
        is_expected=True,
        metadata={
            "anchor_id": anchor.anchor_id,
            "profile_id": calibration_resolution.profile_id,
            "override_applied": bool(calibration_resolution.override),
        },
    )


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
