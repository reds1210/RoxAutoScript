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

