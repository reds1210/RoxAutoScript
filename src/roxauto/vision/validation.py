from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from json import JSONDecodeError, loads
from pathlib import Path
from re import compile
from typing import Any, Self

from roxauto.core.serde import to_primitive
from roxauto.vision.models import (
    AnchorAssetProvenanceKind,
    AnchorCurationProfile,
    AnchorCurationStatus,
)
from roxauto.vision.repository import AnchorRepository

_ASSET_NAME_PATTERN = compile(r"^[a-z0-9_]+$")


class TemplateValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class TemplateReadinessStatus(str, Enum):
    READY = "ready"
    PLACEHOLDER = "placeholder"
    MISSING = "missing"
    INVALID = "invalid"


@dataclass(slots=True)
class TemplateValidationIssue:
    code: str
    severity: TemplateValidationSeverity
    message: str
    anchor_id: str = ""
    path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_severity = data.get("severity", TemplateValidationSeverity.ERROR.value)
        if isinstance(raw_severity, TemplateValidationSeverity):
            severity = raw_severity
        else:
            severity = TemplateValidationSeverity(str(raw_severity))
        return cls(
            code=str(data.get("code", "")),
            severity=severity,
            message=str(data.get("message", "")),
            anchor_id=str(data.get("anchor_id", "")),
            path=str(data.get("path", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class TemplateRepositoryValidationReport:
    repository_root: str
    repository_id: str = ""
    display_name: str = ""
    anchor_count: int = 0
    issues: list[TemplateValidationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == TemplateValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == TemplateValidationSeverity.WARNING)

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            repository_root=str(data.get("repository_root", "")),
            repository_id=str(data.get("repository_id", "")),
            display_name=str(data.get("display_name", "")),
            anchor_count=int(data.get("anchor_count", 0)),
            issues=[TemplateValidationIssue.from_dict(entry) for entry in data.get("issues", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class TemplateWorkspaceValidationReport:
    templates_root: str
    reports: list[TemplateRepositoryValidationReport] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def repository_count(self) -> int:
        return len(self.reports)

    @property
    def error_count(self) -> int:
        return sum(report.error_count for report in self.reports)

    @property
    def warning_count(self) -> int:
        return sum(report.warning_count for report in self.reports)

    @property
    def valid_repository_ids(self) -> list[str]:
        return [
            report.repository_id
            for report in self.reports
            if report.repository_id and report.is_valid
        ]

    @property
    def invalid_repository_ids(self) -> list[str]:
        return [
            report.repository_id or Path(report.repository_root).name
            for report in self.reports
            if not report.is_valid
        ]

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            templates_root=str(data.get("templates_root", "")),
            reports=[
                TemplateRepositoryValidationReport.from_dict(entry)
                for entry in data.get("reports", [])
            ],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class TemplateDependencyReadiness:
    asset_id: str
    task_id: str
    pack_id: str
    anchor_id: str
    inventory_status: str
    readiness_status: TemplateReadinessStatus
    repository_present: bool = False
    anchor_present: bool = False
    asset_exists: bool = False
    source_path: str = ""
    resolved_template_path: str = ""
    inventory_mismatch: bool = False
    curation_status: AnchorCurationStatus | None = None
    curation_reference_count: int = 0
    provenance_kind: AnchorAssetProvenanceKind | None = None
    provenance_summary: str = ""
    curation_summary: str = ""
    failure_case: str = ""
    issue_codes: list[str] = field(default_factory=list)
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_status = data.get("readiness_status", TemplateReadinessStatus.MISSING.value)
        if isinstance(raw_status, TemplateReadinessStatus):
            readiness_status = raw_status
        else:
            readiness_status = TemplateReadinessStatus(str(raw_status))
        raw_curation_status = data.get("curation_status")
        if isinstance(raw_curation_status, AnchorCurationStatus):
            curation_status = raw_curation_status
        elif raw_curation_status:
            curation_status = AnchorCurationStatus(str(raw_curation_status))
        else:
            curation_status = None
        raw_provenance_kind = data.get("provenance_kind")
        if isinstance(raw_provenance_kind, AnchorAssetProvenanceKind):
            provenance_kind = raw_provenance_kind
        elif raw_provenance_kind:
            provenance_kind = AnchorAssetProvenanceKind(str(raw_provenance_kind))
        else:
            provenance_kind = None
        return cls(
            asset_id=str(data.get("asset_id", "")),
            task_id=str(data.get("task_id", "")),
            pack_id=str(data.get("pack_id", "")),
            anchor_id=str(data.get("anchor_id", "")),
            inventory_status=str(data.get("inventory_status", "")),
            readiness_status=readiness_status,
            repository_present=bool(data.get("repository_present", False)),
            anchor_present=bool(data.get("anchor_present", False)),
            asset_exists=bool(data.get("asset_exists", False)),
            source_path=str(data.get("source_path", "")),
            resolved_template_path=str(data.get("resolved_template_path", "")),
            inventory_mismatch=bool(data.get("inventory_mismatch", False)),
            curation_status=curation_status,
            curation_reference_count=int(data.get("curation_reference_count", 0)),
            provenance_kind=provenance_kind,
            provenance_summary=str(data.get("provenance_summary", "")),
            curation_summary=str(data.get("curation_summary", "")),
            failure_case=str(data.get("failure_case", "")),
            issue_codes=[str(code) for code in data.get("issue_codes", [])],
            message=str(data.get("message", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class VisionWorkspaceReadinessReport:
    templates_root: str
    asset_inventory_path: str = ""
    validation_report: TemplateWorkspaceValidationReport | None = None
    template_dependencies: list[TemplateDependencyReadiness] = field(default_factory=list)
    non_template_record_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def template_dependency_count(self) -> int:
        return len(self.template_dependencies)

    @property
    def ready_count(self) -> int:
        return sum(
            1
            for dependency in self.template_dependencies
            if dependency.readiness_status == TemplateReadinessStatus.READY
        )

    @property
    def placeholder_count(self) -> int:
        return sum(
            1
            for dependency in self.template_dependencies
            if dependency.readiness_status == TemplateReadinessStatus.PLACEHOLDER
        )

    @property
    def missing_count(self) -> int:
        return sum(
            1
            for dependency in self.template_dependencies
            if dependency.readiness_status == TemplateReadinessStatus.MISSING
        )

    @property
    def invalid_count(self) -> int:
        return sum(
            1
            for dependency in self.template_dependencies
            if dependency.readiness_status == TemplateReadinessStatus.INVALID
        )

    @property
    def inventory_mismatch_count(self) -> int:
        return sum(1 for dependency in self.template_dependencies if dependency.inventory_mismatch)

    @property
    def blocking_count(self) -> int:
        return self.missing_count + self.invalid_count

    @property
    def missing_anchor_ids(self) -> list[str]:
        return [
            dependency.anchor_id
            for dependency in self.template_dependencies
            if dependency.readiness_status == TemplateReadinessStatus.MISSING
        ]

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_validation_report = data.get("validation_report")
        if isinstance(raw_validation_report, TemplateWorkspaceValidationReport):
            validation_report = raw_validation_report
        elif isinstance(raw_validation_report, dict):
            validation_report = TemplateWorkspaceValidationReport.from_dict(raw_validation_report)
        else:
            validation_report = None
        return cls(
            templates_root=str(data.get("templates_root", "")),
            asset_inventory_path=str(data.get("asset_inventory_path", "")),
            validation_report=validation_report,
            template_dependencies=[
                TemplateDependencyReadiness.from_dict(entry)
                for entry in data.get("template_dependencies", [])
            ],
            non_template_record_count=int(data.get("non_template_record_count", 0)),
            metadata=dict(data.get("metadata", {})),
        )


def validate_template_repository(
    repository: AnchorRepository,
) -> TemplateRepositoryValidationReport:
    issues: list[TemplateValidationIssue] = []
    manifest = repository.manifest
    repository_root = repository.root.resolve()

    if not manifest.repository_id:
        issues.append(
            TemplateValidationIssue(
                code="empty_repository_id",
                severity=TemplateValidationSeverity.ERROR,
                message="Template repository manifest must define repository_id.",
                path=str(repository.root / "manifest.json"),
            )
        )
    if not manifest.display_name:
        issues.append(
            TemplateValidationIssue(
                code="empty_display_name",
                severity=TemplateValidationSeverity.ERROR,
                message="Template repository manifest must define display_name.",
                path=str(repository.root / "manifest.json"),
            )
        )
    if not manifest.version:
        issues.append(
            TemplateValidationIssue(
                code="empty_version",
                severity=TemplateValidationSeverity.ERROR,
                message="Template repository manifest must define version.",
                path=str(repository.root / "manifest.json"),
            )
        )

    anchors = manifest.anchors
    if not anchors:
        issues.append(
            TemplateValidationIssue(
                code="empty_anchor_list",
                severity=TemplateValidationSeverity.WARNING,
                message="Template repository contains no anchors.",
                path=str(repository.root / "manifest.json"),
            )
        )

    seen_anchor_ids: set[str] = set()
    for anchor in anchors:
        if not anchor.anchor_id:
            issues.append(
                TemplateValidationIssue(
                    code="empty_anchor_id",
                    severity=TemplateValidationSeverity.ERROR,
                    message="Anchor definitions must include anchor_id.",
                    path=str(repository.root / "manifest.json"),
                )
            )
        elif anchor.anchor_id in seen_anchor_ids:
            issues.append(
                TemplateValidationIssue(
                    code="duplicate_anchor_id",
                    severity=TemplateValidationSeverity.ERROR,
                    message=f"Anchor id '{anchor.anchor_id}' is duplicated in one repository.",
                    anchor_id=anchor.anchor_id,
                    path=str(repository.root / "manifest.json"),
                )
            )
        else:
            seen_anchor_ids.add(anchor.anchor_id)

        if manifest.repository_id and anchor.anchor_id and not anchor.anchor_id.startswith(
            f"{manifest.repository_id}."
        ):
            issues.append(
                TemplateValidationIssue(
                    code="anchor_id_prefix_mismatch",
                    severity=TemplateValidationSeverity.WARNING,
                    message=(
                        f"Anchor id '{anchor.anchor_id}' should usually start with "
                        f"'{manifest.repository_id}.' to stay grouped by repository."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.root / "manifest.json"),
                )
            )

        if not anchor.label:
            issues.append(
                TemplateValidationIssue(
                    code="missing_anchor_label",
                    severity=TemplateValidationSeverity.ERROR,
                    message=f"Anchor '{anchor.anchor_id or '<unknown>'}' must define a label.",
                    anchor_id=anchor.anchor_id,
                    path=str(repository.root / "manifest.json"),
                )
            )

        if not 0.0 < anchor.confidence_threshold <= 1.0:
            issues.append(
                TemplateValidationIssue(
                    code="invalid_confidence_threshold",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id or '<unknown>'}' must keep "
                        "confidence_threshold within (0.0, 1.0]."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.root / "manifest.json"),
                    metadata={"confidence_threshold": anchor.confidence_threshold},
                )
            )

        if anchor.match_region is not None:
            _, _, width, height = anchor.match_region
            if width <= 0 or height <= 0:
                issues.append(
                    TemplateValidationIssue(
                        code="invalid_match_region",
                        severity=TemplateValidationSeverity.ERROR,
                        message=(
                            f"Anchor '{anchor.anchor_id or '<unknown>'}' must use "
                            "positive width and height in match_region."
                        ),
                        anchor_id=anchor.anchor_id,
                        path=str(repository.root / "manifest.json"),
                        metadata={"match_region": anchor.match_region},
                    )
                )

        issues.extend(_validate_template_path(repository_root, anchor.anchor_id, anchor.template_path))
        issues.extend(_validate_anchor_curation(repository, anchor))

    issues.extend(_validate_claim_rewards_golden_catalog(repository))
    issues.extend(_validate_task_support_contract(repository))

    return TemplateRepositoryValidationReport(
        repository_root=str(repository.root),
        repository_id=manifest.repository_id,
        display_name=manifest.display_name,
        anchor_count=len(anchors),
        issues=issues,
        metadata={"manifest_path": str(repository.root / "manifest.json")},
    )


def validate_template_workspace(
    templates_root: Path | str,
) -> TemplateWorkspaceValidationReport:
    root = Path(templates_root)
    reports: list[TemplateRepositoryValidationReport] = []

    if not root.exists() or not root.is_dir():
        return TemplateWorkspaceValidationReport(
            templates_root=str(root),
            reports=[],
            metadata={
                "templates_root_exists": root.exists(),
                "templates_root_is_dir": root.is_dir(),
            },
        )

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue

        manifest_path = child / "manifest.json"
        if not manifest_path.exists():
            reports.append(
                TemplateRepositoryValidationReport(
                    repository_root=str(child),
                    repository_id=child.name,
                    issues=[
                        TemplateValidationIssue(
                            code="missing_manifest",
                            severity=TemplateValidationSeverity.ERROR,
                            message="Template repository directory is missing manifest.json.",
                            path=str(manifest_path),
                        )
                    ],
                    metadata={"manifest_path": str(manifest_path)},
                )
            )
            continue

        try:
            repository = AnchorRepository.load(child)
        except JSONDecodeError as exc:
            reports.append(
                TemplateRepositoryValidationReport(
                    repository_root=str(child),
                    repository_id=child.name,
                    issues=[
                        TemplateValidationIssue(
                            code="invalid_manifest_json",
                            severity=TemplateValidationSeverity.ERROR,
                            message=f"manifest.json could not be parsed: {exc.msg}",
                            path=str(manifest_path),
                        )
                    ],
                    metadata={"manifest_path": str(manifest_path)},
                )
            )
            continue

        reports.append(validate_template_repository(repository))

    return TemplateWorkspaceValidationReport(
        templates_root=str(root),
        reports=reports,
        metadata={
            "templates_root_exists": root.exists(),
            "templates_root_is_dir": root.is_dir(),
        },
    )


def build_vision_workspace_readiness_report(
    templates_root: Path | str,
    asset_inventory_path: Path | str,
) -> VisionWorkspaceReadinessReport:
    templates_root_path = Path(templates_root)
    inventory_path = Path(asset_inventory_path)
    validation_report = validate_template_workspace(templates_root_path)
    repositories_by_id = {
        repository.repository_id: repository
        for repository in AnchorRepository.discover(templates_root_path)
    }
    validation_by_id = {
        report.repository_id or Path(report.repository_root).name: report
        for report in validation_report.reports
    }
    anchor_issue_codes = _build_anchor_issue_code_map(validation_report)

    if not inventory_path.exists() or not inventory_path.is_file():
        return VisionWorkspaceReadinessReport(
            templates_root=str(templates_root_path),
            asset_inventory_path=str(inventory_path),
            validation_report=validation_report,
            metadata={
                "asset_inventory_exists": inventory_path.exists(),
                "asset_inventory_is_file": inventory_path.is_file(),
            },
        )

    document = loads(inventory_path.read_text(encoding="utf-8"))
    template_dependencies: list[TemplateDependencyReadiness] = []
    non_template_record_count = 0

    for record in document.get("records", []):
        asset_kind = str(record.get("asset_kind", ""))
        if asset_kind != "template":
            non_template_record_count += 1
            continue

        pack_id = str(record.get("pack_id", ""))
        task_id = str(record.get("task_id", ""))
        asset_id = str(record.get("asset_id", ""))
        inventory_status = str(record.get("status", ""))
        source_path = str(record.get("source_path", ""))
        metadata = dict(record.get("metadata", {}))
        anchor_id = str(metadata.get("anchor_id", ""))
        repository = repositories_by_id.get(pack_id)
        validation_entry = validation_by_id.get(pack_id)

        repository_present = repository is not None or validation_entry is not None
        anchor_present = bool(repository is not None and anchor_id and repository.has_anchor(anchor_id))
        issue_codes = list(anchor_issue_codes.get(anchor_id, []))
        resolved_template_path = ""
        asset_exists = False
        curation = None

        if repository is not None and anchor_present:
            anchor = repository.get_anchor(anchor_id)
            resolved_template_path = str(repository.resolve_asset_path(anchor_id))
            asset_exists = Path(resolved_template_path).exists()
            metadata.setdefault("placeholder", bool(anchor.metadata.get("placeholder", False)))
            curation = repository.get_anchor_curation(anchor_id)

        readiness_status, message = _resolve_template_readiness_status(
            repository_present=repository_present,
            anchor_present=anchor_present,
            asset_exists=asset_exists,
            inventory_status=inventory_status,
            issue_codes=issue_codes,
            placeholder=bool(metadata.get("placeholder", False)),
            curation_status=curation.status if curation is not None else None,
            provenance_kind=curation.provenance_kind if curation is not None else None,
        )

        expected_source_path = ""
        if anchor_id and repository_present:
            expected_source_path = f"assets/templates/{pack_id}/manifest.json#{anchor_id}"
        inventory_mismatch = bool(expected_source_path and source_path != expected_source_path)
        if inventory_status == "missing" and anchor_present and asset_exists:
            inventory_mismatch = True
        if (
            curation is not None
            and curation.status == AnchorCurationStatus.CURATED
            and inventory_status == "placeholder"
        ):
            inventory_mismatch = True

        template_dependencies.append(
            TemplateDependencyReadiness(
                asset_id=asset_id,
                task_id=task_id,
                pack_id=pack_id,
                anchor_id=anchor_id,
                inventory_status=inventory_status,
                readiness_status=readiness_status,
                repository_present=repository_present,
                anchor_present=anchor_present,
                asset_exists=asset_exists,
                source_path=source_path,
                resolved_template_path=resolved_template_path,
                inventory_mismatch=inventory_mismatch,
                curation_status=curation.status if curation is not None else None,
                curation_reference_count=curation.reference_count if curation is not None else 0,
                provenance_kind=curation.provenance_kind if curation is not None else None,
                provenance_summary=_provenance_summary(curation),
                curation_summary=_curation_summary(curation),
                failure_case=_failure_case(curation),
                issue_codes=issue_codes,
                message=message,
                metadata={
                    **metadata,
                    "expected_source_path": expected_source_path,
                },
            )
        )

    return VisionWorkspaceReadinessReport(
        templates_root=str(templates_root_path),
        asset_inventory_path=str(inventory_path),
        validation_report=validation_report,
        template_dependencies=template_dependencies,
        non_template_record_count=non_template_record_count,
        metadata={
            "asset_inventory_exists": inventory_path.exists(),
            "asset_inventory_is_file": inventory_path.is_file(),
            "inventory_id": str(document.get("inventory_id", "")),
            "inventory_version": str(document.get("version", "")),
            "claim_rewards_live_capture_coverage": _claim_rewards_live_capture_coverage(repositories_by_id.get("daily_ui")),
        },
    )


def _validate_anchor_curation(
    repository: AnchorRepository,
    anchor: Any,
) -> list[TemplateValidationIssue]:
    metadata = dict(anchor.metadata)
    curation = AnchorCurationProfile.from_metadata(metadata)
    task_ids = set(_anchor_task_ids(metadata))
    if "daily_ui.claim_rewards" not in task_ids and curation is None:
        return []

    issues: list[TemplateValidationIssue] = []
    if "daily_ui.claim_rewards" in task_ids and curation is None:
        issues.append(
            TemplateValidationIssue(
                code="missing_anchor_curation_metadata",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor.anchor_id}' must define metadata.curation for "
                    "'daily_ui.claim_rewards' template curation."
                ),
                anchor_id=anchor.anchor_id,
                path=str(repository.manifest_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        )
        return issues

    if curation is None:
        return issues

    for field_name in ("intent_id", "scene_id", "variant_id"):
        if getattr(curation, field_name):
            continue
        issues.append(
            TemplateValidationIssue(
                code="missing_anchor_curation_field",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor.anchor_id}' must define metadata.curation.{field_name} "
                    "for deterministic curation tracking."
                ),
                anchor_id=anchor.anchor_id,
                path=str(repository.manifest_path),
                metadata={"field": field_name},
            )
        )

    if "daily_ui.claim_rewards" in task_ids and curation.provenance is None:
        issues.append(
            TemplateValidationIssue(
                code="missing_anchor_curation_provenance",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor.anchor_id}' must define metadata.curation.provenance "
                    "so readiness can distinguish live captures from curated stand-ins."
                ),
                anchor_id=anchor.anchor_id,
                path=str(repository.manifest_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        )

    if "daily_ui.claim_rewards" in task_ids:
        failure_case = str(curation.metadata.get("failure_case", "")).strip()
        if not failure_case:
            issues.append(
                TemplateValidationIssue(
                    code="missing_anchor_failure_case",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' must define metadata.curation.metadata.failure_case "
                        "so claim-rewards diagnostics can stay machine-readable."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.manifest_path),
                    metadata={"task_id": "daily_ui.claim_rewards"},
                )
            )

    if curation.status == AnchorCurationStatus.CURATED:
        if bool(metadata.get("placeholder", False)):
            issues.append(
                TemplateValidationIssue(
                    code="curated_anchor_marked_placeholder",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' cannot stay marked as placeholder "
                        "after curation status becomes curated."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.manifest_path),
                )
            )
        if curation.reference_count == 0:
            issues.append(
                TemplateValidationIssue(
                    code="curated_anchor_missing_references",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' must include at least one "
                        "metadata.curation.references entry once curated."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.manifest_path),
                )
            )
        if Path(anchor.template_path).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            issues.append(
                TemplateValidationIssue(
                    code="curated_anchor_requires_raster_template",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' must use a raster template asset "
                        "when curation status is curated."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=anchor.template_path,
                )
            )
        if curation.provenance_kind == AnchorAssetProvenanceKind.PLACEHOLDER:
            issues.append(
                TemplateValidationIssue(
                    code="curated_anchor_invalid_provenance",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' cannot keep placeholder provenance "
                        "after curation status becomes curated."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.manifest_path),
                )
            )
    elif not bool(metadata.get("placeholder", False)):
        issues.append(
            TemplateValidationIssue(
                code="non_curated_anchor_missing_placeholder_flag",
                severity=TemplateValidationSeverity.WARNING,
                message=(
                    f"Anchor '{anchor.anchor_id}' is not curated yet and should keep "
                    "metadata.placeholder=true until live captures are promoted."
                ),
                anchor_id=anchor.anchor_id,
                path=str(repository.manifest_path),
            )
        )

    for reference in curation.references:
        issues.extend(_validate_curation_reference_path(repository.root.resolve(), anchor.anchor_id, reference))

    return issues


def _validate_claim_rewards_golden_catalog(
    repository: AnchorRepository,
) -> list[TemplateValidationIssue]:
    task_support = repository.get_task_support("daily_ui.claim_rewards")
    if not task_support:
        return []

    catalog_path_value = str(task_support.get("golden_catalog_path", "")).strip()
    if not catalog_path_value:
        return [
            TemplateValidationIssue(
                code="missing_claim_rewards_golden_catalog_path",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    "Task support for 'daily_ui.claim_rewards' must define "
                    "metadata.task_support[task_id].golden_catalog_path."
                ),
                path=str(repository.manifest_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        ]

    catalog_path = Path(catalog_path_value)
    if catalog_path.is_absolute() or ".." in catalog_path.parts:
        return [
            TemplateValidationIssue(
                code="invalid_claim_rewards_golden_catalog_path",
                severity=TemplateValidationSeverity.ERROR,
                message="Claim-rewards golden catalog path must stay relative to the repository root.",
                path=catalog_path_value,
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        ]

    resolved_catalog_path = (repository.root.resolve() / catalog_path).resolve()
    try:
        resolved_catalog_path.relative_to(repository.root.resolve())
    except ValueError:
        return [
            TemplateValidationIssue(
                code="invalid_claim_rewards_golden_catalog_path",
                severity=TemplateValidationSeverity.ERROR,
                message="Claim-rewards golden catalog path cannot resolve outside the repository root.",
                path=str(resolved_catalog_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        ]

    if not resolved_catalog_path.exists():
        return [
            TemplateValidationIssue(
                code="missing_claim_rewards_golden_catalog",
                severity=TemplateValidationSeverity.ERROR,
                message="Claim-rewards golden catalog file is missing.",
                path=str(resolved_catalog_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        ]

    try:
        catalog = loads(resolved_catalog_path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        return [
            TemplateValidationIssue(
                code="invalid_claim_rewards_golden_catalog_json",
                severity=TemplateValidationSeverity.ERROR,
                message=f"Claim-rewards golden catalog could not be parsed: {exc.msg}",
                path=str(resolved_catalog_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        ]

    golden_entries = catalog.get("goldens", [])
    if not isinstance(golden_entries, list):
        return [
            TemplateValidationIssue(
                code="invalid_claim_rewards_golden_catalog_entries",
                severity=TemplateValidationSeverity.ERROR,
                message="Claim-rewards golden catalog must define a 'goldens' list.",
                path=str(resolved_catalog_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        ]

    goldens_by_id: dict[str, dict[str, Any]] = {}
    issues: list[TemplateValidationIssue] = []
    for entry in golden_entries:
        if not isinstance(entry, dict):
            issues.append(
                TemplateValidationIssue(
                    code="invalid_claim_rewards_golden_catalog_entry",
                    severity=TemplateValidationSeverity.ERROR,
                    message="Claim-rewards golden catalog entries must be objects.",
                    path=str(resolved_catalog_path),
                    metadata={"task_id": "daily_ui.claim_rewards"},
                )
            )
            continue
        golden_id = str(entry.get("golden_id", "")).strip()
        if not golden_id:
            issues.append(
                TemplateValidationIssue(
                    code="missing_claim_rewards_golden_id",
                    severity=TemplateValidationSeverity.ERROR,
                    message="Each claim-rewards golden catalog entry must define golden_id.",
                    path=str(resolved_catalog_path),
                    metadata={"task_id": "daily_ui.claim_rewards"},
                )
            )
            continue
        goldens_by_id[golden_id] = entry

    for anchor in repository.list_anchors():
        metadata = dict(anchor.metadata)
        if "daily_ui.claim_rewards" not in _anchor_task_ids(metadata):
            continue
        curation = AnchorCurationProfile.from_metadata(metadata)
        curation_metadata = dict(curation.metadata) if curation is not None else {}
        golden_id = str(curation_metadata.get("golden_id", "")).strip()
        anchor_catalog_path = str(curation_metadata.get("golden_catalog_path", "")).strip()
        primary_reference_id = ""
        primary_reference_file_name = ""
        if curation is not None and curation.references:
            primary_reference_id = curation.references[0].reference_id
            primary_reference_file_name = Path(curation.references[0].image_path).name

        if not golden_id:
            issues.append(
                TemplateValidationIssue(
                    code="missing_anchor_golden_id",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' must define metadata.curation.metadata.golden_id "
                        "for claim-rewards golden traceability."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.manifest_path),
                )
            )
            continue

        if anchor_catalog_path != catalog_path_value:
            issues.append(
                TemplateValidationIssue(
                    code="anchor_golden_catalog_path_mismatch",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' golden catalog path does not match the "
                        "task-support golden_catalog_path."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(repository.manifest_path),
                    metadata={"expected": catalog_path_value, "actual": anchor_catalog_path},
                )
            )

        catalog_entry = goldens_by_id.get(golden_id)
        if catalog_entry is None:
            issues.append(
                TemplateValidationIssue(
                    code="missing_anchor_golden_catalog_entry",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor.anchor_id}' points at golden_id '{golden_id}', "
                        "but that entry is missing from the claim-rewards golden catalog."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(resolved_catalog_path),
                )
            )
            continue

        if str(catalog_entry.get("anchor_id", "")) != anchor.anchor_id:
            issues.append(
                TemplateValidationIssue(
                    code="anchor_golden_catalog_anchor_mismatch",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Golden catalog entry '{golden_id}' does not point back to "
                        f"anchor '{anchor.anchor_id}'."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(resolved_catalog_path),
                )
            )

        if primary_reference_id and str(catalog_entry.get("reference_id", "")) != primary_reference_id:
            issues.append(
                TemplateValidationIssue(
                    code="anchor_golden_catalog_reference_mismatch",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Golden catalog entry '{golden_id}' does not match the primary "
                        f"reference id for anchor '{anchor.anchor_id}'."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(resolved_catalog_path),
                )
            )

        if primary_reference_file_name and str(catalog_entry.get("file_name", "")) != primary_reference_file_name:
            issues.append(
                TemplateValidationIssue(
                    code="anchor_golden_catalog_file_mismatch",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Golden catalog entry '{golden_id}' does not match the primary "
                        f"reference file for anchor '{anchor.anchor_id}'."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(resolved_catalog_path),
                )
            )

        catalog_live_capture = bool(catalog_entry.get("live_capture", False))
        expected_live_capture = curation is not None and curation.provenance_kind == AnchorAssetProvenanceKind.LIVE_CAPTURE
        if catalog_live_capture != expected_live_capture:
            issues.append(
                TemplateValidationIssue(
                    code="anchor_golden_catalog_live_capture_mismatch",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Golden catalog entry '{golden_id}' live-capture flag does not match "
                        f"the curation provenance for anchor '{anchor.anchor_id}'."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(resolved_catalog_path),
                    metadata={
                        "catalog_live_capture": catalog_live_capture,
                        "expected_live_capture": expected_live_capture,
                    },
                )
            )

        source_kind = str(curation_metadata.get("source_kind", "")).strip()
        if source_kind and str(catalog_entry.get("source_kind", "")).strip() != source_kind:
            issues.append(
                TemplateValidationIssue(
                    code="anchor_golden_catalog_source_kind_mismatch",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Golden catalog entry '{golden_id}' source_kind does not match "
                        f"the curation metadata for anchor '{anchor.anchor_id}'."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(resolved_catalog_path),
                )
            )

        failure_case = str(curation_metadata.get("failure_case", "")).strip()
        catalog_failure_case = str(catalog_entry.get("failure_case", "")).strip()
        if failure_case and catalog_failure_case != failure_case:
            issues.append(
                TemplateValidationIssue(
                    code="anchor_golden_catalog_failure_case_mismatch",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Golden catalog entry '{golden_id}' failure_case does not match "
                        f"the curation metadata for anchor '{anchor.anchor_id}'."
                    ),
                    anchor_id=anchor.anchor_id,
                    path=str(resolved_catalog_path),
                )
            )

    return issues


def _validate_curation_reference_path(
    repository_root: Path,
    anchor_id: str,
    reference: Any,
) -> list[TemplateValidationIssue]:
    issues: list[TemplateValidationIssue] = []
    reference_id = str(getattr(reference, "reference_id", "") or "")
    image_path = str(getattr(reference, "image_path", "") or "")
    if not image_path:
        issues.append(
            TemplateValidationIssue(
                code="empty_curation_reference_path",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id}' has a curation reference"
                    + (f" '{reference_id}'" if reference_id else "")
                    + " without image_path."
                ),
                anchor_id=anchor_id,
            )
        )
        return issues

    candidate_path = Path(image_path)
    if candidate_path.is_absolute():
        issues.append(
            TemplateValidationIssue(
                code="absolute_curation_reference_path",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id}' must keep curation reference paths "
                    "relative to the repository root."
                ),
                anchor_id=anchor_id,
                path=image_path,
            )
        )
        return issues

    if ".." in candidate_path.parts:
        issues.append(
            TemplateValidationIssue(
                code="curation_reference_path_outside_repository",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id}' cannot resolve a curation reference "
                    "outside the repository root."
                ),
                anchor_id=anchor_id,
                path=image_path,
            )
        )
        return issues

    resolved_path = (repository_root / candidate_path).resolve()
    try:
        resolved_path.relative_to(repository_root)
    except ValueError:
        issues.append(
            TemplateValidationIssue(
                code="curation_reference_path_outside_repository",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id}' cannot resolve a curation reference "
                    "outside the repository root."
                ),
                anchor_id=anchor_id,
                path=str(resolved_path),
            )
        )
        return issues

    if not resolved_path.exists():
        issues.append(
            TemplateValidationIssue(
                code="missing_curation_reference_asset",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id}' points to a missing curation reference image."
                ),
                anchor_id=anchor_id,
                path=str(resolved_path),
            )
        )

    return issues


def _validate_template_path(
    repository_root: Path,
    anchor_id: str,
    template_path: str,
) -> list[TemplateValidationIssue]:
    issues: list[TemplateValidationIssue] = []
    candidate_path = Path(template_path)

    if not template_path:
        issues.append(
            TemplateValidationIssue(
                code="empty_template_path",
                severity=TemplateValidationSeverity.ERROR,
                message=f"Anchor '{anchor_id or '<unknown>'}' must define template_path.",
                anchor_id=anchor_id,
            )
        )
        return issues

    if candidate_path.is_absolute():
        issues.append(
            TemplateValidationIssue(
                code="absolute_template_path",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id or '<unknown>'}' must keep template_path "
                    "relative to the repository root."
                ),
                anchor_id=anchor_id,
                path=template_path,
            )
        )
        return issues

    if ".." in candidate_path.parts:
        issues.append(
            TemplateValidationIssue(
                code="template_path_outside_repository",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id or '<unknown>'}' cannot traverse outside "
                    "the repository root."
                ),
                anchor_id=anchor_id,
                path=template_path,
            )
        )
        return issues

    file_name = candidate_path.name
    stem = candidate_path.stem
    suffix = candidate_path.suffix
    if (
        file_name != file_name.lower()
        or not stem
        or not _ASSET_NAME_PATTERN.fullmatch(stem)
        or (suffix and suffix != suffix.lower())
    ):
        issues.append(
            TemplateValidationIssue(
                code="invalid_template_asset_name",
                severity=TemplateValidationSeverity.WARNING,
                message=(
                    f"Anchor '{anchor_id or '<unknown>'}' should use lowercase file "
                    "names with underscores only."
                ),
                anchor_id=anchor_id,
                path=template_path,
            )
        )

    resolved_path = (repository_root / candidate_path).resolve()
    try:
        resolved_path.relative_to(repository_root)
    except ValueError:
        issues.append(
            TemplateValidationIssue(
                code="template_path_outside_repository",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    f"Anchor '{anchor_id or '<unknown>'}' cannot resolve outside "
                    "the repository root."
                ),
                anchor_id=anchor_id,
                path=str(resolved_path),
            )
        )
        return issues

    if not resolved_path.exists():
        issues.append(
            TemplateValidationIssue(
                code="missing_template_asset",
                severity=TemplateValidationSeverity.ERROR,
                message=f"Anchor '{anchor_id or '<unknown>'}' points to a missing asset file.",
                anchor_id=anchor_id,
                path=str(resolved_path),
            )
        )

    return issues


def _build_anchor_issue_code_map(
    validation_report: TemplateWorkspaceValidationReport,
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for repository_report in validation_report.reports:
        for issue in repository_report.issues:
            if not issue.anchor_id or issue.severity != TemplateValidationSeverity.ERROR:
                continue
            result.setdefault(issue.anchor_id, []).append(issue.code)
    return result


def _validate_task_support_contract(
    repository: AnchorRepository,
) -> list[TemplateValidationIssue]:
    manifest = repository.manifest
    task_support = manifest.metadata.get("task_support", {})
    if not isinstance(task_support, dict):
        return []

    anchor_roles: dict[str, dict[str, list[str]]] = {}
    anchors_missing_roles: dict[str, list[str]] = {}
    for anchor in manifest.anchors:
        anchor_metadata = dict(anchor.metadata)
        task_ids = _anchor_task_ids(anchor_metadata)
        role = str(anchor_metadata.get("inspection_role", "")).strip()
        for task_id in task_ids:
            role_map = anchor_roles.setdefault(task_id, {})
            if role:
                role_map.setdefault(role, []).append(anchor.anchor_id)
            else:
                anchors_missing_roles.setdefault(task_id, []).append(anchor.anchor_id)

    issues: list[TemplateValidationIssue] = []
    for task_id, support in task_support.items():
        if not isinstance(support, dict):
            continue
        normalized_task_id = str(task_id)
        required_roles = [str(role).strip() for role in support.get("required_anchor_roles", []) if str(role).strip()]
        role_map = anchor_roles.get(normalized_task_id, {})
        for anchor_id in anchors_missing_roles.get(normalized_task_id, []):
            issues.append(
                TemplateValidationIssue(
                    code="missing_anchor_task_support_role",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor_id}' is assigned to task '{normalized_task_id}' but is missing "
                        "metadata.inspection_role."
                    ),
                    anchor_id=anchor_id,
                    path=str(repository.manifest_path),
                    metadata={"task_id": normalized_task_id},
                )
            )
        for role in required_roles:
            anchor_ids = list(role_map.get(role, []))
            if not anchor_ids:
                issues.append(
                    TemplateValidationIssue(
                        code="missing_task_support_anchor_role",
                        severity=TemplateValidationSeverity.ERROR,
                        message=(
                            f"Task '{normalized_task_id}' requires an anchor with inspection role '{role}'."
                        ),
                        path=str(repository.manifest_path),
                        metadata={"task_id": normalized_task_id, "inspection_role": role},
                    )
                )
                continue
            if len(anchor_ids) > 1:
                issues.append(
                    TemplateValidationIssue(
                        code="duplicate_task_support_anchor_role",
                        severity=TemplateValidationSeverity.ERROR,
                        message=(
                            f"Task '{normalized_task_id}' has multiple anchors for inspection role '{role}'."
                        ),
                        anchor_id=anchor_ids[0],
                        path=str(repository.manifest_path),
                        metadata={
                            "task_id": normalized_task_id,
                            "inspection_role": role,
                            "anchor_ids": anchor_ids,
                        },
                    )
                )
        if normalized_task_id == "daily_ui.claim_rewards":
            issues.extend(_validate_claim_rewards_live_capture_coverage(repository, support))
    return issues


def _anchor_task_ids(metadata: dict[str, Any]) -> list[str]:
    task_ids: list[str] = []
    raw_task_id = metadata.get("task_id")
    if raw_task_id:
        task_ids.append(str(raw_task_id))
    raw_task_ids = metadata.get("task_ids")
    if isinstance(raw_task_ids, list):
        task_ids.extend(str(task_id) for task_id in raw_task_ids if str(task_id))
    return task_ids


def _curation_summary(curation: AnchorCurationProfile | None) -> str:
    if curation is None:
        return ""
    parts = [curation.status.value]
    if curation.provenance_kind is not None:
        parts.append(f"provenance={curation.provenance_kind.value}")
    if curation.provenance is not None and curation.provenance.locale:
        parts.append(f"locale={curation.provenance.locale}")
    if curation.provenance is not None and curation.provenance.source:
        parts.append(f"source={curation.provenance.source}")
    if curation.scene_id:
        parts.append(f"scene={curation.scene_id}")
    if curation.variant_id:
        parts.append(f"variant={curation.variant_id}")
    parts.append(f"refs={curation.reference_count}")
    if curation.intent_id:
        parts.append(f"intent={curation.intent_id}")
    return " | ".join(parts)


def _provenance_summary(curation: AnchorCurationProfile | None) -> str:
    if curation is None:
        return ""
    return curation.provenance_summary


def _failure_case(curation: AnchorCurationProfile | None) -> str:
    if curation is None:
        return ""
    return str(curation.metadata.get("failure_case", "")).strip()


def _claim_rewards_live_capture_coverage(repository: AnchorRepository | None) -> dict[str, Any]:
    if repository is None:
        return {}
    coverage = repository.get_task_support("daily_ui.claim_rewards").get("live_capture_coverage", {})
    return dict(coverage) if isinstance(coverage, dict) else {}


def _validate_claim_rewards_live_capture_coverage(
    repository: AnchorRepository,
    support: dict[str, Any],
) -> list[TemplateValidationIssue]:
    coverage = support.get("live_capture_coverage")
    if not isinstance(coverage, dict):
        return [
            TemplateValidationIssue(
                code="missing_claim_rewards_live_capture_coverage",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    "Task support for 'daily_ui.claim_rewards' must define "
                    "metadata.task_support[task_id].live_capture_coverage."
                ),
                path=str(repository.manifest_path),
                metadata={"task_id": "daily_ui.claim_rewards"},
            )
        ]

    live_anchor_ids = {
        str(anchor_id).strip()
        for anchor_id in coverage.get("live_anchor_ids", [])
        if str(anchor_id).strip()
    }
    stand_in_anchor_ids = {
        str(anchor_id).strip()
        for anchor_id in coverage.get("stand_in_anchor_ids", [])
        if str(anchor_id).strip()
    }
    blocked_scene_ids = {
        str(scene_id).strip()
        for scene_id in coverage.get("blocked_scene_ids", [])
        if str(scene_id).strip()
    }

    issues: list[TemplateValidationIssue] = []
    if live_anchor_ids & stand_in_anchor_ids:
        issues.append(
            TemplateValidationIssue(
                code="claim_rewards_live_capture_coverage_overlap",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    "Claim-rewards live_capture_coverage cannot list the same anchor "
                    "in both live_anchor_ids and stand_in_anchor_ids."
                ),
                path=str(repository.manifest_path),
                metadata={
                    "task_id": "daily_ui.claim_rewards",
                    "anchor_ids": sorted(live_anchor_ids & stand_in_anchor_ids),
                },
            )
        )

    claim_rewards_anchor_ids = {
        anchor.anchor_id
        for anchor in repository.list_anchors()
        if "daily_ui.claim_rewards" in _anchor_task_ids(dict(anchor.metadata))
    }
    unknown_anchor_ids = (live_anchor_ids | stand_in_anchor_ids) - claim_rewards_anchor_ids
    if unknown_anchor_ids:
        issues.append(
            TemplateValidationIssue(
                code="unknown_claim_rewards_live_capture_anchor",
                severity=TemplateValidationSeverity.ERROR,
                message=(
                    "Claim-rewards live_capture_coverage must only reference anchors "
                    "assigned to daily_ui.claim_rewards."
                ),
                path=str(repository.manifest_path),
                metadata={"task_id": "daily_ui.claim_rewards", "anchor_ids": sorted(unknown_anchor_ids)},
            )
        )

    for anchor_id in sorted(claim_rewards_anchor_ids):
        curation = repository.get_anchor_curation(anchor_id)
        if curation is None or curation.provenance_kind is None:
            continue
        if curation.provenance_kind == AnchorAssetProvenanceKind.LIVE_CAPTURE and anchor_id not in live_anchor_ids:
            issues.append(
                TemplateValidationIssue(
                    code="claim_rewards_live_anchor_missing_from_coverage",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor_id}' is marked as live_capture but is missing from "
                        "live_capture_coverage.live_anchor_ids."
                    ),
                    anchor_id=anchor_id,
                    path=str(repository.manifest_path),
                    metadata={"task_id": "daily_ui.claim_rewards"},
                )
            )
        if curation.provenance_kind == AnchorAssetProvenanceKind.CURATED_STAND_IN and anchor_id not in stand_in_anchor_ids:
            issues.append(
                TemplateValidationIssue(
                    code="claim_rewards_stand_in_anchor_missing_from_coverage",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor_id}' is marked as curated_stand_in but is missing from "
                        "live_capture_coverage.stand_in_anchor_ids."
                    ),
                    anchor_id=anchor_id,
                    path=str(repository.manifest_path),
                    metadata={"task_id": "daily_ui.claim_rewards"},
                )
            )
        if (
            curation.provenance_kind == AnchorAssetProvenanceKind.CURATED_STAND_IN
            and curation.scene_id
            and curation.scene_id not in blocked_scene_ids
        ):
            issues.append(
                TemplateValidationIssue(
                    code="claim_rewards_blocked_scene_missing_from_coverage",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor_id}' is still a curated stand-in, so scene "
                        f"'{curation.scene_id}' must appear in live_capture_coverage.blocked_scene_ids."
                    ),
                    anchor_id=anchor_id,
                    path=str(repository.manifest_path),
                    metadata={"task_id": "daily_ui.claim_rewards", "scene_id": curation.scene_id},
                )
            )
        if (
            curation.provenance_kind == AnchorAssetProvenanceKind.LIVE_CAPTURE
            and curation.scene_id
            and curation.scene_id in blocked_scene_ids
        ):
            issues.append(
                TemplateValidationIssue(
                    code="claim_rewards_live_scene_marked_blocked",
                    severity=TemplateValidationSeverity.ERROR,
                    message=(
                        f"Anchor '{anchor_id}' is already a live capture, so scene "
                        f"'{curation.scene_id}' cannot remain in blocked_scene_ids."
                    ),
                    anchor_id=anchor_id,
                    path=str(repository.manifest_path),
                    metadata={"task_id": "daily_ui.claim_rewards", "scene_id": curation.scene_id},
                )
            )

    return issues


def _resolve_template_readiness_status(
    *,
    repository_present: bool,
    anchor_present: bool,
    asset_exists: bool,
    inventory_status: str,
    issue_codes: list[str],
    placeholder: bool,
    curation_status: AnchorCurationStatus | None,
    provenance_kind: AnchorAssetProvenanceKind | None,
) -> tuple[TemplateReadinessStatus, str]:
    if not repository_present:
        return (
            TemplateReadinessStatus.MISSING,
            "Required template repository is missing from assets/templates.",
        )
    if not anchor_present:
        return (
            TemplateReadinessStatus.MISSING,
            "Required anchor is missing from the template manifest.",
        )
    if not asset_exists:
        return (
            TemplateReadinessStatus.MISSING,
            "Anchor exists in the manifest but the template asset file is missing.",
        )
    if issue_codes:
        return (
            TemplateReadinessStatus.INVALID,
            "Anchor is present but has validation issues that should be resolved before consumption.",
        )
    if curation_status == AnchorCurationStatus.CURATED and not placeholder:
        if provenance_kind == AnchorAssetProvenanceKind.LIVE_CAPTURE:
            return (
                TemplateReadinessStatus.READY,
                "Template dependency is backed by a live capture and resolves without validation errors.",
            )
        if provenance_kind == AnchorAssetProvenanceKind.CURATED_STAND_IN:
            return (
                TemplateReadinessStatus.READY,
                "Template dependency is backed by a curated stand-in and resolves without validation errors.",
            )
        return (
            TemplateReadinessStatus.READY,
            "Template dependency is curated and resolves without validation errors.",
        )
    if placeholder or inventory_status == "placeholder":
        return (
            TemplateReadinessStatus.PLACEHOLDER,
            "Template dependency is present as a placeholder scaffold.",
        )
    return (
        TemplateReadinessStatus.READY,
        "Template dependency is present and resolves without validation errors.",
    )
