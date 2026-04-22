from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.vision import AnchorRepository


class AnchorRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.templates_root = Path(__file__).resolve().parents[2] / "assets" / "templates"

    def test_loads_common_repository(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "common")

        self.assertEqual(repository.repository_id, "common")
        self.assertEqual(repository.display_name, "Common UI Templates")
        self.assertEqual(len(repository.list_anchors()), 2)
        self.assertEqual(repository.get_anchor("common.close_button").template_path, "anchors/common_close_button.svg")
        self.assertTrue(repository.resolve_asset_path("common.confirm_button").exists())
        self.assertEqual(repository.manifest.metadata["owner"], "vision-lab")

    def test_discovers_all_sample_repositories(self) -> None:
        repositories = AnchorRepository.discover(self.templates_root)
        repository_ids = {repository.repository_id for repository in repositories}

        self.assertEqual(repository_ids, {"common", "daily_ui", "odin"})

    def test_daily_ui_repository_includes_guild_check_in_anchor(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "daily_ui")

        self.assertTrue(repository.has_anchor("daily_ui.guild_check_in_button"))
        self.assertTrue(repository.resolve_asset_path("daily_ui.guild_check_in_button").exists())
        reward_panel_curation = repository.get_anchor_curation("daily_ui.reward_panel")
        self.assertIsNotNone(reward_panel_curation)
        self.assertEqual(reward_panel_curation.status.value, "curated")
        self.assertEqual(reward_panel_curation.scene_id, "reward_panel_open")
        self.assertEqual(reward_panel_curation.reference_count, 3)
        self.assertEqual(reward_panel_curation.provenance.kind.value, "live_capture")
        self.assertEqual(reward_panel_curation.provenance.locale, "zh-TW")
        self.assertEqual(
            repository.get_primary_curation_reference("daily_ui.reward_panel").reference_id,
            "reward_panel_baseline_v1",
        )
        self.assertTrue(repository.resolve_curation_reference_path("daily_ui.reward_panel").exists())
        self.assertEqual(
            repository.get_task_support("daily_ui.claim_rewards")["required_anchor_roles"],
            ["reward_panel", "claim_reward_button", "confirm_state"],
        )
        self.assertEqual(
            repository.get_task_support("daily_ui.claim_rewards")["golden_catalog_path"],
            "goldens/claim_rewards/catalog.json",
        )
        self.assertEqual(
            repository.get_task_support("daily_ui.claim_rewards")["live_capture_coverage"]["live_anchor_ids"],
            ["daily_ui.claim_reward", "daily_ui.reward_panel"],
        )
        self.assertEqual(
            repository.get_task_support("daily_ui.claim_rewards")["live_capture_coverage"]["live_context_anchor_ids"],
            [],
        )
        self.assertEqual(
            repository.get_claim_rewards_post_tap_contract()["dispatch_recommendation"],
            "direct_result_overlay_is_valid",
        )
        self.assertEqual(
            repository.get_claim_rewards_post_tap_contract()["observed_live_outcome_scene_ids"],
            ["reward_post_tap_overlay", "reward_claimed_result_state"],
        )
        self.assertEqual(
            reward_panel_curation.metadata["failure_case"],
            "reward_panel_not_open_or_wrong_surface",
        )
        claim_rewards_catalog = repository.get_claim_rewards_golden_catalog()
        self.assertIsNotNone(claim_rewards_catalog)
        self.assertEqual(claim_rewards_catalog.task_id, "daily_ui.claim_rewards")
        self.assertEqual(len(claim_rewards_catalog.goldens), 3)
        self.assertEqual(len(claim_rewards_catalog.supporting_captures), 9)
        reward_panel_golden = repository.get_claim_rewards_anchor_golden("daily_ui.reward_panel")
        self.assertIsNotNone(reward_panel_golden)
        self.assertEqual(reward_panel_golden.golden_id, "reward_panel_open_baseline_v1")
        self.assertTrue(
            str(repository.resolve_claim_rewards_golden_image_path("daily_ui.reward_panel")).endswith(
                "daily_ui_claim_rewards__reward_panel__baseline__v1.png"
            )
        )
        claim_button_curation = repository.get_anchor_curation("daily_ui.claim_reward")
        self.assertIsNotNone(claim_button_curation)
        self.assertEqual(claim_button_curation.reference_count, 1)
        self.assertEqual(claim_button_curation.provenance.kind.value, "live_capture")
        self.assertEqual(
            repository.list_curation_references("daily_ui.claim_reward")[0].reference_id,
            "claim_button_baseline_v1",
        )
        self.assertTrue(
            str(repository.resolve_curation_reference_paths("daily_ui.claim_reward")[0]).endswith(
                "daily_ui_claim_rewards__claim_button__baseline__v1.png"
            )
        )
        claim_button_supporting_captures = repository.list_claim_rewards_supporting_captures("daily_ui.claim_reward")
        self.assertEqual(
            [capture.capture_id for capture in claim_button_supporting_captures],
            [
                "non_claimable_daily_signin_live_capture_emulator_5556_after_daily_tab_attempt_2",
            ],
        )
        self.assertEqual(
            [capture.evidence_role for capture in claim_button_supporting_captures],
            ["negative_case"],
        )
        self.assertEqual(
            [path.name for path in repository.resolve_claim_rewards_supporting_capture_paths("daily_ui.claim_reward")],
            [
                "daily_ui_claim_rewards__non_claimable_daily_signin__live_capture__emulator_5556__after_daily_tab_attempt_2.png",
            ],
        )
        self.assertIsNone(repository.get_claim_rewards_anchor_golden("daily_ui.guild_check_in_button"))
        self.assertIsNone(repository.get_claim_rewards_anchor_golden("daily_ui.guild_order_list"))
        self.assertIsNone(repository.resolve_claim_rewards_golden_image_path("daily_ui.guild_check_in_button"))
        self.assertEqual(repository.list_claim_rewards_supporting_captures("daily_ui.guild_check_in_button"), [])
        self.assertEqual(repository.resolve_claim_rewards_supporting_capture_paths("daily_ui.guild_order_list"), [])

    def test_repository_exposes_manifest_and_search_helpers(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "common")

        self.assertEqual(repository.manifest_path.name, "manifest.json")
        self.assertEqual(repository.version, "0.1.0")
        self.assertEqual(repository.list_anchor_ids(), ["common.close_button", "common.confirm_button"])
        self.assertTrue(repository.has_anchor("common.close_button"))
        self.assertFalse(repository.has_anchor("common.missing"))
        self.assertEqual(
            [anchor.anchor_id for anchor in repository.find_anchors(query="confirm")],
            ["common.confirm_button"],
        )
        self.assertEqual(
            [anchor.anchor_id for anchor in repository.find_anchors(tag="dialog", limit=1)],
            ["common.close_button"],
        )
        self.assertEqual(
            repository.resolve_template_path("anchors/common_close_button.svg"),
            repository.root / "anchors" / "common_close_button.svg",
        )

    def test_discover_returns_empty_list_for_missing_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            missing_root = Path(temp_dir) / "missing"

            repositories = AnchorRepository.discover(missing_root)

        self.assertEqual(repositories, [])

