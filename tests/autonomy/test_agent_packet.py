from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

import tests._bootstrap  # noqa: F401
from roxauto.autonomy.agent_packet import build_agent_packet


class AgentPacketTests(unittest.TestCase):
    @patch("roxauto.autonomy.agent_packet._run_git")
    def test_build_agent_packet_collects_git_state(self, run_git) -> None:
        responses = {
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
        self.assertEqual(packet["git"]["recent_commits"][0]["subject"], "Add autonomy loop")
        self.assertIn("docs/autonomy-loop.md", packet["policy_files"])

