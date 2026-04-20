from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tests._bootstrap  # noqa: F401
from roxauto.profiles.store import JsonProfileStore, Profile


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
            )

            store.save(profile)
            loaded = store.load("main-account")

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.profile_id, "main-account")
            self.assertEqual(loaded.allowed_tasks, ["guild_donation"])
