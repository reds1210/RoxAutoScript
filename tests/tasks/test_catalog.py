from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository


class TaskFoundationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()

    def test_discovers_pre_gate_3_blueprints(self) -> None:
        blueprints = self.repository.discover_blueprints()

        self.assertEqual(
            [blueprint.task_id for blueprint in blueprints],
            [
                "daily_ui.claim_rewards",
                "daily_ui.guild_check_in",
                "odin.preset_entry",
            ],
        )
        self.assertTrue(all(blueprint.implementation_state.value == "spec_only" for blueprint in blueprints))
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
            "missing",
        )
        self.assertEqual(
            records["odin.preset_entry:golden:odin_idle_state"].status.value,
            "planned",
        )
