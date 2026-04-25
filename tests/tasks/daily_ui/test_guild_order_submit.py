from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import InstanceCommandType
from roxauto.core.models import InstanceState, InstanceStatus, PreviewFrame, TaskRunStatus
from roxauto.core.runtime import (
    TaskActionDispatchResult,
    TaskExecutionContext,
    TaskHealthCheckResult,
    TaskRunner,
)
from roxauto.tasks import TaskFoundationRepository, TaskReadinessState
from roxauto.tasks.daily_ui import (
    GuildOrderAvailability,
    GuildOrderDecision,
    GuildOrderDecisionReason,
    GuildOrderDecisionValue,
    GuildOrderInspection,
    GuildOrderMaterialSufficiency,
    GuildOrderObservedTextEvidence,
    GuildOrderOrderKind,
    GuildOrderRequirement,
    GuildOrderSceneState,
    GuildOrderSubmitNavigationPlan,
    GuildOrderVerificationState,
    build_guild_order_submit_runtime_input,
    build_guild_order_submit_runtime_seam,
    build_guild_order_submit_specification,
    build_guild_order_submit_task_spec,
    has_guild_order_submit_runtime_bridge,
    load_guild_order_submit_blueprint,
    load_guild_order_submit_decision_contract,
    load_guild_order_submit_material_policy,
    load_guild_order_submit_visibility_contract,
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
        result = TaskActionDispatchResult(
            command_id=f"cmd-{self._command_count}",
            command_type=InstanceCommandType.TAP,
            instance_id=self.instance_id,
            status=status,
            message=message,
            payload={"point": point},
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
    def __init__(self, inspections: list[GuildOrderInspection]) -> None:
        self._inspections = list(inspections)
        self.calls: list[dict[str, object]] = []

    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        metadata: dict[str, object] | None = None,
    ) -> GuildOrderInspection:
        inspection = self._inspections[len(self.calls)]
        self.calls.append(
            {
                "instance_id": instance.instance_id,
                "screenshot_path": str(screenshot_path),
                "metadata": dict(metadata or {}),
            }
        )
        return replace(inspection, screenshot_path=str(screenshot_path))


class GuildOrderSubmitFoundationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()

    def test_loads_guild_order_blueprint_and_contracts_for_v1_runtime_slice(self) -> None:
        blueprint = load_guild_order_submit_blueprint(self.repository)
        material_policy = load_guild_order_submit_material_policy(self.repository)
        decision_contract = load_guild_order_submit_decision_contract(self.repository)
        visibility_contract = load_guild_order_submit_visibility_contract(self.repository)

        self.assertEqual(blueprint.task_id, "daily_ui.guild_order_submit")
        self.assertEqual(blueprint.implementation_state.value, "fixtured")
        self.assertEqual(blueprint.metadata["asset_requirement_ids"], [])
        self.assertEqual(
            blueprint.metadata["runtime_requirement_ids"],
            ["runtime.daily_ui.dispatch_bridge"],
        )
        self.assertEqual(blueprint.metadata["foundation_requirement_ids"], [])
        self.assertFalse(material_policy.custom_order_enabled)
        self.assertEqual(material_policy.custom_order_selection_boundary, "disabled_in_v1_runtime")
        self.assertEqual(decision_contract.allowed_decisions, ["submit", "skip", "refresh"])
        self.assertIn(GuildOrderDecisionReason.CUSTOM_ORDER_DISABLED.value, decision_contract.reason_ids)
        self.assertNotIn(
            GuildOrderDecisionReason.CUSTOM_ORDER_OPTION_SELECTED.value,
            decision_contract.reason_ids,
        )
        self.assertEqual(visibility_contract.foundation_requirement_ids, [])
        self.assertEqual(
            blueprint.metadata["runtime_seam"]["task_spec_builder"],
            "roxauto.tasks.daily_ui.guild_order_submit.build_guild_order_submit_task_spec",
        )

    def test_builds_guild_order_specification_from_builder_input_and_readiness(self) -> None:
        builder_input = self.repository.build_runtime_builder_input("daily_ui.guild_order_submit")
        readiness = self.repository.evaluate_task_readiness("daily_ui.guild_order_submit")

        specification = build_guild_order_submit_specification(
            builder_input=builder_input,
            readiness_report=readiness,
            foundation_repository=self.repository,
        )

        self.assertEqual(specification.task_id, "daily_ui.guild_order_submit")
        self.assertEqual(specification.fixture_profile.fixture_id, "fixture.tw.guild.default")
        self.assertEqual(specification.metadata["signal_contract_version"], "guild_order_submit.v2")
        self.assertEqual(specification.metadata["runtime_seam"]["signal_contract_version"], "guild_order_submit.v2")
        self.assertEqual(specification.readiness_report.builder_readiness_state, TaskReadinessState.READY)
        self.assertEqual(
            specification.readiness_report.implementation_readiness_state,
            TaskReadinessState.READY,
        )
        self.assertEqual(specification.required_screen_slugs, ["order_list", "order_detail"])
        self.assertEqual(
            specification.supporting_screen_slugs,
            [
                "custom_order_detail",
                "custom_order_list",
                "insufficient_material_state",
                "completed_state",
                "submit_result",
            ],
        )


class GuildOrderSubmitRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )
        self.navigation_plan = _runtime_navigation_plan()

    def test_builds_runtime_input_and_runtime_seam(self) -> None:
        builder_input = self.repository.build_runtime_builder_input("daily_ui.guild_order_submit")
        readiness = self.repository.evaluate_task_readiness("daily_ui.guild_order_submit")

        runtime_input = build_guild_order_submit_runtime_input(
            builder_input=builder_input,
            readiness_report=readiness,
            foundation_repository=self.repository,
        )
        runtime_seam = build_guild_order_submit_runtime_seam(runtime_input=runtime_input)

        self.assertTrue(has_guild_order_submit_runtime_bridge())
        self.assertEqual(runtime_input.task_id, "daily_ui.guild_order_submit")
        self.assertEqual(runtime_input.readiness_report.implementation_readiness_state.value, "ready")
        self.assertEqual(runtime_input.builder_input.runtime_requirement_ids, ["runtime.daily_ui.dispatch_bridge"])
        self.assertFalse(runtime_input.material_policy.custom_order_enabled)
        self.assertEqual(
            [step.step_id for step in runtime_input.step_specs],
            [
                "open_guild_order_list",
                "inspect_visible_order",
                "inspect_custom_order_options",
                "decide_material_action",
                "apply_material_decision",
                "verify_material_outcome",
            ],
        )
        self.assertEqual(
            runtime_input.metadata["evidence_contract"]["required_text_fields"],
            [
                "raw_text",
                "normalized_text",
                "bbox",
                "confidence",
                "screenshot_ref",
                "reader",
            ],
        )
        self.assertEqual(
            runtime_seam.metadata["runtime_bridge_probe"],
            "roxauto.tasks.daily_ui.guild_order_submit.has_guild_order_submit_runtime_bridge",
        )
        self.assertEqual(runtime_seam.signal_contract_version, "guild_order_submit.v2")
        self.assertIn("text_evidence", runtime_seam.result_signal_keys)

    def test_task_spec_builder_embeds_runtime_metadata(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|2|alchemy_reagent|180|40"),
            ]
        )
        runtime_input = build_guild_order_submit_runtime_input(foundation_repository=self.repository)

        spec = build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            runtime_input=runtime_input,
            vision_gateway=gateway,
        )

        self.assertEqual(spec.metadata["implementation_state"], "fixtured")
        self.assertEqual(spec.metadata["implementation_readiness_state"], "ready")
        self.assertEqual(spec.metadata["builder_input"]["task_id"], "daily_ui.guild_order_submit")
        self.assertEqual(spec.metadata["runtime_input"]["fixture_id"], "fixture.tw.guild.default")
        self.assertEqual(
            spec.metadata["runtime_seam"]["metadata"]["runtime_input_builder"],
            "roxauto.tasks.daily_ui.guild_order_submit.build_guild_order_submit_runtime_input",
        )
        self.assertEqual(
            spec.metadata["runtime_seam"]["signal_contract_version"],
            "guild_order_submit.v2",
        )

    def test_runtime_task_submits_when_signature_changes(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(
                    signature="standard|2|alchemy_reagent|180|40",
                    material_label="Alchemy Reagent",
                    normalized_material_id="alchemy_reagent",
                    required_quantity=40,
                    available_quantity=180,
                    screenshot_ref="captures/post-submit.png",
                ),
            ]
        )
        spec = build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.taps, [self.navigation_plan.submit_point])
        self.assertEqual(run.step_results[3].data["decision"], GuildOrderDecisionValue.SUBMIT.value)
        self.assertEqual(run.step_results[4].data["outcome_code"], "submit_applied")
        self.assertEqual(run.step_results[5].data["verification_state"], GuildOrderVerificationState.SUBMIT_VERIFIED.value)
        self.assertEqual(run.step_results[5].data["telemetry"]["post_action_signature"], "standard|2|alchemy_reagent|180|40")
        self.assertEqual(
            sorted(run.step_results[1].data["text_evidence"][0].keys()),
            ["bbox", "confidence", "normalized_text", "raw_text", "reader", "screenshot_ref"],
        )
        self.assertEqual(run.step_results[1].data["text_evidence"][0]["raw_text"], "Bloody Horn")

    def test_runtime_task_refreshes_when_materials_are_insufficient(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _standard_inspection(
                    signature="standard|1|bloody_horn|12|50",
                    available_quantity=12,
                    sufficiency=GuildOrderMaterialSufficiency.INSUFFICIENT,
                ),
                _standard_inspection(
                    signature="standard|1|bloody_horn|12|50",
                    available_quantity=12,
                    sufficiency=GuildOrderMaterialSufficiency.INSUFFICIENT,
                ),
                _standard_inspection(
                    signature="standard|2|amber_shard|240|20",
                    material_label="Amber Shard",
                    normalized_material_id="amber_shard",
                    required_quantity=20,
                    available_quantity=240,
                ),
            ]
        )
        spec = build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(adapter.taps, [self.navigation_plan.refresh_point])
        self.assertEqual(run.step_results[3].data["decision"], GuildOrderDecisionValue.REFRESH.value)
        self.assertTrue(run.step_results[4].data["refresh_attempted"])
        self.assertEqual(run.step_results[5].data["verification_state"], GuildOrderVerificationState.REFRESH_VERIFIED.value)

    def test_runtime_task_records_skip_for_disabled_custom_order(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _custom_inspection(signature="custom|9"),
                _custom_inspection(signature="custom|9"),
            ]
        )
        spec = build_guild_order_submit_task_spec(
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
        self.assertEqual(run.step_results[1].data["outcome_code"], "custom_order_detected")
        self.assertEqual(run.step_results[2].data["outcome_code"], "custom_order_disabled")
        self.assertEqual(run.step_results[3].data["decision"], GuildOrderDecisionValue.SKIP.value)
        self.assertEqual(run.step_results[3].data["reason_id"], GuildOrderDecisionReason.CUSTOM_ORDER_DISABLED.value)
        self.assertEqual(run.step_results[5].data["verification_state"], GuildOrderVerificationState.SKIP_RECORDED.value)

    def test_runtime_task_fails_when_signature_does_not_change_after_submit(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
            ]
        )
        spec = build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.FAILED)
        self.assertEqual(run.step_results[-1].step_id, "verify_material_outcome")
        self.assertEqual(
            run.step_results[-1].data["failure_reason_id"],
            GuildOrderDecisionReason.SUBMIT_VERIFICATION_FAILED.value,
        )
        self.assertEqual(
            run.step_results[-1].data["verification_state"],
            GuildOrderVerificationState.VERIFICATION_FAILED.value,
        )
        self.assertEqual(len(run.step_results[-1].data["inspection_attempts"]), 2)

    def test_runtime_task_prefers_runtime_action_bridge_for_preview_and_taps(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|2|alchemy_reagent|180|40"),
            ]
        )
        spec = build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )
        task_metadata: dict[str, object] = {}
        bridge = FakeTaskActionBridge(
            instance_id=self.instance.instance_id,
            task_id="daily_ui.guild_order_submit",
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
        self.assertEqual([tap["point"] for tap in bridge.taps], [self.navigation_plan.submit_point])
        self.assertEqual(Path(gateway.calls[0]["screenshot_path"]).as_posix(), "captures/bridge-1.png")
        self.assertEqual(run.step_results[4].data["task_action"]["status"], "executed")
        self.assertEqual(run.step_results[4].data["task_action"]["source"], "task_action_bridge")
        self.assertEqual(run.step_results[5].data["telemetry"]["pre_action_signature"], "standard|1|bloody_horn|120|50")

    def test_runtime_task_fails_when_runtime_bridge_rejects_submit(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
            ]
        )
        spec = build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )
        task_metadata: dict[str, object] = {}
        bridge = FakeTaskActionBridge(
            instance_id=self.instance.instance_id,
            task_id="daily_ui.guild_order_submit",
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
        self.assertEqual(run.step_results[-1].step_id, "apply_material_decision")
        self.assertEqual(run.step_results[-1].data["failure_reason_id"], "runtime_dispatch_failed")
        self.assertEqual(run.step_results[-1].data["task_action"]["status"], "rejected")
        self.assertEqual(adapter.screenshot_requests, 0)
        self.assertEqual(adapter.taps, [])
        self.assertEqual(len(bridge.preview_calls), 2)

    def test_open_step_recovers_from_intermediate_route_states(self) -> None:
        adapter = FakeAdapter()
        gateway = ScriptedVisionGateway(
            [
                _scene_inspection(GuildOrderSceneState.UNKNOWN),
                _scene_inspection(GuildOrderSceneState.CARNIVAL_HUB),
                _scene_inspection(GuildOrderSceneState.GUILD_ORDER_CARD_MODAL),
                _scene_inspection(GuildOrderSceneState.GUILD_PANEL),
                _scene_inspection(GuildOrderSceneState.GUILD_ACTIVITY),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|1|bloody_horn|120|50"),
                _standard_inspection(signature="standard|2|alchemy_reagent|180|40"),
            ]
        )
        spec = build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=self.navigation_plan,
            vision_gateway=gateway,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(
            adapter.taps,
            [
                self.navigation_plan.activity_button_point,
                self.navigation_plan.carnival_entry_point,
                self.navigation_plan.guild_order_icon_point,
                self.navigation_plan.go_now_point,
                self.navigation_plan.guild_activity_tab_point,
                self.navigation_plan.guild_order_card_point,
                self.navigation_plan.submit_point,
            ],
        )
        self.assertEqual(run.step_results[0].data["outcome_code"], "guild_order_scene_reached")
        self.assertEqual(len(run.step_results[0].data["inspection_attempts"]), 6)

    def test_observed_text_evidence_round_trips(self) -> None:
        evidence = GuildOrderObservedTextEvidence(
            raw_text="Bloody Horn",
            normalized_text="bloodyhorn",
            bbox=(12, 24, 144, 28),
            confidence=0.97,
            screenshot_ref="captures/guild-order.png",
            reader="mock_ocr",
        )

        restored = GuildOrderObservedTextEvidence.from_dict(evidence.to_dict())

        self.assertEqual(restored.raw_text, "Bloody Horn")
        self.assertEqual(restored.normalized_text, "bloodyhorn")
        self.assertEqual(restored.bbox, (12, 24, 144, 28))
        self.assertEqual(restored.confidence, 0.97)
        self.assertEqual(restored.center(), (84, 38))

    def test_decision_round_trips_with_runtime_fields(self) -> None:
        decision = GuildOrderDecision(
            decision=GuildOrderDecisionValue.REFRESH,
            reason_id=GuildOrderDecisionReason.MATERIALS_INSUFFICIENT.value,
            slot_index=2,
            order_kind=GuildOrderOrderKind.STANDARD,
            requirements=[
                GuildOrderRequirement(
                    slot_index=2,
                    material_label="Bloody Horn",
                    normalized_material_id="bloody_horn",
                    required_quantity=50,
                    evidence={"reader": "mock_ocr"},
                )
            ],
            availability=[
                GuildOrderAvailability(
                    material_label="Bloody Horn",
                    normalized_material_id="bloody_horn",
                    available_quantity=12,
                    sufficiency=GuildOrderMaterialSufficiency.INSUFFICIENT,
                    evidence={"reader": "mock_ocr"},
                )
            ],
            refresh_attempted=True,
            verification_state=GuildOrderVerificationState.REFRESH_VERIFIED,
            metadata={"refresh_attempt_count": 1},
        )

        restored = GuildOrderDecision.from_dict(decision.to_dict())

        self.assertEqual(restored.decision, GuildOrderDecisionValue.REFRESH)
        self.assertEqual(restored.reason_id, GuildOrderDecisionReason.MATERIALS_INSUFFICIENT.value)
        self.assertEqual(restored.availability[0].sufficiency, GuildOrderMaterialSufficiency.INSUFFICIENT)
        self.assertTrue(restored.refresh_attempted)
        self.assertEqual(restored.verification_state, GuildOrderVerificationState.REFRESH_VERIFIED)


def _runtime_navigation_plan() -> GuildOrderSubmitNavigationPlan:
    return GuildOrderSubmitNavigationPlan(
        activity_button_point=(101, 102),
        carnival_entry_point=(103, 104),
        guild_order_icon_point=(105, 106),
        go_now_point=(107, 108),
        guild_activity_tab_point=(109, 110),
        guild_order_card_point=(111, 112),
        refresh_point=(201, 202),
        submit_point=(301, 302),
        wait_after_activity_open_sec=0.0,
        wait_after_carnival_sec=0.0,
        wait_after_guild_order_icon_sec=0.0,
        wait_after_go_now_sec=0.0,
        wait_after_activity_tab_sec=0.0,
        wait_after_guild_order_card_sec=0.0,
        wait_after_refresh_sec=0.0,
        wait_after_submit_sec=0.0,
    )


def _standard_inspection(
    *,
    signature: str,
    slot_index: int = 1,
    material_label: str = "Bloody Horn",
    normalized_material_id: str = "bloody_horn",
    required_quantity: int = 50,
    available_quantity: int = 120,
    sufficiency: GuildOrderMaterialSufficiency | None = None,
    screenshot_ref: str = "captures/guild-order.png",
) -> GuildOrderInspection:
    resolved_sufficiency = sufficiency or (
        GuildOrderMaterialSufficiency.SUFFICIENT
        if available_quantity >= required_quantity
        else GuildOrderMaterialSufficiency.INSUFFICIENT
    )
    text_evidence = [
        _text_evidence(material_label, screenshot_ref=screenshot_ref),
        _text_evidence(
            f"Hold: {available_quantity}",
            normalized_text=f"hold:{available_quantity}",
            bbox=(620, 220, 160, 28),
            screenshot_ref=screenshot_ref,
        ),
        _text_evidence(
            f"{available_quantity}/{required_quantity}",
            normalized_text=f"{available_quantity}/{required_quantity}",
            bbox=(880, 320, 180, 32),
            screenshot_ref=screenshot_ref,
        ),
    ]
    return GuildOrderInspection(
        scene_state=GuildOrderSceneState.GUILD_ORDER_SCENE,
        screenshot_path="",
        text_evidence=text_evidence,
        slot_index=slot_index,
        order_kind=GuildOrderOrderKind.STANDARD,
        requirement=GuildOrderRequirement(
            slot_index=slot_index,
            material_label=material_label,
            normalized_material_id=normalized_material_id,
            required_quantity=required_quantity,
            evidence={"text_evidence": [text_evidence[0].to_dict(), text_evidence[2].to_dict()]},
        ),
        availability=GuildOrderAvailability(
            material_label=material_label,
            normalized_material_id=normalized_material_id,
            available_quantity=available_quantity,
            sufficiency=resolved_sufficiency,
            evidence={"text_evidence": [text_evidence[1].to_dict(), text_evidence[2].to_dict()]},
        ),
        detail_signature=signature,
        order_state_known=True,
        order_completed=False,
        submit_affordance_visible=True,
        refresh_affordance_visible=True,
        message="Captured standard guild-order detail.",
    )


def _custom_inspection(*, signature: str, slot_index: int = 9) -> GuildOrderInspection:
    text_evidence = [
        _text_evidence("Custom Order", normalized_text="customorder"),
        _text_evidence("Self-select", normalized_text="selfselect", bbox=(220, 140, 160, 28)),
    ]
    return GuildOrderInspection(
        scene_state=GuildOrderSceneState.GUILD_ORDER_SCENE,
        screenshot_path="",
        text_evidence=text_evidence,
        slot_index=slot_index,
        order_kind=GuildOrderOrderKind.CUSTOM,
        detail_signature=signature,
        order_state_known=True,
        order_completed=False,
        submit_affordance_visible=False,
        refresh_affordance_visible=True,
        message="Detected custom guild-order state.",
    )


def _scene_inspection(scene_state: GuildOrderSceneState) -> GuildOrderInspection:
    return GuildOrderInspection(
        scene_state=scene_state,
        screenshot_path="",
        text_evidence=[],
        detail_signature=scene_state.value,
        message=scene_state.value,
    )


def _text_evidence(
    raw_text: str,
    *,
    normalized_text: str | None = None,
    bbox: tuple[int, int, int, int] = (12, 24, 144, 28),
    confidence: float | None = 0.97,
    screenshot_ref: str = "captures/guild-order.png",
    reader: str = "mock_ocr",
) -> GuildOrderObservedTextEvidence:
    return GuildOrderObservedTextEvidence(
        raw_text=raw_text,
        normalized_text=normalized_text or raw_text.lower().replace(" ", ""),
        bbox=bbox,
        confidence=confidence,
        screenshot_ref=screenshot_ref,
        reader=reader,
    )
