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
        if not root.exists() or not root.is_dir():
            return []
        repositories: list[AnchorRepository] = []
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "manifest.json").exists():
                repositories.append(cls.load(child))
        return repositories

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    @property
    def repository_id(self) -> str:
        return self.manifest.repository_id

    @property
    def display_name(self) -> str:
        return self.manifest.display_name

    @property
    def version(self) -> str:
        return self.manifest.version

    def list_anchors(self) -> list[AnchorSpec]:
        return list(self.manifest.anchors)

    def list_anchor_ids(self) -> list[str]:
        return [anchor.anchor_id for anchor in self.manifest.anchors]

    def has_anchor(self, anchor_id: str) -> bool:
        return any(anchor.anchor_id == anchor_id for anchor in self.manifest.anchors)

    def get_anchor(self, anchor_id: str) -> AnchorSpec:
        for anchor in self.manifest.anchors:
            if anchor.anchor_id == anchor_id:
                return anchor
        raise KeyError(anchor_id)

    def find_anchors(
        self,
        *,
        query: str = "",
        tag: str = "",
        limit: int | None = None,
    ) -> list[AnchorSpec]:
        normalized_query = query.strip().lower()
        normalized_tag = tag.strip().lower()
        matched: list[AnchorSpec] = []

        for anchor in self.manifest.anchors:
            if normalized_tag and normalized_tag not in {entry.lower() for entry in anchor.tags}:
                continue
            if normalized_query:
                haystacks = [
                    anchor.anchor_id,
                    anchor.label,
                    anchor.description,
                    " ".join(anchor.tags),
                ]
                if not any(normalized_query in haystack.lower() for haystack in haystacks):
                    continue
            matched.append(anchor)
            if limit is not None and len(matched) >= limit:
                break

        return matched

    def resolve_template_path(self, template_path: str | Path) -> Path:
        return self.root / Path(template_path)

    def resolve_asset_path(self, anchor_id: str) -> Path:
        return self.resolve_template_path(self.get_anchor(anchor_id).template_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "manifest": self.manifest.to_dict(),
        }

    def write_manifest(self) -> Path:
        manifest_path = self.manifest_path
        manifest_path.write_text(dumps(self.manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return manifest_path

