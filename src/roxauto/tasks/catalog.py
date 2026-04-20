from __future__ import annotations

from json import loads
from pathlib import Path
from typing import Self

from roxauto.tasks.models import (
    GoldenScreenshotConvention,
    TaskBlueprint,
    TaskFixtureProfile,
    TaskImplementationState,
    TaskInventory,
    TaskInventoryRecord,
)


class TaskFoundationRepository:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    @classmethod
    def load_default(cls) -> Self:
        return cls(Path(__file__).resolve().parent / "foundations")

    def load_golden_convention(self) -> GoldenScreenshotConvention:
        path = self.root / "conventions" / "golden_screenshots.json"
        return GoldenScreenshotConvention.from_dict(loads(path.read_text(encoding="utf-8")))

    def discover_blueprints(self) -> list[TaskBlueprint]:
        blueprints: list[TaskBlueprint] = []
        for path in sorted((self.root / "packs").glob("*/*.task.json")):
            blueprints.append(self.load_blueprint(path))
        return blueprints

    def load_blueprint(self, path: Path | str) -> TaskBlueprint:
        blueprint_path = Path(path)
        return TaskBlueprint.from_dict(loads(blueprint_path.read_text(encoding="utf-8")))

    def discover_fixture_profiles(self) -> list[TaskFixtureProfile]:
        profiles: list[TaskFixtureProfile] = []
        for path in sorted((self.root / "fixture_profiles").glob("*.fixture.json")):
            profiles.append(self.load_fixture_profile(path))
        return profiles

    def load_fixture_profile(self, path: Path | str) -> TaskFixtureProfile:
        fixture_path = Path(path)
        return TaskFixtureProfile.from_json(fixture_path.read_text(encoding="utf-8"))

    def load_inventory(self) -> TaskInventory:
        path = self.root / "inventory.json"
        return TaskInventory.from_json(path.read_text(encoding="utf-8"))

    def build_inventory(self) -> TaskInventory:
        convention = self.load_golden_convention()
        records: list[TaskInventoryRecord] = []
        for path in sorted((self.root / "packs").glob("*/*.task.json")):
            blueprint = self.load_blueprint(path)
            golden_root = convention.directory_template.format(
                pack_id=blueprint.pack_id,
                task_id=blueprint.task_id,
                screen_slug="{screen_slug}",
            )
            records.append(
                TaskInventoryRecord(
                    task_id=blueprint.task_id,
                    pack_id=blueprint.pack_id,
                    implementation_state=TaskImplementationState(blueprint.implementation_state.value),
                    manifest_path=path.relative_to(self.root).as_posix(),
                    fixture_profile_paths=list(blueprint.fixture_profile_paths),
                    golden_root=golden_root,
                    required_anchors=list(blueprint.required_anchors),
                    metadata={"source": "build_inventory"},
                )
            )
        return TaskInventory(
            inventory_id="pre_gate_3_task_foundations",
            version="0.1.0",
            records=records,
            metadata={"purpose": "task_foundation_inventory"},
        )
