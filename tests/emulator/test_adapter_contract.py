from __future__ import annotations

import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.core.models import InstanceState, InstanceStatus
from roxauto.emulator.adapter import EmulatorAdapter


class FakeAdapter:
    def capture_screenshot(self, instance: InstanceState) -> Path:
        return Path("capture.png")

    def tap(self, instance: InstanceState, point: tuple[int, int]) -> None:
        return None

    def swipe(
        self,
        instance: InstanceState,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        return None

    def input_text(self, instance: InstanceState, text: str) -> None:
        return None

    def launch_app(self, instance: InstanceState, package_name: str) -> None:
        return None

    def health_check(self, instance: InstanceState) -> bool:
        return True


class EmulatorAdapterContractTests(unittest.TestCase):
    def test_fake_adapter_matches_runtime_protocol(self) -> None:
        instance = InstanceState(
            instance_id="mumu-0",
            label="MuMu 0",
            adb_serial="127.0.0.1:16384",
            status=InstanceStatus.READY,
        )
        adapter = FakeAdapter()

        self.assertIsInstance(adapter, EmulatorAdapter)
        self.assertTrue(adapter.health_check(instance))
        self.assertEqual(adapter.capture_screenshot(instance), Path("capture.png"))
