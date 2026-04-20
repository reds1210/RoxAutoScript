from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from roxauto.core.models import VisionMatch
from roxauto.vision.models import (
    AnchorSpec,
    CaptureArtifact,
    CaptureArtifactKind,
    CaptureSession,
    CropRegion,
    FailureInspectionRecord,
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


def _action_label(action: RecordingAction) -> str:
    if action.target:
        return f"{action.action_type.value}:{action.target}"
    return action.action_type.value


def _payload_summary(action: RecordingAction) -> str:
    if not action.payload:
        return ""
    return ", ".join(f"{key}={value}" for key, value in sorted(action.payload.items()))
