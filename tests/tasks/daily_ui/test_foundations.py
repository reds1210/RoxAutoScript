from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository
from roxauto.tasks.daily_ui import load_daily_ui_blueprints, load_daily_ui_catalog


class DailyUiFoundationsTests(unittest.TestCase):
    def test_loads_daily_ui_catalog(self) -> None:
        catalog = load_daily_ui_catalog()

        self.assertEqual(catalog.pack_id, "daily_ui")
        self.assertEqual(len(catalog.entries), 2)
        self.assertEqual(catalog.entries[0].display_name, "每日領獎")

    def test_loads_daily_ui_blueprints(self) -> None:
        blueprints = load_daily_ui_blueprints()

        self.assertEqual(
            [blueprint.task_id for blueprint in blueprints],
            ["daily_ui.claim_rewards", "daily_ui.guild_check_in"],
        )

    def test_daily_ui_readiness_states(self) -> None:
        repository = TaskFoundationRepository.load_default()
        reports = {report.task_id: report for report in repository.evaluate_task_readinesses()}

        self.assertEqual(reports["daily_ui.claim_rewards"].builder_readiness_state.value, "ready")
        self.assertEqual(reports["daily_ui.claim_rewards"].implementation_readiness_state.value, "ready")
        self.assertEqual(reports["daily_ui.guild_check_in"].builder_readiness_state.value, "blocked_by_asset")
