from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.models import InstanceState, InstanceStatus, TaskRunStatus, VisionMatch
from roxauto.core.runtime import TaskExecutionContext, TaskRunner
from roxauto.tasks import TaskFoundationRepository
from roxauto.tasks.daily_ui import (
    ClaimRewardsInspection,
    ClaimRewardsNavigationPlan,
    ClaimRewardsPanelState,
    build_claim_rewards_runtime_input,
    TemplateMatcherClaimRewardsVisionGateway,
    build_claim_rewards_task_spec,
    load_claim_rewards_anchor_specs,
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
        self.assertEqual(
            runtime_input.required_anchor_ids,
            ["common.close_button", "common.confirm_button", "daily_ui.claim_reward"],
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
        self.assertEqual(runtime_input.step_specs[2].anchor_id, "daily_ui.claim_reward")
        self.assertEqual(runtime_input.step_specs[3].anchor_id, "common.confirm_button")

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
        self.assertEqual(
            [step.step_id for step in spec.steps],
            [step.step_id for step in runtime_input.step_specs],
        )

    def test_template_match_gateway_classifies_reward_panel_states(self) -> None:
        anchors = load_claim_rewards_anchor_specs()
        cases = [
            (
                "claimable",
                {
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
                },
                ClaimRewardsPanelState.CONFIRM_REQUIRED,
                (460, 530),
            ),
            (
                "claimed",
                {
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
                if expected_state is ClaimRewardsPanelState.CLAIMABLE:
                    self.assertEqual(inspection.claim_point, expected_point)
                elif expected_state is ClaimRewardsPanelState.CONFIRM_REQUIRED:
                    self.assertEqual(inspection.confirm_point, expected_point)
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
        self.assertEqual(adapter.taps, [(100, 200), (640, 360)])
        self.assertEqual(gateway.calls[0]["metadata"]["reason"], "open_reward_panel")

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
        self.assertEqual(adapter.taps, [(100, 200), (640, 360), (700, 500)])

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
        self.assertEqual(adapter.taps, [(100, 200)])
        self.assertEqual(run.step_results[2].message, "Reward is already claimed; tap is not required.")

    def test_claim_rewards_run_fails_when_panel_cannot_be_confirmed(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [_inspection(ClaimRewardsPanelState.UNAVAILABLE)]
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

    def test_claim_rewards_run_fails_when_claim_tap_does_not_advance(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
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
        self.assertEqual(adapter.taps, [(100, 200), (640, 360)])


def _inspection(
    state: ClaimRewardsPanelState,
    *,
    claim_point: tuple[int, int] | None = None,
    confirm_point: tuple[int, int] | None = None,
    close_point: tuple[int, int] | None = None,
) -> ClaimRewardsInspection:
    return ClaimRewardsInspection(
        state=state,
        screenshot_path="",
        message=state.value,
        claim_point=claim_point,
        confirm_point=confirm_point,
        close_point=close_point,
    )
