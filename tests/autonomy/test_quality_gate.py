from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import tests._bootstrap  # noqa: F401
from roxauto.autonomy.quality_gate import CommandSpec, run_quality_gate


class QualityGateTests(unittest.TestCase):
    def test_collects_pass_fail_and_skip_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_quality_gate(
                Path(temp_dir),
                commands=[
                    CommandSpec(
                        name="pass",
                        argv=[sys.executable, "-c", "print('ok')"],
                    ),
                    CommandSpec(
                        name="skip",
                        argv=[sys.executable, "-c", "print('unused')"],
                        optional=True,
                        skip_reason="optional dependency missing",
                    ),
                    CommandSpec(
                        name="fail",
                        argv=[sys.executable, "-c", "import sys; print('bad'); sys.exit(3)"],
                    ),
                ],
            )

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["summary"]["passed"], 1)
        self.assertEqual(report["summary"]["skipped"], 1)
        self.assertEqual(report["summary"]["failed"], 1)
        self.assertEqual(report["commands"][0]["status"], "passed")
        self.assertEqual(report["commands"][1]["status"], "skipped")
        self.assertEqual(report["commands"][2]["returncode"], 3)

