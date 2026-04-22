from __future__ import annotations

from dataclasses import dataclass
from json import dumps, loads
from pathlib import Path
from typing import Any, Self

from roxauto.vision.models import (
    AnchorCurationProfile,
    AnchorCurationReference,
    AnchorSpec,
    ClaimRewardsGoldenCatalog,
    ClaimRewardsGoldenCatalogEntry,
    ClaimRewardsSupportingCapture,
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

    def resolve_claim_rewards_catalog_path(self) -> Path | None:
        catalog_path = str(
            self.get_task_support("daily_ui.claim_rewards").get("golden_catalog_path", "")
        ).strip()
        if not catalog_path:
            return None
        path = Path(catalog_path)
        if path.is_absolute() or ".." in path.parts:
            return None
        resolved = (self.root / path).resolve()
        try:
            resolved.relative_to(self.root.resolve())
        except ValueError:
            return None
        return resolved

    def get_claim_rewards_golden_catalog(self) -> ClaimRewardsGoldenCatalog | None:
        catalog_path = self.resolve_claim_rewards_catalog_path()
        if catalog_path is None or not catalog_path.exists():
            return None
        data = loads(catalog_path.read_text(encoding="utf-8"))
        return ClaimRewardsGoldenCatalog.from_dict(data)

    def get_claim_rewards_post_tap_contract(self) -> dict[str, Any]:
        support = self.get_task_support("daily_ui.claim_rewards")
        contract = support.get("post_tap_contract", {})
        return dict(contract) if isinstance(contract, dict) else {}

    def get_claim_rewards_anchor_golden(
        self,
        anchor_id: str,
    ) -> ClaimRewardsGoldenCatalogEntry | None:
        catalog = self.get_claim_rewards_golden_catalog()
        if catalog is None:
            return None
        curation = self.get_anchor_curation(anchor_id)
        golden_id = ""
        if curation is not None:
            golden_id = str(curation.metadata.get("golden_id", "")).strip()
        if golden_id:
            return catalog.get_golden(golden_id)
        for golden in catalog.goldens:
            if golden.anchor_id == anchor_id:
                return golden
        return None

    def resolve_claim_rewards_golden_image_path(self, anchor_id: str) -> Path | None:
        catalog_path = self.resolve_claim_rewards_catalog_path()
        golden = self.get_claim_rewards_anchor_golden(anchor_id)
        if catalog_path is None or golden is None or not golden.file_name:
            return None
        return catalog_path.parent / Path(golden.file_name)

    def list_claim_rewards_supporting_captures(
        self,
        anchor_id: str,
    ) -> list[ClaimRewardsSupportingCapture]:
        catalog = self.get_claim_rewards_golden_catalog()
        golden = self.get_claim_rewards_anchor_golden(anchor_id)
        if catalog is None or golden is None:
            return []
        captures: list[ClaimRewardsSupportingCapture] = []
        seen_capture_ids: set[str] = set()
        for capture_id in golden.supporting_capture_ids:
            if capture_id in seen_capture_ids:
                continue
            capture = catalog.get_supporting_capture(capture_id)
            if capture is None:
                continue
            captures.append(capture)
            seen_capture_ids.add(capture_id)
        return captures

    def resolve_claim_rewards_supporting_capture_paths(self, anchor_id: str) -> list[Path]:
        catalog_path = self.resolve_claim_rewards_catalog_path()
        if catalog_path is None:
            return []
        paths: list[Path] = []
        for capture in self.list_claim_rewards_supporting_captures(anchor_id):
            if not capture.file_name:
                continue
            paths.append(catalog_path.parent / Path(capture.file_name))
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

