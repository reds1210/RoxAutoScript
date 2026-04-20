from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.instance_registry import InstanceRegistry
from roxauto.core.models import InstanceState, InstanceStatus


class InstanceRegistryTests(unittest.TestCase):
    def test_sync_and_update(self) -> None:
        registry = InstanceRegistry()
        state = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )

        registry.sync([state])
        self.assertIsNotNone(registry.get("mumu-0"))
        updated = registry.update_status("mumu-0", InstanceStatus.BUSY)

        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, InstanceStatus.BUSY)
