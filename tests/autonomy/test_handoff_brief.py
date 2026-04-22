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
                    "changed_files": ["src/roxauto/cli.py", "README.md", "docs/codex-subscription-setup.md"],
                    "policy_files_touched": ["README.md", "docs/codex-subscription-setup.md"],
                    "shared_files_touched": ["README.md"],
                    "workflow_files_touched": [".github/workflows/autonomy-loop.yml"],
                    "staged_files": ["src/roxauto/cli.py"],
                    "unstaged_files": ["README.md"],
                    "untracked_files": ["docs/codex-subscription-setup.md"],
                    "recent_commits": [
                        {"subject": "Improve PR handoff packet accuracy"},
                        {"subject": "Document Codex dispatch workflow"},
                    ],
                }
            },
        )

        self.assertIn("Subscription Loop", markdown)
        self.assertIn("checks summary", markdown)
        self.assertIn("Change Summary", markdown)
        self.assertIn("Improve PR handoff packet accuracy", markdown)
        self.assertIn("`doctor`: `passed`", markdown)
        self.assertIn("`README.md`", markdown)
        self.assertIn("Shared Surfaces", markdown)
        self.assertIn("Policy files touched", markdown)
        self.assertIn("Workflow files touched", markdown)
        self.assertIn("@codex review", markdown)

    def test_render_handoff_brief_falls_back_to_last_commit_files(self) -> None:
        markdown = render_handoff_brief(
            {"status": "passed", "summary": {"passed": 1, "failed": 0, "skipped": 0}, "commands": []},
            {
                "git": {
                    "branch": "codex/pr-body-handoff",
                    "head_sha": "abcdef1234567890",
                    "changed_files": [],
                    "last_commit_files": ["src/roxauto/autonomy/handoff_brief.py", "docs/autonomy-loop.md"],
                    "recent_commits": [{"subject": "Sync Codex handoff into PR body"}],
                }
            },
        )

        self.assertIn("`src/roxauto/autonomy/handoff_brief.py`", markdown)
        self.assertIn("`docs/autonomy-loop.md`", markdown)
