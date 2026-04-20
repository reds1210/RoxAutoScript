from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks.daily_ui import load_daily_ui_blueprints, load_daily_ui_catalog


class DailyUiFoundationsTests(unittest.TestCase):
    def test_loads_daily_ui_catalog(self) -> None:
        catalog = load_daily_ui_catalog()

        self.assertEqual(catalog.pack_id, "daily_ui")
        self.assertEqual(len(catalog.entries), 2)

    def test_loads_daily_ui_blueprints(self) -> None:
        blueprints = load_daily_ui_blueprints()

        self.assertEqual(
            [blueprint.task_id for blueprint in blueprints],
            ["daily_ui.claim_rewards", "daily_ui.guild_check_in"],
        )
