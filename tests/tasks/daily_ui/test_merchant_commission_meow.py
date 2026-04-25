from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.models import InstanceState, InstanceStatus, TaskRunStatus
from roxauto.core.runtime import TaskExecutionContext, TaskRunner
from roxauto.tasks import TaskFoundationRepository, TaskReadinessState
from roxauto.tasks.daily_ui import (
    MerchantCommissionMeowActiveRoundResolution,
    MerchantCommissionMeowActiveRoundNavigationPlan,
    MerchantCommissionMeowCheckpointInspection,
    MerchantCommissionMeowDecisionReason,
    MerchantCommissionMeowDecisionValue,
    MerchantCommissionMeowEntryNavigationPlan,
    MerchantCommissionMeowFullRunNavigationPlan,
    MerchantCommissionMeowRoundEvidence,
    MerchantCommissionMeowLoopContract,
    MerchantCommissionMeowObservedTextEvidence,
    MerchantCommissionMeowRouteContract,
    MerchantCommissionMeowSubmissionPolicy,
    MerchantCommissionMeowSubmitPanelNavigationPlan,
    MerchantCommissionMeowSubmitPanelInspection,
    MerchantCommissionMeowSubmitPanelResolution,
    MerchantCommissionMeowSubmitPanelProgressState,
    MerchantCommissionMeowTaskFailureReason,
    build_merchant_commission_meow_runtime_input,
    build_merchant_commission_meow_runtime_seam,
    build_merchant_commission_meow_specification,
    build_merchant_commission_meow_task_spec,
    evaluate_merchant_commission_meow_round_decision,
    has_merchant_commission_meow_runtime_bridge,
    inspect_merchant_commission_meow_submit_panel_progress,
    load_merchant_commission_meow_blueprint,
    load_merchant_commission_meow_decision_contract,
    load_merchant_commission_meow_loop_contract,
    load_merchant_commission_meow_route_contract,
    load_merchant_commission_meow_submission_policy,
    resolve_merchant_commission_meow_active_round,
    resolve_merchant_commission_meow_entry_accept,
    resolve_merchant_commission_meow_from_main_screen,
    resolve_merchant_commission_meow_submit_panel,
)


class MerchantCommissionMeowFoundationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()
        self.fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "merchant_commission_meow"

    def test_loads_merchant_commission_meow_blueprint_and_contracts(self) -> None:
        blueprint = load_merchant_commission_meow_blueprint(self.repository)
        route_contract = load_merchant_commission_meow_route_contract(self.repository)
        loop_contract = load_merchant_commission_meow_loop_contract(self.repository)
        submission_policy = load_merchant_commission_meow_submission_policy(self.repository)
        decision_contract = load_merchant_commission_meow_decision_contract(self.repository)

        self.assertEqual(blueprint.task_id, "daily_ui.merchant_commission_meow")
        self.assertEqual(blueprint.implementation_state.value, "fixtured")
        self.assertEqual(
            blueprint.required_anchors,
            [
                "common.close_button",
                "daily_ui.merchant_commission_poring_button",
                "daily_ui.merchant_commission_carnival_entry",
                "daily_ui.merchant_commission_detail_modal",
                "daily_ui.merchant_commission_go_now_button",
                "daily_ui.merchant_commission_npc_dialog",
                "daily_ui.merchant_commission_list_panel",
                "daily_ui.merchant_commission_meow_accept_button",
                "daily_ui.merchant_commission_task_list_entry",
                "daily_ui.merchant_commission_meow_submit_option",
                "daily_ui.merchant_commission_submit_item_panel",
                "daily_ui.merchant_commission_buy_now_button",
                "daily_ui.merchant_commission_buy_confirmation_dialog",
                "daily_ui.merchant_commission_buy_confirm_button",
                "daily_ui.merchant_commission_submit_button",
            ],
        )
        self.assertEqual(
            route_contract.entry_checkpoint_ids,
            [
                "idle_prontera_fountain",
                "event_poring_menu",
                "carnival_map",
                "merchant_commission_detail_modal",
                "merchant_autopath_to_npc",
                "merchant_npc_dialog_initial",
                "merchant_commission_list",
            ],
        )
        self.assertEqual(
            route_contract.preferred_reentry_checkpoint_ids,
            [
                "task_list_round_visible",
                "npc_submit_dialog",
                "submit_item_panel",
                "buy_confirmation",
                "round_progression_visible",
            ],
        )
        self.assertIn("top-right line-switch arrow", route_contract.do_not_click_notes[0])
        self.assertEqual(loop_contract.merchant_group_label, "\u55b5\u624b\u5546\u5718")
        self.assertEqual(loop_contract.task_list_label, "[\u65e5\u5e38] \u5546\u6703\u59d4\u8a17")
        self.assertEqual(loop_contract.round_limit, 10)
        self.assertEqual(loop_contract.verified_round_count, 2)
        self.assertEqual(loop_contract.preferred_reentry_mode, "left_task_list")
        self.assertEqual(loop_contract.submit_panel_title, "\u4e0a\u4ea4\u9053\u5177")
        self.assertEqual(loop_contract.buy_now_label, "\u7acb\u5373\u8cfc\u8cb7")
        self.assertEqual(loop_contract.buy_confirm_label, "\u8cfc\u8cb7")
        self.assertEqual(loop_contract.submit_label, "\u4ea4\u4ed8")
        self.assertEqual(
            loop_contract.verified_material_labels,
            ["\u7926\u6e23\u8403\u53d6\u7269", "\u7425\u73c0\u7d50\u6676"],
        )
        self.assertTrue(submission_policy.allow_immediate_buy)
        self.assertTrue(submission_policy.allow_partial_inventory_buy)
        self.assertEqual(submission_policy.verified_reentry_mode, "left_task_list")
        self.assertIn("merchant_group_switch", submission_policy.disallowed_behaviors)
        self.assertEqual(
            decision_contract.allowed_decisions,
            ["direct_submit", "immediate_buy_then_submit", "stop_for_operator"],
        )
        self.assertIn("buy_required", decision_contract.reason_ids)
        self.assertIn("material_progress", decision_contract.decision_signal_keys)

    def test_builds_merchant_commission_meow_specification_from_builder_input_and_readiness(self) -> None:
        builder_input = self.repository.build_runtime_builder_input("daily_ui.merchant_commission_meow")
        readiness = self.repository.evaluate_task_readiness("daily_ui.merchant_commission_meow")

        specification = build_merchant_commission_meow_specification(
            builder_input=builder_input,
            readiness_report=readiness,
            foundation_repository=self.repository,
        )

        self.assertEqual(specification.task_id, "daily_ui.merchant_commission_meow")
        self.assertEqual(specification.fixture_profile.fixture_id, "fixture.tw.merchant.default")
        self.assertEqual(specification.metadata["signal_contract_version"], "merchant_commission_meow.v2")
        self.assertEqual(
            specification.metadata["merchant_commission_meow_handoff_fields"],
            [
                "decision",
                "reason_id",
                "merchant_group_label",
                "round_index",
                "round_limit",
                "material_label",
                "material_progress",
                "buy_required",
                "zeny_cost",
                "reentry_mode",
            ],
        )
        self.assertEqual(
            specification.required_screen_slugs,
            [
                "carnival_entry",
                "commission_detail_modal",
                "merchant_group_list",
                "meow_task_list_round",
                "meow_submit_panel",
                "meow_buy_confirmation",
            ],
        )
        self.assertEqual(
            specification.supporting_screen_slugs,
            ["meow_empty_submit_panel", "meow_round_progression"],
        )
        self.assertEqual(
            specification.readiness_report.builder_readiness_state,
            TaskReadinessState.BLOCKED_BY_ASSET,
        )
        self.assertEqual(
            specification.readiness_report.implementation_readiness_state,
            TaskReadinessState.BLOCKED_BY_ASSET,
        )
        self.assertEqual(specification.route_contract.preferred_reentry_checkpoint_ids[0], "task_list_round_visible")
        self.assertEqual(specification.loop_contract.preferred_reentry_mode, "left_task_list")
        self.assertTrue(specification.submission_policy.allow_immediate_buy)
        self.assertEqual(
            specification.decision_contract.allowed_decisions,
            ["direct_submit", "immediate_buy_then_submit", "stop_for_operator"],
        )

    def test_evaluates_direct_submit_round_decision(self) -> None:
        decision = evaluate_merchant_commission_meow_round_decision(
            round_evidence=MerchantCommissionMeowRoundEvidence(
                round_index=3,
                material_label="豹命毒液",
                current_quantity=15,
                required_quantity=15,
                submit_panel_visible=True,
                submit_button_visible=True,
                buy_now_visible=False,
            ),
            loop_contract=load_merchant_commission_meow_loop_contract(self.repository),
        )

        self.assertEqual(decision.decision, MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT)
        self.assertEqual(decision.reason_id, MerchantCommissionMeowDecisionReason.MATERIALS_READY.value)
        self.assertFalse(decision.buy_required)
        self.assertEqual(decision.material_progress, "15/15")
        self.assertEqual(decision.reentry_mode, "left_task_list")

    def test_evaluates_immediate_buy_round_decision(self) -> None:
        decision = evaluate_merchant_commission_meow_round_decision(
            round_evidence=MerchantCommissionMeowRoundEvidence(
                round_index=2,
                material_label="琥珀結晶",
                current_quantity=0,
                required_quantity=15,
                submit_panel_visible=True,
                submit_button_visible=False,
                buy_now_visible=True,
                empty_inventory_feedback_visible=True,
                zeny_cost=1200,
            ),
            submission_policy=load_merchant_commission_meow_submission_policy(self.repository),
            loop_contract=load_merchant_commission_meow_loop_contract(self.repository),
        )

        self.assertEqual(
            decision.decision,
            MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT,
        )
        self.assertEqual(decision.reason_id, MerchantCommissionMeowDecisionReason.BUY_REQUIRED.value)
        self.assertTrue(decision.buy_required)
        self.assertTrue(decision.requires_buy_confirmation)
        self.assertEqual(decision.zeny_cost, 1200)

    def test_stops_when_buy_now_is_not_available_for_incomplete_round(self) -> None:
        decision = evaluate_merchant_commission_meow_round_decision(
            round_evidence=MerchantCommissionMeowRoundEvidence(
                round_index=4,
                material_label="未知材料",
                current_quantity=3,
                required_quantity=15,
                submit_panel_visible=True,
                submit_button_visible=False,
                buy_now_visible=False,
                empty_inventory_feedback_visible=True,
            ),
            submission_policy=MerchantCommissionMeowSubmissionPolicy(
                allow_immediate_buy=True,
                allow_partial_inventory_buy=True,
                buy_flow_requires_confirmation=True,
                verified_reentry_mode="left_task_list",
                disallowed_behaviors=["crafting", "gathering", "pathing"],
            ),
            loop_contract=load_merchant_commission_meow_loop_contract(self.repository),
        )

        self.assertEqual(
            decision.decision,
            MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR,
        )
        self.assertEqual(
            decision.reason_id,
            MerchantCommissionMeowDecisionReason.BUY_NOW_UNAVAILABLE.value,
        )
        self.assertTrue(decision.buy_required)

    def test_round_trips_machine_readable_route_and_loop_contracts(self) -> None:
        route_contract = MerchantCommissionMeowRouteContract(
            entry_checkpoint_ids=["entry_a", "entry_b"],
            preferred_reentry_checkpoint_ids=["reentry_a"],
            do_not_click_notes=["stay inside validated route"],
            notes="fixed entry plus task-list reentry",
        )
        loop_contract = MerchantCommissionMeowLoopContract(
            merchant_group_label="Meow Group",
            task_list_label="[Daily] Merchant Commission",
            round_limit=10,
            verified_round_count=2,
            preferred_reentry_mode="left_task_list",
            submit_panel_title="Submit Items",
            buy_now_label="Buy Now",
            buy_confirm_label="Buy",
            submit_label="Submit",
            task_round_pattern="Merchant Commission({round_index}/10)",
            verified_material_labels=["ore_extract", "amber"],
            notes="semi-fixed 10-round chain",
        )

        restored_route_contract = MerchantCommissionMeowRouteContract.from_dict(
            route_contract.to_dict()
        )
        restored_loop_contract = MerchantCommissionMeowLoopContract.from_dict(
            loop_contract.to_dict()
        )

        self.assertEqual(restored_route_contract.entry_checkpoint_ids, ["entry_a", "entry_b"])
        self.assertEqual(restored_route_contract.do_not_click_notes, ["stay inside validated route"])
        self.assertEqual(restored_loop_contract.merchant_group_label, "Meow Group")
        self.assertEqual(restored_loop_contract.round_limit, 10)
        self.assertEqual(restored_loop_contract.verified_material_labels, ["ore_extract", "amber"])

    def test_inspects_submit_panel_progress_as_incomplete_for_partial_inventory(self) -> None:
        inspection = inspect_merchant_commission_meow_submit_panel_progress(
            self.fixture_root / "submit_panel_partial_7_of_15.png"
        )

        self.assertEqual(
            inspection.progress_state,
            MerchantCommissionMeowSubmitPanelProgressState.INCOMPLETE,
        )
        self.assertGreater(inspection.numerator_ink, 40)
        self.assertGreater(inspection.denominator_ink, 40)
        self.assertLess(inspection.normalized_similarity, 0.5)

    def test_inspects_submit_panel_progress_as_full_for_ready_inventory(self) -> None:
        inspection = inspect_merchant_commission_meow_submit_panel_progress(
            self.fixture_root / "submit_panel_full_15_of_15.png"
        )

        self.assertEqual(
            inspection.progress_state,
            MerchantCommissionMeowSubmitPanelProgressState.FULL,
        )
        self.assertGreaterEqual(inspection.normalized_similarity, 0.5)

    def test_inspects_submit_panel_progress_as_incomplete_for_empty_inventory_feedback(self) -> None:
        inspection = inspect_merchant_commission_meow_submit_panel_progress(
            self.fixture_root / "submit_panel_empty_0_of_15.png"
        )

        self.assertEqual(
            inspection.progress_state,
            MerchantCommissionMeowSubmitPanelProgressState.INCOMPLETE,
        )
        self.assertGreaterEqual(
            float(inspection.metadata.get("empty_feedback_score", 0.0)),
            0.9,
        )

    def test_resolve_submit_panel_buys_then_submits_for_incomplete_inventory(self) -> None:
        adapter = _FakeSubmitPanelAdapter(
            self.fixture_root / "submit_panel_partial_7_of_15.png"
        )

        resolution = resolve_merchant_commission_meow_submit_panel(
            adapter=adapter,
            instance=object(),
            navigation_plan=MerchantCommissionMeowSubmitPanelNavigationPlan(
                buy_now_point=(1, 2),
                buy_confirm_point=(3, 4),
                submit_point=(5, 6),
                wait_after_buy_sec=0.0,
                wait_after_confirm_sec=0.0,
            ),
            sleep_fn=lambda seconds: None,
        )

        self.assertEqual(
            resolution.decision,
            MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT,
        )
        self.assertEqual(adapter.taps, [(1, 2), (3, 4), (5, 6)])

    def test_resolve_submit_panel_direct_submits_for_full_inventory(self) -> None:
        adapter = _FakeSubmitPanelAdapter(
            self.fixture_root / "submit_panel_full_15_of_15.png"
        )

        resolution = resolve_merchant_commission_meow_submit_panel(
            adapter=adapter,
            instance=object(),
            navigation_plan=MerchantCommissionMeowSubmitPanelNavigationPlan(
                buy_now_point=(1, 2),
                buy_confirm_point=(3, 4),
                submit_point=(5, 6),
            ),
            sleep_fn=lambda seconds: None,
        )

        self.assertEqual(
            resolution.decision,
            MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT,
        )
        self.assertEqual(adapter.taps, [(5, 6)])

    def test_resolve_active_round_enters_task_then_resolves_submit_panel(self) -> None:
        adapter = _FakeSubmitPanelAdapter(
            self.fixture_root / "submit_panel_partial_7_of_15.png"
        )

        resolution = resolve_merchant_commission_meow_active_round(
            adapter=adapter,
            instance=object(),
            navigation_plan=MerchantCommissionMeowActiveRoundNavigationPlan(
                task_entry_point=(10, 11),
                submit_option_point=(12, 13),
                wait_after_task_entry_sec=0.0,
                wait_after_submit_option_sec=0.0,
                submit_panel_plan=MerchantCommissionMeowSubmitPanelNavigationPlan(
                    buy_now_point=(1, 2),
                    buy_confirm_point=(3, 4),
                    submit_point=(5, 6),
                    wait_after_buy_sec=0.0,
                    wait_after_confirm_sec=0.0,
                ),
            ),
            sleep_fn=lambda seconds: None,
        )

        self.assertEqual(
            resolution.submit_panel_resolution.decision,
            MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT,
        )
        self.assertEqual(adapter.taps, [(10, 11), (12, 13), (1, 2), (3, 4), (5, 6)])

    def test_round_trips_active_round_resolution(self) -> None:
        resolution = MerchantCommissionMeowActiveRoundResolution(
            submit_panel_resolution=MerchantCommissionMeowSubmitPanelResolution(
                decision=MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT,
                inspection=MerchantCommissionMeowSubmitPanelInspection(
                    screenshot_path="submit.png",
                    progress_state=MerchantCommissionMeowSubmitPanelProgressState.FULL,
                    numerator_ink=88,
                    denominator_ink=90,
                    normalized_similarity=0.95,
                    metadata={"fixture": "full"},
                ),
                executed_points=[(5, 6)],
                metadata={"path": "submit_only"},
            ),
            executed_points=[(10, 11), (12, 13), (5, 6)],
            metadata={"step": "active_round"},
        )

        restored = MerchantCommissionMeowActiveRoundResolution.from_dict(
            resolution.to_dict()
        )

        self.assertEqual(
            restored.submit_panel_resolution.decision,
            MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT,
        )
        self.assertEqual(restored.executed_points, [(10, 11), (12, 13), (5, 6)])
        self.assertEqual(restored.metadata, {"step": "active_round"})

    def test_resolve_entry_accept_follows_validated_meow_route(self) -> None:
        adapter = _FakeSubmitPanelAdapter(
            self.fixture_root / "submit_panel_partial_7_of_15.png"
        )

        resolution = resolve_merchant_commission_meow_entry_accept(
            adapter=adapter,
            instance=object(),
            navigation_plan=MerchantCommissionMeowEntryNavigationPlan(
                activity_button_point=(1, 2),
                carnival_entry_point=(3, 4),
                merchant_commission_icon_point=(5, 6),
                go_now_point=(7, 8),
                npc_commission_option_point=(9, 10),
                meow_accept_point=(11, 12),
                close_list_point=(13, 14),
                expand_task_tab_point=(15, 16),
                task_list_swipe_start=(17, 18),
                task_list_swipe_end=(19, 20),
                task_list_swipe_duration_ms=321,
                wait_after_activity_open_sec=0.0,
                wait_after_carnival_sec=0.0,
                wait_after_merchant_detail_sec=0.0,
                wait_after_go_now_sec=0.0,
                wait_after_npc_option_sec=0.0,
                wait_after_accept_sec=0.0,
                wait_after_close_list_sec=0.0,
                wait_after_expand_task_tab_sec=0.0,
                wait_after_task_swipe_sec=0.0,
            ),
            sleep_fn=lambda seconds: None,
        )

        self.assertEqual(
            adapter.taps,
            [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)],
        )
        self.assertEqual(adapter.swipes, [((17, 18), (19, 20), 321)])
        self.assertEqual(
            resolution.executed_points,
            [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)],
        )

    def test_resolve_from_main_screen_accepts_then_completes_one_round(self) -> None:
        adapter = _FakeSubmitPanelAdapter(
            self.fixture_root / "submit_panel_partial_7_of_15.png"
        )

        resolution = resolve_merchant_commission_meow_from_main_screen(
            adapter=adapter,
            instance=object(),
            navigation_plan=MerchantCommissionMeowFullRunNavigationPlan(
                entry_plan=MerchantCommissionMeowEntryNavigationPlan(
                    activity_button_point=(1, 2),
                    carnival_entry_point=(3, 4),
                    merchant_commission_icon_point=(5, 6),
                    go_now_point=(7, 8),
                    npc_commission_option_point=(9, 10),
                    meow_accept_point=(11, 12),
                    close_list_point=(13, 14),
                    expand_task_tab_point=(15, 16),
                    task_list_swipe_start=(17, 18),
                    task_list_swipe_end=(19, 20),
                    task_list_swipe_duration_ms=321,
                    wait_after_activity_open_sec=0.0,
                    wait_after_carnival_sec=0.0,
                    wait_after_merchant_detail_sec=0.0,
                    wait_after_go_now_sec=0.0,
                    wait_after_npc_option_sec=0.0,
                    wait_after_accept_sec=0.0,
                    wait_after_close_list_sec=0.0,
                    wait_after_expand_task_tab_sec=0.0,
                    wait_after_task_swipe_sec=0.0,
                ),
                active_round_plan=MerchantCommissionMeowActiveRoundNavigationPlan(
                    task_entry_point=(21, 22),
                    submit_option_point=(23, 24),
                    wait_after_task_entry_sec=0.0,
                    wait_after_submit_option_sec=0.0,
                    submit_panel_plan=MerchantCommissionMeowSubmitPanelNavigationPlan(
                        buy_now_point=(25, 26),
                        buy_confirm_point=(27, 28),
                        submit_point=(29, 30),
                        wait_after_buy_sec=0.0,
                        wait_after_confirm_sec=0.0,
                    ),
                ),
            ),
            sleep_fn=lambda seconds: None,
        )

        self.assertEqual(
            resolution.active_round_resolution.submit_panel_resolution.decision,
            MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT,
        )
        self.assertEqual(
            adapter.taps,
            [
                (1, 2),
                (3, 4),
                (5, 6),
                (7, 8),
                (9, 10),
                (11, 12),
                (13, 14),
                (15, 16),
                (21, 22),
                (23, 24),
                (25, 26),
                (27, 28),
                (29, 30),
            ],
        )
        self.assertEqual(adapter.swipes, [((17, 18), (19, 20), 321)])


class MerchantCommissionMeowRuntimeBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()
        self.fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "merchant_commission_meow"
        self.instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )
        self.navigation_plan = _runtime_navigation_plan()

    def test_builds_runtime_input_and_runtime_seam(self) -> None:
        builder_input = self.repository.build_runtime_builder_input("daily_ui.merchant_commission_meow")
        readiness = self.repository.evaluate_task_readiness("daily_ui.merchant_commission_meow")

        runtime_input = build_merchant_commission_meow_runtime_input(
            builder_input=builder_input,
            readiness_report=readiness,
            foundation_repository=self.repository,
        )
        runtime_seam = build_merchant_commission_meow_runtime_seam(runtime_input=runtime_input)

        self.assertTrue(has_merchant_commission_meow_runtime_bridge())
        self.assertEqual(runtime_input.task_id, "daily_ui.merchant_commission_meow")
        self.assertEqual(runtime_input.readiness_report.implementation_readiness_state.value, "blocked_by_asset")
        self.assertEqual(runtime_input.blueprint.implementation_state.value, "fixtured")
        self.assertEqual(runtime_input.fixture_profile.fixture_id, "fixture.tw.merchant.default")
        self.assertEqual(
            runtime_input.builder_input.runtime_requirement_ids,
            ["runtime.daily_ui.dispatch_bridge"],
        )
        self.assertEqual(
            [step.step_id for step in runtime_input.step_specs],
            [
                "open_merchant_commission_entry",
                "accept_meow_group_commission",
                "reenter_from_daily_task_list",
                "resolve_round_material_submission",
                "verify_round_progression",
            ],
        )
        self.assertEqual(runtime_input.metadata["signal_contract_version"], "merchant_commission_meow.v2")
        self.assertEqual(
            runtime_input.metadata["runtime_seam"]["runtime_input_builder"],
            "roxauto.tasks.daily_ui.merchant_commission_meow.build_merchant_commission_meow_runtime_input",
        )
        self.assertEqual(
            runtime_seam.metadata["runtime_bridge_probe"],
            "roxauto.tasks.daily_ui.merchant_commission_meow.has_merchant_commission_meow_runtime_bridge",
        )
        self.assertEqual(
            runtime_seam.result_signal_keys,
            [
                "anchor_id",
                "decision",
                "failure_reason_id",
                "inspection_attempts",
                "matched_anchor_ids",
                "outcome_code",
                "round_index",
                "step_outcome",
                "task_action",
                "telemetry",
                "text_evidence",
            ],
        )

    def test_runtime_task_spec_completes_full_meow_slice(self) -> None:
        adapter = _ScriptedMerchantRuntimeAdapter(
            self.fixture_root / "submit_panel_partial_7_of_15.png"
        )
        gateway = _ScriptedMerchantVisionGateway(
            [
                _inspection("open_merchant_commission_entry"),
                _inspection("open_merchant_commission_entry", matched_anchor_ids=["daily_ui.merchant_commission_detail_modal"]),
                _inspection("accept_meow_group_commission"),
                _inspection(
                    "accept_meow_group_commission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_list_panel",
                        "daily_ui.merchant_commission_meow_accept_button",
                    ],
                ),
                _inspection(
                    "accept_meow_group_commission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_task_list_entry",
                        "daily_ui.merchant_commission_round_counter",
                    ],
                    text_evidence=[_text_evidence("(1/10)", 0.97)],
                    round_index=1,
                ),
                _inspection(
                    "reenter_from_daily_task_list",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_task_list_entry",
                        "daily_ui.merchant_commission_round_counter",
                    ],
                    text_evidence=[_text_evidence("(1/10)", 0.98)],
                    round_index=1,
                ),
                _inspection(
                    "reenter_from_daily_task_list",
                    matched_anchor_ids=["daily_ui.merchant_commission_meow_submit_option"],
                ),
                _inspection("resolve_round_material_submission"),
                _inspection(
                    "resolve_round_material_submission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_submit_item_panel",
                        "daily_ui.merchant_commission_buy_now_button",
                    ],
                ),
                _inspection(
                    "resolve_round_material_submission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_buy_confirmation_dialog",
                        "daily_ui.merchant_commission_buy_confirm_button",
                    ],
                ),
                _inspection(
                    "resolve_round_material_submission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_submit_item_panel",
                        "daily_ui.merchant_commission_submit_button",
                    ],
                ),
                _inspection(
                    "verify_round_progression",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_task_list_entry",
                        "daily_ui.merchant_commission_round_counter",
                    ],
                    text_evidence=[_text_evidence("(2/10)", 0.99)],
                    round_index=2,
                ),
            ]
        )

        runtime_input = build_merchant_commission_meow_runtime_input(
            foundation_repository=self.repository
        )
        runtime_seam = build_merchant_commission_meow_runtime_seam(runtime_input=runtime_input)
        spec = build_merchant_commission_meow_task_spec(
            adapter=adapter,
            vision_gateway=gateway,
            navigation_plan=self.navigation_plan,
            runtime_seam=runtime_seam,
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.SUCCEEDED)
        self.assertEqual(
            [result.step_id for result in run.step_results],
            [
                "open_merchant_commission_entry",
                "accept_meow_group_commission",
                "reenter_from_daily_task_list",
                "resolve_round_material_submission",
                "verify_round_progression",
            ],
        )
        self.assertEqual(
            adapter.taps,
            [
                (101, 102),
                (103, 104),
                (105, 106),
                (107, 108),
                (109, 110),
                (111, 112),
                (113, 114),
                (115, 116),
                (201, 202),
                (203, 204),
                (301, 302),
                (303, 304),
                (305, 306),
            ],
        )
        self.assertEqual(adapter.swipes, [((117, 118), (119, 120), 321)])
        self.assertEqual(run.step_results[2].data["round_index"], 1)
        self.assertEqual(
            run.step_results[3].data["decision"],
            MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
        )
        self.assertEqual(
            run.step_results[3].data["reason_id"],
            MerchantCommissionMeowDecisionReason.BUY_REQUIRED.value,
        )
        self.assertEqual(run.step_results[4].data["round_index"], 2)
        self.assertEqual(run.step_results[4].data["outcome_code"], "round_progression_verified")
        self.assertEqual(run.step_results[4].data["text_evidence"][0]["raw_text"], "(1/10)")
        self.assertEqual(run.step_results[4].data["text_evidence"][1]["raw_text"], "(2/10)")
        self.assertEqual(spec.metadata["runtime_seam"]["signal_contract_version"], "merchant_commission_meow.v2")

    def test_runtime_task_spec_blocks_low_confidence_progression_text(self) -> None:
        adapter = _ScriptedMerchantRuntimeAdapter(
            self.fixture_root / "submit_panel_full_15_of_15.png"
        )
        gateway = _ScriptedMerchantVisionGateway(
            [
                _inspection("open_merchant_commission_entry"),
                _inspection("open_merchant_commission_entry", matched_anchor_ids=["daily_ui.merchant_commission_detail_modal"]),
                _inspection("accept_meow_group_commission"),
                _inspection(
                    "accept_meow_group_commission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_list_panel",
                        "daily_ui.merchant_commission_meow_accept_button",
                    ],
                ),
                _inspection(
                    "accept_meow_group_commission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_task_list_entry",
                        "daily_ui.merchant_commission_round_counter",
                    ],
                    text_evidence=[_text_evidence("(1/10)", 0.96)],
                    round_index=1,
                ),
                _inspection(
                    "reenter_from_daily_task_list",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_task_list_entry",
                        "daily_ui.merchant_commission_round_counter",
                    ],
                    text_evidence=[_text_evidence("(1/10)", 0.97)],
                    round_index=1,
                ),
                _inspection(
                    "reenter_from_daily_task_list",
                    matched_anchor_ids=["daily_ui.merchant_commission_meow_submit_option"],
                ),
                _inspection("resolve_round_material_submission"),
                _inspection(
                    "resolve_round_material_submission",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_submit_item_panel",
                        "daily_ui.merchant_commission_submit_button",
                    ],
                ),
                _inspection(
                    "verify_round_progression",
                    matched_anchor_ids=[
                        "daily_ui.merchant_commission_task_list_entry",
                        "daily_ui.merchant_commission_round_counter",
                    ],
                    text_evidence=[_text_evidence("(2/10)", 0.41)],
                    round_index=2,
                ),
            ]
        )

        spec = build_merchant_commission_meow_task_spec(
            adapter=adapter,
            vision_gateway=gateway,
            navigation_plan=self.navigation_plan,
            runtime_input=build_merchant_commission_meow_runtime_input(
                foundation_repository=self.repository
            ),
        )

        run = TaskRunner().run_task(
            spec=spec,
            context=TaskExecutionContext(instance=self.instance),
        )

        self.assertEqual(run.status, TaskRunStatus.FAILED)
        self.assertEqual(run.step_results[-1].step_id, "verify_round_progression")
        self.assertEqual(
            run.step_results[-1].data["failure_reason_id"],
            MerchantCommissionMeowTaskFailureReason.PROGRESSION_LOW_CONFIDENCE.value,
        )
        text_evidence = run.step_results[-1].data["text_evidence"]
        self.assertEqual(len(text_evidence), 2)
        self.assertEqual(
            sorted(text_evidence[0].keys()),
            [
                "bbox",
                "confidence",
                "normalized_text",
                "raw_text",
                "reader",
                "screenshot_ref",
                "source_type",
            ],
        )
        self.assertEqual(
            run.step_results[3].data["decision"],
            MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT.value,
        )


class _FakeSubmitPanelAdapter:
    def __init__(self, screenshot_path: Path) -> None:
        self._screenshot_path = screenshot_path
        self.taps: list[tuple[int, int]] = []
        self.swipes: list[tuple[tuple[int, int], tuple[int, int], int]] = []

    def capture_screenshot(self, instance: object) -> Path:
        return self._screenshot_path

    def tap(self, instance: object, point: tuple[int, int]) -> None:
        self.taps.append(point)

    def swipe(
        self,
        instance: object,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        self.swipes.append((start, end, duration_ms))


class _ScriptedMerchantRuntimeAdapter:
    def __init__(self, screenshot_path: Path) -> None:
        self._screenshot_path = screenshot_path
        self.taps: list[tuple[int, int]] = []
        self.swipes: list[tuple[tuple[int, int], tuple[int, int], int]] = []

    def capture_screenshot(self, instance: object) -> Path:
        return self._screenshot_path

    def tap(self, instance: object, point: tuple[int, int]) -> None:
        self.taps.append(point)

    def swipe(
        self,
        instance: object,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        self.swipes.append((start, end, duration_ms))


class _ScriptedMerchantVisionGateway:
    def __init__(self, inspections: list[MerchantCommissionMeowCheckpointInspection]) -> None:
        self._inspections = list(inspections)
        self.calls: list[dict[str, object]] = []

    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        step_id: str,
        signal_anchor_ids,
        metadata=None,
    ) -> MerchantCommissionMeowCheckpointInspection:
        inspection = self._inspections[len(self.calls)]
        self.calls.append(
            {
                "instance_id": instance.instance_id,
                "step_id": step_id,
                "screenshot_path": str(screenshot_path),
                "signal_anchor_ids": list(signal_anchor_ids),
                "metadata": dict(metadata or {}),
            }
        )
        return replace(inspection, screenshot_path=str(screenshot_path))


def _runtime_navigation_plan() -> MerchantCommissionMeowFullRunNavigationPlan:
    return MerchantCommissionMeowFullRunNavigationPlan(
        entry_plan=MerchantCommissionMeowEntryNavigationPlan(
            activity_button_point=(101, 102),
            carnival_entry_point=(103, 104),
            merchant_commission_icon_point=(105, 106),
            go_now_point=(107, 108),
            npc_commission_option_point=(109, 110),
            meow_accept_point=(111, 112),
            close_list_point=(113, 114),
            expand_task_tab_point=(115, 116),
            task_list_swipe_start=(117, 118),
            task_list_swipe_end=(119, 120),
            task_list_swipe_duration_ms=321,
            wait_after_activity_open_sec=0.0,
            wait_after_carnival_sec=0.0,
            wait_after_merchant_detail_sec=0.0,
            wait_after_go_now_sec=0.0,
            wait_after_npc_option_sec=0.0,
            wait_after_accept_sec=0.0,
            wait_after_close_list_sec=0.0,
            wait_after_expand_task_tab_sec=0.0,
            wait_after_task_swipe_sec=0.0,
        ),
        active_round_plan=MerchantCommissionMeowActiveRoundNavigationPlan(
            task_entry_point=(201, 202),
            submit_option_point=(203, 204),
            wait_after_task_entry_sec=0.0,
            wait_after_submit_option_sec=0.0,
            submit_panel_plan=MerchantCommissionMeowSubmitPanelNavigationPlan(
                buy_now_point=(301, 302),
                buy_confirm_point=(303, 304),
                submit_point=(305, 306),
                wait_after_buy_sec=0.0,
                wait_after_confirm_sec=0.0,
            ),
        ),
    )


def _inspection(
    checkpoint_id: str,
    *,
    matched_anchor_ids: list[str] | None = None,
    text_evidence: list[MerchantCommissionMeowObservedTextEvidence] | None = None,
    round_index: int | None = None,
) -> MerchantCommissionMeowCheckpointInspection:
    return MerchantCommissionMeowCheckpointInspection(
        checkpoint_id=checkpoint_id,
        screenshot_path="",
        matched_anchor_ids=list(matched_anchor_ids or []),
        text_evidence=list(text_evidence or []),
        round_index=round_index,
    )


def _text_evidence(raw_text: str, confidence: float) -> MerchantCommissionMeowObservedTextEvidence:
    return MerchantCommissionMeowObservedTextEvidence(
        source_type="ocr",
        raw_text=raw_text,
        normalized_text=raw_text.replace(" ", ""),
        bbox=(12, 24, 144, 28),
        confidence=confidence,
        screenshot_ref="captures/task-list-round.png",
        reader="mock_ocr",
    )
