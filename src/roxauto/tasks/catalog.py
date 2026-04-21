from __future__ import annotations

from dataclasses import dataclass
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
            metadata={"source": "task_foundations"},
        )

    def build_runtime_builder_inputs(self) -> list[TaskRuntimeBuilderInput]:
        return [self.build_runtime_builder_input(record.task_id) for record in self.load_inventory().records]

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

    def _inventory_record_by_task_id(self) -> dict[str, TaskInventoryRecord]:
        return {record.task_id: record for record in self.load_inventory().records}

    def _asset_records_by_task_id(self) -> dict[str, list[TaskAssetRecord]]:
        grouped: dict[str, list[TaskAssetRecord]] = {}
        for record in self.load_asset_inventory().records:
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
                "task_spec_builder=roxauto.tasks.daily_ui.claim_rewards.build_claim_rewards_task_spec"
            )
        return "Requirement is not yet satisfied by current task foundations."

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
