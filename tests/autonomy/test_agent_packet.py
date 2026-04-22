from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

import tests._bootstrap  # noqa: F401
from roxauto.autonomy.agent_packet import build_agent_packet


class AgentPacketTests(unittest.TestCase):
    @patch("roxauto.autonomy.agent_packet._run_git")
    def test_build_agent_packet_collects_git_state(self, run_git) -> None:
        responses = {
            ("show", "--pretty=format:", "--name-only", "HEAD"): "README.md\nsrc/roxauto/cli.py\nAGENTS.md\n",
            ("diff", "--no-color", "--unified=1", "HEAD"): "diff --git a/a.py b/a.py\n+print('x')\n",
            ("status", "--short"): " M README.md\n?? AGENTS.md\n",
            ("diff", "--cached", "--name-only"): "src/roxauto/cli.py\n",
            ("diff", "--name-only"): "README.md\nsrc/roxauto/cli.py\n",
            ("ls-files", "--others", "--exclude-standard"): "AGENTS.md\n",
            ("rev-parse", "--abbrev-ref", "HEAD"): "codex/autonomy-loop",
            ("rev-parse", "HEAD"): "abc123",
            ("log", "-5", "--pretty=format:%H%x1f%s%x1f%cI"): "abc123\x1fAdd autonomy loop\x1f2026-04-22T08:00:00+00:00",
        }

        def fake_run_git(repo_root: Path, *args: str) -> str:
            return responses.get(args, "")

        run_git.side_effect = fake_run_git

        packet = build_agent_packet(
            Path.cwd(),
            quality_gate_path=None,
        )

        self.assertEqual(packet["git"]["branch"], "codex/autonomy-loop")
        self.assertEqual(packet["git"]["head_sha"], "abc123")
        self.assertTrue(packet["git"]["working_tree_dirty"])
        self.assertEqual(packet["git"]["staged_files"], ["src/roxauto/cli.py"])
        self.assertEqual(packet["git"]["untracked_files"], ["AGENTS.md"])
        self.assertEqual(packet["git"]["last_commit_files"], ["README.md", "src/roxauto/cli.py", "AGENTS.md"])
        self.assertEqual(packet["git"]["policy_files_touched"], ["README.md", "AGENTS.md"])
        self.assertEqual(packet["git"]["shared_files_touched"], ["README.md"])
        self.assertEqual(packet["git"]["workflow_files_touched"], [])
        self.assertEqual(packet["git"]["recent_commits"][0]["subject"], "Add autonomy loop")
        self.assertIn("docs/autonomy-loop.md", packet["policy_files"])
        self.assertIn("docs/codex-subscription-setup.md", packet["policy_files"])

    @patch.dict(
        os.environ,
        {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_HEAD_REF": "codex/ui-redesign",
        },
        clear=False,
    )
    @patch("roxauto.autonomy.agent_packet._run_git")
    def test_build_agent_packet_prefers_pr_context_for_detached_head(self, run_git) -> None:
        responses = {
            ("show", "--pretty=format:", "--name-only", "HEAD"): "src/roxauto/app/shell.py\nassets/ui/operator_console.qss\n",
            ("diff", "--name-only", "HEAD^1", "HEAD^2"): "src/roxauto/app/shell.py\nassets/ui/operator_console.qss\n",
            ("diff", "--no-color", "--unified=1", "HEAD^1", "HEAD^2"): "diff --git a/a.py b/a.py\n+print('x')\n",
            ("status", "--short"): "?? artifacts/quality-gate.json\n",
            ("diff", "--cached", "--name-only"): "",
            ("diff", "--name-only"): "artifacts/quality-gate.json\n",
            ("ls-files", "--others", "--exclude-standard"): "artifacts/quality-gate.json\n",
            ("rev-parse", "--abbrev-ref", "HEAD"): "HEAD",
            ("rev-parse", "HEAD"): "def456",
            ("log", "-5", "--pretty=format:%H%x1f%s%x1f%cI"): "def456\x1fImprove handoff packet\x1f2026-04-22T12:00:00+00:00",
        }

        def fake_run_git(repo_root: Path, *args: str) -> str:
            return responses.get(args, "")

        run_git.side_effect = fake_run_git

        packet = build_agent_packet(Path.cwd(), quality_gate_path=None)

        self.assertEqual(packet["git"]["branch"], "codex/ui-redesign")
        self.assertFalse(packet["git"]["working_tree_dirty"])
        self.assertEqual(
            packet["git"]["changed_files"],
            ["src/roxauto/app/shell.py", "assets/ui/operator_console.qss"],
        )
        self.assertEqual(
            packet["git"]["last_commit_files"],
            ["src/roxauto/app/shell.py", "assets/ui/operator_console.qss"],
        )
        self.assertEqual(packet["git"]["policy_files_touched"], [])
        self.assertEqual(packet["git"]["shared_files_touched"], [])
        self.assertEqual(packet["git"]["workflow_files_touched"], [])
        self.assertEqual(packet["git"]["untracked_files"], [])
        self.assertIn("diff --git", packet["git"]["diff_excerpt"])

    @patch("roxauto.autonomy.agent_packet._run_git")
    def test_build_agent_packet_uses_last_commit_files_when_worktree_is_clean(self, run_git) -> None:
        responses = {
            ("show", "--pretty=format:", "--name-only", "HEAD"): "src/roxauto/autonomy/handoff_brief.py\ndocs/autonomy-loop.md\n",
            ("diff", "--no-color", "--unified=1", "HEAD"): "",
            ("status", "--short"): "",
            ("diff", "--cached", "--name-only"): "",
            ("diff", "--name-only"): "",
            ("ls-files", "--others", "--exclude-standard"): "",
            ("rev-parse", "--abbrev-ref", "HEAD"): "codex/pr-body-handoff",
            ("rev-parse", "HEAD"): "ghi789",
            ("log", "-5", "--pretty=format:%H%x1f%s%x1f%cI"): "ghi789\x1fSync Codex handoff into PR body\x1f2026-04-22T13:24:00+00:00",
        }

        def fake_run_git(repo_root: Path, *args: str) -> str:
            return responses.get(args, "")

        run_git.side_effect = fake_run_git

        packet = build_agent_packet(Path.cwd(), quality_gate_path=None)

        self.assertEqual(packet["git"]["changed_files"], [])
        self.assertEqual(
            packet["git"]["last_commit_files"],
            ["src/roxauto/autonomy/handoff_brief.py", "docs/autonomy-loop.md"],
        )
        self.assertEqual(packet["git"]["policy_files_touched"], ["docs/autonomy-loop.md"])

    @patch.dict(
        os.environ,
        {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_HEAD_REF": "codex/ui-redesign",
        },
        clear=False,
    )
    @patch("roxauto.autonomy.agent_packet._run_git")
    def test_build_agent_packet_prefers_pr_context_for_detached_head(self, run_git) -> None:
        responses = {
            ("diff", "--name-only", "HEAD^1", "HEAD^2"): "src/roxauto/app/shell.py\nassets/ui/operator_console.qss\n",
            ("diff", "--no-color", "--unified=1", "HEAD^1", "HEAD^2"): "diff --git a/a.py b/a.py\n+print('x')\n",
            ("status", "--short"): "?? artifacts/quality-gate.json\n",
            ("diff", "--cached", "--name-only"): "",
            ("diff", "--name-only"): "artifacts/quality-gate.json\n",
            ("ls-files", "--others", "--exclude-standard"): "artifacts/quality-gate.json\n",
            ("rev-parse", "--abbrev-ref", "HEAD"): "HEAD",
            ("rev-parse", "HEAD"): "def456",
            ("log", "-5", "--pretty=format:%H%x1f%s%x1f%cI"): "def456\x1fImprove handoff packet\x1f2026-04-22T12:00:00+00:00",
        }

        def fake_run_git(repo_root: Path, *args: str) -> str:
            return responses.get(args, "")

        run_git.side_effect = fake_run_git

        packet = build_agent_packet(Path.cwd(), quality_gate_path=None)

        self.assertEqual(packet["git"]["branch"], "codex/ui-redesign")
        self.assertFalse(packet["git"]["working_tree_dirty"])
        self.assertEqual(
            packet["git"]["changed_files"],
            ["src/roxauto/app/shell.py", "assets/ui/operator_console.qss"],
        )
        self.assertEqual(packet["git"]["untracked_files"], [])
        self.assertIn("diff --git", packet["git"]["diff_excerpt"])

