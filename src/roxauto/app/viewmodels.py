from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InstanceCardView:
    instance_id: str
    label: str
    adb_serial: str
    status: str
    last_seen_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConsoleSnapshot:
    adb_path: str
    instance_count: int
    packages: dict[str, bool]
    instances: list[InstanceCardView]

    @property
    def available_runtime_features(self) -> list[str]:
        enabled: list[str] = []
        for package_name, installed in self.packages.items():
            if installed:
                enabled.append(package_name)
        return enabled


def build_console_snapshot(report: dict[str, Any]) -> ConsoleSnapshot:
    adb = report.get("adb", {})
    packages = dict(report.get("packages", {}))
    instances = [
        InstanceCardView(
            instance_id=str(instance.get("instance_id", "")),
            label=str(instance.get("label", "")),
            adb_serial=str(instance.get("adb_serial", "")),
            status=str(instance.get("status", "")),
            last_seen_at=str(instance.get("last_seen_at", "")),
            metadata=dict(instance.get("metadata", {})),
        )
        for instance in report.get("instances", [])
    ]
    return ConsoleSnapshot(
        adb_path=str(adb.get("path") or "not found"),
        instance_count=int(adb.get("instances_found") or len(instances)),
        packages=packages,
        instances=instances,
    )
