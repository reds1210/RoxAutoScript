from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable

from roxauto.core.serde import to_primitive


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: list[str]
    optional: bool = False
    skip_reason: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def build_default_commands(*, python_executable: str | None = None) -> list[CommandSpec]:
    python_bin = python_executable or sys.executable
    commands = [
        CommandSpec(
            name="doctor",
            argv=[python_bin, "-m", "roxauto", "doctor"],
        ),
        CommandSpec(
            name="pytest",
            argv=[python_bin, "-m", "pytest"],
        ),
    ]
    commands.append(
        CommandSpec(
            name="ruff",
            argv=[python_bin, "-m", "ruff", "check", "src", "tests"],
            optional=True,
            skip_reason=None if _module_available("ruff") else "ruff is not installed",
        )
    )
    return commands


def _run_command(command: CommandSpec, *, repo_root: Path) -> dict[str, object]:
    started_at = _utc_now()
    if command.skip_reason:
        finished_at = _utc_now()
        return {
            "name": command.name,
            "argv": command.argv,
            "optional": command.optional,
            "status": "skipped",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "skip_reason": command.skip_reason,
            "started_at": started_at,
            "finished_at": finished_at,
        }

    completed = subprocess.run(
        command.argv,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    finished_at = _utc_now()
    status = "passed" if completed.returncode == 0 else "failed"
    return {
        "name": command.name,
        "argv": command.argv,
        "optional": command.optional,
        "status": status,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "skip_reason": None,
        "started_at": started_at,
        "finished_at": finished_at,
    }


def run_quality_gate(
    repo_root: Path,
    *,
    commands: Iterable[CommandSpec] | None = None,
    python_executable: str | None = None,
) -> dict[str, object]:
    repo_root = Path(repo_root).resolve()
    started_at = _utc_now()
    active_commands = list(commands) if commands is not None else build_default_commands(python_executable=python_executable)
    command_results = [_run_command(command, repo_root=repo_root) for command in active_commands]

    required_failures = [
        result
        for result in command_results
        if result["status"] == "failed" and not bool(result["optional"])
    ]
    finished_at = _utc_now()

    return {
        "repo_root": repo_root,
        "python_executable": python_executable or sys.executable,
        "status": "failed" if required_failures else "passed",
        "started_at": started_at,
        "finished_at": finished_at,
        "summary": {
            "passed": sum(1 for result in command_results if result["status"] == "passed"),
            "failed": sum(1 for result in command_results if result["status"] == "failed"),
            "skipped": sum(1 for result in command_results if result["status"] == "skipped"),
        },
        "commands": command_results,
    }


def write_quality_gate_report(
    repo_root: Path,
    *,
    output_path: Path | None = None,
    commands: Iterable[CommandSpec] | None = None,
    python_executable: str | None = None,
) -> tuple[dict[str, object], int]:
    report = run_quality_gate(
        repo_root,
        commands=commands,
        python_executable=python_executable,
    )
    payload = json.dumps(to_primitive(report), indent=2, ensure_ascii=False)
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return report, 0 if report["status"] == "passed" else 1
