from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.instance_registry import InstanceRegistry, InstanceStateTransitionError
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

    def test_rejects_invalid_transition_without_force(self) -> None:
        registry = InstanceRegistry()
        state = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.DISCONNECTED,
        )

        registry.sync([state])

        with self.assertRaises(InstanceStateTransitionError):
            registry.transition_status("mumu-0", InstanceStatus.BUSY)

    def test_sync_preserves_runtime_metadata_and_disconnects_missing_instances(self) -> None:
        registry = InstanceRegistry()
        initial = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )

        registry.sync([initial])
        registry.get("mumu-0").metadata["profile_id"] = "main-account"

        registry.sync(
            [
                InstanceState(
                    instance_id="mumu-0",
                    label="MuMu 0",
                    adb_serial="127.0.0.1:16384",
                    status=InstanceStatus.BUSY,
                )
            ]
        )

        refreshed = registry.get("mumu-0")
        self.assertEqual(refreshed.status, InstanceStatus.BUSY)
        self.assertEqual(refreshed.metadata["profile_id"], "main-account")

        registry.sync([])

        self.assertEqual(registry.get("mumu-0").status, InstanceStatus.DISCONNECTED)
