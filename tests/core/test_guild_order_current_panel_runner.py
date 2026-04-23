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

    def test_resolves_visible_custom_order_index_in_row_major_order(self) -> None:
        self.assertEqual(SCRIPT_MODULE._resolve_custom_backpack_item_point(1), (740, 355))
        self.assertEqual(SCRIPT_MODULE._resolve_custom_backpack_item_point(6), (740, 457))
        self.assertEqual(SCRIPT_MODULE._resolve_custom_backpack_item_point(10), (1144, 457))

    def test_rejects_custom_order_index_below_one(self) -> None:
        with self.assertRaises(ValueError):
            SCRIPT_MODULE._resolve_custom_backpack_item_point(0)
