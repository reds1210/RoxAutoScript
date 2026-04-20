from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.emulator.discovery import build_instance_state, infer_mumu_index, parse_adb_devices


class DiscoveryTests(unittest.TestCase):
    def test_parse_adb_devices_filters_only_ready_devices(self) -> None:
        output = "\n".join(
            [
                "List of devices attached",
                "127.0.0.1:16384\tdevice",
                "127.0.0.1:16416\toffline",
                "",
            ]
        )

        self.assertEqual(parse_adb_devices(output), ["127.0.0.1:16384"])

    def test_infer_mumu_index_uses_official_port_pattern(self) -> None:
        self.assertEqual(infer_mumu_index("127.0.0.1:16384"), 0)
        self.assertEqual(infer_mumu_index("127.0.0.1:16416"), 1)

    def test_build_instance_state_prefers_mumu_label_when_possible(self) -> None:
        state = build_instance_state("127.0.0.1:16416")
        self.assertEqual(state.instance_id, "mumu-1")
        self.assertEqual(state.label, "MuMu 1")
