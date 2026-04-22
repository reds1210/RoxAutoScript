from __future__ import annotations

import json
from pathlib import Path


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def render_handoff_brief(
    quality_gate: dict[str, object],
    agent_packet: dict[str, object],
) -> str:
    git = agent_packet.get("git", {})
    commands = quality_gate.get("commands", [])
    changed_files = []
    for key in ("staged_files", "unstaged_files", "untracked_files"):
        for path in git.get(key, []):
            if path not in changed_files:
                changed_files.append(path)

    lines = [
        "<!-- roxauto-subscription-loop -->",
        "# Subscription Loop",
        "",
        f"- quality gate: `{quality_gate.get('status', 'unknown')}`",
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
