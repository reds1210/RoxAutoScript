from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from json import dumps, loads
from pathlib import PurePosixPath
import re
from typing import Any, Self

from roxauto.core.models import StopCondition, StopConditionKind, TaskManifest
from roxauto.core.serde import to_primitive

_GOLDEN_FILENAME_RE = re.compile(r"^[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+__v[0-9]+\.png$")


class TaskImplementationState(str, Enum):
    SPEC_ONLY = "spec_only"
    FIXTURED = "fixtured"
    READY_FOR_IMPLEMENTATION = "ready_for_implementation"


@dataclass(slots=True)
class GoldenScreenshotCase:
    screen_slug: str
    variants: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            screen_slug=str(data.get("screen_slug", "")),
            variants=[str(item) for item in data.get("variants", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class GoldenScreenshotConvention:
    convention_id: str
    directory_template: str = "{pack_id}/{task_id}/{screen_slug}"
    filename_template: str = "{task_id}__{screen_slug}__{variant}__v{revision}.png"
    required_variants: list[str] = field(default_factory=lambda: ["baseline", "failure"])
    image_format: str = "png"
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            convention_id=str(data.get("convention_id", "")),
            directory_template=str(data.get("directory_template", "{pack_id}/{task_id}/{screen_slug}")),
            filename_template=str(
                data.get("filename_template", "{task_id}__{screen_slug}__{variant}__v{revision}.png")
            ),
            required_variants=[str(item) for item in data.get("required_variants", ["baseline", "failure"])],
            image_format=str(data.get("image_format", "png")),
            notes=str(data.get("notes", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def render_path(
        self,
        *,
        pack_id: str,
        task_id: str,
        screen_slug: str,
        variant: str,
        revision: int = 1,
    ) -> PurePosixPath:
        directory = self.directory_template.format(pack_id=pack_id, task_id=task_id, screen_slug=screen_slug)
        filename = self.filename_template.format(
            task_id=task_id,
            screen_slug=screen_slug,
            variant=variant,
            revision=revision,
        )
        return PurePosixPath(directory) / filename

    def is_valid_filename(self, filename: str) -> bool:
        return bool(_GOLDEN_FILENAME_RE.match(filename))


@dataclass(slots=True)
class TaskFixtureProfile:
    fixture_id: str
    display_name: str
    locale: str = "zh-TW"
    emulator_name: str = "mumu"
    resolution: tuple[int, int] = (1280, 720)
    template_packs: list[str] = field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(asdict(self))

    def to_json(self) -> str:
        return dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        resolution = data.get("resolution", (1280, 720))
        return cls(
            fixture_id=str(data.get("fixture_id", "")),
            display_name=str(data.get("display_name", "")),
            locale=str(data.get("locale", "zh-TW")),
            emulator_name=str(data.get("emulator_name", "mumu")),
            resolution=(int(resolution[0]), int(resolution[1])),
            template_packs=[str(item) for item in data.get("template_packs", [])],
            notes=str(data.get("notes", "")),
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls.from_dict(loads(payload))


def _stop_condition_from_dict(data: dict[str, Any]) -> StopCondition:
    raw_kind = data.get("kind", StopConditionKind.MANUAL.value)
    if isinstance(raw_kind, StopConditionKind):
        kind = raw_kind
    else:
        kind = StopConditionKind(str(raw_kind))
    return StopCondition(
        condition_id=str(data.get("condition_id", "")),
        kind=kind,
        message=str(data.get("message", "")),
        enabled=bool(data.get("enabled", True)),
        timeout_ms=int(data["timeout_ms"]) if data.get("timeout_ms") is not None else None,
        metadata=dict(data.get("metadata", {})),
    )


def _task_manifest_from_dict(data: dict[str, Any]) -> TaskManifest:
    return TaskManifest(
        task_id=str(data.get("task_id", "")),
        name=str(data.get("name", "")),
        version=str(data.get("version", "0.1.0")),
        requires=[str(item) for item in data.get("requires", [])],
        entry_condition=str(data.get("entry_condition", "")),
        success_condition=str(data.get("success_condition", "")),
        failure_condition=str(data.get("failure_condition", "")),
        recovery_policy=str(data.get("recovery_policy", "abort")),
        stop_conditions=[_stop_condition_from_dict(item) for item in data.get("stop_conditions", [])],
        metadata=dict(data.get("metadata", {})),
    )


@dataclass(slots=True)
class TaskBlueprint:
    pack_id: str
    manifest: TaskManifest
    implementation_state: TaskImplementationState = TaskImplementationState.SPEC_ONLY
    required_anchors: list[str] = field(default_factory=list)
    fixture_profile_paths: list[str] = field(default_factory=list)
    golden_cases: list[GoldenScreenshotCase] = field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def task_id(self) -> str:
        return self.manifest.task_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "task_manifest": to_primitive(asdict(self.manifest)),
            "implementation_state": self.implementation_state.value,
            "required_anchors": list(self.required_anchors),
            "fixture_profile_paths": list(self.fixture_profile_paths),
            "golden_cases": [case.to_dict() for case in self.golden_cases],
            "notes": self.notes,
            "metadata": to_primitive(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_state = data.get("implementation_state", TaskImplementationState.SPEC_ONLY.value)
        if isinstance(raw_state, TaskImplementationState):
            state = raw_state
        else:
            state = TaskImplementationState(str(raw_state))
        return cls(
            pack_id=str(data.get("pack_id", "")),
            manifest=_task_manifest_from_dict(dict(data.get("task_manifest", {}))),
            implementation_state=state,
            required_anchors=[str(item) for item in data.get("required_anchors", [])],
            fixture_profile_paths=[str(item) for item in data.get("fixture_profile_paths", [])],
            golden_cases=[GoldenScreenshotCase.from_dict(item) for item in data.get("golden_cases", [])],
            notes=str(data.get("notes", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class TaskInventoryRecord:
    task_id: str
    pack_id: str
    implementation_state: TaskImplementationState
    manifest_path: str
    fixture_profile_paths: list[str] = field(default_factory=list)
    golden_root: str = ""
    required_anchors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "pack_id": self.pack_id,
            "implementation_state": self.implementation_state.value,
            "manifest_path": self.manifest_path,
            "fixture_profile_paths": list(self.fixture_profile_paths),
            "golden_root": self.golden_root,
            "required_anchors": list(self.required_anchors),
            "metadata": to_primitive(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_state = data.get("implementation_state", TaskImplementationState.SPEC_ONLY.value)
        if isinstance(raw_state, TaskImplementationState):
            state = raw_state
        else:
            state = TaskImplementationState(str(raw_state))
        return cls(
            task_id=str(data.get("task_id", "")),
            pack_id=str(data.get("pack_id", "")),
            implementation_state=state,
            manifest_path=str(data.get("manifest_path", "")),
            fixture_profile_paths=[str(item) for item in data.get("fixture_profile_paths", [])],
            golden_root=str(data.get("golden_root", "")),
            required_anchors=[str(item) for item in data.get("required_anchors", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class TaskInventory:
    inventory_id: str
    version: str
    records: list[TaskInventoryRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "inventory_id": self.inventory_id,
            "version": self.version,
            "records": [record.to_dict() for record in self.records],
            "metadata": to_primitive(self.metadata),
        }

    def to_json(self) -> str:
        return dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            inventory_id=str(data.get("inventory_id", "")),
            version=str(data.get("version", "0.1.0")),
            records=[TaskInventoryRecord.from_dict(item) for item in data.get("records", [])],
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls.from_dict(loads(payload))
