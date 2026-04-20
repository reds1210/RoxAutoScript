from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from roxauto.core.models import InstanceState, InstanceStatus

MUMU_BASE_PORT = 16384
MUMU_PORT_STEP = 32


def find_adb_executable() -> Path | None:
    adb_on_path = shutil.which("adb")
    if adb_on_path:
        return Path(adb_on_path)

    user_profile = os.environ.get("USERPROFILE")
    if not user_profile:
        return None

    candidates = [
        Path(user_profile) / "Netease" / "MuMuPlayer-12.0" / "shell" / "adb.exe",
        Path(user_profile) / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def parse_adb_devices(output: str) -> list[str]:
    serials: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        if "\tdevice" not in line:
            continue
        serial, _status = line.split("\t", 1)
        serials.append(serial)
    return serials


def infer_mumu_index(serial: str) -> int | None:
    if ":" not in serial:
        return None
    try:
        _host, port_text = serial.rsplit(":", 1)
        port = int(port_text)
    except ValueError:
        return None

    if port < MUMU_BASE_PORT:
        return None

    delta = port - MUMU_BASE_PORT
    if delta % MUMU_PORT_STEP != 0:
        return None
    return delta // MUMU_PORT_STEP


def build_instance_state(serial: str) -> InstanceState:
    inferred_index = infer_mumu_index(serial)
    if inferred_index is not None:
        label = f"MuMu {inferred_index}"
        instance_id = f"mumu-{inferred_index}"
    else:
        sanitized = serial.replace(":", "-")
        label = f"ADB {serial}"
        instance_id = f"adb-{sanitized}"

    return InstanceState(
        instance_id=instance_id,
        label=label,
        adb_serial=serial,
        status=InstanceStatus.READY,
    )


def discover_instances(adb_path: Path | None = None) -> list[InstanceState]:
    executable = adb_path or find_adb_executable()
    if executable is None:
        return []

    try:
        completed = subprocess.run(
            [str(executable), "devices"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    return [build_instance_state(serial) for serial in parse_adb_devices(completed.stdout)]

