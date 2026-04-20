from __future__ import annotations

import unittest
from datetime import datetime, timezone

import tests._bootstrap  # noqa: F401
from roxauto.core.models import VisionMatch
from roxauto.vision import (
    AnchorSpec,
    CaptureArtifactKind,
    MatchStatus,
    RecordingAction,
    RecordingActionType,
    ReplayScript,
    build_failure_inspection,
    build_match_result,
    build_replay_view,
    create_capture_artifact,
    create_capture_session,
)


class VisionServiceTests(unittest.TestCase):
    def test_build_match_result_uses_anchor_threshold(self) -> None:
        anchor = AnchorSpec(
            anchor_id="common.close_button",
            label="Close",
            template_path="anchors/common_close_button.svg",
            confidence_threshold=0.9,
        )

        result = build_match_result(
            source_image="captures/frame.png",
            candidates=[
                VisionMatch(
                    anchor_id="common.close_button",
                    confidence=0.91,
                    bbox=(0, 0, 10, 10),
                    source_image="captures/frame.png",
                ),
                VisionMatch(
                    anchor_id="common.confirm_button",
                    confidence=0.99,
                    bbox=(0, 0, 10, 10),
                    source_image="captures/frame.png",
                ),
            ],
            expected_anchor=anchor,
        )

        self.assertEqual(result.status, MatchStatus.MATCHED)
        self.assertEqual(result.matched_candidate().anchor_id, "common.close_button")

    def test_capture_helpers_build_crop_artifact_and_session(self) -> None:
        session = create_capture_session(
            session_id="capture-1",
            instance_id="mumu-1",
            source_image="captures/source.png",
            crop_region=(10, 20, 30, 40),
            selected_anchor_id="common.close_button",
        )
        artifact = create_capture_artifact(
            artifact_id="artifact-1",
            image_path="captures/crop.png",
            source_image=session.source_image,
            kind=CaptureArtifactKind.CROP,
            crop_region=session.crop_region,
        )
        session.append_artifact(artifact)

        self.assertEqual(session.crop_region.to_tuple(), (10, 20, 30, 40))
        self.assertEqual(session.artifacts[0].kind, CaptureArtifactKind.CROP)
        self.assertEqual(session.selected_anchor_id, "common.close_button")

    def test_build_replay_view_selects_first_action_by_default(self) -> None:
        script = ReplayScript(
            script_id="script-1",
            name="Replay Script",
            actions=[
                RecordingAction(
                    action_id="a1",
                    action_type=RecordingActionType.CAPTURE,
                    target="preview",
                    payload={"note": "first"},
                    occurred_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
                ),
                RecordingAction(
                    action_id="a2",
                    action_type=RecordingActionType.ANNOTATE,
                    target="common.close_button",
                    payload={"note": "second"},
                    occurred_at=datetime(2026, 4, 21, 10, 1, tzinfo=timezone.utc),
                ),
            ],
        )

        view = build_replay_view(script)

        self.assertEqual(view.total_actions, 2)
        self.assertEqual(view.selected_action_id, "a1")
        self.assertTrue(view.actions[0].is_selected)
        self.assertEqual(view.actions[0].label, "capture:preview")

    def test_build_failure_inspection_uses_match_context(self) -> None:
        match = build_match_result(
            source_image="captures/failure.png",
            candidates=[
                VisionMatch(
                    anchor_id="common.close_button",
                    confidence=0.82,
                    bbox=(5, 5, 10, 10),
                    source_image="captures/failure.png",
                )
            ],
            expected_anchor=AnchorSpec(
                anchor_id="common.close_button",
                label="Close",
                template_path="anchors/common_close_button.svg",
                confidence_threshold=0.9,
            ),
            message="below threshold",
        )

        inspection = build_failure_inspection(
            failure_id="failure-1",
            instance_id="mumu-1",
            screenshot_path="captures/failure.png",
            preview_image_path="captures/failure-preview.png",
            match_result=match,
        )

        self.assertEqual(inspection.anchor_id, "common.close_button")
        self.assertEqual(inspection.message, "below threshold")
        self.assertEqual(inspection.best_candidate().confidence, 0.82)

