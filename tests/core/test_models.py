from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.models import (
    FailureSnapshotMetadata,
    FailureSnapshotReason,
    InstanceRuntimeContext,
    InstanceStatus,
    PreviewFrame,
    ProfileBinding,
    StopCondition,
    StopConditionKind,
    TaskManifest,
)
from roxauto.core.serde import to_primitive


class CoreModelSerializationTests(unittest.TestCase):
    def test_preview_frame_and_failure_snapshot_serialize(self) -> None:
        preview = PreviewFrame(
            frame_id="frame-1",
            instance_id="mumu-0",
            image_path="captures/frame.png",
            thumbnail_path="captures/frame-thumb.png",
            metadata={"source": "test"},
        )
        snapshot = FailureSnapshotMetadata(
            snapshot_id="snapshot-1",
            instance_id="mumu-0",
            task_id="task.daily",
            run_id="run-1",
            reason=FailureSnapshotReason.STEP_FAILED,
            screenshot_path="captures/frame.png",
            preview_frame=preview,
            metadata={"message": "failed"},
        )

        primitive = to_primitive(snapshot)

        self.assertEqual(primitive["reason"], "step_failed")
        self.assertEqual(primitive["preview_frame"]["frame_id"], "frame-1")
        self.assertEqual(primitive["preview_frame"]["thumbnail_path"], "captures/frame-thumb.png")

    def test_stop_condition_and_task_manifest_serialize(self) -> None:
        stop_condition = StopCondition(
            condition_id="stop-1",
            kind=StopConditionKind.TIMEOUT,
            timeout_ms=5000,
            message="timeout",
        )
        manifest = TaskManifest(
            task_id="task.daily",
            name="Daily",
            version="1.0.0",
            requires=["anchor.daily"],
            entry_condition="screen ready",
            success_condition="reward collected",
            failure_condition="popup encountered",
            recovery_policy="retry",
            stop_conditions=[stop_condition],
            metadata={"category": "daily"},
        )

        primitive = to_primitive(manifest)

        self.assertEqual(primitive["task_id"], "task.daily")
        self.assertEqual(primitive["stop_conditions"][0]["kind"], "timeout")
        self.assertEqual(primitive["requires"], ["anchor.daily"])

    def test_profile_binding_and_runtime_context_serialize(self) -> None:
        binding = ProfileBinding(
            profile_id="main-account",
            display_name="Main Account",
            server_name="TW-1",
            character_name="Knight",
            allowed_tasks=["daily.claim"],
            calibration_id="calib-main",
            capture_offset=(4, 8),
            capture_scale=1.1,
            settings={"language": "zh-TW"},
            notes="bound to primary emulator",
        )
        context = InstanceRuntimeContext(
            instance_id="mumu-0",
            status=InstanceStatus.READY,
            queue_depth=2,
            profile_binding=binding,
            health_check_ok=True,
            metadata={"profile_id": "main-account"},
        )

        primitive = to_primitive(context)

        self.assertEqual(primitive["profile_binding"]["profile_id"], "main-account")
        self.assertEqual(primitive["profile_binding"]["capture_offset"], [4, 8])
        self.assertTrue(primitive["health_check_ok"])
