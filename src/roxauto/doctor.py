from __future__ import annotations

import importlib.util
import json
import platform
import sys

from roxauto.core.serde import to_primitive
from roxauto.emulator.discovery import discover_instances, find_adb_executable


def build_doctor_report() -> dict[str, object]:
    adb_path = find_adb_executable()
    instances = discover_instances(adb_path=adb_path)
    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "packages": {
            "PySide6": importlib.util.find_spec("PySide6") is not None,
            "adbutils": importlib.util.find_spec("adbutils") is not None,
            "cv2": importlib.util.find_spec("cv2") is not None,
        },
        "adb": {
            "path": str(adb_path) if adb_path else None,
            "instances_found": len(instances),
        },
        "instances": instances,
    }


def print_doctor_report() -> int:
    report = build_doctor_report()
    print(json.dumps(to_primitive(report), indent=2, ensure_ascii=False))
    return 0
