from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.app.viewmodels import (
    build_console_snapshot,
    build_log_pane,
    build_manual_control_command,
    build_operator_console_state,
    build_vision_workspace_snapshot,
)
from roxauto.core.commands import CommandRouter, InstanceCommandType
from roxauto.core.events import AppEvent
from roxauto.core.models import StopCondition, StopConditionKind, TaskManifest, TaskSpec, VisionMatch
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import TaskStep, step_success
from roxauto.vision import (
    AnchorRepository,
    CalibrationProfile,
    RecordingAction,
    RecordingActionType,
    ReplayScript,
    build_match_result,
)


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

    def test_operator_console_state_filters_queue_and_logs_for_selected_instance(self) -> None:
        snapshot = build_console_snapshot(
            {
                "packages": {"PySide6": True},
                "adb": {"path": "C:/platform-tools/adb.exe", "instances_found": 2},
                "instances": [
                    {
                        "instance_id": "mumu-1",
                        "label": "MuMu 1",
                        "adb_serial": "127.0.0.1:16448",
                        "status": "ready",
                        "last_seen_at": "2026-04-21T10:00:00+08:00",
                        "metadata": {"server": "TW-1"},
                    },
                    {
                        "instance_id": "mumu-2",
                        "label": "MuMu 2",
                        "adb_serial": "127.0.0.1:16449",
                        "status": "paused",
                        "last_seen_at": "2026-04-21T10:05:00+08:00",
                        "metadata": {"server": "TW-2"},
                    },
                ],
            }
        )
        vision_snapshot = _build_vision_snapshot()
        queue_items = [
            _queued_task("mumu-1", "daily.claim", "Daily Claim", 100),
            _queued_task("mumu-2", "guild.donate", "Guild Donate", 90),
        ]
        events = [
            AppEvent(
                name="task.progress",
                payload={"instance_id": "mumu-1", "message": "Claim reward", "status": "running"},
            ),
            AppEvent(
                name="task.failure_snapshot",
                payload={"instance_id": "mumu-2", "message": "Vision miss", "status": "failed"},
            ),
        ]

        state = build_operator_console_state(
            snapshot,
            vision_snapshot,
            queue_items=queue_items,
            events=events,
            selected_instance_id="mumu-2",
            global_emergency_stop_active=True,
        )

        self.assertEqual(state.selected_instance_id, "mumu-2")
        self.assertEqual(state.queue.total_count, 1)
        self.assertEqual(state.queue.items[0].task_id, "guild.donate")
        self.assertEqual(state.logs.filtered_count, 1)
        self.assertEqual(state.logs.failure_count, 1)
        self.assertFalse(state.manual_controls.enabled)
        self.assertIn("Emergency stop requested", state.detail.warning)

    def test_manual_control_commands_route_through_shared_router(self) -> None:
        router = CommandRouter()

        tap_route = router.route(
            build_manual_control_command("tap", instance_id="mumu-1", payload={"x": 400, "y": 200})
        )
        swipe_route = router.route(
            build_manual_control_command(
                "swipe",
                instance_id="mumu-1",
                payload={"start": (100, 200), "end": (100, 50), "duration_ms": 300},
            )
        )
        text_route = router.route(
            build_manual_control_command("input_text", instance_id="mumu-1", payload={"text": "hello"})
        )
        stop_route = router.route(build_manual_control_command("emergency_stop"))

        self.assertEqual(tap_route.command_type, InstanceCommandType.TAP)
        self.assertEqual(tap_route.payload["point"], (400, 200))
        self.assertEqual(swipe_route.payload["duration_ms"], 300)
        self.assertEqual(text_route.payload["text"], "hello")
        self.assertEqual(stop_route.command_type, InstanceCommandType.EMERGENCY_STOP)
        self.assertEqual(stop_route.kind.value, "global_control")

    def test_log_pane_marks_failure_entries_as_error(self) -> None:
        logs = build_log_pane(
            [
                AppEvent(
                    name="task.failure_snapshot",
                    payload={"instance_id": "mumu-2", "message": "Vision miss", "status": "failed"},
                )
            ],
            selected_instance_id="mumu-2",
        )

        self.assertEqual(logs.failure_count, 1)
        self.assertEqual(logs.entries[0].level, "error")

    def test_vision_workspace_snapshot_uses_repository_and_scripts(self) -> None:
        snapshot = _build_vision_snapshot()

        self.assertEqual(snapshot.preview.selected_anchor_id, "common.close_button")
        self.assertEqual(snapshot.preview.match_status, "matched")
        self.assertIn("common.close_button", snapshot.preview.candidate_summaries[0])
        self.assertEqual(snapshot.calibration.anchor_rows[0].anchor_id, "common.close_button")
        self.assertIn("confidence_threshold=0.95", snapshot.calibration.anchor_rows[0].override_summary)
        self.assertEqual(snapshot.recording.action_count, 1)
        self.assertEqual(snapshot.recording.action_rows[0].action_type, "capture")
        self.assertEqual(snapshot.anchors.selected_anchor_summary.split(" | ")[0], "Close Button")
        self.assertEqual(snapshot.failure.status, "matched")


def _build_vision_snapshot():
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

    return build_vision_workspace_snapshot(
        repository=repository,
        calibration_profile=profile,
        replay_script=script,
        match_result=match_result,
        source_image="preview://sample",
    )


def _queued_task(instance_id: str, task_id: str, name: str, priority: int) -> QueuedTask:
    manifest = TaskManifest(
        task_id=task_id,
        name=name,
        version="0.1.0",
        recovery_policy="abort",
        stop_conditions=[
            StopCondition(
                condition_id=f"{task_id}.manual",
                kind=StopConditionKind.MANUAL,
                message="manual stop",
            )
        ],
    )
    spec = TaskSpec(
        task_id=task_id,
        name=name,
        version="0.1.0",
        entry_state="ready",
        manifest=manifest,
        steps=[
            TaskStep(
                step_id="noop",
                description="No-op",
                handler=lambda context: step_success("noop", "ok"),
            )
        ],
    )
    return QueuedTask(instance_id=instance_id, spec=spec, priority=priority)
