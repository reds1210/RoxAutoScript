from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.app.viewmodels import build_console_snapshot


class ConsoleSnapshotTests(unittest.TestCase):
    def test_snapshot_uses_doctor_payload_shape(self) -> None:
        report = {
            "packages": {"PySide6": True, "adbutils": False, "cv2": False},
            "adb": {"path": "C:/platform-tools/adb.exe", "instances_found": 1},
            "instances": [
                {
                    "instance_id": "mumu-2",
                    "label": "MuMu 2",
                    "adb_serial": "127.0.0.1:16448",
                    "status": "ready",
                    "last_seen_at": "2026-04-21T10:00:00+08:00",
                    "metadata": {"server": "TW-1"},
                }
            ],
        }

        snapshot = build_console_snapshot(report)

        self.assertEqual(snapshot.adb_path, "C:/platform-tools/adb.exe")
        self.assertEqual(snapshot.instance_count, 1)
        self.assertEqual(snapshot.available_runtime_features, ["PySide6"])
        self.assertEqual(snapshot.instances[0].instance_id, "mumu-2")
        self.assertEqual(snapshot.instances[0].metadata["server"], "TW-1")
