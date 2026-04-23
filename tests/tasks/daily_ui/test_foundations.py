from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository
from roxauto.tasks.daily_ui import load_daily_ui_blueprints, load_daily_ui_catalog


class DailyUiFoundationsTests(unittest.TestCase):
    def test_loads_daily_ui_catalog(self) -> None:
        catalog = load_daily_ui_catalog()

        self.assertEqual(catalog.pack_id, "daily_ui")
        self.assertEqual(len(catalog.entries), 3)
        self.assertEqual(catalog.entries[0].display_name, "每日領獎")
        self.assertEqual(
            catalog.entries[0].required_anchors,
            [
                "daily_ui.reward_panel",
                "daily_ui.claim_reward",
                "common.confirm_button",
                "common.close_button",
            ],
        )
        self.assertEqual(
            catalog.entries[0].metadata["supporting_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            catalog.entries[0].metadata["runtime_seam"]["task_spec_builder"],
            "roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_task_spec",
        )
        self.assertEqual(catalog.entries[2].task_id, "daily_ui.guild_order_submit")
        self.assertEqual(catalog.entries[2].display_name, "Guild Order Submit")
        self.assertEqual(
            catalog.entries[2].metadata["supporting_anchor_ids"],
            [
                "daily_ui.guild_order_material_label",
                "daily_ui.guild_order_required_quantity",
                "daily_ui.guild_order_available_quantity",
                "daily_ui.guild_order_custom_list_button",
                "daily_ui.guild_order_custom_list_panel",
                "daily_ui.guild_order_custom_option_material_label",
                "daily_ui.guild_order_custom_option_required_quantity",
                "daily_ui.guild_order_custom_option_available_quantity",
                "daily_ui.guild_order_custom_option_selected_state",
                "daily_ui.guild_order_unavailable_state",
                "daily_ui.guild_order_insufficient_material_feedback",
                "daily_ui.guild_order_submit_result_state",
            ],
        )

    def test_loads_daily_ui_blueprints(self) -> None:
        blueprints = load_daily_ui_blueprints()

        self.assertEqual(
            [blueprint.task_id for blueprint in blueprints],
            ["daily_ui.claim_rewards", "daily_ui.guild_check_in", "daily_ui.guild_order_submit"],
        )
        self.assertEqual(
            blueprints[0].required_anchors,
            [
                "daily_ui.reward_panel",
                "daily_ui.claim_reward",
                "common.confirm_button",
                "common.close_button",
            ],
        )
        self.assertEqual(
            blueprints[0].metadata["supporting_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            [case.screen_slug for case in blueprints[0].golden_cases],
            ["reward_panel", "claim_button", "confirm_state"],
        )
        self.assertEqual(
            blueprints[2].metadata["foundation_requirement_ids"],
            [
                "foundation.daily_ui.guild_order_visible_quantity_contract",
                "foundation.daily_ui.guild_order_result_state_contract",
                "foundation.daily_ui.guild_order_custom_option_contract",
            ],
        )

    def test_daily_ui_readiness_states(self) -> None:
        repository = TaskFoundationRepository.load_default()
        reports = {report.task_id: report for report in repository.evaluate_task_readinesses()}

        self.assertEqual(reports["daily_ui.claim_rewards"].builder_readiness_state.value, "ready")
        self.assertEqual(reports["daily_ui.claim_rewards"].implementation_readiness_state.value, "ready")
        self.assertEqual(
            [item.metadata["anchor_id"] for item in reports["daily_ui.claim_rewards"].warning_requirements],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            [item.metadata["requirement_level"] for item in reports["daily_ui.claim_rewards"].warning_requirements],
            ["supporting"],
        )
        self.assertEqual(reports["daily_ui.guild_check_in"].builder_readiness_state.value, "blocked_by_asset")
        self.assertEqual(reports["daily_ui.guild_order_submit"].builder_readiness_state.value, "blocked_by_foundation")
        self.assertEqual(
            reports["daily_ui.guild_order_submit"].implementation_readiness_state.value,
            "blocked_by_foundation",
        )
