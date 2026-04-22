from __future__ import annotations

import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.app.viewmodels import (
    ClaimRewardsPaneView,
    build_console_snapshot,
    build_console_snapshot_from_runtime,
    build_log_pane,
    build_manual_control_command,
    build_operator_console_state,
    build_task_readiness_pane,
)
from roxauto.core.commands import CommandDispatchResult, CommandDispatchStatus, CommandRouter, InstanceCommandType
from roxauto.core.models import (
    InstanceRuntimeContext,
    InstanceState,
    InstanceStatus,
    PreviewFrame,
    ProfileBinding,
    TaskManifest,
    TaskSpec,
    VisionMatch,
)
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import RuntimeInspectionResult, TaskStep, step_success
from roxauto.core.time import utc_now
from roxauto.emulator import LiveRuntimeEventRecord, LiveRuntimeInstanceSnapshot, LiveRuntimeSnapshot
from roxauto.tasks import TaskFoundationRepository
from roxauto.vision import (
    AnchorRepository,
    CalibrationProfile,
    build_failure_inspection,
    build_match_result,
    build_vision_tooling_state,
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

    def test_runtime_snapshot_projection_and_console_state_follow_shared_contracts(self) -> None:
        runtime_snapshot = _runtime_snapshot()
        snapshot = build_console_snapshot_from_runtime(
            runtime_snapshot,
            adb_path="C:/platform-tools/adb.exe",
            packages={"PySide6": True},
        )
        state = build_operator_console_state(
            snapshot,
            runtime_snapshot,
            _build_vision_state(),
            selected_instance_id="mumu-9",
            global_emergency_stop_active=False,
            task_readiness_reports=_task_foundations().evaluate_task_readinesses(),
            task_runtime_builder_inputs=_task_foundations().build_runtime_builder_inputs(),
            claim_rewards=ClaimRewardsPaneView(
                workflow_status="queued",
                selected_scope_summary="instance=mumu-9 | active",
            ),
        )

        self.assertEqual(snapshot.instances[0].metadata["queue_depth"], 2)
        self.assertEqual(snapshot.instances[0].metadata["profile_id"], "profile.mumu-9")
        self.assertEqual(state.detail.queue_depth, 2)
        self.assertIn("active_task_id: daily_ui.claim_rewards", state.detail.metadata_lines)
        self.assertIn("inspection.health_check_message: healthy", state.detail.metadata_lines)
        self.assertIn("preview_frame: runtime_logs/previews/mumu-9-1.png", state.detail.metadata_lines)
        self.assertEqual(state.summary.selected_queue_depth, 2)
        self.assertEqual(state.instance_rows[0].profile_summary, "MuMu 9 Profile")
        self.assertEqual(state.manual_controls.last_command_status, "completed")
        self.assertIn("pause routed", state.manual_controls.last_command_summary)
        self.assertIsNotNone(state.selected_inspection_result)
        self.assertEqual(state.task_readiness.blocked_by_runtime_count, 0)
        self.assertEqual(state.task_readiness.blocked_by_asset_count, 1)
        self.assertEqual(state.claim_rewards.workflow_status, "queued")
        self.assertEqual(state.claim_rewards.selected_scope_summary, "instance=mumu-9 | active")
        self.assertEqual(state.vision.workspace.selected_repository_id, "common")
        self.assertIsNotNone(state.vision.readiness)

    def test_log_pane_filters_live_runtime_events_and_marks_failures(self) -> None:
        logs = build_log_pane(
            [
                LiveRuntimeEventRecord(
                    sequence_id=1,
                    name="task.failure_snapshot",
                    emitted_at=utc_now(),
                    instance_id="mumu-2",
                    payload={"instance_id": "mumu-2", "message": "Vision miss", "status": "failed"},
                ),
                LiveRuntimeEventRecord(
                    sequence_id=2,
                    name="instance.updated",
                    emitted_at=utc_now(),
                    instance_id="mumu-1",
                    payload={"instance_id": "mumu-1", "status": "ready"},
                ),
            ],
            selected_instance_id="mumu-2",
        )

        self.assertEqual(logs.filtered_count, 1)
        self.assertEqual(logs.failure_count, 1)
        self.assertEqual(logs.entries[0].level, "error")

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

    def test_task_readiness_pane_projects_foundation_gaps(self) -> None:
        repository = _task_foundations()
        reports = repository.evaluate_task_readinesses()
        pane = build_task_readiness_pane(
            reports,
            repository.build_runtime_builder_inputs(),
            selected_instance_snapshot=_runtime_snapshot().get_instance_snapshot("mumu-9"),
        )

        self.assertEqual(pane.total_tasks, len(reports))
        self.assertEqual(pane.builder_ready_count, 2)
        self.assertEqual(pane.blocked_by_asset_count, 1)
        self.assertEqual(pane.blocked_by_runtime_count, 0)
        self.assertEqual(pane.blocked_by_calibration_count, 1)
        self.assertEqual(pane.selected_task_ids, ["daily_ui.claim_rewards"])
        self.assertNotIn("odin.preset_entry", pane.selected_task_ids)
        self.assertTrue(any(row.is_related_to_selected_instance for row in pane.rows))
        focused_row = pane.rows[0]
        self.assertEqual(focused_row.task_id, "daily_ui.claim_rewards")
        self.assertEqual(focused_row.scope_reasons, ["active"])
        self.assertEqual(
            focused_row.fixture_profile_paths,
            ["fixture_profiles/default_tw_daily.fixture.json"],
        )
        self.assertEqual(
            focused_row.runtime_requirement_ids,
            ["runtime.daily_ui.dispatch_bridge"],
        )


def _runtime_snapshot() -> LiveRuntimeSnapshot:
    instance = InstanceState(
        instance_id="mumu-9",
        label="MuMu 9",
        adb_serial="127.0.0.1:16768",
        status=InstanceStatus.READY,
        metadata={"server": "TW-9"},
    )
    context = InstanceRuntimeContext(
        instance_id="mumu-9",
        status=InstanceStatus.READY,
        queue_depth=2,
        active_task_id="daily_ui.claim_rewards",
        active_run_id="run-9",
        stop_requested=False,
        health_check_ok=True,
        profile_binding=ProfileBinding(
            profile_id="profile.mumu-9",
            display_name="MuMu 9 Profile",
            server_name="TW-9",
            character_name="Knight",
            calibration_id="calibration.mumu-9",
            allowed_tasks=["daily_ui.claim_rewards", "odin.preset_entry"],
        ),
        preview_frame=PreviewFrame(
            frame_id="frame-9",
            instance_id="mumu-9",
            image_path="runtime_logs/previews/mumu-9-1.png",
        ),
    )
    queue_item = _queued_task("mumu-9", "sample.mumu-9.0", "Preview Sync", 100)
    instance_snapshot = LiveRuntimeInstanceSnapshot(
        instance_id="mumu-9",
        instance=instance,
        context=context,
        queue_items=[queue_item, _queued_task("mumu-9", "sample.mumu-9.1", "Audit Sweep", 90)],
    )
    return LiveRuntimeSnapshot(
        revision=3,
        instances=[instance],
        contexts=[context],
        queue_items=[queue_item],
        instance_snapshots=[instance_snapshot],
        last_inspection_results=[
            RuntimeInspectionResult(
                instance_id="mumu-9",
                status=InstanceStatus.READY,
                health_check_ok=True,
                health_check_message="healthy",
                preview_frame=context.preview_frame,
                metadata={"capture_preview": True, "run_health_check": True},
            )
        ],
        recent_events=[
            LiveRuntimeEventRecord(
                sequence_id=1,
                name="preview.captured",
                emitted_at=utc_now(),
                instance_id="mumu-9",
                payload={"instance_id": "mumu-9", "frame_id": "frame-9", "image_path": "runtime_logs/previews/mumu-9-1.png"},
            )
        ],
        last_command_result=CommandDispatchResult(
            command_id="cmd-1",
            command_type=InstanceCommandType.PAUSE,
            instance_ids=["mumu-9"],
            status=CommandDispatchStatus.COMPLETED,
            message="pause routed to runtime",
        ),
        last_queue_result=None,
    )


def _build_vision_state():
    templates_root = Path(__file__).resolve().parents[2] / "assets" / "templates"
    repository = next(item for item in AnchorRepository.discover(templates_root) if item.repository_id == "common")
    anchor = repository.get_anchor("common.close_button")
    profile = CalibrationProfile(
        profile_id="calibration.mumu-9",
        instance_id="mumu-9",
        crop_region=(1, 2, 3, 4),
        anchor_overrides={"common.close_button": {"confidence_threshold": 0.95}},
    )
    match_result = build_match_result(
        source_image="runtime_logs/previews/mumu-9-1.png",
        candidates=[
            VisionMatch(
                anchor_id=anchor.anchor_id,
                confidence=0.94,
                bbox=(10, 20, 30, 40),
                source_image="runtime_logs/previews/mumu-9-1.png",
            )
        ],
        expected_anchor=anchor,
        message="Matched close button",
    )
    failure_record = build_failure_inspection(
        failure_id="failure-1",
        instance_id="mumu-9",
        screenshot_path="runtime_logs/previews/mumu-9-1.png",
        match_result=match_result,
        message="matched",
    )
    return build_vision_tooling_state(
        templates_root=templates_root,
        repository=repository,
        calibration_profile=profile,
        match_result=match_result,
        failure_record=failure_record,
        asset_inventory_path=Path(__file__).resolve().parents[2]
        / "src"
        / "roxauto"
        / "tasks"
        / "foundations"
        / "asset_inventory.json",
        selected_repository_id="common",
        source_image="runtime_logs/previews/mumu-9-1.png",
    )


def _queued_task(instance_id: str, task_id: str, name: str, priority: int) -> QueuedTask:
    manifest = TaskManifest(
        task_id=task_id,
        name=name,
        version="0.1.0",
        recovery_policy="abort",
    )
    spec = TaskSpec(
        task_id=task_id,
        name=name,
        version="0.1.0",
        entry_state="ready",
        manifest=manifest,
        steps=[TaskStep("noop", "No-op", lambda context: step_success("noop", "ok"))],
    )
    return QueuedTask(instance_id=instance_id, spec=spec, priority=priority)


def _task_foundations() -> TaskFoundationRepository:
    return TaskFoundationRepository.load_default()
