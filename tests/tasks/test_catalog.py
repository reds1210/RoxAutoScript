from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository


class TaskFoundationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()

    def test_discovers_pre_gate_3_blueprints(self) -> None:
        blueprints = self.repository.discover_blueprints()
        implementation_states = {
            blueprint.task_id: blueprint.implementation_state.value
            for blueprint in blueprints
        }

        self.assertEqual(
            [blueprint.task_id for blueprint in blueprints],
            [
                "daily_ui.claim_rewards",
                "daily_ui.guild_check_in",
                "daily_ui.guild_order_submit",
                "daily_ui.merchant_commission_meow",
                "odin.preset_entry",
            ],
        )
        self.assertEqual(
            implementation_states,
            {
                "daily_ui.claim_rewards": "fixtured",
                "daily_ui.guild_check_in": "spec_only",
                "daily_ui.guild_order_submit": "spec_only",
                "daily_ui.merchant_commission_meow": "spec_only",
                "odin.preset_entry": "spec_only",
            },
        )
        self.assertIn("daily_ui.claim_reward", blueprints[0].required_anchors)
        self.assertIn("daily_ui.reward_panel", blueprints[0].required_anchors)
        self.assertNotIn("daily_ui.reward_confirm_state", blueprints[0].required_anchors)
        self.assertEqual(
            blueprints[0].metadata["supporting_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertTrue(blueprints[0].steps)

    def test_loads_fixture_profiles_and_convention(self) -> None:
        profiles = self.repository.discover_fixture_profiles()
        convention = self.repository.load_golden_convention()

        self.assertEqual(len(profiles), 4)
        self.assertEqual(profiles[0].locale, "zh-TW")
        self.assertEqual(convention.required_variants, ["baseline", "failure"])
        self.assertEqual(profiles[0].metadata["region"], "tw")

    def test_inventory_matches_discovered_blueprints(self) -> None:
        curated = self.repository.load_inventory()
        built = self.repository.build_task_inventory()

        self.assertEqual(curated.to_dict(), built.to_dict())
        self.assertEqual(curated.records[0].manifest_path, "packs/daily_ui/daily_claim_rewards.task.json")
        self.assertIn("{screen_slug}", built.records[0].golden_root)
        self.assertEqual(
            curated.records[0].metadata["asset_state"],
            "mixed_live_capture_and_curated_stand_in",
        )
        self.assertEqual(
            curated.records[0].metadata["asset_provenance"]["replacement_pending_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            curated.records[0].metadata["supporting_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            curated.records[0].metadata["post_claim_resolution"]["decision"],
            "direct_result_overlay_is_valid",
        )
        self.assertEqual(
            curated.records[0].metadata["claim_rewards_alternate_post_tap_capture_ids"],
            [
                "post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22",
                "post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap",
                "post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap",
                "post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap",
            ],
        )
        self.assertEqual(
            curated.records[0].metadata["claim_rewards_capture_inventory"]["missing_device_serials"],
            [],
        )
        self.assertEqual(
            curated.records[0].metadata["runtime_seam"]["runtime_seam_builder"],
            "roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_runtime_seam",
        )
        self.assertEqual(built.records[0].metadata["signal_contract_version"], "claim_rewards.v2")
        meow_record = next(record for record in curated.records if record.task_id == "daily_ui.merchant_commission_meow")
        self.assertEqual(meow_record.fixture_profile_paths, ["fixture_profiles/default_tw_merchant.fixture.json"])
        self.assertEqual(
            meow_record.metadata["merchant_commission_meow_loop_contract"]["preferred_reentry_mode"],
            "left_task_list",
        )
        self.assertTrue(
            meow_record.metadata["merchant_commission_meow_submission_policy"]["allow_immediate_buy"]
        )
        self.assertEqual(
            meow_record.metadata["merchant_commission_meow_decision_contract"]["allowed_decisions"],
            ["direct_submit", "immediate_buy_then_submit", "stop_for_operator"],
        )
        self.assertEqual(
            meow_record.metadata["merchant_commission_meow_handoff_fields"],
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

    def test_discovers_pack_catalogs(self) -> None:
        catalogs = self.repository.discover_pack_catalogs()

        self.assertEqual([catalog.pack_id for catalog in catalogs], ["daily_ui", "odin"])
        self.assertEqual(catalogs[0].entries[0].task_id, "daily_ui.claim_rewards")
        self.assertEqual(catalogs[0].entries[0].display_name, "每日領獎")
        self.assertEqual(
            catalogs[0].entries[0].required_anchors,
            [
                "daily_ui.reward_panel",
                "daily_ui.claim_reward",
                "common.confirm_button",
                "common.close_button",
            ],
        )
        self.assertEqual(
            catalogs[0].entries[0].metadata["supporting_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(catalogs[0].entries[2].task_id, "daily_ui.guild_order_submit")
        self.assertEqual(
            catalogs[0].entries[2].metadata["signal_contract_version"],
            "guild_order_submit.v2",
        )
        self.assertEqual(catalogs[0].entries[3].task_id, "daily_ui.merchant_commission_meow")
        self.assertEqual(
            catalogs[0].entries[3].metadata["signal_contract_version"],
            "merchant_commission_meow.v1",
        )

    def test_builds_asset_inventory(self) -> None:
        inventory = self.repository.build_asset_inventory()
        records = {record.asset_id: record for record in inventory.records}

        self.assertTrue(
            records["daily_ui.claim_rewards:template:daily_ui.reward_panel"].metadata["live_capture"]
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:template:daily_ui.claim_reward"].status.value,
            "present",
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:template:daily_ui.claim_reward"].metadata["provenance_kind"],
            "live_capture",
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:template:daily_ui.reward_panel"].status.value,
            "present",
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:template:daily_ui.reward_confirm_state"].status.value,
            "present",
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:template:daily_ui.reward_confirm_state"].metadata["requirement_level"],
            "supporting",
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:template:common.confirm_button"].status.value,
            "present",
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:golden:claim_button"].status.value,
            "present",
        )
        self.assertTrue(
            records["daily_ui.claim_rewards:golden:claim_button"].metadata["live_capture"]
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:golden:confirm_state"].status.value,
            "present",
        )
        self.assertEqual(
            records["daily_ui.claim_rewards:golden:reward_panel"].status.value,
            "present",
        )
        self.assertEqual(
            records["daily_ui.guild_check_in:template:daily_ui.guild_check_in_button"].status.value,
            "placeholder",
        )
        self.assertEqual(
            records["daily_ui.guild_order_submit:template:daily_ui.guild_order_list_panel"].status.value,
            "placeholder",
        )
        self.assertEqual(
            records["daily_ui.guild_order_submit:template:daily_ui.guild_order_list_panel"].source_path,
            "assets/templates/daily_ui/manifest.json#daily_ui.guild_order_list_panel",
        )
        self.assertEqual(
            records["daily_ui.guild_order_submit:template:daily_ui.guild_order_available_quantity"].metadata["requirement_level"],
            "supporting",
        )
        self.assertEqual(
            records["daily_ui.guild_order_submit:golden:order_list"].status.value,
            "planned",
        )
        self.assertEqual(
            records["daily_ui.merchant_commission_meow:template:daily_ui.merchant_commission_poring_button"].status.value,
            "missing",
        )
        self.assertEqual(
            records["daily_ui.merchant_commission_meow:template:daily_ui.merchant_commission_empty_inventory_feedback"].metadata[
                "requirement_level"
            ],
            "supporting",
        )
        self.assertEqual(
            records["daily_ui.merchant_commission_meow:golden:merchant_group_list"].status.value,
            "planned",
        )
        self.assertEqual(
            records["daily_ui.merchant_commission_meow:golden:meow_empty_submit_panel"].metadata[
                "requirement_level"
            ],
            "supporting",
        )
        self.assertEqual(
            records["odin.preset_entry:golden:odin_idle_state"].status.value,
            "planned",
        )
        self.assertEqual(self.repository.load_asset_inventory().to_dict(), inventory.to_dict())

    def test_builds_runtime_builder_inputs(self) -> None:
        inputs = self.repository.build_runtime_builder_inputs()
        by_task = {item.task_id: item for item in inputs}

        self.assertEqual(
            by_task["daily_ui.claim_rewards"].runtime_requirement_ids,
            ["runtime.daily_ui.dispatch_bridge"],
        )
        self.assertEqual(
            by_task["daily_ui.claim_rewards"].metadata["runtime_seam"]["task_spec_builder"],
            "roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_task_spec",
        )
        self.assertEqual(
            by_task["daily_ui.claim_rewards"].metadata["runtime_seam"]["result_signal_keys"],
            [
                "failure_reason_id",
                "outcome_code",
                "expected_panel_states",
                "inspection_attempts",
                "signals",
                "step_outcome",
                "telemetry",
                "task_action",
            ],
        )
        self.assertEqual(
            by_task["daily_ui.claim_rewards"].required_anchors,
            [
                "daily_ui.reward_panel",
                "daily_ui.claim_reward",
                "common.confirm_button",
                "common.close_button",
            ],
        )
        self.assertEqual(
            by_task["daily_ui.claim_rewards"].metadata["supporting_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            by_task["daily_ui.claim_rewards"].metadata["post_claim_resolution"]["decision"],
            "direct_result_overlay_is_valid",
        )
        self.assertEqual(
            by_task["daily_ui.guild_check_in"].asset_requirement_ids,
            ["asset.daily_ui.guild_check_in_button"],
        )
        self.assertEqual(
            by_task["daily_ui.guild_order_submit"].asset_requirement_ids,
            [
                "asset.daily_ui.guild_order_list",
                "asset.daily_ui.guild_order_detail",
                "asset.daily_ui.guild_order_submit_button",
                "asset.daily_ui.guild_order_refresh_button",
            ],
        )
        self.assertEqual(
            by_task["daily_ui.guild_order_submit"].foundation_requirement_ids,
            [
                "foundation.daily_ui.guild_order_visible_quantity_contract",
                "foundation.daily_ui.guild_order_result_state_contract",
                "foundation.daily_ui.guild_order_custom_option_contract",
            ],
        )
        self.assertEqual(
            by_task["daily_ui.guild_order_submit"].metadata["guild_order_decision_contract"]["allowed_decisions"],
            ["submit", "skip", "refresh"],
        )
        self.assertEqual(
            by_task["daily_ui.merchant_commission_meow"].asset_requirement_ids,
            [
                "asset.daily_ui.merchant_commission_poring_button",
                "asset.daily_ui.merchant_commission_carnival_entry",
                "asset.daily_ui.merchant_commission_detail_modal",
                "asset.daily_ui.merchant_commission_go_now_button",
                "asset.daily_ui.merchant_commission_npc_dialog",
                "asset.daily_ui.merchant_commission_list_panel",
                "asset.daily_ui.merchant_commission_meow_accept_button",
                "asset.daily_ui.merchant_commission_task_list_entry",
                "asset.daily_ui.merchant_commission_meow_submit_option",
                "asset.daily_ui.merchant_commission_submit_item_panel",
                "asset.daily_ui.merchant_commission_buy_now_button",
                "asset.daily_ui.merchant_commission_buy_confirmation_dialog",
                "asset.daily_ui.merchant_commission_buy_confirm_button",
                "asset.daily_ui.merchant_commission_submit_button",
            ],
        )
        self.assertEqual(
            by_task["daily_ui.merchant_commission_meow"].metadata["merchant_commission_meow_loop_contract"][
                "preferred_reentry_mode"
            ],
            "left_task_list",
        )
        self.assertTrue(
            by_task["daily_ui.merchant_commission_meow"].metadata["merchant_commission_meow_submission_policy"][
                "allow_immediate_buy"
            ]
        )
        self.assertEqual(
            by_task["daily_ui.merchant_commission_meow"].metadata["merchant_commission_meow_decision_contract"][
                "allowed_decisions"
            ],
            ["direct_submit", "immediate_buy_then_submit", "stop_for_operator"],
        )
        self.assertEqual(
            by_task["daily_ui.merchant_commission_meow"].metadata["merchant_commission_meow_route_contract"][
                "entry_checkpoint_ids"
            ],
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
            by_task["odin.preset_entry"].calibration_requirement_ids,
            ["calibration.odin.idle_state_profile"],
        )

    def test_evaluates_task_readinesses(self) -> None:
        reports = self.repository.evaluate_task_readinesses()
        by_task = {report.task_id: report for report in reports}

        self.assertEqual(by_task["daily_ui.claim_rewards"].builder_readiness_state.value, "ready")
        self.assertEqual(
            by_task["daily_ui.claim_rewards"].implementation_readiness_state.value,
            "ready",
        )
        self.assertTrue(by_task["daily_ui.claim_rewards"].implementation_requirements[0].satisfied)
        self.assertIn(
            "runtime_input_builder=roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_runtime_input",
            by_task["daily_ui.claim_rewards"].implementation_requirements[0].details,
        )
        self.assertIn(
            "runtime_seam_builder=roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_runtime_seam",
            by_task["daily_ui.claim_rewards"].implementation_requirements[0].details,
        )
        self.assertEqual(
            [item.metadata["anchor_id"] for item in by_task["daily_ui.claim_rewards"].warning_requirements],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            [item.metadata["requirement_level"] for item in by_task["daily_ui.claim_rewards"].warning_requirements],
            ["supporting"],
        )
        self.assertEqual(by_task["daily_ui.guild_check_in"].builder_readiness_state.value, "blocked_by_asset")
        self.assertEqual(
            by_task["daily_ui.guild_check_in"].implementation_readiness_state.value,
            "blocked_by_asset",
        )
        self.assertEqual(
            by_task["daily_ui.guild_order_submit"].builder_readiness_state.value,
            "blocked_by_foundation",
        )
        self.assertEqual(
            by_task["daily_ui.guild_order_submit"].implementation_readiness_state.value,
            "blocked_by_foundation",
        )
        self.assertEqual(
            [item.requirement_id for item in by_task["daily_ui.guild_order_submit"].builder_requirements],
            [
                "asset.daily_ui.guild_order_list",
                "asset.daily_ui.guild_order_detail",
                "asset.daily_ui.guild_order_submit_button",
                "asset.daily_ui.guild_order_refresh_button",
                "foundation.daily_ui.guild_order_visible_quantity_contract",
                "foundation.daily_ui.guild_order_result_state_contract",
                "foundation.daily_ui.guild_order_custom_option_contract",
            ],
        )
        self.assertEqual(
            by_task["daily_ui.merchant_commission_meow"].builder_readiness_state.value,
            "blocked_by_asset",
        )
        self.assertEqual(
            by_task["daily_ui.merchant_commission_meow"].implementation_readiness_state.value,
            "blocked_by_asset",
        )
        self.assertEqual(
            [item.requirement_id for item in by_task["daily_ui.merchant_commission_meow"].builder_requirements],
            [
                "asset.daily_ui.merchant_commission_poring_button",
                "asset.daily_ui.merchant_commission_carnival_entry",
                "asset.daily_ui.merchant_commission_detail_modal",
                "asset.daily_ui.merchant_commission_go_now_button",
                "asset.daily_ui.merchant_commission_npc_dialog",
                "asset.daily_ui.merchant_commission_list_panel",
                "asset.daily_ui.merchant_commission_meow_accept_button",
                "asset.daily_ui.merchant_commission_task_list_entry",
                "asset.daily_ui.merchant_commission_meow_submit_option",
                "asset.daily_ui.merchant_commission_submit_item_panel",
                "asset.daily_ui.merchant_commission_buy_now_button",
                "asset.daily_ui.merchant_commission_buy_confirmation_dialog",
                "asset.daily_ui.merchant_commission_buy_confirm_button",
                "asset.daily_ui.merchant_commission_submit_button",
            ],
        )
        self.assertEqual(by_task["odin.preset_entry"].builder_readiness_state.value, "ready")
        self.assertEqual(
            by_task["odin.preset_entry"].implementation_readiness_state.value,
            "blocked_by_calibration",
        )

    def test_loads_curated_readiness_report(self) -> None:
        readiness = self.repository.load_readiness_report()

        self.assertEqual(readiness.report_id, "pre_gate_3_task_readiness")
        self.assertEqual(len(readiness.reports), 5)
        claim_rewards = next(report for report in readiness.reports if report.task_id == "daily_ui.claim_rewards")
        guild_order_submit = next(
            report for report in readiness.reports if report.task_id == "daily_ui.guild_order_submit"
        )
        merchant_commission_meow = next(
            report for report in readiness.reports if report.task_id == "daily_ui.merchant_commission_meow"
        )
        self.assertEqual(claim_rewards.implementation_readiness_state.value, "ready")
        self.assertEqual(self.repository.build_readiness_collection().to_dict(), readiness.to_dict())
        self.assertEqual(
            [item.metadata["anchor_id"] for item in claim_rewards.warning_requirements],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            [item.metadata["requirement_level"] for item in claim_rewards.warning_requirements],
            ["supporting"],
        )
        self.assertEqual(guild_order_submit.builder_readiness_state.value, "blocked_by_foundation")
        self.assertEqual(merchant_commission_meow.builder_readiness_state.value, "blocked_by_asset")

    def test_guild_order_foundation_checks_ignore_golden_records(self) -> None:
        from roxauto.tasks.models import TaskAssetKind, TaskAssetRecord, TaskAssetStatus

        golden_only_records = [
            TaskAssetRecord(
                asset_id="daily_ui.guild_order_submit:golden:fake",
                pack_id="daily_ui",
                task_id="daily_ui.guild_order_submit",
                asset_kind=TaskAssetKind.GOLDEN_SCREENSHOT,
                status=TaskAssetStatus.PRESENT,
                source_path="assets/templates/daily_ui/goldens/fake.png",
                metadata={"anchor_id": "daily_ui.guild_order_unavailable_state"},
            )
        ]

        self.assertFalse(
            self.repository._all_anchor_records_present(
                golden_only_records,
                ["daily_ui.guild_order_unavailable_state"],
            )
        )
        self.assertEqual(
            self.repository._anchor_status_summary(
                golden_only_records,
                ["daily_ui.guild_order_unavailable_state"],
            ),
            "daily_ui.guild_order_unavailable_state:missing",
        )
