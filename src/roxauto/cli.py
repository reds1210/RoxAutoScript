from __future__ import annotations

import argparse
from pathlib import Path

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

    parser.error(f"Unknown command: {args.command}")
    return 2
