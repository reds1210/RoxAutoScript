from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from roxauto.core.serde import to_primitive


@dataclass(slots=True)
class Profile:
    profile_id: str
    display_name: str
    server_name: str
    character_name: str
    allowed_tasks: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)


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
        return Profile(**raw)

    def list_profiles(self) -> list[Profile]:
        profiles: list[Profile] = []
        for file_path in sorted(self.root.glob("*.json")):
            with file_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            profiles.append(Profile(**raw))
        return profiles

