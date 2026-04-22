from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from roxauto.core.serde import to_primitive


POLICY_FILES = [
    "README.md",
    "AGENTS.md",
    "docs/rox-mvp-plan.md",
    "docs/engine-roster.md",
    "docs/worktree-playbook.md",
    "docs/architecture-contracts.md",
    "docs/autonomy-loop.md",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _load_json(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_recent_commits(raw: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        sha, subject, committed_at = (line.split("\x1f") + ["", "", ""])[:3]
        commits.append(
            {
                "sha": sha,
                "subject": subject,
                "committed_at": committed_at,
            }
        )
    return commits


def build_agent_packet(
    repo_root: Path,
    *,
    quality_gate_path: Path | None = None,
    max_diff_chars: int = 12000,
    recent_commit_count: int = 5,
) -> dict[str, object]:
    repo_root = Path(repo_root).resolve()
    quality_gate = _load_json(quality_gate_path)

    diff_excerpt = _run_git(repo_root, "diff", "--no-color", "--unified=1", "HEAD")
    diff_truncated = len(diff_excerpt) > max_diff_chars
    if diff_truncated:
        diff_excerpt = diff_excerpt[:max_diff_chars].rstrip() + "\n...[truncated]"

    status_lines = [line for line in _run_git(repo_root, "status", "--short").splitlines() if line.strip()]
    staged_files = [line for line in _run_git(repo_root, "diff", "--cached", "--name-only").splitlines() if line.strip()]
    unstaged_files = [line for line in _run_git(repo_root, "diff", "--name-only").splitlines() if line.strip()]
    untracked_files = [line for line in _run_git(repo_root, "ls-files", "--others", "--exclude-standard").splitlines() if line.strip()]

    return {
        "generated_at": _utc_now(),
        "repo_root": repo_root,
        "policy_files": POLICY_FILES,
        "recommended_loop": [
            "python -m roxauto quality-gate --output runtime_logs/autonomy/quality-gate.json",
            "python -m roxauto agent-packet --quality-gate runtime_logs/autonomy/quality-gate.json --output runtime_logs/autonomy/agent-packet.json",
            "python -m roxauto handoff-brief --quality-gate runtime_logs/autonomy/quality-gate.json --agent-packet runtime_logs/autonomy/agent-packet.json --output runtime_logs/autonomy/handoff-brief.md",
        ],
        "git": {
            "branch": _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            "head_sha": _run_git(repo_root, "rev-parse", "HEAD"),
            "working_tree_dirty": bool(status_lines),
            "status_lines": status_lines,
            "staged_files": staged_files,
            "unstaged_files": unstaged_files,
            "untracked_files": untracked_files,
            "diff_excerpt": diff_excerpt,
            "diff_truncated": diff_truncated,
            "recent_commits": _parse_recent_commits(
                _run_git(
                    repo_root,
                    "log",
                    f"-{recent_commit_count}",
                    "--pretty=format:%H%x1f%s%x1f%cI",
                )
            ),
        },
        "quality_gate": quality_gate,
    }


def write_agent_packet(
    repo_root: Path,
    *,
    output_path: Path,
    quality_gate_path: Path | None = None,
    max_diff_chars: int = 12000,
    recent_commit_count: int = 5,
) -> dict[str, object]:
    packet = build_agent_packet(
        repo_root,
        quality_gate_path=quality_gate_path,
        max_diff_chars=max_diff_chars,
        recent_commit_count=recent_commit_count,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(to_primitive(packet), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return packet
