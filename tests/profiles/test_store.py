from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.profiles.store import CalibrationProfile, InstanceProfileOverride, JsonProfileStore, Profile


class ProfileStoreTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = JsonProfileStore(Path(tmp_dir))
            profile = Profile(
                profile_id="main-account",
                display_name="Main Account",
                server_name="TW-1",
                character_name="Knight",
                allowed_tasks=["guild_donation"],
                calibration=CalibrationProfile(
                    calibration_id="calib-main",
                    description="Main calibration",
                    capture_offset=(12, 24),
                    capture_scale=1.25,
                    crop_box=(0, 0, 1600, 900),
                    anchor_overrides={"daily_panel": {"threshold": 0.92}},
                ),
                instance_overrides={
                    "mumu-0": InstanceProfileOverride(
                        instance_id="mumu-0",
                        adb_serial="127.0.0.1:16384",
                        calibration_id="calib-main",
                        capture_offset=(4, 8),
                        capture_scale=1.1,
                        notes="Primary emulator",
                    )
                },
            )

            store.save(profile)
            loaded = store.load("main-account")

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.profile_id, "main-account")
            self.assertEqual(loaded.allowed_tasks, ["guild_donation"])
            self.assertIsNotNone(loaded.calibration)
            self.assertEqual(loaded.calibration.capture_offset, (12, 24))
            self.assertEqual(loaded.instance_overrides["mumu-0"].calibration_id, "calib-main")
            self.assertEqual(loaded.instance_overrides["mumu-0"].capture_offset, (4, 8))
