from __future__ import annotations

from dataclasses import dataclass
from json import dumps, loads
from pathlib import Path
from typing import Any, Self

from roxauto.vision.models import AnchorSpec, TemplateRepositoryManifest


@dataclass(slots=True)
class AnchorRepository:
    root: Path
    manifest: TemplateRepositoryManifest

    @classmethod
    def load(cls, root: Path | str) -> Self:
        repository_root = Path(root)
        manifest_path = repository_root / "manifest.json"
        data = loads(manifest_path.read_text(encoding="utf-8"))
        return cls(root=repository_root, manifest=TemplateRepositoryManifest.from_dict(data))

    @classmethod
    def discover(cls, templates_root: Path | str) -> list[Self]:
        root = Path(templates_root)
        repositories: list[AnchorRepository] = []
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "manifest.json").exists():
                repositories.append(cls.load(child))
        return repositories

    @property
    def repository_id(self) -> str:
        return self.manifest.repository_id

    @property
    def display_name(self) -> str:
        return self.manifest.display_name

    def list_anchors(self) -> list[AnchorSpec]:
        return list(self.manifest.anchors)

    def get_anchor(self, anchor_id: str) -> AnchorSpec:
        for anchor in self.manifest.anchors:
            if anchor.anchor_id == anchor_id:
                return anchor
        raise KeyError(anchor_id)

    def resolve_asset_path(self, anchor_id: str) -> Path:
        return self.root / self.get_anchor(anchor_id).template_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "manifest": self.manifest.to_dict(),
        }

    def write_manifest(self) -> Path:
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(dumps(self.manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return manifest_path

