from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roxauto.core.serde import to_primitive


def _as_tuple(value: Any, size: int | None = None) -> tuple[int, ...] | None:
    if value is None:
        return None
    if isinstance(value, tuple):
        numbers = tuple(int(item) for item in value)
    elif isinstance(value, list):
        numbers = tuple(int(item) for item in value)
    else:
        raise TypeError(f"Expected tuple/list-compatible value, got {type(value)!r}")
    if size is not None and len(numbers) != size:
        raise ValueError(f"Expected {size} values, got {len(numbers)}")
    return numbers


@dataclass(slots=True)
class CalibrationProfile:
    calibration_id: str
    description: str = ""
    capture_offset: tuple[int, int] = (0, 0)
    capture_scale: float = 1.0
    crop_box: tuple[int, int, int, int] | None = None
    anchor_overrides: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "CalibrationProfile":
        return cls(
            calibration_id=str(raw["calibration_id"]),
            description=str(raw.get("description", "")),
            capture_offset=_as_tuple(raw.get("capture_offset", (0, 0)), size=2) or (0, 0),
            capture_scale=float(raw.get("capture_scale", 1.0)),
            crop_box=_as_tuple(raw.get("crop_box")),
            anchor_overrides=dict(raw.get("anchor_overrides") or {}),
            metadata=dict(raw.get("metadata") or {}),
        )


@dataclass(slots=True)
class InstanceProfileOverride:
    instance_id: str
    adb_serial: str | None = None
    calibration_id: str | None = None
    capture_offset: tuple[int, int] = (0, 0)
    capture_scale: float | None = None
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "InstanceProfileOverride":
        return cls(
            instance_id=str(raw["instance_id"]),
            adb_serial=raw.get("adb_serial"),
            calibration_id=raw.get("calibration_id"),
            capture_offset=_as_tuple(raw.get("capture_offset", (0, 0)), size=2) or (0, 0),
            capture_scale=None if raw.get("capture_scale") is None else float(raw["capture_scale"]),
            notes=str(raw.get("notes", "")),
            metadata=dict(raw.get("metadata") or {}),
        )


@dataclass(slots=True)
class Profile:
    profile_id: str
    display_name: str
    server_name: str
    character_name: str
    allowed_tasks: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    calibration: CalibrationProfile | None = None
    instance_overrides: dict[str, InstanceProfileOverride] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "Profile":
        calibration_raw = raw.get("calibration")
        overrides_raw = raw.get("instance_overrides", {})
        return cls(
            profile_id=str(raw["profile_id"]),
            display_name=str(raw["display_name"]),
            server_name=str(raw["server_name"]),
            character_name=str(raw["character_name"]),
            allowed_tasks=[str(task_id) for task_id in (raw.get("allowed_tasks") or [])],
            settings=dict(raw.get("settings") or {}),
            calibration=CalibrationProfile.from_mapping(calibration_raw) if calibration_raw else None,
            instance_overrides={
                str(instance_id): InstanceProfileOverride.from_mapping(override)
                for instance_id, override in (overrides_raw or {}).items()
            },
        )


class JsonProfileStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, profile: Profile) -> Path:
        target = self.root / f"{profile.profile_id}.json"
        with target.open("w", encoding="utf-8") as handle:
            json.dump(to_primitive(profile), handle, indent=2, ensure_ascii=False)
        return target

    def load(self, profile_id: str) -> Profile | None:
        target = self.root / f"{profile_id}.json"
        if not target.exists():
            return None
        with target.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return Profile.from_mapping(raw)

    def list_profiles(self) -> list[Profile]:
        profiles: list[Profile] = []
        for file_path in sorted(self.root.glob("*.json")):
            with file_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            profiles.append(Profile.from_mapping(raw))
        return profiles
