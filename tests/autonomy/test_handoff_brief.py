from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.autonomy.handoff_brief import render_handoff_brief


class HandoffBriefTests(unittest.TestCase):
    def test_render_handoff_brief_includes_checks_and_next_steps(self) -> None:
        markdown = render_handoff_brief(
            {
                "status": "passed",
                "commands": [
                    {"name": "doctor", "status": "passed"},
                    {"name": "pytest", "status": "passed"},
                ],
            },
            {
                "git": {
                    "branch": "codex/subscription-only",
                    "head_sha": "abcdef1234567890",
                    "staged_files": ["src/roxauto/cli.py"],
                    "unstaged_files": ["README.md"],
                    "untracked_files": ["docs/codex-subscription-setup.md"],
                }
            },
        )

        self.assertIn("Subscription Loop", markdown)
        self.assertIn("`doctor`: `passed`", markdown)
        self.assertIn("`README.md`", markdown)
        self.assertIn("@codex review", markdown)
