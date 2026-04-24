from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository, TaskReadinessState
from roxauto.tasks.daily_ui import (
    MerchantCommissionMeowLoopContract,
    MerchantCommissionMeowRouteContract,
    build_merchant_commission_meow_specification,
    load_merchant_commission_meow_blueprint,
    load_merchant_commission_meow_loop_contract,
    load_merchant_commission_meow_route_contract,
)


class MerchantCommissionMeowFoundationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()

    def test_loads_merchant_commission_meow_blueprint_and_contracts(self) -> None:
        blueprint = load_merchant_commission_meow_blueprint(self.repository)
        route_contract = load_merchant_commission_meow_route_contract(self.repository)
        loop_contract = load_merchant_commission_meow_loop_contract(self.repository)

        self.assertEqual(blueprint.task_id, "daily_ui.merchant_commission_meow")
        self.assertEqual(blueprint.implementation_state.value, "spec_only")
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
        self.assertEqual(specification.metadata["signal_contract_version"], "merchant_commission_meow.v1")
        self.assertEqual(
            specification.metadata["merchant_commission_meow_handoff_fields"],
            [
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
