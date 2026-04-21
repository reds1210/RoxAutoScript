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
                "odin.preset_entry",
            ],
        )
        self.assertEqual(
            implementation_states,
            {
                "daily_ui.claim_rewards": "fixtured",
                "daily_ui.guild_check_in": "spec_only",
                "odin.preset_entry": "spec_only",
            },
        )
        self.assertIn("daily_ui.claim_reward", blueprints[0].required_anchors)
        self.assertTrue(blueprints[0].steps)

    def test_loads_fixture_profiles_and_convention(self) -> None:
        profiles = self.repository.discover_fixture_profiles()
        convention = self.repository.load_golden_convention()

        self.assertEqual(len(profiles), 3)
        self.assertEqual(profiles[0].locale, "zh-TW")
        self.assertEqual(convention.required_variants, ["baseline", "failure"])
        self.assertEqual(profiles[0].metadata["region"], "tw")

    def test_inventory_matches_discovered_blueprints(self) -> None:
        curated = self.repository.load_inventory()
        built = self.repository.build_task_inventory()

        self.assertEqual(
            [record.task_id for record in curated.records],
            [record.task_id for record in built.records],
        )
        self.assertEqual(curated.records[0].manifest_path, "packs/daily_ui/daily_claim_rewards.task.json")
        self.assertIn("{screen_slug}", built.records[0].golden_root)

    def test_discovers_pack_catalogs(self) -> None:
        catalogs = self.repository.discover_pack_catalogs()

        self.assertEqual([catalog.pack_id for catalog in catalogs], ["daily_ui", "odin"])
        self.assertEqual(catalogs[0].entries[0].task_id, "daily_ui.claim_rewards")

    def test_builds_asset_inventory(self) -> None:
        inventory = self.repository.build_asset_inventory()
        records = {record.asset_id: record for record in inventory.records}

        self.assertEqual(
            records["daily_ui.claim_rewards:template:daily_ui.claim_reward"].status.value,
            "placeholder",
        )
        self.assertEqual(
            records["daily_ui.guild_check_in:template:daily_ui.guild_check_in_button"].status.value,
            "placeholder",
        )
        self.assertEqual(
            records["odin.preset_entry:golden:odin_idle_state"].status.value,
            "planned",
        )

    def test_builds_runtime_builder_inputs(self) -> None:
        inputs = self.repository.build_runtime_builder_inputs()
        by_task = {item.task_id: item for item in inputs}

        self.assertEqual(
            by_task["daily_ui.claim_rewards"].runtime_requirement_ids,
            ["runtime.daily_ui.dispatch_bridge"],
        )
        self.assertEqual(
            by_task["daily_ui.claim_rewards"].required_anchors,
            [
                "common.close_button",
                "common.confirm_button",
                "daily_ui.claim_reward",
            ],
        )
        self.assertEqual(
            by_task["daily_ui.guild_check_in"].asset_requirement_ids,
            ["asset.daily_ui.guild_check_in_button"],
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
        self.assertEqual(by_task["daily_ui.guild_check_in"].builder_readiness_state.value, "blocked_by_asset")
        self.assertEqual(
            by_task["daily_ui.guild_check_in"].implementation_readiness_state.value,
            "blocked_by_asset",
        )
        self.assertEqual(by_task["odin.preset_entry"].builder_readiness_state.value, "ready")
        self.assertEqual(
            by_task["odin.preset_entry"].implementation_readiness_state.value,
            "blocked_by_calibration",
        )

    def test_loads_curated_readiness_report(self) -> None:
        readiness = self.repository.load_readiness_report()

        self.assertEqual(readiness.report_id, "pre_gate_3_task_readiness")
        self.assertEqual(len(readiness.reports), 3)
        claim_rewards = next(report for report in readiness.reports if report.task_id == "daily_ui.claim_rewards")
        self.assertEqual(claim_rewards.implementation_readiness_state.value, "ready")
