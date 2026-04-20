from __future__ import annotations

import json
import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.tasks import GoldenScreenshotConvention, TaskAssetStatus, TaskFoundationRepository


class TaskFixtureExamplesTests(unittest.TestCase):
    def test_golden_examples_follow_convention(self) -> None:
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "golden_examples.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        convention = GoldenScreenshotConvention(convention_id="goldens")

        self.assertTrue(payload["examples"])
        for example in payload["examples"]:
            self.assertTrue(convention.is_valid_filename(example), example)

    def test_blueprints_reference_known_fixture_profiles(self) -> None:
        repository = TaskFoundationRepository.load_default()
        known_profiles = {
            path.relative_to(repository.root).as_posix()
            for path in (repository.root / "fixture_profiles").glob("*.fixture.json")
        }

        for blueprint in repository.discover_blueprints():
            self.assertTrue(blueprint.fixture_profile_paths)
            self.assertTrue(set(blueprint.fixture_profile_paths).issubset(known_profiles))

    def test_curated_asset_inventory_matches_expected_gaps(self) -> None:
        repository = TaskFoundationRepository.load_default()
        inventory = repository.load_asset_inventory()
        statuses = {record.asset_id: record.status for record in inventory.records}

        self.assertEqual(
            statuses["daily_ui.guild_check_in:template:daily_ui.guild_check_in_button"],
            TaskAssetStatus.MISSING,
        )
        self.assertEqual(
            statuses["daily_ui.claim_rewards:template:daily_ui.claim_reward"],
            TaskAssetStatus.PLACEHOLDER,
        )
