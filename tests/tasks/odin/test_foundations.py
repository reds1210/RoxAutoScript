from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository
from roxauto.tasks.odin import load_odin_blueprints, load_odin_catalog


class OdinFoundationsTests(unittest.TestCase):
    def test_loads_odin_catalog(self) -> None:
        catalog = load_odin_catalog()

        self.assertEqual(catalog.pack_id, "odin")
        self.assertEqual(len(catalog.entries), 1)

    def test_loads_odin_blueprints(self) -> None:
        blueprints = load_odin_blueprints()

        self.assertEqual([blueprint.task_id for blueprint in blueprints], ["odin.preset_entry"])

    def test_odin_readiness_state(self) -> None:
        repository = TaskFoundationRepository.load_default()
        reports = {report.task_id: report for report in repository.evaluate_task_readinesses()}

        self.assertEqual(reports["odin.preset_entry"].builder_readiness_state.value, "ready")
        self.assertEqual(reports["odin.preset_entry"].implementation_readiness_state.value, "blocked_by_calibration")
