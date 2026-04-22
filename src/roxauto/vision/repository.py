from __future__ import annotations

from dataclasses import dataclass
from json import dumps, loads
from pathlib import Path
from typing import Any, Self

from roxauto.vision.models import (
    AnchorCurationProfile,
    AnchorCurationReference,
    AnchorSpec,
    TemplateRepositoryManifest,
)


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

    def resolve_repository_path(self, relative_path: str | Path) -> Path:
        return self.root / Path(relative_path)

    def resolve_template_path(self, template_path: str | Path) -> Path:
        return self.resolve_repository_path(template_path)

    def resolve_asset_path(self, anchor_id: str) -> Path:
        return self.resolve_template_path(self.get_anchor(anchor_id).template_path)

    def get_anchor_curation(self, anchor_id: str) -> AnchorCurationProfile | None:
        return AnchorCurationProfile.from_metadata(self.get_anchor(anchor_id).metadata)

    def get_primary_curation_reference(self, anchor_id: str) -> AnchorCurationReference | None:
        curation = self.get_anchor_curation(anchor_id)
        if curation is None or not curation.references:
            return None
        return curation.references[0]

    def list_curation_references(self, anchor_id: str) -> list[AnchorCurationReference]:
        curation = self.get_anchor_curation(anchor_id)
        if curation is None:
            return []
        return list(curation.references)

    def resolve_curation_reference_path(self, anchor_id: str) -> Path | None:
        reference = self.get_primary_curation_reference(anchor_id)
        if reference is None or not reference.image_path:
            return None
        return self.resolve_repository_path(reference.image_path)

    def resolve_curation_reference_paths(self, anchor_id: str) -> list[Path]:
        paths: list[Path] = []
        for reference in self.list_curation_references(anchor_id):
            if not reference.image_path:
                continue
            paths.append(self.resolve_repository_path(reference.image_path))
        return paths

    def get_task_support(self, task_id: str) -> dict[str, Any]:
        task_support = self.manifest.metadata.get("task_support", {})
        if not isinstance(task_support, dict):
            return {}
        support = task_support.get(task_id, {})
        return dict(support) if isinstance(support, dict) else {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "manifest": self.manifest.to_dict(),
        }

    def write_manifest(self) -> Path:
        manifest_path = self.manifest_path
        manifest_path.write_text(dumps(self.manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return manifest_path

