from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import InstanceCommandType
from roxauto.core.models import InstanceState, InstanceStatus, PreviewFrame, TaskRunStatus, VisionMatch
from roxauto.core.runtime import (
    TaskActionDispatchResult,
    TaskExecutionContext,
    TaskHealthCheckResult,
    TaskRunner,
)
from roxauto.tasks import TaskFoundationRepository
from roxauto.tasks.daily_ui import (
    build_claim_rewards_task_display_model,
    build_claim_rewards_task_preset,
    ClaimRewardsInspection,
    ClaimRewardsNavigationPlan,
    ClaimRewardsPanelState,
    build_claim_rewards_runtime_input,
    TemplateMatcherClaimRewardsVisionGateway,
    build_claim_rewards_task_spec,
    load_claim_rewards_anchor_specs,
    load_claim_rewards_display_metadata,
)


class FakeAdapter:
    def __init__(self) -> None:
        self.screenshot_requests = 0
        self.taps: list[tuple[int, int]] = []

    def capture_screenshot(self, instance: InstanceState) -> Path:
        self.screenshot_requests += 1
        return Path("captures") / f"{instance.instance_id}-{self.screenshot_requests}.png"

    def tap(self, instance: InstanceState, point: tuple[int, int]) -> None:
        self.taps.append(point)

    def swipe(
        self,
        instance: InstanceState,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        return None

    def input_text(self, instance: InstanceState, text: str) -> None:
        return None

    def health_check(self, instance: InstanceState) -> bool:
        return True


class FakeTaskActionBridge:
    def __init__(
        self,
        *,
        instance_id: str,
        task_id: str,
        task_metadata: dict[str, object],
        tap_statuses: list[str] | None = None,
    ) -> None:
        self.instance_id = instance_id
        self.task_id = task_id
        self.queue_id = "queue-1"
        self._task_metadata = task_metadata
        self._tap_statuses = list(tap_statuses or [])
        self._command_count = 0
        self._preview_count = 0
        self.taps: list[dict[str, object]] = []
        self.preview_calls: list[dict[str, object]] = []

    def dispatch(self, command, *, step_id=None, metadata=None):
        raise NotImplementedError

    def tap(self, point: tuple[int, int], *, step_id=None, metadata=None) -> TaskActionDispatchResult:
        self._command_count += 1
        status = self._tap_statuses.pop(0) if self._tap_statuses else "executed"
        message = "" if status == "executed" else "tap rejected for test"
        payload = {"point": point}
        result = TaskActionDispatchResult(
            command_id=f"cmd-{self._command_count}",
            command_type=InstanceCommandType.TAP,
            instance_id=self.instance_id,
            status=status,
            message=message,
            payload=payload,
            metadata={"task_id": self.task_id, **dict(metadata or {})},
        )
        self.taps.append(
            {
                "point": point,
                "step_id": step_id,
                "metadata": dict(metadata or {}),
                "status": status,
            }
        )
        self._task_metadata["last_task_action_type"] = result.command_type.value
        self._task_metadata["last_task_action_status"] = result.status
        self._task_metadata["last_task_action_message"] = result.message
        if step_id is not None:
            self._task_metadata["last_task_action_step_id"] = step_id
        return result

    def swipe(self, start, end, *, duration_ms=250, step_id=None, metadata=None):
        raise NotImplementedError

    def input_text(self, text, *, step_id=None, metadata=None):
        raise NotImplementedError

    def capture_preview(self, *, step_id=None, metadata=None) -> PreviewFrame:
        self._preview_count += 1
        frame = PreviewFrame(
            frame_id=f"frame-{self._preview_count}",
            instance_id=self.instance_id,
            image_path=f"captures/bridge-{self._preview_count}.png",
            source="task_action_bridge",
            metadata=dict(metadata or {}),
        )
        self.preview_calls.append(
            {
                "step_id": step_id,
                "metadata": dict(metadata or {}),
                "image_path": frame.image_path,
            }
        )
        self._task_metadata["preview_frame"] = frame
        if step_id is not None:
            self._task_metadata["last_preview_step_id"] = step_id
        return frame

    def check_health(self, *, step_id=None, metadata=None) -> TaskHealthCheckResult:
        return TaskHealthCheckResult(
            instance_id=self.instance_id,
            healthy=True,
            message="healthy",
            metadata={"task_id": self.task_id, **dict(metadata or {})},
        )


class ScriptedVisionGateway:
    def __init__(self, inspections: list[ClaimRewardsInspection]) -> None:
        self._inspections = list(inspections)
        self.calls: list[dict[str, object]] = []

    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        anchor_specs,
        metadata=None,
    ) -> ClaimRewardsInspection:
        inspection = self._inspections[len(self.calls)]
        self.calls.append(
            {
                "instance_id": instance.instance_id,
                "screenshot_path": str(screenshot_path),
                "metadata": dict(metadata or {}),
                "anchor_ids": sorted(anchor_specs),
            }
        )
        return replace(inspection, screenshot_path=str(screenshot_path))


class FakeMatcher:
    def __init__(self, matches_by_anchor: dict[str, list[VisionMatch]]) -> None:
        self.matches_by_anchor = matches_by_anchor

    def match(self, image_path: Path, anchor, *, instance: InstanceState, metadata=None):
        return list(self.matches_by_anchor.get(anchor.anchor_id, []))


class ClaimRewardsTaskBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )
        self.navigation_plan = ClaimRewardsNavigationPlan(open_panel_point=(100, 200))

    def test_runtime_input_aligns_builder_input_readiness_and_blueprint(self) -> None:
        builder_input = self.repository.build_runtime_builder_input("daily_ui.claim_rewards")
        readiness = self.repository.evaluate_task_readiness("daily_ui.claim_rewards")

        runtime_input = build_claim_rewards_runtime_input(
            builder_input=builder_input,
            readiness_report=readiness,
            foundation_repository=self.repository,
        )

        self.assertEqual(runtime_input.task_id, "daily_ui.claim_rewards")
        self.assertEqual(runtime_input.builder_input.task_id, "daily_ui.claim_rewards")
        self.assertEqual(runtime_input.readiness_report.implementation_readiness_state.value, "ready")
        self.assertEqual(runtime_input.fixture_profile.fixture_id, "fixture.tw.daily_ui.default")
        self.assertEqual(runtime_input.display_metadata.locale, "zh-TW")
        self.assertEqual(runtime_input.display_metadata.display_name, "每日領獎")
        self.assertEqual(
            runtime_input.required_anchor_ids,
            [
                "daily_ui.reward_panel",
                "daily_ui.claim_reward",
                "daily_ui.reward_confirm_state",
                "common.confirm_button",
                "common.close_button",
            ],
        )
        self.assertEqual(
            [step.step_id for step in runtime_input.step_specs],
            [
                "open_reward_panel",
                "verify_claim_affordance",
                "claim_reward",
                "confirm_reward_claim",
                "verify_claimed",
            ],
        )
        self.assertEqual(runtime_input.step_specs[0].anchor_id, "daily_ui.reward_panel")
        self.assertEqual(runtime_input.step_specs[2].anchor_id, "daily_ui.claim_reward")
        self.assertEqual(runtime_input.step_specs[3].anchor_id, "common.confirm_button")
        self.assertEqual(runtime_input.step_specs[0].display_name, "開啟每日獎勵")
        self.assertEqual(runtime_input.step_specs[2].status_texts["running"], "正在點擊領獎")
        self.assertEqual(
            runtime_input.step_specs[4].metadata["signal_anchor_ids"],
            [
                "daily_ui.reward_panel",
                "daily_ui.claim_reward",
                "daily_ui.reward_confirm_state",
                "common.close_button",
            ],
        )
        self.assertEqual(
            runtime_input.display_metadata.metadata["signal_contract_version"],
            "claim_rewards.v2",
        )

    def test_task_spec_builder_embeds_runtime_input_metadata(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        runtime_input = build_claim_rewards_runtime_input(foundation_repository=self.repository)

        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            runtime_input=runtime_input,
            vision_gateway=gateway,
        )

        self.assertEqual(spec.metadata["implementation_readiness_state"], "ready")
        self.assertEqual(spec.metadata["builder_input"]["task_id"], "daily_ui.claim_rewards")
        self.assertEqual(spec.metadata["runtime_input"]["fixture_id"], "fixture.tw.daily_ui.default")
        self.assertEqual(spec.metadata["product_display"]["display_name"], "每日領獎")
        self.assertEqual(spec.metadata["task_preset"]["display_name"], "每日領獎")
        self.assertEqual(spec.name, "每日領獎")
        self.assertEqual(
            [step.step_id for step in spec.steps],
            [step.step_id for step in runtime_input.step_specs],
        )
        self.assertEqual(spec.steps[0].description, "開啟固定的每日獎勵面板。")

    def test_load_display_metadata_and_task_preset_for_gui(self) -> None:
        display_metadata = load_claim_rewards_display_metadata(self.repository)
        runtime_input = build_claim_rewards_runtime_input(foundation_repository=self.repository)
        preset = build_claim_rewards_task_preset(runtime_input=runtime_input)

        self.assertEqual(display_metadata.display_name, "每日領獎")
        self.assertEqual(display_metadata.description, "開啟固定每日獎勵面板並完成領獎，必要時確認彈窗。")
        self.assertEqual(display_metadata.status_texts["ready"], "可執行")
        self.assertEqual(display_metadata.failure_reason_map()["claim_tap_no_effect"].title, "領獎點擊沒有生效")
        self.assertEqual(
            display_metadata.failure_reason_map()["runtime_dispatch_failed"].title,
            "Runtime bridge 派送失敗",
        )
        self.assertEqual(preset.display_name, "每日領獎")
        self.assertEqual(preset.category_label, "每日任務")
        self.assertEqual(preset.readiness_state, "ready")
        self.assertEqual(preset.status_text, "可執行")

    def test_build_display_model_projects_gui_labels_and_failure_reason(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
            ]
        )
        runtime_input = build_claim_rewards_runtime_input(foundation_repository=self.repository)
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            runtime_input=runtime_input,
            vision_gateway=gateway,
        )
        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        display_model = build_claim_rewards_task_display_model(run=run, runtime_input=runtime_input)

        self.assertEqual(display_model.display_name, "每日領獎")
        self.assertEqual(display_model.status, "failed")
        self.assertEqual(display_model.status_text, "執行失敗")
        self.assertEqual(display_model.failure_reason.reason_id, "claim_tap_no_effect")
        self.assertEqual(display_model.failure_reason.title, "領獎點擊沒有生效")
        self.assertEqual(display_model.steps[0].display_name, "開啟每日獎勵")
        self.assertEqual(display_model.steps[0].status_text, "已開啟獎勵面板")
        self.assertEqual(display_model.steps[2].status_text, "領獎點擊失敗")
        self.assertEqual(display_model.steps[2].failure_reason.reason_id, "claim_tap_no_effect")
        self.assertEqual(display_model.steps[2].metadata["outcome_code"], "claim_tap_no_effect")
        self.assertIn("畫面沒有進入已領取或待確認狀態", display_model.status_summary)

    def test_template_match_gateway_classifies_reward_panel_states(self) -> None:
        anchors = load_claim_rewards_anchor_specs()
        cases = [
            (
                "claimable",
                {
                    "daily_ui.reward_panel": [
                        VisionMatch(
                            anchor_id="daily_ui.reward_panel",
                            confidence=0.97,
                            bbox=(20, 20, 1180, 820),
                            source_image="captures/frame.png",
                        )
                    ],
                    "daily_ui.claim_reward": [
                        VisionMatch(
                            anchor_id="daily_ui.claim_reward",
                            confidence=0.96,
                            bbox=(40, 60, 100, 50),
                            source_image="captures/frame.png",
                        )
                    ]
                },
                ClaimRewardsPanelState.CLAIMABLE,
                (90, 85),
            ),
            (
                "confirm_required",
                {
                    "daily_ui.reward_panel": [
                        VisionMatch(
                            anchor_id="daily_ui.reward_panel",
                            confidence=0.95,
                            bbox=(20, 20, 1180, 820),
                            source_image="captures/frame.png",
                        )
                    ],
                    "daily_ui.claim_reward": [
                        VisionMatch(
                            anchor_id="daily_ui.claim_reward",
                            confidence=0.94,
                            bbox=(40, 60, 100, 50),
                            source_image="captures/frame.png",
                        )
                    ],
                    "common.confirm_button": [
                        VisionMatch(
                            anchor_id="common.confirm_button",
                            confidence=0.97,
                            bbox=(400, 500, 120, 60),
                            source_image="captures/frame.png",
                        )
                    ],
                    "daily_ui.reward_confirm_state": [
                        VisionMatch(
                            anchor_id="daily_ui.reward_confirm_state",
                            confidence=0.96,
                            bbox=(300, 180, 640, 360),
                            source_image="captures/frame.png",
                        )
                    ],
                },
                ClaimRewardsPanelState.CONFIRM_REQUIRED,
                (460, 530),
            ),
            (
                "claimed",
                {
                    "daily_ui.reward_panel": [
                        VisionMatch(
                            anchor_id="daily_ui.reward_panel",
                            confidence=0.94,
                            bbox=(20, 20, 1180, 820),
                            source_image="captures/frame.png",
                        )
                    ],
                    "common.close_button": [
                        VisionMatch(
                            anchor_id="common.close_button",
                            confidence=0.93,
                            bbox=(1100, 40, 40, 40),
                            source_image="captures/frame.png",
                        )
                    ]
                },
                ClaimRewardsPanelState.CLAIMED,
                (1120, 60),
            ),
        ]

        for label, matches_by_anchor, expected_state, expected_point in cases:
            with self.subTest(label=label):
                gateway = TemplateMatcherClaimRewardsVisionGateway(FakeMatcher(matches_by_anchor))

                inspection = gateway.inspect(
                    instance=self.instance,
                    screenshot_path=Path("captures/frame.png"),
                    anchor_specs=anchors,
                    metadata={"reason": label},
                )

                self.assertEqual(inspection.state, expected_state)
                self.assertTrue(inspection.signals["reward_panel_visible"])
                if expected_state is ClaimRewardsPanelState.CLAIMABLE:
                    self.assertEqual(inspection.claim_point, expected_point)
                elif expected_state is ClaimRewardsPanelState.CONFIRM_REQUIRED:
                    self.assertEqual(inspection.confirm_point, expected_point)
                    self.assertTrue(inspection.signals["confirm_state_visible"])
                else:
                    self.assertEqual(inspection.close_point, expected_point)

    def test_claim_rewards_run_succeeds_without_confirmation(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual([result.step_id for result in run.step_results], [
            "open_reward_panel",
            "verify_claim_affordance",
            "claim_reward",
            "confirm_reward_claim",
            "verify_claimed",
        ])
        self.assertEqual(adapter.taps, [(640, 360)])
        self.assertEqual(gateway.calls[0]["metadata"]["reason"], "open_reward_panel.precheck")
        self.assertEqual(run.step_results[0].data["outcome_code"], "open_panel_already_claimable")
        self.assertEqual(run.step_results[2].data["outcome_code"], "claim_tap_advanced_to_claimed")

    def test_claim_rewards_run_handles_confirmation_modal(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CONFIRM_REQUIRED, confirm_point=(700, 500)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.taps, [(640, 360), (700, 500)])
        self.assertEqual(run.step_results[2].data["outcome_code"], "claim_tap_advanced_to_confirm_required")
        self.assertEqual(run.step_results[3].data["outcome_code"], "confirm_completed")

    def test_claim_rewards_run_recovers_when_confirmation_modal_is_already_open(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CONFIRM_REQUIRED, confirm_point=(700, 500)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.taps, [(700, 500)])
        self.assertEqual(
            run.step_results[2].message,
            "Claim action already advanced to the confirmation modal; tap is not required.",
        )
        self.assertEqual(len(gateway.calls), 3)
        self.assertEqual(run.step_results[0].data["outcome_code"], "open_panel_already_confirm_required")
        self.assertEqual(run.step_results[2].data["outcome_code"], "claim_already_confirm_required")

    def test_claim_rewards_run_skips_tap_when_reward_is_already_claimed(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.taps, [])
        self.assertEqual(run.step_results[2].message, "Reward is already claimed; tap is not required.")
        self.assertEqual(run.step_results[0].data["outcome_code"], "open_panel_already_claimed")
        self.assertEqual(run.step_results[2].data["outcome_code"], "claim_already_claimed")

    def test_claim_rewards_run_fails_when_panel_cannot_be_confirmed(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.UNAVAILABLE),
                _inspection(ClaimRewardsPanelState.UNAVAILABLE),
                _inspection(ClaimRewardsPanelState.UNAVAILABLE),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.FAILED)
        self.assertEqual(run.step_results[0].step_id, "open_reward_panel")
        self.assertEqual(adapter.taps, [(100, 200)])
        self.assertEqual(run.step_results[0].data["failure_reason_id"], "reward_panel_unavailable")
        self.assertEqual(run.step_results[0].data["outcome_code"], "open_panel_unverified")
        self.assertEqual(len(run.step_results[0].data["inspection_attempts"]), 2)

    def test_claim_rewards_run_fails_when_claim_tap_does_not_advance(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.FAILED)
        self.assertEqual(run.step_results[-1].step_id, "claim_reward")
        self.assertEqual(adapter.taps, [(640, 360)])
        self.assertEqual(run.step_results[-1].data["failure_reason_id"], "claim_tap_no_effect")
        self.assertEqual(run.step_results[-1].data["outcome_code"], "claim_tap_no_effect")
        self.assertEqual(len(run.step_results[-1].data["inspection_attempts"]), 2)

    def test_claim_rewards_run_retries_panel_open_and_claim_follow_up(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.UNAVAILABLE),
                _inspection(ClaimRewardsPanelState.UNAVAILABLE),
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CONFIRM_REQUIRED, confirm_point=(700, 500)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.taps, [(100, 200), (640, 360), (700, 500)])
        self.assertEqual(run.step_results[0].data["outcome_code"], "open_panel_verified_claimable")
        self.assertEqual(len(run.step_results[0].data["inspection_attempts"]), 2)
        self.assertEqual(run.step_results[2].data["outcome_code"], "claim_tap_advanced_to_confirm_required")
        self.assertEqual(len(run.step_results[2].data["inspection_attempts"]), 2)

    def test_claim_rewards_run_retries_final_claimed_verification(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.UNAVAILABLE),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(run.step_results[-1].data["outcome_code"], "claimed_verified")
        self.assertEqual(len(run.step_results[-1].data["inspection_attempts"]), 2)

    def test_claim_rewards_run_prefers_runtime_action_bridge_for_preview_and_taps(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
                _inspection(ClaimRewardsPanelState.CLAIMED, close_point=(1180, 80)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )
        task_metadata: dict[str, object] = {}
        bridge = FakeTaskActionBridge(
            instance_id=self.instance.instance_id,
            task_id="daily_ui.claim_rewards",
            task_metadata=task_metadata,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(
                instance=self.instance,
                action_bridge=bridge,
                metadata=task_metadata,
            ),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.screenshot_requests, 0)
        self.assertEqual(adapter.taps, [])
        self.assertEqual(
            [tap["point"] for tap in bridge.taps],
            [(640, 360)],
        )
        self.assertEqual(
            Path(gateway.calls[0]["screenshot_path"]).as_posix(),
            "captures/bridge-1.png",
        )
        self.assertEqual(task_metadata["last_task_action_status"], "executed")
        self.assertEqual(task_metadata["last_preview_step_id"], "verify_claimed")
        self.assertNotIn("task_action", run.step_results[0].data)
        self.assertEqual(run.step_results[2].data["task_action"]["status"], "executed")
        self.assertEqual(run.step_results[2].data["telemetry"]["task_action"]["source"], "task_action_bridge")

    def test_claim_rewards_run_fails_when_runtime_bridge_rejects_claim_tap(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _inspection(ClaimRewardsPanelState.CLAIMABLE, claim_point=(640, 360)),
            ]
        )
        spec = build_claim_rewards_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )
        task_metadata: dict[str, object] = {}
        bridge = FakeTaskActionBridge(
            instance_id=self.instance.instance_id,
            task_id="daily_ui.claim_rewards",
            task_metadata=task_metadata,
            tap_statuses=["rejected"],
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(
                instance=self.instance,
                action_bridge=bridge,
                metadata=task_metadata,
            ),
        )

        self.assertEqual(run.status, TaskRunStatus.FAILED)
        self.assertEqual(run.step_results[-1].step_id, "claim_reward")
        self.assertIn("runtime bridge", run.step_results[-1].message)
        self.assertEqual(adapter.screenshot_requests, 0)
        self.assertEqual(adapter.taps, [])
        self.assertEqual(len(bridge.preview_calls), 1)
        self.assertEqual(run.step_results[-1].data["task_action"]["status"], "rejected")
        self.assertEqual(run.step_results[-1].data["failure_reason_id"], "runtime_dispatch_failed")
        self.assertEqual(run.step_results[-1].data["outcome_code"], "claim_dispatch_failed")


def _inspection(
    state: ClaimRewardsPanelState,
    *,
    claim_point: tuple[int, int] | None = None,
    confirm_point: tuple[int, int] | None = None,
    close_point: tuple[int, int] | None = None,
    signals: dict[str, bool] | None = None,
) -> ClaimRewardsInspection:
    inspection_signals = {
        "reward_panel_visible": state is not ClaimRewardsPanelState.UNAVAILABLE,
        "claim_button_visible": state is ClaimRewardsPanelState.CLAIMABLE or claim_point is not None,
        "confirm_state_visible": state is ClaimRewardsPanelState.CONFIRM_REQUIRED,
        "confirm_button_visible": state is ClaimRewardsPanelState.CONFIRM_REQUIRED or confirm_point is not None,
        "close_button_visible": state is ClaimRewardsPanelState.CLAIMED or close_point is not None,
    }
    inspection_signals.update(signals or {})
    return ClaimRewardsInspection(
        state=state,
        screenshot_path="",
        message=state.value,
        signals=inspection_signals,
        claim_point=claim_point,
        confirm_point=confirm_point,
        close_point=close_point,
    )
