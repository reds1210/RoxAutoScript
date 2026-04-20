from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roxauto.core.models import ProfileBinding
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

    def resolve_binding(self, instance_id: str, adb_serial: str | None = None) -> ProfileBinding:
        override = self.instance_overrides.get(instance_id)
        if override is None and adb_serial is not None:
            override = next(
                (
                    candidate
                    for candidate in self.instance_overrides.values()
                    if candidate.adb_serial == adb_serial
                ),
                None,
            )

        calibration_id = None
        capture_offset = (0, 0)
        capture_scale = 1.0
        metadata: dict[str, Any] = {}
        if self.calibration is not None:
            calibration_id = self.calibration.calibration_id
            capture_offset = self.calibration.capture_offset
            capture_scale = self.calibration.capture_scale
            metadata["calibration_metadata"] = dict(self.calibration.metadata)
            if self.calibration.anchor_overrides:
                metadata["anchor_overrides"] = dict(self.calibration.anchor_overrides)

        notes = ""
        if override is not None:
            calibration_id = override.calibration_id or calibration_id
            capture_offset = override.capture_offset
            capture_scale = override.capture_scale if override.capture_scale is not None else capture_scale
            notes = override.notes
            if override.metadata:
                metadata["override_metadata"] = dict(override.metadata)

        return ProfileBinding(
            profile_id=self.profile_id,
            display_name=self.display_name,
            server_name=self.server_name,
            character_name=self.character_name,
            allowed_tasks=list(self.allowed_tasks),
            calibration_id=calibration_id,
            capture_offset=capture_offset,
            capture_scale=capture_scale,
            settings=dict(self.settings),
            notes=notes,
            metadata=metadata,
        )

    def matches_instance(self, instance_id: str, adb_serial: str | None = None) -> bool:
        if instance_id in self.instance_overrides:
            return True
        if adb_serial is None:
            return False
        return any(
            override.adb_serial == adb_serial
            for override in self.instance_overrides.values()
            if override.adb_serial is not None
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

    def list_matching_profiles(self, instance_id: str, adb_serial: str | None = None) -> list[Profile]:
        return [
            profile
            for profile in self.list_profiles()
            if profile.matches_instance(instance_id=instance_id, adb_serial=adb_serial)
        ]

    def resolve_binding(self, profile_id: str, instance_id: str, adb_serial: str | None = None) -> ProfileBinding | None:
        profile = self.load(profile_id)
        if profile is None:
            return None
        return profile.resolve_binding(instance_id=instance_id, adb_serial=adb_serial)

    def resolve_binding_for_instance(
        self,
        instance_id: str,
        adb_serial: str | None = None,
        *,
        profile_id: str | None = None,
    ) -> ProfileBinding | None:
        if profile_id is not None:
            return self.resolve_binding(profile_id=profile_id, instance_id=instance_id, adb_serial=adb_serial)
        matches = self.list_matching_profiles(instance_id=instance_id, adb_serial=adb_serial)
        if len(matches) != 1:
            return None
        return matches[0].resolve_binding(instance_id=instance_id, adb_serial=adb_serial)
