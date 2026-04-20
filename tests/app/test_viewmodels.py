from __future__ import annotations

import unittest
from pathlib import Path
from datetime import datetime, timezone

import tests._bootstrap  # noqa: F401
from roxauto.app.viewmodels import build_console_snapshot, build_vision_workspace_snapshot
from roxauto.core.models import VisionMatch
from roxauto.vision import AnchorRepository, CalibrationProfile, RecordingAction, RecordingActionType, ReplayScript, build_match_result


class ConsoleSnapshotTests(unittest.TestCase):
    def test_snapshot_uses_doctor_payload_shape(self) -> None:
        report = {
            "packages": {"PySide6": True, "adbutils": False, "cv2": False},
            "adb": {"path": "C:/platform-tools/adb.exe", "instances_found": 1},
            "instances": [
                {
                    "instance_id": "mumu-2",
                    "label": "MuMu 2",
                    "adb_serial": "127.0.0.1:16448",
                    "status": "ready",
                    "last_seen_at": "2026-04-21T10:00:00+08:00",
                    "metadata": {"server": "TW-1"},
                }
            ],
        }

        snapshot = build_console_snapshot(report)

        self.assertEqual(snapshot.adb_path, "C:/platform-tools/adb.exe")
        self.assertEqual(snapshot.instance_count, 1)
        self.assertEqual(snapshot.available_runtime_features, ["PySide6"])
        self.assertEqual(snapshot.instances[0].instance_id, "mumu-2")
        self.assertEqual(snapshot.instances[0].metadata["server"], "TW-1")

    def test_vision_workspace_snapshot_uses_repository_and_scripts(self) -> None:
        templates_root = Path(__file__).resolve().parents[2] / "assets" / "templates"
        repository = AnchorRepository.load(templates_root / "common")
        anchor = repository.get_anchor("common.close_button")
        profile = CalibrationProfile(
            profile_id="profile.common",
            instance_id="mumu-0",
            emulator_name="mumu",
            scale_x=1.25,
            scale_y=1.25,
            offset_x=12,
            offset_y=24,
            crop_region=(1, 2, 3, 4),
            anchor_overrides={"common.close_button": {"confidence_threshold": 0.95}},
        )
        script = ReplayScript(
            script_id="script.common",
            name="Common flow",
            version="0.2.0",
            actions=[
                RecordingAction(
                    action_id="action-1",
                    action_type=RecordingActionType.CAPTURE,
                    target="preview",
                    payload={"note": "capture"},
                    occurred_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
                )
            ],
        )
        match_result = build_match_result(
            source_image="preview://sample",
            candidates=[
                VisionMatch(
                    anchor_id=anchor.anchor_id,
                    confidence=0.94,
                    bbox=(10, 20, 30, 40),
                    source_image="preview://sample",
                )
            ],
            expected_anchor=anchor,
            threshold=anchor.confidence_threshold,
            message="Matched close button",
        )

        snapshot = build_vision_workspace_snapshot(
            repository=repository,
            calibration_profile=profile,
            replay_script=script,
            match_result=match_result,
            source_image="preview://sample",
        )

        self.assertEqual(snapshot.preview.selected_anchor_id, "common.close_button")
        self.assertEqual(snapshot.preview.match_status, "matched")
        self.assertIn("common.close_button", snapshot.preview.candidate_summaries[0])
        self.assertEqual(snapshot.calibration.anchor_rows[0].anchor_id, "common.close_button")
        self.assertIn("confidence_threshold=0.95", snapshot.calibration.anchor_rows[0].override_summary)
        self.assertEqual(snapshot.recording.action_count, 1)
        self.assertEqual(snapshot.recording.action_rows[0].action_type, "capture")
        self.assertEqual(snapshot.anchors.selected_anchor_summary.split(" | ")[0], "Close Button")
        self.assertEqual(snapshot.failure.status, "matched")

