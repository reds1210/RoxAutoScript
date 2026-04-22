from __future__ import annotations

from dataclasses import dataclass
from json import loads
from pathlib import Path, PurePosixPath
from typing import Any, Self

from roxauto.tasks.models import (
    GoldenScreenshotConvention,
    TaskBlueprint,
    TaskAssetInventory,
    TaskAssetKind,
    TaskAssetRecord,
    TaskAssetStatus,
    TaskFixtureProfile,
    TaskGapDomain,
    TaskImplementationState,
    TaskInventory,
    TaskInventoryRecord,
    TaskPackCatalog,
    TaskReadinessCollection,
    TaskReadinessReport,
    TaskReadinessRequirement,
    TaskReadinessState,
    TaskRuntimeBuilderInput,
)


@dataclass(frozen=True, slots=True)
class _RequirementSpec:
    requirement_id: str
    domain: TaskGapDomain
    summary: str
    builder_blocking: bool = False
    implementation_blocking: bool = False
    asset_anchor_id: str = ""


@dataclass(frozen=True, slots=True)
class _DiscoveredTemplateAsset:
    source_path: str
    status: TaskAssetStatus
    template_path: str = ""
    placeholder: bool = False
    curation_status: str = ""
    provenance_kind: str = ""
    source_kind: str = ""
    live_capture: bool | None = None
    replacement_target: str = ""
    inspection_role: str = ""
    stage: str = ""


@dataclass(frozen=True, slots=True)
class _DiscoveredGoldenAsset:
    source_path: str
    source_kind: str = ""
    live_capture: bool | None = None
    anchor_id: str = ""
    inspection_role: str = ""
    stage: str = ""
    scene_id: str = ""
    reference_id: str = ""
    golden_id: str = ""


_REQUIREMENT_SPECS: dict[str, _RequirementSpec] = {
    "asset.daily_ui.guild_check_in_button": _RequirementSpec(
        requirement_id="asset.daily_ui.guild_check_in_button",
        domain=TaskGapDomain.ASSET,
        summary="Guild check-in still requires a curated guild check-in button asset, not just placeholder scaffolding.",
        builder_blocking=True,
        implementation_blocking=True,
        asset_anchor_id="daily_ui.guild_check_in_button",
    ),
    "runtime.daily_ui.dispatch_bridge": _RequirementSpec(
        requirement_id="runtime.daily_ui.dispatch_bridge",
        domain=TaskGapDomain.RUNTIME,
        summary="Daily UI fixed-flow tasks require a production runtime action-dispatch bridge.",
        implementation_blocking=True,
    ),
    "calibration.odin.idle_state_profile": _RequirementSpec(
        requirement_id="calibration.odin.idle_state_profile",
        domain=TaskGapDomain.CALIBRATION,
        summary="Odin preset entry requires an idle-state calibration profile before runtime binding is safe.",
        implementation_blocking=True,
    ),
}


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
        anchor_sources = self._discover_template_anchor_assets()
        golden_sources = self._discover_golden_catalog_assets()
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
                    asset_requirement_ids=self._requirement_ids(blueprint, "asset_requirement_ids"),
                    runtime_requirement_ids=self._requirement_ids(blueprint, "runtime_requirement_ids"),
                    calibration_requirement_ids=self._requirement_ids(blueprint, "calibration_requirement_ids"),
                    foundation_requirement_ids=self._requirement_ids(blueprint, "foundation_requirement_ids"),
                    metadata=self._inventory_metadata(
                        blueprint,
                        anchor_sources=anchor_sources,
                        golden_sources=golden_sources,
                        convention=convention,
                    ),
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

    def load_readiness_report(self) -> TaskReadinessCollection:
        path = self.root / "readiness_report.json"
        return TaskReadinessCollection.from_json(path.read_text(encoding="utf-8"))

    def build_runtime_builder_input(self, task_id: str) -> TaskRuntimeBuilderInput:
        record = self._inventory_record_by_task_id()[task_id]
        return TaskRuntimeBuilderInput(
            task_id=record.task_id,
            pack_id=record.pack_id,
            manifest_path=record.manifest_path,
            fixture_profile_paths=list(record.fixture_profile_paths),
            required_anchors=list(record.required_anchors),
            asset_requirement_ids=list(record.asset_requirement_ids),
            runtime_requirement_ids=list(record.runtime_requirement_ids),
            calibration_requirement_ids=list(record.calibration_requirement_ids),
            foundation_requirement_ids=list(record.foundation_requirement_ids),
            metadata={
                **dict(record.metadata),
                "inventory_source": str(record.metadata.get("source", "")),
                "source": "task_foundations",
            },
        )

    def build_runtime_builder_inputs(self) -> list[TaskRuntimeBuilderInput]:
        return [self.build_runtime_builder_input(record.task_id) for record in self.load_inventory().records]

    def build_asset_inventory(self) -> TaskAssetInventory:
        anchor_sources = self._discover_template_anchor_assets()
        golden_sources = self._discover_golden_catalog_assets()
        convention = self.load_golden_convention()
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
            for anchor_id in self._tracked_anchor_ids(blueprint):
                anchor_source = anchor_sources.get(anchor_id)
                records.append(
                    TaskAssetRecord(
                        asset_id=f"{blueprint.task_id}:template:{anchor_id}",
                        pack_id=blueprint.pack_id,
                        task_id=blueprint.task_id,
                        asset_kind=TaskAssetKind.TEMPLATE,
                        status=anchor_source.status if anchor_source is not None else TaskAssetStatus.MISSING,
                        source_path=anchor_source.source_path if anchor_source is not None else "",
                        metadata=self._template_asset_metadata(
                            anchor_id,
                            anchor_source,
                            requirement_level=self._anchor_requirement_level(blueprint, anchor_id),
                        ),
                    )
                )
            for case in blueprint.golden_cases:
                golden_asset = self._resolve_golden_asset(
                    blueprint,
                    case.screen_slug,
                    convention,
                    golden_sources=golden_sources,
                )
                records.append(
                    TaskAssetRecord(
                        asset_id=f"{blueprint.task_id}:golden:{case.screen_slug}",
                        pack_id=blueprint.pack_id,
                        task_id=blueprint.task_id,
                        asset_kind=TaskAssetKind.GOLDEN_SCREENSHOT,
                        status=golden_asset["status"],
                        source_path=golden_asset["source_path"],
                        metadata=self._golden_asset_metadata(
                            case,
                            golden_asset,
                            requirement_level=self._golden_requirement_level(blueprint, case.screen_slug),
                        ),
                    )
                )
        return TaskAssetInventory(
            inventory_id="pre_gate_3_task_asset_inventory",
            version="0.1.0",
            records=records,
            metadata={"purpose": "task_asset_inventory"},
        )

    def evaluate_task_readiness(self, task_id: str) -> TaskReadinessReport:
        builder_input = self.build_runtime_builder_input(task_id)
        inventory_record = self._inventory_record_by_task_id()[task_id]
        asset_records = self._asset_records_by_task_id().get(task_id, [])
        builder_requirements: list[TaskReadinessRequirement] = []
        implementation_requirements: list[TaskReadinessRequirement] = []

        for requirement_id in builder_input.asset_requirement_ids:
            requirement = self._evaluate_requirement(
                requirement_id,
                asset_records=asset_records,
                blocking=True,
            )
            if requirement is not None:
                builder_requirements.append(requirement)
                implementation_requirements.append(requirement)

        for requirement_id in builder_input.runtime_requirement_ids:
            requirement = self._evaluate_requirement(
                requirement_id,
                asset_records=asset_records,
                blocking=True,
            )
            if requirement is not None:
                implementation_requirements.append(requirement)

        for requirement_id in builder_input.calibration_requirement_ids:
            requirement = self._evaluate_requirement(
                requirement_id,
                asset_records=asset_records,
                blocking=True,
            )
            if requirement is not None:
                implementation_requirements.append(requirement)

        for requirement_id in builder_input.foundation_requirement_ids:
            requirement = self._evaluate_requirement(
                requirement_id,
                asset_records=asset_records,
                blocking=True,
            )
            if requirement is not None:
                builder_requirements.append(requirement)
                implementation_requirements.append(requirement)

        warning_requirements = self._warning_requirements(
            task_id=task_id,
            asset_records=asset_records,
            blocking_requirement_ids=set(
                builder_input.asset_requirement_ids
                + builder_input.runtime_requirement_ids
                + builder_input.calibration_requirement_ids
                + builder_input.foundation_requirement_ids
            ),
        )
        return TaskReadinessReport(
            task_id=task_id,
            pack_id=inventory_record.pack_id,
            builder_readiness_state=self._derive_readiness_state(builder_requirements),
            implementation_readiness_state=self._derive_readiness_state(implementation_requirements),
            builder_requirements=builder_requirements,
            implementation_requirements=implementation_requirements,
            warning_requirements=warning_requirements,
            metadata={
                "builder_input": builder_input.to_dict(),
                "implementation_state": inventory_record.implementation_state.value,
            },
        )

    def evaluate_task_readinesses(self) -> list[TaskReadinessReport]:
        return [self.evaluate_task_readiness(record.task_id) for record in self.load_inventory().records]

    def build_readiness_collection(self) -> TaskReadinessCollection:
        return TaskReadinessCollection(
            report_id="pre_gate_3_task_readiness",
            version="0.1.0",
            reports=self.evaluate_task_readinesses(),
            metadata={"source": "task_foundations"},
        )

    def _discover_template_anchor_assets(self) -> dict[str, _DiscoveredTemplateAsset]:
        sources: dict[str, _DiscoveredTemplateAsset] = {}
        for manifest_path in sorted((self.repo_root / "assets" / "templates").glob("*/manifest.json")):
            payload = loads(manifest_path.read_text(encoding="utf-8"))
            relative_path = manifest_path.relative_to(self.repo_root).as_posix()
            for anchor in payload.get("anchors", []):
                anchor_id = str(anchor.get("anchor_id", ""))
                if anchor_id:
                    metadata = dict(anchor.get("metadata", {}))
                    template_path = str(anchor.get("template_path", ""))
                    resolved_template_path = manifest_path.parent / template_path if template_path else None
                    template_exists = bool(resolved_template_path and resolved_template_path.exists())
                    curation = metadata.get("curation", {})
                    curation_status = (
                        str(curation.get("status", "")).strip().lower()
                        if isinstance(curation, dict)
                        else ""
                    )
                    provenance = dict(curation.get("provenance", {})) if isinstance(curation, dict) else {}
                    curation_metadata = dict(curation.get("metadata", {})) if isinstance(curation, dict) else {}
                    status = TaskAssetStatus.MISSING
                    if template_exists:
                        status = (
                            TaskAssetStatus.PLACEHOLDER
                            if bool(metadata.get("placeholder", False))
                            else TaskAssetStatus.PRESENT
                        )
                    sources[anchor_id] = _DiscoveredTemplateAsset(
                        source_path=f"{relative_path}#{anchor_id}",
                        status=status,
                        template_path=template_path,
                        placeholder=bool(metadata.get("placeholder", False)),
                        curation_status=curation_status,
                        provenance_kind=str(provenance.get("kind", "")).strip().lower(),
                        source_kind=str(curation_metadata.get("source_kind", "")).strip().lower(),
                        live_capture=self._optional_bool(curation_metadata.get("live_capture")),
                        replacement_target=str(curation_metadata.get("replacement_target", "")).strip(),
                        inspection_role=str(metadata.get("inspection_role", "")).strip(),
                        stage=str(metadata.get("stage", "")).strip(),
                    )
        return sources

    def _discover_golden_catalog_assets(self) -> dict[str, _DiscoveredGoldenAsset]:
        assets: dict[str, _DiscoveredGoldenAsset] = {}
        for catalog_path in sorted((self.repo_root / "assets" / "templates").glob("*/goldens/*/catalog.json")):
            payload = loads(catalog_path.read_text(encoding="utf-8"))
            catalog_dir = catalog_path.parent
            for raw_entry in list(payload.get("goldens", [])) + list(payload.get("supplemental_live_captures", [])):
                file_name = str(raw_entry.get("file_name", "")).strip()
                if not file_name:
                    continue
                source_path = (catalog_dir / file_name).relative_to(self.repo_root).as_posix()
                assets[source_path] = _DiscoveredGoldenAsset(
                    source_path=source_path,
                    source_kind=str(raw_entry.get("source_kind", "")).strip().lower(),
                    live_capture=self._optional_bool(raw_entry.get("live_capture")),
                    anchor_id=str(raw_entry.get("anchor_id", "")).strip(),
                    inspection_role=str(raw_entry.get("inspection_role", "")).strip(),
                    stage=str(raw_entry.get("stage", "")).strip(),
                    scene_id=str(raw_entry.get("scene_id", "")).strip(),
                    reference_id=str(raw_entry.get("reference_id", "")).strip(),
                    golden_id=str(raw_entry.get("golden_id", raw_entry.get("capture_id", ""))).strip(),
                )
        return assets

    def _inventory_record_by_task_id(self) -> dict[str, TaskInventoryRecord]:
        return {record.task_id: record for record in self.load_inventory().records}

    def _asset_records_by_task_id(self) -> dict[str, list[TaskAssetRecord]]:
        grouped: dict[str, list[TaskAssetRecord]] = {}
        for record in self.build_asset_inventory().records:
            grouped.setdefault(record.task_id, []).append(record)
        return grouped

    def _requirement_ids(self, blueprint: TaskBlueprint, key: str) -> list[str]:
        metadata = dict(blueprint.metadata)
        if key in metadata:
            return [str(item) for item in metadata.get(key, [])]
        defaults = {
            "daily_ui.guild_check_in": {
                "asset_requirement_ids": ["asset.daily_ui.guild_check_in_button"],
            }
        }
        return list(defaults.get(blueprint.task_id, {}).get(key, []))

    def _evaluate_requirement(
        self,
        requirement_id: str,
        *,
        asset_records: list[TaskAssetRecord],
        blocking: bool,
    ) -> TaskReadinessRequirement | None:
        spec = _REQUIREMENT_SPECS.get(requirement_id)
        if spec is None:
            return TaskReadinessRequirement(
                requirement_id=requirement_id,
                domain=TaskGapDomain.FOUNDATION,
                summary="Unknown readiness requirement.",
                satisfied=False,
                blocking=blocking,
                details="Requirement id is not registered in the task foundation catalog.",
            )
        satisfied = self._requirement_satisfied(spec, asset_records)
        details = self._requirement_details(spec, asset_records, satisfied)
        return TaskReadinessRequirement(
            requirement_id=spec.requirement_id,
            domain=spec.domain,
            summary=spec.summary,
            satisfied=satisfied,
            blocking=blocking,
            details=details,
            metadata={"domain": spec.domain.value},
        )

    def _requirement_satisfied(
        self,
        spec: _RequirementSpec,
        asset_records: list[TaskAssetRecord],
    ) -> bool:
        if spec.domain is TaskGapDomain.ASSET and spec.asset_anchor_id:
            for record in asset_records:
                if record.metadata.get("anchor_id") == spec.asset_anchor_id:
                    return record.status is TaskAssetStatus.PRESENT
            return False
        if spec.requirement_id == "runtime.daily_ui.dispatch_bridge":
            try:
                from roxauto.tasks.daily_ui import has_claim_rewards_runtime_bridge
            except ImportError:
                return False
            return has_claim_rewards_runtime_bridge()
        return False

    def _requirement_details(
        self,
        spec: _RequirementSpec,
        asset_records: list[TaskAssetRecord],
        satisfied: bool,
    ) -> str:
        if spec.domain is TaskGapDomain.ASSET and spec.asset_anchor_id:
            for record in asset_records:
                if record.metadata.get("anchor_id") == spec.asset_anchor_id:
                    return (
                        f"asset_status={record.status.value} "
                        f"source_path={record.source_path or 'n/a'}"
                    )
            return "asset_status=missing source_path=n/a"
        if spec.requirement_id == "runtime.daily_ui.dispatch_bridge":
            status = "implemented" if satisfied else "missing"
            return (
                "runtime_bridge="
                f"{status} "
                "runtime_input_builder=roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_runtime_input "
                "runtime_seam_builder=roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_runtime_seam "
                "task_spec_builder=roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_task_spec"
            )
        return "Requirement is not yet satisfied by current task foundations."

    def _inventory_metadata(
        self,
        blueprint: TaskBlueprint,
        *,
        anchor_sources: dict[str, _DiscoveredTemplateAsset],
        golden_sources: dict[str, _DiscoveredGoldenAsset],
        convention: GoldenScreenshotConvention,
    ) -> dict[str, object]:
        blueprint_metadata = dict(blueprint.metadata)
        product_display = dict(blueprint_metadata.get("product_display", {}))
        metadata: dict[str, object] = {"source": "curated_inventory"}
        if "phase" in blueprint_metadata:
            metadata["phase"] = str(blueprint_metadata.get("phase", ""))
        if "asset_state" in blueprint_metadata:
            metadata["asset_state"] = str(blueprint_metadata.get("asset_state", ""))
        asset_provenance = self._asset_provenance_summary(
            blueprint,
            anchor_sources=anchor_sources,
            golden_sources=golden_sources,
            convention=convention,
        )
        if asset_provenance:
            metadata["asset_provenance"] = asset_provenance
            if asset_provenance.get("asset_state"):
                metadata["asset_state"] = str(asset_provenance.get("asset_state", ""))
        if isinstance(blueprint_metadata.get("runtime_seam"), dict):
            metadata["runtime_seam"] = dict(blueprint_metadata.get("runtime_seam", {}))
        signal_contract_version = self._signal_contract_version(blueprint)
        if signal_contract_version:
            metadata["signal_contract_version"] = signal_contract_version
        if product_display.get("preset_id"):
            metadata["preset_id"] = str(product_display.get("preset_id", ""))
        if product_display.get("display_name"):
            metadata["product_display_name"] = str(product_display.get("display_name", ""))
        supporting_anchor_ids = self._supporting_anchor_ids(blueprint)
        if supporting_anchor_ids:
            metadata["supporting_anchor_ids"] = supporting_anchor_ids
        supporting_golden_screen_slugs = self._supporting_golden_screen_slugs(blueprint)
        if supporting_golden_screen_slugs:
            metadata["supporting_golden_screen_slugs"] = supporting_golden_screen_slugs
        post_claim_resolution = blueprint.metadata.get("post_claim_resolution")
        if isinstance(post_claim_resolution, dict):
            metadata["post_claim_resolution"] = dict(post_claim_resolution)
        metadata.update(self._claim_rewards_contract_metadata(blueprint))
        return metadata

    def _signal_contract_version(self, blueprint: TaskBlueprint) -> str:
        runtime_seam = blueprint.metadata.get("runtime_seam", {})
        if isinstance(runtime_seam, dict):
            value = str(runtime_seam.get("signal_contract_version", "")).strip()
            if value:
                return value
        product_display = blueprint.metadata.get("product_display", {})
        if isinstance(product_display, dict):
            display_metadata = product_display.get("metadata", {})
            if isinstance(display_metadata, dict):
                value = str(display_metadata.get("signal_contract_version", "")).strip()
                if value:
                    return value
        return str(blueprint.manifest.metadata.get("signal_contract_version", "")).strip()

    def _resolve_golden_asset(
        self,
        blueprint: TaskBlueprint,
        screen_slug: str,
        convention: GoldenScreenshotConvention,
        *,
        golden_sources: dict[str, _DiscoveredGoldenAsset] | None = None,
    ) -> dict[str, object]:
        configured_sources = blueprint.metadata.get("golden_asset_sources", {})
        configured_source = (
            dict(configured_sources.get(screen_slug, {}))
            if isinstance(configured_sources, dict) and isinstance(configured_sources.get(screen_slug), dict)
            else {}
        )
        discovered_golden_sources = golden_sources or self._discover_golden_catalog_assets()
        if configured_source:
            source_path = str(configured_source.get("source_path", ""))
            variant = str(
                configured_source.get(
                    "variant",
                    convention.required_variants[0] if convention.required_variants else "baseline",
                )
            )
            status = (
                TaskAssetStatus.PRESENT
                if source_path and self._repo_relative_path(source_path).exists()
                else TaskAssetStatus.MISSING
            )
            golden_source = discovered_golden_sources.get(source_path)
            return {
                "source": "golden_asset_sources",
                "source_path": source_path,
                "status": status,
                "variant": variant,
                "source_kind": golden_source.source_kind if golden_source is not None else "",
                "live_capture": golden_source.live_capture if golden_source is not None else None,
                "anchor_id": golden_source.anchor_id if golden_source is not None else "",
                "inspection_role": golden_source.inspection_role if golden_source is not None else "",
                "stage": golden_source.stage if golden_source is not None else "",
                "scene_id": golden_source.scene_id if golden_source is not None else "",
                "reference_id": golden_source.reference_id if golden_source is not None else "",
                "golden_id": golden_source.golden_id if golden_source is not None else "",
            }
        variant = convention.required_variants[0] if convention.required_variants else "baseline"
        return {
            "source": "golden_convention",
            "source_path": convention.render_path(
                pack_id=blueprint.pack_id,
                task_id=blueprint.task_id,
                screen_slug=screen_slug,
                variant=variant,
            ).as_posix(),
            "status": TaskAssetStatus.PLANNED,
            "variant": variant,
        }

    def _repo_relative_path(self, relative_path: str) -> Path:
        return self.repo_root.joinpath(*PurePosixPath(relative_path).parts)

    def _warning_requirements(
        self,
        *,
        task_id: str,
        asset_records: list[TaskAssetRecord],
        blocking_requirement_ids: set[str],
    ) -> list[TaskReadinessRequirement]:
        requirements: list[TaskReadinessRequirement] = []
        for record in asset_records:
            requirement_id = f"warning.{record.asset_id}"
            if record.asset_kind is TaskAssetKind.TEMPLATE and record.status is TaskAssetStatus.PLACEHOLDER:
                if "guild_check_in_button" in requirement_id and "asset.daily_ui.guild_check_in_button" in blocking_requirement_ids:
                    continue
                requirements.append(
                    TaskReadinessRequirement(
                        requirement_id=requirement_id,
                        domain=TaskGapDomain.ASSET,
                        summary="Template asset is still placeholder scaffolding.",
                        satisfied=False,
                        blocking=False,
                        details=f"asset_status={record.status.value} source_path={record.source_path}",
                    )
                )
            if self._requires_live_capture_followup(record):
                requirement_level = str(record.metadata.get("requirement_level", "required")).strip() or "required"
                requirements.append(
                    TaskReadinessRequirement(
                        requirement_id=f"{requirement_id}.provenance",
                        domain=TaskGapDomain.ASSET,
                        summary=(
                            "Supporting template asset still relies on curated stand-in provenance instead of an approved live capture."
                            if requirement_level == "supporting"
                            else "Template asset still relies on curated stand-in provenance instead of an approved live capture."
                        ),
                        satisfied=False,
                        blocking=False,
                        details=(
                            f"asset_status={record.status.value} "
                            f"requirement_level={requirement_level} "
                            f"provenance_kind={record.metadata.get('provenance_kind', '')} "
                            f"live_capture={str(record.metadata.get('live_capture', False)).lower()} "
                            f"replacement_target={record.metadata.get('replacement_target', '')} "
                            f"source_path={record.source_path}"
                        ),
                        metadata={
                            "anchor_id": str(record.metadata.get("anchor_id", "")),
                            "requirement_level": requirement_level,
                            "provenance_kind": str(record.metadata.get("provenance_kind", "")),
                            "live_capture": record.metadata.get("live_capture"),
                            "replacement_target": str(record.metadata.get("replacement_target", "")),
                        },
                    )
                )
            if record.asset_kind is TaskAssetKind.GOLDEN_SCREENSHOT and record.status is TaskAssetStatus.PLANNED:
                requirements.append(
                    TaskReadinessRequirement(
                        requirement_id=requirement_id,
                        domain=TaskGapDomain.ASSET,
                        summary="Golden screenshots are still planned and not curated yet.",
                        satisfied=False,
                        blocking=False,
                        details=f"asset_status={record.status.value} source_path={record.source_path}",
                    )
                )
        return requirements

    def _derive_readiness_state(
        self,
        requirements: list[TaskReadinessRequirement],
    ) -> TaskReadinessState:
        for domain, state in (
            (TaskGapDomain.FOUNDATION, TaskReadinessState.BLOCKED_BY_FOUNDATION),
            (TaskGapDomain.ASSET, TaskReadinessState.BLOCKED_BY_ASSET),
            (TaskGapDomain.RUNTIME, TaskReadinessState.BLOCKED_BY_RUNTIME),
            (TaskGapDomain.CALIBRATION, TaskReadinessState.BLOCKED_BY_CALIBRATION),
        ):
            if any(item.blocking and not item.satisfied and item.domain is domain for item in requirements):
                return state
        return TaskReadinessState.READY

    def _template_asset_metadata(
        self,
        anchor_id: str,
        anchor_source: _DiscoveredTemplateAsset | None,
        *,
        requirement_level: str = "required",
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "anchor_id": anchor_id,
            "source": "template_manifest",
            "template_path": anchor_source.template_path if anchor_source is not None else "",
            "placeholder": anchor_source.placeholder if anchor_source is not None else False,
            "curation_status": anchor_source.curation_status if anchor_source is not None else "",
            "requirement_level": requirement_level,
        }
        if anchor_source is None:
            return metadata
        if anchor_source.provenance_kind:
            metadata["provenance_kind"] = anchor_source.provenance_kind
        if anchor_source.source_kind:
            metadata["source_kind"] = anchor_source.source_kind
        if anchor_source.live_capture is not None:
            metadata["live_capture"] = anchor_source.live_capture
        if anchor_source.replacement_target:
            metadata["replacement_target"] = anchor_source.replacement_target
        if anchor_source.inspection_role:
            metadata["inspection_role"] = anchor_source.inspection_role
        if anchor_source.stage:
            metadata["stage"] = anchor_source.stage
        return metadata

    def _golden_asset_metadata(
        self,
        case: Any,
        golden_asset: dict[str, object],
        *,
        requirement_level: str = "required",
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "variants": list(case.variants),
            "source": golden_asset["source"],
            "variant": golden_asset["variant"],
            "requirement_level": requirement_level,
        }
        for key in (
            "source_kind",
            "live_capture",
            "anchor_id",
            "inspection_role",
            "stage",
            "scene_id",
            "reference_id",
            "golden_id",
        ):
            value = golden_asset.get(key)
            if value not in ("", None):
                metadata[key] = value
        return metadata

    def _asset_provenance_summary(
        self,
        blueprint: TaskBlueprint,
        *,
        anchor_sources: dict[str, _DiscoveredTemplateAsset],
        golden_sources: dict[str, _DiscoveredGoldenAsset],
        convention: GoldenScreenshotConvention,
    ) -> dict[str, object]:
        template_provenance: dict[str, list[str]] = {}
        golden_provenance: dict[str, list[str]] = {}
        for anchor_id in self._tracked_anchor_ids(blueprint):
            anchor_source = anchor_sources.get(anchor_id)
            bucket = self._provenance_bucket(
                provenance_kind=anchor_source.provenance_kind if anchor_source is not None else "",
                source_kind=anchor_source.source_kind if anchor_source is not None else "",
                live_capture=anchor_source.live_capture if anchor_source is not None else None,
            )
            if bucket:
                template_provenance.setdefault(bucket, []).append(anchor_id)
        for case in blueprint.golden_cases:
            golden_asset = self._resolve_golden_asset(
                blueprint,
                case.screen_slug,
                convention,
                golden_sources=golden_sources,
            )
            bucket = self._provenance_bucket(
                source_kind=str(golden_asset.get("source_kind", "")),
                live_capture=self._optional_bool(golden_asset.get("live_capture")),
            )
            if bucket:
                golden_provenance.setdefault(bucket, []).append(case.screen_slug)
        if not template_provenance and not golden_provenance:
            return {}
        summary: dict[str, object] = {}
        if template_provenance:
            summary["template_anchor_provenance"] = {
                key: list(values) for key, values in sorted(template_provenance.items())
            }
        if golden_provenance:
            summary["golden_case_provenance"] = {
                key: list(values) for key, values in sorted(golden_provenance.items())
            }
        replacement_pending_anchor_ids = template_provenance.get("curated_stand_in", [])
        if replacement_pending_anchor_ids:
            summary["replacement_pending_anchor_ids"] = list(replacement_pending_anchor_ids)
        replacement_pending_golden_screen_slugs = golden_provenance.get("curated_stand_in", [])
        if replacement_pending_golden_screen_slugs:
            summary["replacement_pending_golden_screen_slugs"] = list(
                replacement_pending_golden_screen_slugs
            )
        asset_state = self._summarize_asset_state(template_provenance, golden_provenance)
        if asset_state:
            summary["asset_state"] = asset_state
        return summary

    def _tracked_anchor_ids(self, blueprint: TaskBlueprint) -> list[str]:
        tracked_anchor_ids: list[str] = []
        for anchor_id in [*blueprint.required_anchors, *self._supporting_anchor_ids(blueprint)]:
            normalized_anchor_id = str(anchor_id).strip()
            if normalized_anchor_id and normalized_anchor_id not in tracked_anchor_ids:
                tracked_anchor_ids.append(normalized_anchor_id)
        return tracked_anchor_ids

    def _supporting_anchor_ids(self, blueprint: TaskBlueprint) -> list[str]:
        raw_value = blueprint.metadata.get("supporting_anchor_ids", [])
        if not isinstance(raw_value, list):
            return []
        supporting_anchor_ids: list[str] = []
        for item in raw_value:
            anchor_id = str(item).strip()
            if anchor_id and anchor_id not in supporting_anchor_ids:
                supporting_anchor_ids.append(anchor_id)
        return supporting_anchor_ids

    def _supporting_golden_screen_slugs(self, blueprint: TaskBlueprint) -> list[str]:
        raw_value = blueprint.metadata.get("supporting_golden_screen_slugs", [])
        if not isinstance(raw_value, list):
            return []
        supporting_screen_slugs: list[str] = []
        for item in raw_value:
            screen_slug = str(item).strip()
            if screen_slug and screen_slug not in supporting_screen_slugs:
                supporting_screen_slugs.append(screen_slug)
        return supporting_screen_slugs

    def _anchor_requirement_level(self, blueprint: TaskBlueprint, anchor_id: str) -> str:
        if anchor_id in self._supporting_anchor_ids(blueprint):
            return "supporting"
        return "required"

    def _golden_requirement_level(self, blueprint: TaskBlueprint, screen_slug: str) -> str:
        if screen_slug in self._supporting_golden_screen_slugs(blueprint):
            return "supporting"
        return "required"

    def _claim_rewards_contract_metadata(self, blueprint: TaskBlueprint) -> dict[str, Any]:
        if blueprint.task_id != "daily_ui.claim_rewards":
            return {}
        metadata: dict[str, Any] = {}

        manifest_path = self.repo_root / "assets" / "templates" / "daily_ui" / "manifest.json"
        if manifest_path.exists():
            manifest_payload = loads(manifest_path.read_text(encoding="utf-8"))
            task_support = (
                manifest_payload.get("metadata", {})
                .get("task_support", {})
                .get(blueprint.task_id, {})
            )
            if isinstance(task_support, dict):
                live_capture_coverage = task_support.get("live_capture_coverage")
                if isinstance(live_capture_coverage, dict):
                    metadata["claim_rewards_live_capture_coverage"] = dict(live_capture_coverage)

        catalog_path = self.repo_root / "assets" / "templates" / "daily_ui" / "goldens" / "claim_rewards" / "catalog.json"
        if catalog_path.exists():
            catalog_payload = loads(catalog_path.read_text(encoding="utf-8"))
            catalog_metadata = catalog_payload.get("metadata", {})
            if isinstance(catalog_metadata, dict):
                capture_inventory = catalog_metadata.get("capture_inventory")
                if isinstance(capture_inventory, dict):
                    metadata["claim_rewards_capture_inventory"] = dict(capture_inventory)
            alternate_post_tap_capture_ids = [
                capture_id
                for capture_id in (
                    str(item.get("capture_id", "")).strip()
                    for item in catalog_payload.get("supporting_captures", [])
                    if isinstance(item, dict)
                    and str(item.get("evidence_role", "")).strip() == "alternate_post_tap_outcome"
                )
                if capture_id
            ]
            if alternate_post_tap_capture_ids:
                metadata["claim_rewards_alternate_post_tap_capture_ids"] = alternate_post_tap_capture_ids
        return metadata

    def _provenance_bucket(
        self,
        *,
        provenance_kind: str = "",
        source_kind: str = "",
        live_capture: bool | None = None,
    ) -> str:
        normalized_provenance_kind = provenance_kind.strip().lower()
        normalized_source_kind = source_kind.strip().lower()
        if live_capture is True or normalized_provenance_kind == "live_capture" or normalized_source_kind.startswith("live_"):
            return "live_capture"
        if normalized_provenance_kind == "curated_stand_in" or normalized_source_kind == "repo_curated_screenshot_style":
            return "curated_stand_in"
        return ""

    def _summarize_asset_state(
        self,
        template_provenance: dict[str, list[str]],
        golden_provenance: dict[str, list[str]],
    ) -> str:
        has_live_capture = bool(
            template_provenance.get("live_capture") or golden_provenance.get("live_capture")
        )
        has_curated_stand_in = bool(
            template_provenance.get("curated_stand_in") or golden_provenance.get("curated_stand_in")
        )
        if has_live_capture and has_curated_stand_in:
            return "mixed_live_capture_and_curated_stand_in"
        if has_live_capture:
            return "live_capture"
        if has_curated_stand_in:
            return "curated_stand_in"
        return ""

    def _requires_live_capture_followup(self, record: TaskAssetRecord) -> bool:
        if record.asset_kind is not TaskAssetKind.TEMPLATE:
            return False
        return (
            record.status is TaskAssetStatus.PRESENT
            and str(record.metadata.get("provenance_kind", "")).strip().lower() == "curated_stand_in"
            and record.metadata.get("live_capture") is False
            and bool(str(record.metadata.get("replacement_target", "")).strip())
        )

    def _optional_bool(self, value: object) -> bool | None:
        if isinstance(value, bool):
            return value
        return None
