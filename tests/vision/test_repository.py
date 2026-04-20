from __future__ import annotations

import unittest
from pathlib import Path

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

