from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from json import JSONDecodeError
from pathlib import Path
from re import compile
from typing import Any, Self

from roxauto.core.serde import to_primitive
from roxauto.vision.repository import AnchorRepository

_ASSET_NAME_PATTERN = compile(r"^[a-z0-9_]+$")


class TemplateValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


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
