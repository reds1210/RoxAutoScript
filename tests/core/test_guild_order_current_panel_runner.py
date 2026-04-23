from __future__ import annotations

import builtins
import importlib.util
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock

import tests._bootstrap  # noqa: F401


def _load_script_module(module_name: str | None = None):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run-guild-order-current-panel.py"
    resolved_module_name = module_name or f"guild_order_current_panel_runner_script_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(resolved_module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load script module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCRIPT_MODULE = _load_script_module()


class GuildOrderCurrentPanelRunnerScriptTests(unittest.TestCase):
    def test_script_import_does_not_require_pillow(self) -> None:
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.split(".", 1)[0] == "PIL":
                raise ModuleNotFoundError("No module named 'PIL'")
            return real_import(name, globals, locals, fromlist, level)

        with mock.patch("builtins.__import__", side_effect=guarded_import):
            module = _load_script_module()

        self.addCleanup(sys.modules.pop, module.__name__, None)
        self.assertTrue(hasattr(module, "build_parser"))

    def test_parser_defaults_custom_order_index_to_one(self) -> None:
        parser = SCRIPT_MODULE.build_parser()

        args = parser.parse_args(["--serial", "127.0.0.1:16480"])

        self.assertEqual(args.custom_order_index, 1)
        self.assertEqual(args.poll_interval_sec, 0.5)
        self.assertEqual(args.checkpoint_timeout_sec, 6.0)

    def test_resolves_visible_custom_order_index_in_row_major_order(self) -> None:
        self.assertEqual(SCRIPT_MODULE._resolve_custom_backpack_item_point(1), (740, 355))
        self.assertEqual(SCRIPT_MODULE._resolve_custom_backpack_item_point(6), (740, 457))
        self.assertEqual(SCRIPT_MODULE._resolve_custom_backpack_item_point(10), (1144, 457))

    def test_rejects_custom_order_index_below_one(self) -> None:
        with self.assertRaises(ValueError):
            SCRIPT_MODULE._resolve_custom_backpack_item_point(0)

    def test_poll_for_checkpoint_retries_until_predicate_matches(self) -> None:
        clock = {"value": 0.0}
        sleeps: list[float] = []
        capture_paths = [
            Path("attempt-1.png"),
            Path("attempt-2.png"),
            Path("attempt-3.png"),
        ]

        def fake_capture() -> Path:
            return capture_paths.pop(0)

        def fake_sleep(duration: float) -> None:
            sleeps.append(duration)
            clock["value"] += duration

        def fake_monotonic() -> float:
            return clock["value"]

        result = SCRIPT_MODULE._poll_for_checkpoint(
            capture=fake_capture,
            predicate=lambda path: path.name == "attempt-3.png",
            initial_delay_sec=0.2,
            poll_interval_sec=0.5,
            timeout_sec=2.0,
            sleep_fn=fake_sleep,
            monotonic_fn=fake_monotonic,
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.screenshot_path, Path("attempt-3.png"))
        self.assertEqual(result.attempt_count, 3)
        self.assertEqual(sleeps, [0.2, 0.5, 0.5])
        self.assertAlmostEqual(result.elapsed_sec, 1.2)

    def test_poll_for_checkpoint_times_out_with_last_capture(self) -> None:
        clock = {"value": 0.0}
        sleeps: list[float] = []
        capture_paths = [
            Path("attempt-1.png"),
            Path("attempt-2.png"),
            Path("attempt-3.png"),
        ]

        def fake_capture() -> Path:
            return capture_paths.pop(0)

        def fake_sleep(duration: float) -> None:
            sleeps.append(duration)
            clock["value"] += duration

        def fake_monotonic() -> float:
            return clock["value"]

        result = SCRIPT_MODULE._poll_for_checkpoint(
            capture=fake_capture,
            predicate=lambda _path: False,
            initial_delay_sec=0.2,
            poll_interval_sec=0.5,
            timeout_sec=1.0,
            sleep_fn=fake_sleep,
            monotonic_fn=fake_monotonic,
        )

        self.assertFalse(result.matched)
        self.assertEqual(result.screenshot_path, Path("attempt-3.png"))
        self.assertEqual(result.attempt_count, 3)
        self.assertEqual(len(sleeps), 3)
        self.assertAlmostEqual(sleeps[0], 0.2)
        self.assertAlmostEqual(sleeps[1], 0.5)
        self.assertAlmostEqual(sleeps[2], 0.3)
        self.assertAlmostEqual(result.elapsed_sec, 1.0)
