from __future__ import annotations

import json
from pathlib import Path


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _format_quality_gate_summary(quality_gate: dict[str, object]) -> str | None:
    summary = quality_gate.get("summary", {})
    parts: list[str] = []
    if isinstance(summary, dict):
        for key in ("passed", "failed", "skipped"):
            value = summary.get(key)
            if isinstance(value, int):
                parts.append(f"{value} {key}")
    if not parts:
        commands = quality_gate.get("commands", [])
        if isinstance(commands, list):
            counts = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
            }
            for command in commands:
                if not isinstance(command, dict):
                    continue
                status = command.get("status")
                if status in counts:
                    counts[status] += 1
            for key in ("passed", "failed", "skipped"):
                parts.append(f"{counts[key]} {key}")
    return ", ".join(parts) if parts else None


def _recent_commit_subjects(agent_packet: dict[str, object], *, limit: int = 3) -> list[str]:
    git = agent_packet.get("git", {})
    if not isinstance(git, dict):
        return []

    subjects: list[str] = []
    for commit in git.get("recent_commits", []):
        if not isinstance(commit, dict):
            continue
        subject = str(commit.get("subject", "")).strip()
        if subject:
            subjects.append(subject)
        if len(subjects) >= limit:
            break
    return subjects


def render_handoff_brief(
    quality_gate: dict[str, object],
    agent_packet: dict[str, object],
) -> str:
    git = agent_packet.get("git", {})
    commands = quality_gate.get("commands", [])
    changed_files = list(git.get("changed_files", []))
    quality_gate_summary = _format_quality_gate_summary(quality_gate)
    recent_commit_subjects = _recent_commit_subjects(agent_packet)
    policy_files_touched = list(git.get("policy_files_touched", []))
    shared_files_touched = list(git.get("shared_files_touched", []))
    workflow_files_touched = list(git.get("workflow_files_touched", []))
    if not changed_files:
        for key in ("staged_files", "unstaged_files", "untracked_files"):
            for path in git.get(key, []):
                if path not in changed_files:
                    changed_files.append(path)

    lines = [
        "<!-- roxauto-subscription-loop -->",
        "# Subscription Loop",
        "",
        f"- quality gate: `{quality_gate.get('status', 'unknown')}`",
        *([f"- checks summary: `{quality_gate_summary}`"] if quality_gate_summary else []),
        f"- branch: `{git.get('branch', 'unknown')}`",
        f"- head: `{str(git.get('head_sha', ''))[:12]}`",
        "",
        "## Checks",
        "",
    ]

    if commands:
        for command in commands:
            if not isinstance(command, dict):
                continue
            lines.append(
                f"- `{command.get('name', 'command')}`: `{command.get('status', 'unknown')}`"
            )
    else:
        lines.append("- No check results captured.")

    lines.extend(
        [
            "",
            "## Change Summary",
            "",
        ]
    )
    if recent_commit_subjects:
        for subject in recent_commit_subjects:
            lines.append(f"- `{subject}`")
    else:
        lines.append("- No recent commit subjects recorded.")

    lines.extend(
        [
            "",
            "## Changed Files",
            "",
        ]
    )
    if changed_files:
        for path in changed_files[:20]:
            lines.append(f"- `{path}`")
        if len(changed_files) > 20:
            lines.append(f"- `...` and {len(changed_files) - 20} more")
    else:
        lines.append("- No changed files recorded.")

    if policy_files_touched or shared_files_touched or workflow_files_touched:
        lines.extend(
            [
                "",
                "## Shared Surfaces",
                "",
            ]
        )
        if policy_files_touched:
            lines.append(
                "- Policy files touched: "
                + ", ".join(f"`{path}`" for path in policy_files_touched)
            )
        if shared_files_touched:
            lines.append(
                "- Shared files touched: "
                + ", ".join(f"`{path}`" for path in shared_files_touched)
            )
        if workflow_files_touched:
            lines.append(
                "- Workflow files touched: "
                + ", ".join(f"`{path}`" for path in workflow_files_touched)
            )

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Rely on repository-level Codex automatic review if it is enabled for this repository.",
            "- If automatic reviews are not enabled, mention `@codex review` on the pull request.",
            "- Use the uploaded `quality-gate.json`, `agent-packet.json`, and this brief as the handoff packet for the next Codex task.",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def write_handoff_brief(
    quality_gate_path: Path,
    agent_packet_path: Path,
    *,
    output_path: Path | None = None,
) -> str:
    quality_gate = _load_json(quality_gate_path)
    agent_packet = _load_json(agent_packet_path)
    brief = render_handoff_brief(quality_gate, agent_packet)
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(brief, encoding="utf-8")
    else:
        print(brief, end="")
    return brief
