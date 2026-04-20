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
        self.assertIn("daily_ui.claim_button", blueprints[0].required_anchors)

    def test_loads_fixture_profiles_and_convention(self) -> None:
        profiles = self.repository.discover_fixture_profiles()
        convention = self.repository.load_golden_convention()

        self.assertEqual(len(profiles), 3)
        self.assertEqual(profiles[0].locale, "zh-TW")
        self.assertEqual(convention.required_variants, ["baseline", "failure"])

    def test_inventory_matches_discovered_blueprints(self) -> None:
        curated = self.repository.load_inventory()
        built = self.repository.build_inventory()

        self.assertEqual(
            [record.task_id for record in curated.records],
            [record.task_id for record in built.records],
        )
        self.assertEqual(curated.records[0].manifest_path, "packs/daily_ui/daily_claim_rewards.task.json")
        self.assertIn("{screen_slug}", built.records[0].golden_root)
