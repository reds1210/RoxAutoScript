from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

from roxauto.core.serde import to_primitive
from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import TaskBlueprint, TaskFixtureProfile, TaskReadinessReport, TaskRuntimeBuilderInput


class GuildOrderDecisionValue(str, Enum):
    SUBMIT = "submit"
    SKIP = "skip"
    REFRESH = "refresh"


class GuildOrderDecisionReason(str, Enum):
    MATERIALS_SUFFICIENT = "materials_sufficient"
    MATERIALS_INSUFFICIENT = "materials_insufficient"
    POLICY_BLOCKED_MATERIAL = "policy_blocked_material"
    ORDER_ALREADY_COMPLETED = "order_already_completed"
    ORDER_STATE_UNKNOWN = "order_state_unknown"
    REFRESH_NOT_ALLOWED = "refresh_not_allowed"
    REFRESH_LIMIT_REACHED = "refresh_limit_reached"
    SUBMIT_VERIFICATION_FAILED = "submit_verification_failed"
    REFRESH_VERIFICATION_FAILED = "refresh_verification_failed"


class GuildOrderMaterialSufficiency(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class GuildOrderVerificationState(str, Enum):
    SUBMIT_VERIFIED = "submit_verified"
    SKIP_RECORDED = "skip_recorded"
    REFRESH_VERIFIED = "refresh_verified"
    VERIFICATION_FAILED = "verification_failed"
    ORDER_STATE_UNKNOWN = "order_state_unknown"


@dataclass(slots=True)
class GuildOrderRequirement:
    slot_index: int
    material_label: str
    normalized_material_id: str | None = None
    required_quantity: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "slot_index": self.slot_index,
                "material_label": self.material_label,
                "normalized_material_id": self.normalized_material_id,
                "required_quantity": self.required_quantity,
                "evidence": self.evidence,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            slot_index=int(data.get("slot_index", 0)),
            material_label=str(data.get("material_label", "")),
            normalized_material_id=_optional_string(data.get("normalized_material_id")),
            required_quantity=_optional_int(data.get("required_quantity")),
            evidence=dict(data.get("evidence", {})),
        )


@dataclass(slots=True)
class GuildOrderAvailability:
    material_label: str
    normalized_material_id: str | None = None
    available_quantity: int | None = None
    sufficiency: GuildOrderMaterialSufficiency = GuildOrderMaterialSufficiency.UNKNOWN
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "material_label": self.material_label,
                "normalized_material_id": self.normalized_material_id,
                "available_quantity": self.available_quantity,
                "sufficiency": self.sufficiency.value,
                "evidence": self.evidence,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_sufficiency = data.get("sufficiency", GuildOrderMaterialSufficiency.UNKNOWN.value)
        sufficiency = (
            raw_sufficiency
            if isinstance(raw_sufficiency, GuildOrderMaterialSufficiency)
            else GuildOrderMaterialSufficiency(str(raw_sufficiency))
        )
        return cls(
            material_label=str(data.get("material_label", "")),
            normalized_material_id=_optional_string(data.get("normalized_material_id")),
            available_quantity=_optional_int(data.get("available_quantity")),
            sufficiency=sufficiency,
            evidence=dict(data.get("evidence", {})),
        )


@dataclass(slots=True)
class GuildOrderDecision:
    decision: GuildOrderDecisionValue
    reason_id: str
    slot_index: int
    requirements: list[GuildOrderRequirement] = field(default_factory=list)
    availability: list[GuildOrderAvailability] = field(default_factory=list)
    refresh_attempted: bool = False
    verification_state: GuildOrderVerificationState = GuildOrderVerificationState.ORDER_STATE_UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "decision": self.decision.value,
                "reason_id": self.reason_id,
                "slot_index": self.slot_index,
                "requirements": [item.to_dict() for item in self.requirements],
                "availability": [item.to_dict() for item in self.availability],
                "refresh_attempted": self.refresh_attempted,
                "verification_state": self.verification_state.value,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_decision = data.get("decision", GuildOrderDecisionValue.SKIP.value)
        raw_verification_state = data.get(
            "verification_state",
            GuildOrderVerificationState.ORDER_STATE_UNKNOWN.value,
        )
        decision = (
            raw_decision
            if isinstance(raw_decision, GuildOrderDecisionValue)
            else GuildOrderDecisionValue(str(raw_decision))
        )
        verification_state = (
            raw_verification_state
            if isinstance(raw_verification_state, GuildOrderVerificationState)
            else GuildOrderVerificationState(str(raw_verification_state))
        )
        return cls(
            decision=decision,
            reason_id=str(data.get("reason_id", "")),
            slot_index=int(data.get("slot_index", 0)),
            requirements=[GuildOrderRequirement.from_dict(item) for item in data.get("requirements", [])],
            availability=[GuildOrderAvailability.from_dict(item) for item in data.get("availability", [])],
            refresh_attempted=bool(data.get("refresh_attempted", False)),
            verification_state=verification_state,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class GuildOrderMaterialPolicy:
    allowed_material_ids: list[str] = field(default_factory=list)
    allowed_material_labels: list[str] = field(default_factory=list)
    blocked_material_ids: list[str] = field(default_factory=list)
    blocked_material_labels: list[str] = field(default_factory=list)
    reserve_quantity_by_material_id: dict[str, int] = field(default_factory=dict)
    reserve_quantity_by_material_label: dict[str, int] = field(default_factory=dict)
    refresh_allowed: bool = True
    max_refresh_attempts_per_run: int = 1
    decision_priority: list[str] = field(default_factory=list)
    decision_boundary: str = ""
    disallowed_behaviors: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "allowed_material_ids": self.allowed_material_ids,
                "allowed_material_labels": self.allowed_material_labels,
                "blocked_material_ids": self.blocked_material_ids,
                "blocked_material_labels": self.blocked_material_labels,
                "reserve_quantity_by_material_id": self.reserve_quantity_by_material_id,
                "reserve_quantity_by_material_label": self.reserve_quantity_by_material_label,
                "refresh_allowed": self.refresh_allowed,
                "max_refresh_attempts_per_run": self.max_refresh_attempts_per_run,
                "decision_priority": self.decision_priority,
                "decision_boundary": self.decision_boundary,
                "disallowed_behaviors": self.disallowed_behaviors,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            allowed_material_ids=[str(item) for item in data.get("allowed_material_ids", [])],
            allowed_material_labels=[str(item) for item in data.get("allowed_material_labels", [])],
            blocked_material_ids=[str(item) for item in data.get("blocked_material_ids", [])],
            blocked_material_labels=[str(item) for item in data.get("blocked_material_labels", [])],
            reserve_quantity_by_material_id={
                str(key): int(value)
                for key, value in dict(data.get("reserve_quantity_by_material_id", {})).items()
            },
            reserve_quantity_by_material_label={
                str(key): int(value)
                for key, value in dict(data.get("reserve_quantity_by_material_label", {})).items()
            },
            refresh_allowed=bool(data.get("refresh_allowed", True)),
            max_refresh_attempts_per_run=int(data.get("max_refresh_attempts_per_run", 1)),
            decision_priority=[str(item) for item in data.get("decision_priority", [])],
            decision_boundary=str(data.get("decision_boundary", "")),
            disallowed_behaviors=[str(item) for item in data.get("disallowed_behaviors", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class GuildOrderDecisionContract:
    allowed_decisions: list[str] = field(default_factory=list)
    reason_ids: list[str] = field(default_factory=list)
    verification_state_ids: list[str] = field(default_factory=list)
    decision_signal_keys: list[str] = field(default_factory=list)
    material_evidence_fields: list[str] = field(default_factory=list)
    decision_rules: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "allowed_decisions": self.allowed_decisions,
                "reason_ids": self.reason_ids,
                "verification_state_ids": self.verification_state_ids,
                "decision_signal_keys": self.decision_signal_keys,
                "material_evidence_fields": self.material_evidence_fields,
                "decision_rules": self.decision_rules,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            allowed_decisions=[str(item) for item in data.get("allowed_decisions", [])],
            reason_ids=[str(item) for item in data.get("reason_ids", [])],
            verification_state_ids=[str(item) for item in data.get("verification_state_ids", [])],
            decision_signal_keys=[str(item) for item in data.get("decision_signal_keys", [])],
            material_evidence_fields=[str(item) for item in data.get("material_evidence_fields", [])],
            decision_rules={str(key): str(value) for key, value in dict(data.get("decision_rules", {})).items()},
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class GuildOrderVisibilityContract:
    required_anchor_ids: list[str] = field(default_factory=list)
    supporting_anchor_ids: list[str] = field(default_factory=list)
    required_screen_slugs: list[str] = field(default_factory=list)
    supporting_screen_slugs: list[str] = field(default_factory=list)
    decision_input_fields: list[str] = field(default_factory=list)
    foundation_requirement_ids: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "required_anchor_ids": self.required_anchor_ids,
                "supporting_anchor_ids": self.supporting_anchor_ids,
                "required_screen_slugs": self.required_screen_slugs,
                "supporting_screen_slugs": self.supporting_screen_slugs,
                "decision_input_fields": self.decision_input_fields,
                "foundation_requirement_ids": self.foundation_requirement_ids,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            required_anchor_ids=[str(item) for item in data.get("required_anchor_ids", [])],
            supporting_anchor_ids=[str(item) for item in data.get("supporting_anchor_ids", [])],
            required_screen_slugs=[str(item) for item in data.get("required_screen_slugs", [])],
            supporting_screen_slugs=[str(item) for item in data.get("supporting_screen_slugs", [])],
            decision_input_fields=[str(item) for item in data.get("decision_input_fields", [])],
            foundation_requirement_ids=[str(item) for item in data.get("foundation_requirement_ids", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class GuildOrderSubmitSpecification:
    task_id: str
    pack_id: str
    manifest_path: str
    builder_input: TaskRuntimeBuilderInput
    readiness_report: TaskReadinessReport
    blueprint: TaskBlueprint
    fixture_profile_path: str
    fixture_profile: TaskFixtureProfile
    required_anchor_ids: list[str] = field(default_factory=list)
    supporting_anchor_ids: list[str] = field(default_factory=list)
    required_screen_slugs: list[str] = field(default_factory=list)
    supporting_screen_slugs: list[str] = field(default_factory=list)
    material_policy: GuildOrderMaterialPolicy = field(default_factory=GuildOrderMaterialPolicy)
    decision_contract: GuildOrderDecisionContract = field(default_factory=GuildOrderDecisionContract)
    visibility_contract: GuildOrderVisibilityContract = field(default_factory=GuildOrderVisibilityContract)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "task_id": self.task_id,
                "pack_id": self.pack_id,
                "manifest_path": self.manifest_path,
                "builder_input": self.builder_input.to_dict(),
                "readiness_report": self.readiness_report.to_dict(),
                "blueprint": self.blueprint.to_dict(),
                "fixture_profile_path": self.fixture_profile_path,
                "fixture_profile": self.fixture_profile.to_dict(),
                "required_anchor_ids": self.required_anchor_ids,
                "supporting_anchor_ids": self.supporting_anchor_ids,
                "required_screen_slugs": self.required_screen_slugs,
                "supporting_screen_slugs": self.supporting_screen_slugs,
                "material_policy": self.material_policy.to_dict(),
                "decision_contract": self.decision_contract.to_dict(),
                "visibility_contract": self.visibility_contract.to_dict(),
                "metadata": self.metadata,
            }
        )


def load_guild_order_submit_blueprint(
    repository: TaskFoundationRepository | None = None,
) -> TaskBlueprint:
    repo = repository or TaskFoundationRepository.load_default()
    return repo.load_blueprint(repo.root / "packs" / "daily_ui" / "guild_order_submit.task.json")


def load_guild_order_submit_material_policy(
    repository: TaskFoundationRepository | None = None,
) -> GuildOrderMaterialPolicy:
    blueprint = load_guild_order_submit_blueprint(repository)
    return GuildOrderMaterialPolicy.from_dict(
        _metadata_dict(blueprint.metadata, "guild_order_material_policy"),
    )


def load_guild_order_submit_decision_contract(
    repository: TaskFoundationRepository | None = None,
) -> GuildOrderDecisionContract:
    blueprint = load_guild_order_submit_blueprint(repository)
    return GuildOrderDecisionContract.from_dict(
        _metadata_dict(blueprint.metadata, "guild_order_decision_contract"),
    )


def load_guild_order_submit_visibility_contract(
    repository: TaskFoundationRepository | None = None,
) -> GuildOrderVisibilityContract:
    blueprint = load_guild_order_submit_blueprint(repository)
    return GuildOrderVisibilityContract.from_dict(
        _metadata_dict(blueprint.metadata, "guild_order_visibility_contract"),
    )


def build_guild_order_submit_specification(
    *,
    builder_input: TaskRuntimeBuilderInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> GuildOrderSubmitSpecification:
    repo = foundation_repository or TaskFoundationRepository.load_default()
    resolved_builder_input = builder_input or repo.build_runtime_builder_input("daily_ui.guild_order_submit")
    if resolved_builder_input.task_id != "daily_ui.guild_order_submit":
        raise ValueError("build_guild_order_submit_specification only supports daily_ui.guild_order_submit")

    resolved_readiness_report = readiness_report or repo.evaluate_task_readiness(resolved_builder_input.task_id)
    if resolved_readiness_report.task_id != resolved_builder_input.task_id:
        raise ValueError("Guild-order readiness report does not match the runtime builder input task id")

    blueprint = load_guild_order_submit_blueprint(repo)
    fixture_profile_path = _select_fixture_profile_path(resolved_builder_input)
    fixture_profile = repo.load_fixture_profile(repo.root / fixture_profile_path)
    metadata_source = dict(resolved_builder_input.metadata)
    blueprint_metadata = dict(blueprint.metadata)

    return GuildOrderSubmitSpecification(
        task_id=resolved_builder_input.task_id,
        pack_id=resolved_builder_input.pack_id,
        manifest_path=resolved_builder_input.manifest_path,
        builder_input=resolved_builder_input,
        readiness_report=resolved_readiness_report,
        blueprint=blueprint,
        fixture_profile_path=fixture_profile_path,
        fixture_profile=fixture_profile,
        required_anchor_ids=list(resolved_builder_input.required_anchors),
        supporting_anchor_ids=_metadata_string_list(metadata_source, "supporting_anchor_ids"),
        required_screen_slugs=[
            case.screen_slug
            for case in blueprint.golden_cases
            if case.screen_slug not in _metadata_string_list(metadata_source, "supporting_golden_screen_slugs")
        ],
        supporting_screen_slugs=_metadata_string_list(metadata_source, "supporting_golden_screen_slugs"),
        material_policy=GuildOrderMaterialPolicy.from_dict(
            _metadata_dict(metadata_source, "guild_order_material_policy")
            or _metadata_dict(blueprint_metadata, "guild_order_material_policy")
        ),
        decision_contract=GuildOrderDecisionContract.from_dict(
            _metadata_dict(metadata_source, "guild_order_decision_contract")
            or _metadata_dict(blueprint_metadata, "guild_order_decision_contract")
        ),
        visibility_contract=GuildOrderVisibilityContract.from_dict(
            _metadata_dict(metadata_source, "guild_order_visibility_contract")
            or _metadata_dict(blueprint_metadata, "guild_order_visibility_contract")
        ),
        metadata={
            "signal_contract_version": str(metadata_source.get("signal_contract_version", "")),
            "guild_order_spec_builders": _metadata_dict(metadata_source, "guild_order_spec_builders"),
            "guild_order_handoff_fields": _metadata_string_list(metadata_source, "guild_order_handoff_fields"),
            "implementation_state": str(resolved_readiness_report.metadata.get("implementation_state", "")),
        },
    )


def _metadata_dict(metadata: dict[str, Any], key: str) -> dict[str, Any]:
    value = metadata.get(key)
    if isinstance(value, dict):
        return dict(value)
    return {}


def _metadata_string_list(metadata: dict[str, Any], key: str) -> list[str]:
    value = metadata.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_string(value: object) -> str | None:
    if value in ("", None):
        return None
    return str(value)


def _select_fixture_profile_path(builder_input: TaskRuntimeBuilderInput) -> str:
    if not builder_input.fixture_profile_paths:
        raise ValueError("Guild-order specification requires at least one fixture profile path")
    return builder_input.fixture_profile_paths[0]
