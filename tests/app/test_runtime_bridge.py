from __future__ import annotations

from dataclasses import replace
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.app.runtime_bridge import OperatorConsoleRuntimeBridge
from roxauto.core.models import (
    InstanceState,
    InstanceStatus,
    ProfileBinding,
    TaskManifest,
    TaskRunStatus,
    TaskRunTelemetry,
    TaskSpec,
    TaskStepTelemetry,
    TaskStepTelemetryStatus,
)
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import TaskStep, step_success
from roxauto.profiles import JsonProfileStore
from roxauto.tasks import TaskGapDomain, TaskReadinessRequirement, TaskReadinessState


class FakeAdapter:
    def __init__(self, preview_root: Path, *, healthy: bool = True) -> None:
        self._preview_root = preview_root
        self.healthy = healthy
        self.health_checks = 0
        self.screenshot_requests = 0
        self.taps: list[tuple[int, int]] = []
        self.swipes: list[tuple[tuple[int, int], tuple[int, int], int]] = []
        self.text_inputs: list[str] = []

    def capture_screenshot(self, instance: InstanceState) -> Path:
        self.screenshot_requests += 1
        path = self._preview_root / f"{instance.instance_id}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"preview")
        return path

    def tap(self, instance: InstanceState, point: tuple[int, int]) -> None:
        self.taps.append(point)

    def swipe(
        self,
        instance: InstanceState,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        self.swipes.append((start, end, duration_ms))

    def input_text(self, instance: InstanceState, text: str) -> None:
        self.text_inputs.append(text)

    def health_check(self, instance: InstanceState) -> bool:
        self.health_checks += 1
        return self.healthy


class OperatorConsoleRuntimeBridgeTests(unittest.TestCase):
    def test_refresh_polls_live_runtime_and_populates_snapshot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )

            snapshot = bridge.refresh()
            instance_snapshot = snapshot.get_instance_snapshot("mumu-0")
            console_snapshot = bridge.console_snapshot()

            self.assertEqual(snapshot.instances[0].instance_id, "mumu-0")
            self.assertIsNotNone(instance_snapshot)
            self.assertTrue(snapshot.last_sync_ok)
            self.assertEqual(len(snapshot.last_inspection_results), 1)
            self.assertIsNotNone(instance_snapshot.preview_frame)
            self.assertTrue(instance_snapshot.health_check_ok)
            self.assertEqual(adapter.health_checks, 1)
            self.assertEqual(adapter.screenshot_requests, 1)
            self.assertGreaterEqual(len(snapshot.recent_events), 2)
            self.assertEqual(console_snapshot.instances[0].metadata["profile_id"], "profile.mumu-0")
            self.assertEqual(
                console_snapshot.instances[0].metadata["preview_frame"],
                str((Path(temp_dir) / "mumu-0.png")),
            )

    def test_interaction_commands_refresh_runtime_contexts_without_extra_health_probe(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()

            dispatch = bridge.dispatch_manual_action(
                "tap",
                instance_id="mumu-0",
                payload={"x": 12, "y": 34},
            )

            self.assertEqual(dispatch.command_type.value, "tap")
            self.assertEqual(adapter.taps, [(12, 34)])
            self.assertEqual(adapter.health_checks, 1)
            self.assertEqual(adapter.screenshot_requests, 2)
            self.assertIsNotNone(bridge.selected_inspection_result("mumu-0"))
            self.assertEqual(bridge.snapshot().last_command_result.command_type.value, "tap")

    def test_dispatch_manual_actions_update_live_queue_and_global_stop_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0"), _instance("mumu-1")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            bridge.session.enqueue(QueuedTask(instance_id="mumu-0", spec=_success_spec(), priority=100))

            dispatch = bridge.dispatch_manual_action("start_queue", instance_id="mumu-0")
            snapshot = bridge.snapshot()

            self.assertEqual(dispatch.command_type.value, "start_queue")
            self.assertIsNotNone(snapshot.last_queue_result)
            self.assertEqual(snapshot.last_queue_result.instance_id, "mumu-0")
            self.assertEqual(len(snapshot.last_queue_result.runs), 1)
            self.assertEqual(len(bridge.queue_items("mumu-0")), 0)

            bridge.dispatch_manual_action("emergency_stop")

            self.assertTrue(bridge.global_emergency_stop_active())
            self.assertTrue(bridge.snapshot().get_instance_snapshot("mumu-0").context.stop_requested)
            self.assertTrue(bridge.snapshot().get_instance_snapshot("mumu-1").context.stop_requested)

    def test_vision_tooling_state_uses_shared_workspace_and_failure_contracts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=False)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()

            vision = bridge.vision_tooling_state("mumu-0")

            self.assertEqual(vision.workspace.selected_repository_id, "common")
            self.assertIsNotNone(vision.readiness)
            self.assertIsNotNone(vision.preview)
            self.assertEqual(vision.preview.metadata["kind"], "runtime_preview")
            self.assertIsNotNone(vision.capture.selected_artifact)
            self.assertEqual(vision.capture.selected_artifact.image_path, str((Path(temp_dir) / "mumu-0.png")))
            self.assertTrue(vision.failure.failure_id)
            self.assertEqual(vision.failure.instance_id, "mumu-0")
            self.assertGreaterEqual(vision.readiness.template_dependency_count, 1)

    def test_claim_rewards_workflow_can_queue_run_and_apply_editor_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()

            captured = bridge.capture_claim_rewards_source("mumu-0", source_kind="preview")
            bridge.update_claim_rewards_workflow(
                "mumu-0",
                workflow_mode="claimable",
                crop_region=(1, 2, 120, 80),
                match_region=(10, 20, 240, 120),
                confidence_threshold=0.96,
                capture_scale=1.5,
                capture_offset=(7, 8),
            )
            queued = bridge.queue_claim_rewards("mumu-0")
            queued_pane = bridge.claim_rewards_pane("mumu-0")

            dispatch = bridge.run_claim_rewards("mumu-0")
            pane = bridge.claim_rewards_pane("mumu-0")
            vision = bridge.vision_tooling_state("mumu-0")

            self.assertEqual(captured, str((Path(temp_dir) / "mumu-0.png")))
            self.assertEqual(queued.task_id, "daily_ui.claim_rewards")
            self.assertEqual(queued_pane.workflow_status, "queued")
            self.assertFalse(queued_pane.can_queue)
            self.assertTrue(queued_pane.can_run_now)
            self.assertTrue(queued_pane.is_queued)
            self.assertEqual(queued_pane.preset_summary, "每日任務 | 可執行 | 固定介面的每日獎勵領取流程。")
            self.assertEqual(queued_pane.active_step_summary, "已排入佇列，等待「開啟每日獎勵」。")
            self.assertEqual(
                queued_pane.next_action_summary,
                "保持佇列啟動；如果長時間沒有開始，先按「啟動佇列」再重新同步。",
            )
            self.assertEqual(queued_pane.failure_check_summary, "")
            self.assertEqual(queued_pane.editor.artifact_count, 1)
            self.assertEqual(queued_pane.editor.crop_region_text, "1,2,120,80")
            self.assertEqual(
                queued_pane.runtime_gate_summary,
                "目前沒有阻擋執行的 runtime 條件。",
            )
            self.assertIn("模擬器：", queued_pane.selected_scope_summary)
            self.assertIn("設定檔：mumu-0 profile", queued_pane.selected_scope_summary)
            self.assertEqual(queued_pane.step_rows[0].title, "開啟每日獎勵")
            self.assertEqual(queued_pane.step_rows[0].status_text, "等待開啟獎勵面板")
            self.assertEqual(dispatch.command_type.value, "start_queue")
            self.assertEqual(pane.workflow_status, "succeeded")
            self.assertEqual(pane.last_run_status, "succeeded")
            self.assertTrue(pane.can_queue)
            self.assertTrue(pane.can_run_now)
            self.assertEqual(pane.active_step_summary, "每日領獎已完成。")
            self.assertEqual(pane.failure_summary, "每日領獎已完成。")
            self.assertEqual(
                pane.next_action_summary,
                "本輪已完成；若要再跑一次，先確認遊戲仍停留在可開啟每日獎勵的主畫面。",
            )
            self.assertEqual(
                [row.status for row in pane.step_rows],
                ["succeeded", "succeeded", "succeeded", "succeeded", "succeeded"],
            )
            self.assertEqual(pane.step_rows[2].title, "點擊領獎")
            self.assertEqual(pane.step_rows[2].status_text, "已完成領獎點擊")
            self.assertEqual(vision.workspace.selected_repository_id, "daily_ui")
            self.assertIsNotNone(vision.calibration.selected_resolution)
            self.assertEqual(
                vision.calibration.selected_resolution.effective_confidence_threshold,
                0.96,
            )
            self.assertIsNotNone(vision.capture.crop_region)
            self.assertEqual(vision.capture.crop_region.to_tuple(), (1, 2, 120, 80))

    def test_claim_rewards_workflow_reports_failed_step_and_failure_surface(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            bridge.capture_claim_rewards_source("mumu-0", source_kind="preview")
            bridge.update_claim_rewards_workflow("mumu-0", workflow_mode="ambiguous")

            bridge.run_claim_rewards("mumu-0")
            pane = bridge.claim_rewards_pane("mumu-0")
            vision = bridge.vision_tooling_state("mumu-0")

            self.assertEqual(pane.workflow_status, "failed")
            self.assertEqual(pane.failure_step_id, "verify_claim_affordance")
            self.assertEqual(pane.failure_reason, "獎勵狀態無法辨識")
            self.assertEqual(pane.failure_summary, "獎勵狀態無法辨識：無法分辨目前是可領取、已領取或需要確認。")
            self.assertEqual(pane.active_step_summary, "獎勵狀態無法辨識：無法分辨目前是可領取、已領取或需要確認。")
            self.assertEqual(pane.current_step_title, "確認獎勵狀態")
            self.assertEqual(
                pane.failure_check_summary,
                "確認彈窗 | 對應步驟：確認獎勵狀態 | 檢查結果：已命中 | 已看到確認彈窗。",
            )
            self.assertTrue(pane.next_action_summary.startswith("先確認是否真的出現確認彈窗；若有，"))
            self.assertIn("門檻", pane.next_action_summary)
            self.assertIn("比對區域", pane.next_action_summary)
            self.assertIn("daily_ui.reward_confirm_state", pane.next_action_summary)
            self.assertIn("daily_ui.reward_confirm_state", pane.selected_anchor_summary)
            self.assertIn("curated_stand_in", pane.selected_provenance_summary)
            self.assertIn("repo_curated_baseline", pane.selected_provenance_summary)
            self.assertIn("provenance=curated_stand_in", pane.selected_curation_summary)
            self.assertIn("Confirmation modal detected.", pane.failure_explanation)
            self.assertIn("curated stand-in", pane.failure_explanation)
            self.assertIn("門檻=", pane.selected_anchor_summary)
            self.assertIn("區域=", pane.selected_anchor_summary)
            self.assertEqual(pane.step_rows[0].status, "succeeded")
            self.assertEqual(pane.step_rows[1].status, "failed")
            self.assertEqual(pane.step_rows[1].title, "確認獎勵狀態")
            self.assertEqual(pane.step_rows[1].status_text, "獎勵狀態辨識失敗")
            self.assertEqual(
                [row.status for row in pane.step_rows[2:]],
                ["pending", "pending", "pending"],
            )
            self.assertTrue(vision.failure.failure_id)
            self.assertEqual(vision.failure.anchor_id, "daily_ui.claim_reward")
            self.assertEqual(vision.failure.status.value, "missed")
            self.assertIsNotNone(vision.failure.claim_rewards)
            self.assertEqual(vision.failure.claim_rewards.selected_check_id, "confirm_state")
            self.assertIn("current=confirm_state", vision.failure.claim_rewards.workflow_summary)

    def test_claim_rewards_pane_disables_actions_when_runtime_readiness_is_blocked(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            readiness = bridge._task_foundations.evaluate_task_readiness("daily_ui.claim_rewards")
            blocked_requirement = TaskReadinessRequirement(
                requirement_id="runtime.daily_ui.dispatch_bridge",
                domain=TaskGapDomain.RUNTIME,
                summary="Daily UI fixed-flow tasks require a production runtime action-dispatch bridge.",
                satisfied=False,
                blocking=True,
            )
            blocked_readiness = replace(
                readiness,
                implementation_readiness_state=TaskReadinessState.BLOCKED_BY_RUNTIME,
                implementation_requirements=[blocked_requirement],
            )
            bridge._task_foundations.evaluate_task_readiness = lambda task_id: blocked_readiness

            pane = bridge.claim_rewards_pane("mumu-0")
            state = bridge.get_live_state("mumu-0")

            self.assertFalse(pane.can_queue)
            self.assertFalse(pane.can_run_now)
            self.assertEqual(pane.task_id, "daily_ui.claim_rewards")
            self.assertEqual(pane.task_name, "每日領獎")
            self.assertIn("production runtime action-dispatch bridge", pane.runtime_gate_summary)
            self.assertIn("production runtime action-dispatch bridge", pane.workflow_banner)
            self.assertEqual(
                pane.active_step_summary,
                "每日領獎目前尚未就緒：Daily UI fixed-flow tasks require a production runtime action-dispatch bridge.",
            )
            self.assertFalse(state.claim_rewards.can_queue)
            self.assertFalse(state.claim_rewards.can_run_now)
            with self.assertRaisesRegex(ValueError, "production runtime action-dispatch bridge"):
                bridge.queue_claim_rewards("mumu-0")

    def test_get_live_state_projects_cached_state_without_refreshing_runtime(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()

            state = bridge.get_live_state("mumu-0")

            self.assertEqual(adapter.health_checks, 1)
            self.assertEqual(adapter.screenshot_requests, 1)
            self.assertEqual(state.selected_instance_id, "mumu-0")
            self.assertEqual(state.claim_rewards.task_id, "daily_ui.claim_rewards")

    def test_claim_rewards_pane_uses_runtime_owned_last_run_when_bridge_record_is_empty(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            bridge.run_claim_rewards("mumu-0")
            bridge._claim_rewards_records.clear()

            pane = bridge.claim_rewards_pane("mumu-0")

            self.assertEqual(pane.workflow_status, "succeeded")
            self.assertEqual(pane.last_run_status, "succeeded")
            self.assertTrue(pane.last_run_id)
            self.assertEqual(
                [row.status for row in pane.step_rows],
                ["succeeded", "succeeded", "succeeded", "succeeded", "succeeded"],
            )

    def test_claim_rewards_pane_uses_runtime_owned_active_run_when_bridge_record_is_empty(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            snapshot = bridge.snapshot().get_instance_snapshot("mumu-0")
            assert snapshot is not None
            assert snapshot.context is not None
            snapshot.context.active_task_id = "daily_ui.claim_rewards"
            snapshot.context.active_run_id = "run-active"
            snapshot.context.active_task_run = _running_claim_rewards_telemetry()
            bridge._claim_rewards_records.clear()

            pane = bridge.claim_rewards_pane("mumu-0")

            self.assertEqual(pane.workflow_status, "running")
            self.assertEqual(
                [row.status for row in pane.step_rows],
                ["succeeded", "succeeded", "running", "pending", "pending"],
            )
            self.assertTrue(pane.step_rows[2].is_current)
            self.assertEqual(pane.current_step_title, pane.step_rows[2].title)

    def test_vision_tooling_rebuilds_claim_failure_from_runtime_last_run_when_metadata_is_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            bridge.capture_claim_rewards_source("mumu-0", source_kind="preview")
            bridge.update_claim_rewards_workflow("mumu-0", workflow_mode="ambiguous")
            bridge.run_claim_rewards("mumu-0")

            snapshot = bridge.snapshot().get_instance_snapshot("mumu-0")
            assert snapshot is not None
            assert snapshot.context is not None
            assert snapshot.context.last_failure_snapshot is not None
            snapshot.context.last_failure_snapshot.metadata.pop("claim_rewards", None)
            snapshot.context.last_failure_snapshot.metadata.pop("anchor_id", None)
            snapshot.context.last_failure_snapshot.metadata.pop("expected_anchor_id", None)
            bridge._claim_rewards_records.clear()

            vision = bridge.vision_tooling_state("mumu-0")
            pane = bridge.claim_rewards_pane("mumu-0")

            self.assertEqual(vision.workspace.selected_repository_id, "daily_ui")
            self.assertIsNotNone(vision.failure.claim_rewards)
            assert vision.failure.claim_rewards is not None
            self.assertEqual(vision.failure.claim_rewards.selected_check_id, "confirm_state")
            self.assertEqual(
                vision.failure.claim_rewards.selected_anchor_id,
                "daily_ui.reward_confirm_state",
            )
            self.assertTrue(vision.failure.claim_rewards.selected_template_path.endswith("daily_reward_confirm_state.png"))
            self.assertEqual(pane.workflow_status, "failed")
            self.assertEqual(pane.failure_step_id, "verify_claim_affordance")
            self.assertIn("daily_ui.reward_confirm_state", pane.selected_anchor_summary)
            self.assertIn("curated_stand_in", pane.selected_provenance_summary)
            self.assertIn("provenance=curated_stand_in", pane.selected_curation_summary)
            self.assertIn("Confirmation modal detected.", pane.failure_explanation)
            self.assertIn("門檻=", pane.selected_anchor_summary)
            self.assertIn("區域=", pane.selected_anchor_summary)
            self.assertIn("門檻", pane.next_action_summary)
            self.assertIn("比對區域", pane.next_action_summary)

    def test_scheduled_claim_rewards_run_updates_live_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            bridge.start_live_updates(poll_interval_sec=60.0, bootstrap=False)
            try:
                bridge.schedule_claim_rewards_run("mumu-0")
                self.assertTrue(bridge.wait_for_idle(timeout_sec=5.0))

                state = bridge.get_live_state("mumu-0")

                self.assertEqual(state.claim_rewards.workflow_status, "succeeded")
                self.assertEqual(
                    [row.status for row in state.claim_rewards.step_rows],
                    ["succeeded", "succeeded", "succeeded", "succeeded", "succeeded"],
                )
            finally:
                bridge.stop_live_updates()

    def test_save_claim_rewards_editor_profile_persists_profile_file(self) -> None:
        with TemporaryDirectory() as temp_dir, TemporaryDirectory() as profile_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                profiles_root=Path(profile_dir),
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
                profile_resolver=lambda instance: _profile_binding(instance.instance_id),
            )
            bridge.refresh()
            bridge.update_claim_rewards_workflow(
                "mumu-0",
                crop_region=(1, 2, 120, 80),
                match_region=(10, 20, 240, 120),
                confidence_threshold=0.96,
                capture_scale=1.5,
                capture_offset=(7, 8),
            )

            saved_path = bridge.save_claim_rewards_editor_profile("mumu-0")
            saved = JsonProfileStore(Path(profile_dir)).load("profile.mumu-0")

            self.assertEqual(saved_path, Path(profile_dir) / "profile.mumu-0.json")
            self.assertIsNotNone(saved)
            assert saved is not None
            self.assertIsNotNone(saved.calibration)
            self.assertEqual(saved.calibration.capture_offset, (7, 8))
            self.assertEqual(saved.calibration.capture_scale, 1.5)
            self.assertEqual(saved.calibration.crop_box, (1, 2, 120, 80))
            self.assertEqual(
                saved.calibration.anchor_overrides["daily_ui.claim_reward"]["match_region"],
                [10, 20, 240, 120],
            )
            pane = bridge.claim_rewards_pane("mumu-0")
            self.assertIn("profile.mumu-0.json", pane.editor.persistence_summary)

    def test_default_profile_resolver_reloads_saved_claim_rewards_profile(self) -> None:
        with TemporaryDirectory() as temp_dir, TemporaryDirectory() as profile_dir:
            adapter = FakeAdapter(Path(temp_dir), healthy=True)
            bridge = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                profiles_root=Path(profile_dir),
                doctor_report_provider=_doctor_report,
                adapter=adapter,
                discovery=lambda: [_instance("mumu-0")],
            )
            bridge.refresh()
            bridge.update_claim_rewards_workflow(
                "mumu-0",
                crop_region=(2, 4, 90, 60),
                match_region=(11, 22, 180, 90),
                confidence_threshold=0.91,
                capture_scale=1.4,
                capture_offset=(5, 6),
            )
            bridge.save_claim_rewards_editor_profile("mumu-0")

            second_adapter = FakeAdapter(Path(temp_dir), healthy=True)
            reloaded = OperatorConsoleRuntimeBridge(
                workspace_root=Path(__file__).resolve().parents[2],
                profiles_root=Path(profile_dir),
                doctor_report_provider=_doctor_report,
                adapter=second_adapter,
                discovery=lambda: [_instance("mumu-0")],
            )
            reloaded.refresh()

            pane = reloaded.claim_rewards_pane("mumu-0")
            snapshot = reloaded.snapshot().get_instance_snapshot("mumu-0")

            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.profile_binding.capture_scale, 1.4)
            self.assertEqual(snapshot.profile_binding.capture_offset, (5, 6))
            self.assertEqual(pane.editor.crop_region_text, "2,4,90,60")
            self.assertIn("profile.mumu-0.json", pane.editor.persistence_summary)


def _instance(instance_id: str) -> InstanceState:
    return InstanceState(
        instance_id=instance_id,
        label=instance_id.replace("mumu", "MuMu "),
        adb_serial=f"127.0.0.1:{16384 + int(instance_id.split('-')[1]) * 32}",
        status=InstanceStatus.READY,
    )


def _running_claim_rewards_telemetry() -> TaskRunTelemetry:
    return TaskRunTelemetry(
        task_id="daily_ui.claim_rewards",
        run_id="run-active",
        status=TaskRunStatus.RUNNING,
        step_count=5,
        completed_step_count=2,
        current_step_id="claim_reward",
        current_step_index=2,
        steps=[
            TaskStepTelemetry(
                step_id="open_reward_panel",
                description="Open reward panel",
                status=TaskStepTelemetryStatus.SUCCEEDED,
                message="ok",
            ),
            TaskStepTelemetry(
                step_id="verify_claim_affordance",
                description="Verify claim affordance",
                status=TaskStepTelemetryStatus.SUCCEEDED,
                message="ok",
            ),
            TaskStepTelemetry(
                step_id="claim_reward",
                description="Claim reward",
                status=TaskStepTelemetryStatus.RUNNING,
                message="running",
            ),
            TaskStepTelemetry(
                step_id="confirm_reward_claim",
                description="Confirm reward",
                status=TaskStepTelemetryStatus.PENDING,
            ),
            TaskStepTelemetry(
                step_id="verify_claimed",
                description="Verify claimed",
                status=TaskStepTelemetryStatus.PENDING,
            ),
        ],
    )


def _profile_binding(instance_id: str) -> ProfileBinding:
    return ProfileBinding(
        profile_id=f"profile.{instance_id}",
        display_name=f"{instance_id} profile",
        server_name="TW-1",
        character_name="Knight",
        allowed_tasks=["common.preview"],
        calibration_id=f"calibration.{instance_id}",
        capture_offset=(12, 24),
        capture_scale=1.25,
        settings={"anchor_overrides": {"common.close_button": {"confidence_threshold": 0.91}}},
        metadata={"repository_id": "common"},
    )


def _doctor_report() -> dict[str, object]:
    return {
        "packages": {"PySide6": True, "adbutils": True, "cv2": False},
        "adb": {"path": "C:/platform-tools/adb.exe", "instances_found": 1},
        "instances": [],
    }


def _success_spec() -> TaskSpec:
    manifest = TaskManifest(
        task_id="task.success",
        name="Success Task",
        version="0.1.0",
        recovery_policy="abort",
    )
    return TaskSpec(
        task_id="task.success",
        name="Success Task",
        version="0.1.0",
        entry_state="ready",
        manifest=manifest,
        steps=[TaskStep("step-a", "No-op", lambda ctx: step_success("step-a", "ok"))],
    )
