from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import (
    GoldenScreenshotCase,
    GoldenScreenshotConvention,
    TaskAssetInventory,
    TaskAssetKind,
    TaskAssetRecord,
    TaskAssetStatus,
    TaskFixtureProfile,
    TaskPackCatalog,
    TaskPackCatalogEntry,
    TaskStepBlueprint,
)


class GoldenScreenshotConventionTests(unittest.TestCase):
    def test_renders_revisioned_png_path(self) -> None:
        convention = GoldenScreenshotConvention(convention_id="goldens")

        path = convention.render_path(
            pack_id="daily_ui",
            task_id="daily_ui.claim_rewards",
            screen_slug="reward_panel",
            variant="baseline",
            revision=2,
        )

        self.assertEqual(
            path.as_posix(),
            "daily_ui/daily_ui_claim_rewards/reward_panel/daily_ui_claim_rewards__reward_panel__baseline__v2.png",
        )
        self.assertTrue(convention.is_valid_filename(path.name))

    def test_rejects_invalid_filename(self) -> None:
        convention = GoldenScreenshotConvention(convention_id="goldens")

        self.assertFalse(convention.is_valid_filename("DailyClaimRewards.png"))


class TaskFixtureProfileTests(unittest.TestCase):
    def test_round_trips_fixture_profile(self) -> None:
        profile = TaskFixtureProfile(
            fixture_id="fixture.tw.daily_ui.default",
            display_name="TW Daily UI Fixture",
            template_packs=["common", "daily_ui"],
            metadata={"purpose": "daily_ui"},
        )

        restored = TaskFixtureProfile.from_json(profile.to_json())

        self.assertEqual(restored.fixture_id, profile.fixture_id)
        self.assertEqual(restored.template_packs, ["common", "daily_ui"])


class GoldenScreenshotCaseTests(unittest.TestCase):
    def test_case_serializes(self) -> None:
        case = GoldenScreenshotCase(
            screen_slug="reward_panel",
            variants=["baseline", "failure"],
            notes="Stable reward panel states.",
        )

        payload = case.to_dict()

        self.assertEqual(payload["screen_slug"], "reward_panel")
        self.assertEqual(payload["variants"], ["baseline", "failure"])


class TaskPackCatalogTests(unittest.TestCase):
    def test_round_trips_pack_catalog(self) -> None:
        catalog = TaskPackCatalog(
            pack_id="daily_ui",
            version="0.1.0",
            entries=[
                TaskPackCatalogEntry(
                    task_id="daily_ui.claim_rewards",
                    blueprint_path="packs/daily_ui/daily_claim_rewards.task.json",
                    display_name="Daily Reward Claim",
                )
            ],
        )

        restored = TaskPackCatalog.from_dict(catalog.to_dict())

        self.assertEqual(restored.pack_id, "daily_ui")
        self.assertEqual(restored.entries[0].task_id, "daily_ui.claim_rewards")


class TaskAssetInventoryTests(unittest.TestCase):
    def test_round_trips_asset_inventory(self) -> None:
        inventory = TaskAssetInventory(
            inventory_id="assets",
            version="0.1.0",
            records=[
                TaskAssetRecord(
                    asset_id="daily_ui.claim_rewards:template:daily_ui.claim_reward",
                    pack_id="daily_ui",
                    task_id="daily_ui.claim_rewards",
                    asset_kind=TaskAssetKind.TEMPLATE,
                    status=TaskAssetStatus.PLACEHOLDER,
                    source_path="assets/templates/daily_ui/manifest.json#daily_ui.claim_reward",
                )
            ],
        )

        restored = TaskAssetInventory.from_json(inventory.to_json())

        self.assertEqual(restored.records[0].status, TaskAssetStatus.PLACEHOLDER)
        self.assertEqual(restored.records[0].asset_kind, TaskAssetKind.TEMPLATE)


class TaskStepBlueprintTests(unittest.TestCase):
    def test_step_serializes(self) -> None:
        step = TaskStepBlueprint(
            step_id="verify_claim_affordance",
            action="vision_verify",
            success_condition="Claim state can be classified.",
        )

        payload = step.to_dict()

        self.assertEqual(payload["step_id"], "verify_claim_affordance")
        self.assertEqual(payload["action"], "vision_verify")
