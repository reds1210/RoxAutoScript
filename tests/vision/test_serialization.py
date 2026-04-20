from __future__ import annotations

import unittest
from datetime import datetime, timezone

import tests._bootstrap  # noqa: F401
from roxauto.vision import (
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
    RecordingActionType,
    ReplayScript,
    TemplateMatchResult,
)
from roxauto.core.models import VisionMatch


class VisionSerializationTests(unittest.TestCase):
    def test_calibration_profile_roundtrip(self) -> None:
        profile = CalibrationProfile(
            profile_id="profile-1",
            instance_id="mumu-1",
            emulator_name="mumu",
            scale_x=1.2,
            scale_y=1.3,
            offset_x=12,
            offset_y=34,
            crop_region=(5, 6, 7, 8),
            anchor_overrides={
                "common.close_button": {"confidence_threshold": 0.95, "note": "tight"},
            },
            metadata={"source": "test"},
        )

        restored = CalibrationProfile.from_json(profile.to_json())

        self.assertEqual(restored.profile_id, profile.profile_id)
        self.assertEqual(restored.instance_id, profile.instance_id)
        self.assertEqual(restored.crop_region, profile.crop_region)
        self.assertEqual(restored.anchor_overrides, profile.anchor_overrides)
        self.assertEqual(restored.to_dict(), profile.to_dict())

    def test_replay_script_roundtrip(self) -> None:
        script = ReplayScript(
            script_id="script-1",
            name="Script One",
            version="0.2.0",
            actions=[
                RecordingAction(
                    action_id="action-1",
                    action_type=RecordingActionType.CAPTURE,
                    target="preview",
                    payload={"note": "capture"},
                    occurred_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
                ),
                RecordingAction(
                    action_id="action-2",
                    action_type=RecordingActionType.ANNOTATE,
                    target="common.close_button",
                    payload={"label": "close"},
                    occurred_at=datetime(2026, 4, 21, 10, 1, tzinfo=timezone.utc),
                ),
            ],
            metadata={"source": "test"},
        )

        restored = ReplayScript.from_json(script.to_json())

        self.assertEqual(restored.script_id, script.script_id)
        self.assertEqual(restored.name, script.name)
        self.assertEqual(len(restored.actions), 2)
        self.assertEqual(restored.actions[0].action_type, RecordingActionType.CAPTURE)
        self.assertEqual(restored.actions[1].payload["label"], "close")
        self.assertEqual(restored.actions[0].occurred_at, script.actions[0].occurred_at)
        self.assertEqual(restored.to_dict(), script.to_dict())

    def test_capture_session_roundtrip(self) -> None:
        session = CaptureSession(
            session_id="capture-1",
            instance_id="mumu-1",
            source_image="captures/source.png",
            selected_anchor_id="common.close_button",
            crop_region=CropRegion(x=10, y=20, width=30, height=40),
            artifacts=[
                CaptureArtifact(
                    artifact_id="artifact-1",
                    kind=CaptureArtifactKind.SCREENSHOT,
                    image_path="captures/source.png",
                    source_image="captures/source.png",
                ),
                CaptureArtifact(
                    artifact_id="artifact-2",
                    kind=CaptureArtifactKind.CROP,
                    image_path="captures/crop.png",
                    source_image="captures/source.png",
                    crop_region=CropRegion(x=10, y=20, width=30, height=40),
                ),
            ],
            metadata={"source": "test"},
        )

        restored = CaptureSession.from_json(session.to_json())

        self.assertEqual(restored.session_id, session.session_id)
        self.assertEqual(restored.crop_region.to_tuple(), (10, 20, 30, 40))
        self.assertEqual(restored.artifacts[1].kind, CaptureArtifactKind.CROP)
        self.assertEqual(restored.to_dict(), session.to_dict())

    def test_failure_inspection_roundtrip(self) -> None:
        inspection = FailureInspectionRecord(
            failure_id="failure-1",
            instance_id="mumu-1",
            screenshot_path="captures/failure.png",
            anchor_id="common.close_button",
            preview_image_path="captures/failure-preview.png",
            match_result=TemplateMatchResult(
                source_image="captures/failure.png",
                candidates=[
                    VisionMatch(
                        anchor_id="common.close_button",
                        confidence=0.92,
                        bbox=(1, 2, 3, 4),
                        source_image="captures/failure.png",
                    )
                ],
                expected_anchor_id="common.close_button",
                threshold=0.9,
                status=MatchStatus.MATCHED,
                message="matched",
            ),
            message="Captured failure context",
            metadata={"source": "test"},
        )

        restored = FailureInspectionRecord.from_dict(inspection.to_dict())

        self.assertEqual(restored.failure_id, inspection.failure_id)
        self.assertEqual(restored.best_candidate().anchor_id, "common.close_button")
        self.assertEqual(restored.to_dict(), inspection.to_dict())

    def test_image_inspection_state_roundtrip(self) -> None:
        inspection = ImageInspectionState(
            inspection_id="inspection-1",
            image_path="captures/source.png",
            source_image="captures/source.png",
            selected_overlay_id="overlay-1",
            selected_overlay=InspectionOverlay(
                overlay_id="overlay-1",
                kind=InspectionOverlayKind.MATCHED_ANCHOR,
                label="common.close_button",
                region=CropRegion(x=10, y=20, width=30, height=40),
                confidence=0.97,
                is_match=True,
                metadata={"source": "selected"},
            ),
            overlays=[
                InspectionOverlay(
                    overlay_id="overlay-1",
                    kind=InspectionOverlayKind.MATCHED_ANCHOR,
                    label="common.close_button",
                    region=CropRegion(x=10, y=20, width=30, height=40),
                    confidence=0.97,
                    is_match=True,
                ),
                InspectionOverlay(
                    overlay_id="overlay-2",
                    kind=InspectionOverlayKind.EXPECTED_ANCHOR,
                    label="expected",
                    region=CropRegion(x=11, y=22, width=33, height=44),
                    is_expected=True,
                ),
            ],
            overlay_count=2,
            selected_overlay_summary="common.close_button | kind=matched_anchor",
            metadata={"source": "test"},
        )

        restored = ImageInspectionState.from_dict(inspection.to_dict())

        self.assertEqual(restored.inspection_id, inspection.inspection_id)
        self.assertEqual(restored.selected_overlay.kind, InspectionOverlayKind.MATCHED_ANCHOR)
        self.assertEqual(restored.overlays[1].kind, InspectionOverlayKind.EXPECTED_ANCHOR)
        self.assertEqual(restored.to_dict(), inspection.to_dict())

    def test_calibration_override_resolution_roundtrip(self) -> None:
        resolution = CalibrationOverrideResolution(
            anchor_id="common.close_button",
            profile_id="profile-1",
            base_confidence_threshold=0.88,
            effective_confidence_threshold=0.96,
            base_match_region=(1, 2, 3, 4),
            effective_match_region=(5, 6, 7, 8),
            capture_crop_region=CropRegion(x=10, y=20, width=30, height=40),
            scale_x=1.2,
            scale_y=1.3,
            offset_x=14,
            offset_y=15,
            override={"confidence_threshold": 0.96},
            metadata={"source": "test"},
        )

        restored = CalibrationOverrideResolution.from_dict(resolution.to_dict())

        self.assertEqual(restored.anchor_id, resolution.anchor_id)
        self.assertEqual(restored.effective_match_region, resolution.effective_match_region)
        self.assertEqual(restored.capture_crop_region.to_tuple(), (10, 20, 30, 40))
        self.assertEqual(restored.to_dict(), resolution.to_dict())

