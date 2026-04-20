from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from roxauto.core.models import VisionMatch
from roxauto.vision.models import (
    AnchorSpec,
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
    RecordingAction,
    ReplayActionView,
    ReplayScript,
    ReplayViewerState,
    TemplateMatchResult,
)


def build_match_result(
    *,
    source_image: str,
    candidates: Iterable[VisionMatch],
    expected_anchor: AnchorSpec | None = None,
    threshold: float | None = None,
    message: str = "",
) -> TemplateMatchResult:
    candidate_list = list(candidates)
    selected_threshold = threshold
    if selected_threshold is None and expected_anchor is not None:
        selected_threshold = expected_anchor.confidence_threshold
    if selected_threshold is None:
        selected_threshold = 0.85

    if expected_anchor is not None:
        matching_candidates = [
            candidate
            for candidate in candidate_list
            if candidate.anchor_id == expected_anchor.anchor_id and candidate.confidence >= selected_threshold
        ]
        best_candidate = max(matching_candidates, key=lambda candidate: candidate.confidence, default=None)
    else:
        best_candidate = max(candidate_list, key=lambda candidate: candidate.confidence, default=None)
        if best_candidate is not None and best_candidate.confidence < selected_threshold:
            best_candidate = None

    is_match = best_candidate is not None

    return TemplateMatchResult(
        source_image=source_image,
        candidates=candidate_list,
        expected_anchor_id=expected_anchor.anchor_id if expected_anchor else "",
        threshold=selected_threshold,
        status=MatchStatus.MATCHED if is_match else MatchStatus.MISSED,
        message=message or ("matched" if is_match else "no anchor met threshold"),
    )


def create_capture_session(
    *,
    session_id: str,
    instance_id: str,
    source_image: str,
    crop_region: CropRegion | tuple[int, int, int, int] | None = None,
    selected_anchor_id: str = "",
    metadata: dict[str, object] | None = None,
) -> CaptureSession:
    return CaptureSession(
        session_id=session_id,
        instance_id=instance_id,
        source_image=source_image,
        selected_anchor_id=selected_anchor_id,
        crop_region=CropRegion.from_value(crop_region),
        metadata=dict(metadata or {}),
    )


def create_capture_artifact(
    *,
    artifact_id: str,
    image_path: str,
    source_image: str = "",
    kind: CaptureArtifactKind = CaptureArtifactKind.SCREENSHOT,
    crop_region: CropRegion | tuple[int, int, int, int] | None = None,
    metadata: dict[str, object] | None = None,
) -> CaptureArtifact:
    return CaptureArtifact(
        artifact_id=artifact_id,
        kind=kind,
        image_path=image_path,
        source_image=source_image,
        crop_region=CropRegion.from_value(crop_region),
        metadata=dict(metadata or {}),
    )


def build_replay_view(
    script: ReplayScript,
    *,
    selected_action_id: str = "",
) -> ReplayViewerState:
    actions = [
        ReplayActionView(
            action_id=action.action_id,
            label=_action_label(action),
            action_type=action.action_type,
            occurred_at=action.occurred_at,
            payload_summary=_payload_summary(action),
            is_selected=bool(selected_action_id) and action.action_id == selected_action_id,
            metadata=dict(action.metadata),
        )
        for action in script.actions
    ]
    if actions and not any(action.is_selected for action in actions):
        actions[0] = replace(actions[0], is_selected=True)
        selected_action_id = actions[0].action_id
    return ReplayViewerState(
        script_id=script.script_id,
        script_name=script.name,
        version=script.version,
        total_actions=len(actions),
        selected_action_id=selected_action_id,
        actions=actions,
        metadata=dict(script.metadata),
    )


def build_failure_inspection(
    *,
    failure_id: str,
    instance_id: str,
    screenshot_path: str,
    match_result: TemplateMatchResult | None = None,
    anchor_id: str = "",
    preview_image_path: str = "",
    message: str = "",
    metadata: dict[str, object] | None = None,
) -> FailureInspectionRecord:
    resolved_anchor_id = anchor_id or (match_result.expected_anchor_id if match_result else "")
    resolved_message = message or (match_result.message if match_result else "")
    return FailureInspectionRecord(
        failure_id=failure_id,
        instance_id=instance_id,
        screenshot_path=screenshot_path,
        anchor_id=resolved_anchor_id,
        preview_image_path=preview_image_path,
        match_result=match_result,
        message=resolved_message,
        metadata=dict(metadata or {}),
    )


def resolve_calibration_override(
    *,
    anchor: AnchorSpec | None = None,
    anchor_id: str = "",
    calibration_profile: CalibrationProfile | None = None,
) -> CalibrationOverrideResolution:
    resolved_anchor_id = anchor_id or (anchor.anchor_id if anchor is not None else "")
    override = (
        dict(calibration_profile.anchor_overrides.get(resolved_anchor_id, {}))
        if calibration_profile is not None and resolved_anchor_id
        else {}
    )
    base_threshold = anchor.confidence_threshold if anchor is not None else 0.85
    effective_threshold = _coerce_float(override.get("confidence_threshold"), default=base_threshold)
    base_match_region = anchor.match_region if anchor is not None else None
    effective_match_region = _region_tuple(override.get("match_region")) or base_match_region
    capture_crop_region = (
        CropRegion.from_value(override.get("crop_region"))
        or CropRegion.from_value(calibration_profile.crop_region if calibration_profile is not None else None)
    )
    return CalibrationOverrideResolution(
        anchor_id=resolved_anchor_id,
        profile_id=calibration_profile.profile_id if calibration_profile is not None else "",
        base_confidence_threshold=base_threshold,
        effective_confidence_threshold=effective_threshold,
        base_match_region=base_match_region,
        effective_match_region=effective_match_region,
        capture_crop_region=capture_crop_region,
        scale_x=calibration_profile.scale_x if calibration_profile is not None else 1.0,
        scale_y=calibration_profile.scale_y if calibration_profile is not None else 1.0,
        offset_x=calibration_profile.offset_x if calibration_profile is not None else 0,
        offset_y=calibration_profile.offset_y if calibration_profile is not None else 0,
        override=override,
        metadata=dict(calibration_profile.metadata) if calibration_profile is not None else {},
    )


def build_image_inspection_state(
    *,
    inspection_id: str,
    image_path: str,
    source_image: str = "",
    match_result: TemplateMatchResult | None = None,
    capture_session: CaptureSession | None = None,
    calibration: CalibrationOverrideResolution | None = None,
    selected_overlay_id: str = "",
    metadata: dict[str, object] | None = None,
) -> ImageInspectionState:
    overlays: list[InspectionOverlay] = []

    expected_overlay = _expected_region_overlay(
        match_result=match_result,
        calibration=calibration,
    )
    if expected_overlay is not None:
        overlays.append(expected_overlay)

    crop_overlay = _capture_crop_overlay(capture_session)
    if crop_overlay is not None:
        overlays.append(crop_overlay)

    overlays.extend(_match_candidate_overlays(match_result))
    selected_overlay = _select_overlay(overlays, selected_overlay_id)
    if selected_overlay is not None:
        overlays = [
            replace(overlay, is_selected=overlay.overlay_id == selected_overlay.overlay_id)
            for overlay in overlays
        ]
        selected_overlay = next(
            overlay for overlay in overlays if overlay.overlay_id == selected_overlay.overlay_id
        )

    return ImageInspectionState(
        inspection_id=inspection_id,
        image_path=image_path,
        source_image=source_image or image_path,
        selected_overlay_id=selected_overlay.overlay_id if selected_overlay is not None else "",
        selected_overlay=selected_overlay,
        overlays=overlays,
        overlay_count=len(overlays),
        selected_overlay_summary=_overlay_summary(selected_overlay),
        metadata=dict(metadata or {}),
    )


def _action_label(action: RecordingAction) -> str:
    if action.target:
        return f"{action.action_type.value}:{action.target}"
    return action.action_type.value


def _payload_summary(action: RecordingAction) -> str:
    if not action.payload:
        return ""
    return ", ".join(f"{key}={value}" for key, value in sorted(action.payload.items()))


def _coerce_float(value: object, *, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _region_tuple(value: object) -> tuple[int, int, int, int] | None:
    region = CropRegion.from_value(value)
    return region.to_tuple() if region is not None else None


def _capture_crop_overlay(
    capture_session: CaptureSession | None,
) -> InspectionOverlay | None:
    if capture_session is None or capture_session.crop_region is None:
        return None
    return InspectionOverlay(
        overlay_id=f"{capture_session.session_id}:crop",
        kind=InspectionOverlayKind.CROP_REGION,
        label="capture crop",
        region=CropRegion.from_value(capture_session.crop_region),
        stroke_color="#33c3ff",
        stroke_style="dashed",
        metadata={"session_id": capture_session.session_id},
    )


def _expected_region_overlay(
    *,
    match_result: TemplateMatchResult | None,
    calibration: CalibrationOverrideResolution | None,
) -> InspectionOverlay | None:
    region = None
    anchor_id = ""
    if calibration is not None:
        region = CropRegion.from_value(calibration.effective_match_region)
        anchor_id = calibration.anchor_id
    if region is None or not anchor_id:
        if match_result is None or not match_result.expected_anchor_id:
            return None
        anchor_id = match_result.expected_anchor_id
    if region is None:
        return None
    return InspectionOverlay(
        overlay_id=f"{anchor_id}:expected",
        kind=InspectionOverlayKind.EXPECTED_ANCHOR,
        label=f"expected:{anchor_id}",
        region=region,
        stroke_color="#ffb02e",
        stroke_style="dashed",
        is_expected=True,
        metadata={"anchor_id": anchor_id},
    )


def _match_candidate_overlays(
    match_result: TemplateMatchResult | None,
) -> list[InspectionOverlay]:
    if match_result is None:
        return []
    matched_candidate = match_result.matched_candidate()
    best_candidate = match_result.best_candidate()
    overlays: list[InspectionOverlay] = []
    for index, candidate in enumerate(match_result.candidates):
        is_matched = (
            matched_candidate is not None
            and candidate.anchor_id == matched_candidate.anchor_id
            and candidate.bbox == matched_candidate.bbox
            and candidate.source_image == matched_candidate.source_image
        )
        is_best = (
            best_candidate is not None
            and candidate.anchor_id == best_candidate.anchor_id
            and candidate.bbox == best_candidate.bbox
            and candidate.source_image == best_candidate.source_image
        )
        overlays.append(
            InspectionOverlay(
                overlay_id=f"candidate:{index}:{candidate.anchor_id}",
                kind=InspectionOverlayKind.MATCHED_ANCHOR if is_matched else InspectionOverlayKind.MATCH_CANDIDATE,
                label=f"{candidate.anchor_id}:{candidate.confidence:.3f}",
                region=CropRegion.from_value(candidate.bbox),
                stroke_color="#31b66a" if is_matched else "#7d8ca3",
                fill_color="#31b66a22" if is_matched else "",
                stroke_style="solid",
                line_width=3 if is_matched else 2,
                is_expected=bool(match_result.expected_anchor_id)
                and candidate.anchor_id == match_result.expected_anchor_id,
                is_match=is_matched,
                is_warning=not is_matched and candidate.confidence < match_result.threshold,
                confidence=candidate.confidence,
                metadata={
                    "anchor_id": candidate.anchor_id,
                    "bbox": candidate.bbox,
                    "is_best_candidate": is_best,
                    "passed_threshold": candidate.confidence >= match_result.threshold,
                },
            )
        )
    return overlays


def _select_overlay(
    overlays: list[InspectionOverlay],
    selected_overlay_id: str,
) -> InspectionOverlay | None:
    for overlay in overlays:
        if overlay.overlay_id == selected_overlay_id:
            return overlay
    for overlay in overlays:
        if overlay.is_match:
            return overlay
    for overlay in overlays:
        if overlay.is_expected:
            return overlay
    return overlays[0] if overlays else None


def _overlay_summary(overlay: InspectionOverlay | None) -> str:
    if overlay is None:
        return ""
    region = overlay.region.to_tuple() if overlay.region is not None else None
    summary = f"{overlay.label} | kind={overlay.kind.value}"
    if overlay.confidence is not None:
        summary += f" | confidence={overlay.confidence:.3f}"
    if region is not None:
        summary += f" | region={region}"
    return summary
