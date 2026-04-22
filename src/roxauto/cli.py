from __future__ import annotations

import argparse
from pathlib import Path

from roxauto.autonomy.agent_packet import write_agent_packet
from roxauto.autonomy.handoff_brief import write_handoff_brief
from roxauto.autonomy.quality_gate import write_quality_gate_report
from roxauto.app.shell import launch_placeholder_gui
from roxauto.demo import run_runtime_demo
from roxauto.doctor import print_doctor_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roxauto",
        description="ROX multi-instance automation foundation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "doctor",
        help="Inspect environment, adb availability, and discovered emulator instances",
    )

    demo_parser = subparsers.add_parser(
        "demo-runtime",
        help="Run a mock task through the runtime and write an audit log",
    )
    demo_parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("runtime_logs"),
        help="Directory for demo audit output",
    )

    subparsers.add_parser(
        "gui",
        help="Launch the MVP GUI console if PySide6 is installed",
    )

    quality_gate_parser = subparsers.add_parser(
        "quality-gate",
        help="Run deterministic repo checks and write a machine-readable report",
    )
    quality_gate_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path for the quality gate report",
    )

    agent_packet_parser = subparsers.add_parser(
        "agent-packet",
        help="Capture git state and quality gate output for the next autonomous step",
    )
    agent_packet_parser.add_argument(
        "--quality-gate",
        type=Path,
        default=None,
        help="Optional path to a previously generated quality gate JSON report",
    )
    agent_packet_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="JSON output path for the agent packet",
    )

    handoff_brief_parser = subparsers.add_parser(
        "handoff-brief",
        help="Render a Markdown handoff brief for Codex subscription workflows",
    )
    handoff_brief_parser.add_argument(
        "--quality-gate",
        type=Path,
        required=True,
        help="Path to the quality gate JSON input",
    )
    handoff_brief_parser.add_argument(
        "--agent-packet",
        type=Path,
        required=True,
        help="Path to the agent packet JSON input",
    )
    handoff_brief_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional Markdown output path for the handoff brief",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return print_doctor_report()

    if args.command == "demo-runtime":
        return run_runtime_demo(args.log_dir)

    if args.command == "gui":
        return launch_placeholder_gui()

    if args.command == "quality-gate":
        _, exit_code = write_quality_gate_report(Path.cwd(), output_path=args.output)
        return exit_code

    if args.command == "agent-packet":
        write_agent_packet(
            Path.cwd(),
            output_path=args.output,
            quality_gate_path=args.quality_gate,
        )
        return 0

    if args.command == "handoff-brief":
        write_handoff_brief(
            args.quality_gate,
            args.agent_packet,
            output_path=args.output,
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
