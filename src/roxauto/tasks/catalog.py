from __future__ import annotations

from json import loads
from pathlib import Path
from typing import Self

from roxauto.tasks.models import (
    GoldenScreenshotConvention,
    TaskBlueprint,
    TaskAssetInventory,
    TaskAssetKind,
    TaskAssetRecord,
    TaskAssetStatus,
    TaskFixtureProfile,
    TaskImplementationState,
    TaskInventory,
    TaskInventoryRecord,
    TaskPackCatalog,
)


class TaskFoundationRepository:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.repo_root = Path(__file__).resolve().parents[3]

    @classmethod
    def load_default(cls) -> Self:
        return cls(Path(__file__).resolve().parent / "foundations")

    def load_golden_convention(self) -> GoldenScreenshotConvention:
        path = self.root / "conventions" / "golden_screenshots.json"
        return GoldenScreenshotConvention.from_dict(loads(path.read_text(encoding="utf-8")))

    def discover_blueprints(self, pack_id: str | None = None) -> list[TaskBlueprint]:
        blueprints: list[TaskBlueprint] = []
        pattern = f"{pack_id}/*.task.json" if pack_id else "*/*.task.json"
        for path in sorted((self.root / "packs").glob(pattern)):
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

    def discover_pack_catalogs(self) -> list[TaskPackCatalog]:
        catalogs: list[TaskPackCatalog] = []
        for path in sorted((self.root / "packs").glob("*/catalog.json")):
            catalogs.append(self.load_pack_catalog(path))
        return catalogs

    def load_pack_catalog(self, path: Path | str) -> TaskPackCatalog:
        catalog_path = Path(path)
        return TaskPackCatalog.from_dict(loads(catalog_path.read_text(encoding="utf-8")))

    def load_pack_catalog_for_pack(self, pack_id: str) -> TaskPackCatalog:
        return self.load_pack_catalog(self.root / "packs" / pack_id / "catalog.json")

    def load_inventory(self) -> TaskInventory:
        path = self.root / "inventory.json"
        return TaskInventory.from_json(path.read_text(encoding="utf-8"))

    def build_task_inventory(self) -> TaskInventory:
        convention = self.load_golden_convention()
        records: list[TaskInventoryRecord] = []
        for path in sorted((self.root / "packs").glob("*/*.task.json")):
            blueprint = self.load_blueprint(path)
            golden_root = convention.directory_template.format(
                pack_id=blueprint.pack_id,
                task_id=blueprint.task_id.replace(".", "_").replace("-", "_"),
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
                    metadata={"source": "build_task_inventory"},
                )
            )
        return TaskInventory(
            inventory_id="pre_gate_3_task_foundations",
            version="0.1.0",
            records=records,
            metadata={"purpose": "task_foundation_inventory"},
        )

    def build_inventory(self) -> TaskInventory:
        return self.build_task_inventory()

    def load_asset_inventory(self) -> TaskAssetInventory:
        path = self.root / "asset_inventory.json"
        return TaskAssetInventory.from_json(path.read_text(encoding="utf-8"))

    def build_asset_inventory(self) -> TaskAssetInventory:
        anchor_sources = self._discover_template_anchor_sources()
        records: list[TaskAssetRecord] = []
        for blueprint in self.discover_blueprints():
            for fixture_profile_path in blueprint.fixture_profile_paths:
                fixture_path = self.root / fixture_profile_path
                records.append(
                    TaskAssetRecord(
                        asset_id=f"{blueprint.task_id}:fixture:{Path(fixture_profile_path).stem}",
                        pack_id=blueprint.pack_id,
                        task_id=blueprint.task_id,
                        asset_kind=TaskAssetKind.FIXTURE_PROFILE,
                        status=TaskAssetStatus.PRESENT if fixture_path.exists() else TaskAssetStatus.MISSING,
                        source_path=fixture_profile_path,
                        metadata={"source": "fixture_profile"},
                    )
                )
            for anchor_id in blueprint.required_anchors:
                source_path = anchor_sources.get(anchor_id, "")
                records.append(
                    TaskAssetRecord(
                        asset_id=f"{blueprint.task_id}:template:{anchor_id}",
                        pack_id=blueprint.pack_id,
                        task_id=blueprint.task_id,
                        asset_kind=TaskAssetKind.TEMPLATE,
                        status=TaskAssetStatus.PLACEHOLDER if source_path else TaskAssetStatus.MISSING,
                        source_path=source_path,
                        metadata={"anchor_id": anchor_id, "source": "template_manifest"},
                    )
                )
            convention = self.load_golden_convention()
            for case in blueprint.golden_cases:
                records.append(
                    TaskAssetRecord(
                        asset_id=f"{blueprint.task_id}:golden:{case.screen_slug}",
                        pack_id=blueprint.pack_id,
                        task_id=blueprint.task_id,
                        asset_kind=TaskAssetKind.GOLDEN_SCREENSHOT,
                        status=TaskAssetStatus.PLANNED,
                        source_path=convention.render_path(
                            pack_id=blueprint.pack_id,
                            task_id=blueprint.task_id,
                            screen_slug=case.screen_slug,
                            variant=convention.required_variants[0],
                        ).as_posix(),
                        metadata={"variants": list(case.variants), "source": "golden_convention"},
                    )
                )
        return TaskAssetInventory(
            inventory_id="pre_gate_3_task_asset_inventory",
            version="0.1.0",
            records=records,
            metadata={"purpose": "task_asset_inventory"},
        )

    def _discover_template_anchor_sources(self) -> dict[str, str]:
        sources: dict[str, str] = {}
        for manifest_path in sorted((self.repo_root / "assets" / "templates").glob("*/manifest.json")):
            payload = loads(manifest_path.read_text(encoding="utf-8"))
            relative_path = manifest_path.relative_to(self.repo_root).as_posix()
            for anchor in payload.get("anchors", []):
                anchor_id = str(anchor.get("anchor_id", ""))
                if anchor_id:
                    sources[anchor_id] = f"{relative_path}#{anchor_id}"
        return sources
