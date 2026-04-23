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
    CUSTOM_ORDER_DISABLED = "custom_order_disabled"
    CUSTOM_ORDER_LIST_UNAVAILABLE = "custom_order_list_unavailable"
    CUSTOM_ORDER_NO_VIABLE_OPTION = "custom_order_no_viable_option"
    CUSTOM_ORDER_OPTION_SELECTED = "custom_order_option_selected"
    SUBMIT_VERIFICATION_FAILED = "submit_verification_failed"
    REFRESH_VERIFICATION_FAILED = "refresh_verification_failed"


class GuildOrderMaterialSufficiency(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class GuildOrderOrderKind(str, Enum):
    STANDARD = "standard"
    CUSTOM = "custom"


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
class GuildOrderCustomOption:
    candidate_index: int
    material_label: str
    normalized_material_id: str | None = None
    required_quantity: int | None = None
    available_quantity: int | None = None
    sufficiency: GuildOrderMaterialSufficiency = GuildOrderMaterialSufficiency.UNKNOWN
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "candidate_index": self.candidate_index,
                "material_label": self.material_label,
                "normalized_material_id": self.normalized_material_id,
                "required_quantity": self.required_quantity,
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
            candidate_index=int(data.get("candidate_index", 1)),
            material_label=str(data.get("material_label", "")),
            normalized_material_id=_optional_string(data.get("normalized_material_id")),
            required_quantity=_optional_int(data.get("required_quantity")),
            available_quantity=_optional_int(data.get("available_quantity")),
            sufficiency=sufficiency,
            evidence=dict(data.get("evidence", {})),
        )


@dataclass(slots=True)
class GuildOrderDecision:
    decision: GuildOrderDecisionValue
    reason_id: str
    slot_index: int
    order_kind: GuildOrderOrderKind = GuildOrderOrderKind.STANDARD
    requirements: list[GuildOrderRequirement] = field(default_factory=list)
    availability: list[GuildOrderAvailability] = field(default_factory=list)
    custom_options: list[GuildOrderCustomOption] = field(default_factory=list)
    selected_custom_option: GuildOrderCustomOption | None = None
    refresh_attempted: bool = False
    verification_state: GuildOrderVerificationState = GuildOrderVerificationState.ORDER_STATE_UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "decision": self.decision.value,
                "reason_id": self.reason_id,
                "slot_index": self.slot_index,
                "order_kind": self.order_kind.value,
                "requirements": [item.to_dict() for item in self.requirements],
                "availability": [item.to_dict() for item in self.availability],
                "custom_options": [item.to_dict() for item in self.custom_options],
                "selected_custom_option": (
                    self.selected_custom_option.to_dict() if self.selected_custom_option is not None else None
                ),
                "refresh_attempted": self.refresh_attempted,
                "verification_state": self.verification_state.value,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_decision = data.get("decision", GuildOrderDecisionValue.SKIP.value)
        raw_order_kind = data.get("order_kind", GuildOrderOrderKind.STANDARD.value)
        raw_verification_state = data.get(
            "verification_state",
            GuildOrderVerificationState.ORDER_STATE_UNKNOWN.value,
        )
        decision = (
            raw_decision
            if isinstance(raw_decision, GuildOrderDecisionValue)
            else GuildOrderDecisionValue(str(raw_decision))
        )
        order_kind = (
            raw_order_kind
            if isinstance(raw_order_kind, GuildOrderOrderKind)
            else GuildOrderOrderKind(str(raw_order_kind))
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
            order_kind=order_kind,
            requirements=[GuildOrderRequirement.from_dict(item) for item in data.get("requirements", [])],
            availability=[GuildOrderAvailability.from_dict(item) for item in data.get("availability", [])],
            custom_options=[GuildOrderCustomOption.from_dict(item) for item in data.get("custom_options", [])],
            selected_custom_option=(
                GuildOrderCustomOption.from_dict(selected_custom_option)
                if isinstance((selected_custom_option := data.get("selected_custom_option")), dict)
                else None
            ),
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
    custom_order_enabled: bool = True
    custom_order_preferred_material_ids: list[str] = field(default_factory=list)
    custom_order_preferred_material_labels: list[str] = field(default_factory=list)
    custom_order_selected_candidate_index: int | None = 1
    custom_order_max_candidates_to_inspect: int = 8
    custom_order_selection_boundary: str = ""
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
                "custom_order_enabled": self.custom_order_enabled,
                "custom_order_preferred_material_ids": self.custom_order_preferred_material_ids,
                "custom_order_preferred_material_labels": self.custom_order_preferred_material_labels,
                "custom_order_selected_candidate_index": self.custom_order_selected_candidate_index,
                "custom_order_max_candidates_to_inspect": self.custom_order_max_candidates_to_inspect,
                "custom_order_selection_boundary": self.custom_order_selection_boundary,
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
            custom_order_enabled=bool(data.get("custom_order_enabled", True)),
            custom_order_preferred_material_ids=[
                str(item) for item in data.get("custom_order_preferred_material_ids", [])
            ],
            custom_order_preferred_material_labels=[
                str(item) for item in data.get("custom_order_preferred_material_labels", [])
            ],
            custom_order_selected_candidate_index=_optional_positive_int(
                data.get("custom_order_selected_candidate_index", 1)
            ),
            custom_order_max_candidates_to_inspect=int(data.get("custom_order_max_candidates_to_inspect", 8)),
            custom_order_selection_boundary=str(data.get("custom_order_selection_boundary", "")),
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


def select_guild_order_custom_option(
    *,
    custom_options: list[GuildOrderCustomOption],
    policy: GuildOrderMaterialPolicy,
) -> GuildOrderCustomOption | None:
    ranked_options: list[tuple[tuple[int, int, int, str], GuildOrderCustomOption]] = []
    max_candidates = max(0, policy.custom_order_max_candidates_to_inspect)
    inspected_options = custom_options[:max_candidates] if max_candidates else []
    explicit_candidate_index = policy.custom_order_selected_candidate_index

    if explicit_candidate_index is not None:
        selected_option = next(
            (option for option in inspected_options if option.candidate_index == explicit_candidate_index),
            None,
        )
        if selected_option is None:
            return None
        sufficiency = _resolve_custom_option_sufficiency(selected_option, policy)
        if not _is_material_allowed(
            policy,
            normalized_material_id=selected_option.normalized_material_id,
            material_label=selected_option.material_label,
        ):
            return None
        if sufficiency is not GuildOrderMaterialSufficiency.SUFFICIENT:
            return None
        return _clone_custom_option_with_sufficiency(selected_option, sufficiency)

    for option in inspected_options:
        sufficiency = _resolve_custom_option_sufficiency(option, policy)
        if not _is_material_allowed(
            policy,
            normalized_material_id=option.normalized_material_id,
            material_label=option.material_label,
        ):
            continue
        if sufficiency is not GuildOrderMaterialSufficiency.SUFFICIENT:
            continue
        rank = (
            _material_preference_rank(
                normalized_material_id=option.normalized_material_id,
                material_label=option.material_label,
                preferred_ids=policy.custom_order_preferred_material_ids,
                preferred_labels=policy.custom_order_preferred_material_labels,
            ),
            option.candidate_index,
            -(option.available_quantity or 0),
            option.material_label,
        )
        ranked_options.append((rank, _clone_custom_option_with_sufficiency(option, sufficiency)))

    if not ranked_options:
        return None
    ranked_options.sort(key=lambda item: item[0])
    return ranked_options[0][1]


def evaluate_guild_order_submit_decision(
    *,
    slot_index: int,
    order_kind: GuildOrderOrderKind,
    policy: GuildOrderMaterialPolicy,
    requirements: list[GuildOrderRequirement] | None = None,
    availability: list[GuildOrderAvailability] | None = None,
    custom_options: list[GuildOrderCustomOption] | None = None,
    refresh_attempt_count: int = 0,
    order_completed: bool = False,
    order_state_known: bool = True,
    custom_order_list_visible: bool = True,
) -> GuildOrderDecision:
    resolved_requirements = list(requirements or [])
    resolved_availability = list(availability or [])
    resolved_custom_options = list(custom_options or [])

    if order_completed:
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.SKIP,
            reason_id=GuildOrderDecisionReason.ORDER_ALREADY_COMPLETED.value,
            slot_index=slot_index,
            order_kind=order_kind,
            requirements=resolved_requirements,
            availability=resolved_availability,
            custom_options=resolved_custom_options,
            verification_state=GuildOrderVerificationState.SKIP_RECORDED,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    if not order_state_known:
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.SKIP,
            reason_id=GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
            slot_index=slot_index,
            order_kind=order_kind,
            requirements=resolved_requirements,
            availability=resolved_availability,
            custom_options=resolved_custom_options,
            verification_state=GuildOrderVerificationState.ORDER_STATE_UNKNOWN,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    if order_kind is GuildOrderOrderKind.CUSTOM:
        return _evaluate_custom_order_decision(
            slot_index=slot_index,
            policy=policy,
            custom_options=resolved_custom_options,
            refresh_attempt_count=refresh_attempt_count,
            custom_order_list_visible=custom_order_list_visible,
        )

    return _evaluate_standard_order_decision(
        slot_index=slot_index,
        policy=policy,
        requirements=resolved_requirements,
        availability=resolved_availability,
        refresh_attempt_count=refresh_attempt_count,
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


def _optional_positive_int(value: object) -> int | None:
    parsed = _optional_int(value)
    if parsed is None:
        return None
    return parsed if parsed > 0 else None


def _optional_string(value: object) -> str | None:
    if value in ("", None):
        return None
    return str(value)


def _select_fixture_profile_path(builder_input: TaskRuntimeBuilderInput) -> str:
    if not builder_input.fixture_profile_paths:
        raise ValueError("Guild-order specification requires at least one fixture profile path")
    return builder_input.fixture_profile_paths[0]


def _evaluate_standard_order_decision(
    *,
    slot_index: int,
    policy: GuildOrderMaterialPolicy,
    requirements: list[GuildOrderRequirement],
    availability: list[GuildOrderAvailability],
    refresh_attempt_count: int,
) -> GuildOrderDecision:
    if not requirements:
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.SKIP,
            reason_id=GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
            slot_index=slot_index,
            order_kind=GuildOrderOrderKind.STANDARD,
            requirements=[],
            availability=[],
            verification_state=GuildOrderVerificationState.ORDER_STATE_UNKNOWN,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    matched_availability = [
        _match_availability_for_requirement(requirement, availability) for requirement in requirements
    ]
    blocked_requirement = next(
        (
            requirement
            for requirement in requirements
            if not _is_material_allowed(
                policy,
                normalized_material_id=requirement.normalized_material_id,
                material_label=requirement.material_label,
            )
        ),
        None,
    )
    if blocked_requirement is not None:
        return _build_refresh_or_skip_decision(
            slot_index=slot_index,
            order_kind=GuildOrderOrderKind.STANDARD,
            policy=policy,
            requirements=requirements,
            availability=matched_availability,
            refresh_attempt_count=refresh_attempt_count,
            fallback_reason=GuildOrderDecisionReason.POLICY_BLOCKED_MATERIAL,
        )

    if all(
        _resolve_requirement_sufficiency(requirement, matched_availability[index], policy)
        is GuildOrderMaterialSufficiency.SUFFICIENT
        for index, requirement in enumerate(requirements)
    ):
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.SUBMIT,
            reason_id=GuildOrderDecisionReason.MATERIALS_SUFFICIENT.value,
            slot_index=slot_index,
            order_kind=GuildOrderOrderKind.STANDARD,
            requirements=requirements,
            availability=matched_availability,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    return _build_refresh_or_skip_decision(
        slot_index=slot_index,
        order_kind=GuildOrderOrderKind.STANDARD,
        policy=policy,
        requirements=requirements,
        availability=matched_availability,
        refresh_attempt_count=refresh_attempt_count,
        fallback_reason=GuildOrderDecisionReason.MATERIALS_INSUFFICIENT,
    )


def _evaluate_custom_order_decision(
    *,
    slot_index: int,
    policy: GuildOrderMaterialPolicy,
    custom_options: list[GuildOrderCustomOption],
    refresh_attempt_count: int,
    custom_order_list_visible: bool,
) -> GuildOrderDecision:
    if not policy.custom_order_enabled:
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.SKIP,
            reason_id=GuildOrderDecisionReason.CUSTOM_ORDER_DISABLED.value,
            slot_index=slot_index,
            order_kind=GuildOrderOrderKind.CUSTOM,
            custom_options=custom_options,
            verification_state=GuildOrderVerificationState.SKIP_RECORDED,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    if not custom_order_list_visible:
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.SKIP,
            reason_id=GuildOrderDecisionReason.CUSTOM_ORDER_LIST_UNAVAILABLE.value,
            slot_index=slot_index,
            order_kind=GuildOrderOrderKind.CUSTOM,
            custom_options=custom_options,
            verification_state=GuildOrderVerificationState.ORDER_STATE_UNKNOWN,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    selected_option = select_guild_order_custom_option(custom_options=custom_options, policy=policy)
    if selected_option is not None:
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.SUBMIT,
            reason_id=GuildOrderDecisionReason.CUSTOM_ORDER_OPTION_SELECTED.value,
            slot_index=slot_index,
            order_kind=GuildOrderOrderKind.CUSTOM,
            requirements=[
                GuildOrderRequirement(
                    slot_index=slot_index,
                    material_label=selected_option.material_label,
                    normalized_material_id=selected_option.normalized_material_id,
                    required_quantity=selected_option.required_quantity,
                    evidence=dict(selected_option.evidence),
                )
            ],
            availability=[
                GuildOrderAvailability(
                    material_label=selected_option.material_label,
                    normalized_material_id=selected_option.normalized_material_id,
                    available_quantity=selected_option.available_quantity,
                    sufficiency=selected_option.sufficiency,
                    evidence=dict(selected_option.evidence),
                )
            ],
            custom_options=[
                _clone_custom_option_with_sufficiency(option, _resolve_custom_option_sufficiency(option, policy))
                for option in custom_options
            ],
            selected_custom_option=selected_option,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    return _build_refresh_or_skip_decision(
        slot_index=slot_index,
        order_kind=GuildOrderOrderKind.CUSTOM,
        policy=policy,
        requirements=[],
        availability=[],
        refresh_attempt_count=refresh_attempt_count,
        fallback_reason=GuildOrderDecisionReason.CUSTOM_ORDER_NO_VIABLE_OPTION,
        custom_options=[
            _clone_custom_option_with_sufficiency(option, _resolve_custom_option_sufficiency(option, policy))
            for option in custom_options
        ],
    )


def _build_refresh_or_skip_decision(
    *,
    slot_index: int,
    order_kind: GuildOrderOrderKind,
    policy: GuildOrderMaterialPolicy,
    requirements: list[GuildOrderRequirement],
    availability: list[GuildOrderAvailability],
    refresh_attempt_count: int,
    fallback_reason: GuildOrderDecisionReason,
    custom_options: list[GuildOrderCustomOption] | None = None,
) -> GuildOrderDecision:
    refresh_attempted = refresh_attempt_count > 0
    if policy.refresh_allowed and refresh_attempt_count < policy.max_refresh_attempts_per_run:
        return GuildOrderDecision(
            decision=GuildOrderDecisionValue.REFRESH,
            reason_id=fallback_reason.value,
            slot_index=slot_index,
            order_kind=order_kind,
            requirements=requirements,
            availability=availability,
            custom_options=list(custom_options or []),
            refresh_attempted=refresh_attempted,
            metadata={"refresh_attempt_count": refresh_attempt_count},
        )

    final_reason = (
        GuildOrderDecisionReason.REFRESH_NOT_ALLOWED
        if not policy.refresh_allowed
        else GuildOrderDecisionReason.REFRESH_LIMIT_REACHED
    )
    return GuildOrderDecision(
        decision=GuildOrderDecisionValue.SKIP,
        reason_id=final_reason.value,
        slot_index=slot_index,
        order_kind=order_kind,
        requirements=requirements,
        availability=availability,
        custom_options=list(custom_options or []),
        refresh_attempted=refresh_attempted,
        verification_state=GuildOrderVerificationState.SKIP_RECORDED,
        metadata={
            "refresh_attempt_count": refresh_attempt_count,
            "fallback_reason_id": fallback_reason.value,
        },
    )


def _match_availability_for_requirement(
    requirement: GuildOrderRequirement,
    availability: list[GuildOrderAvailability],
) -> GuildOrderAvailability:
    for option in availability:
        if requirement.normalized_material_id and option.normalized_material_id == requirement.normalized_material_id:
            return option
        if option.material_label == requirement.material_label:
            return option
    return GuildOrderAvailability(
        material_label=requirement.material_label,
        normalized_material_id=requirement.normalized_material_id,
        available_quantity=None,
        sufficiency=GuildOrderMaterialSufficiency.UNKNOWN,
        evidence={"source": "unmatched_requirement"},
    )


def _resolve_requirement_sufficiency(
    requirement: GuildOrderRequirement,
    availability: GuildOrderAvailability,
    policy: GuildOrderMaterialPolicy,
) -> GuildOrderMaterialSufficiency:
    if availability.sufficiency is not GuildOrderMaterialSufficiency.UNKNOWN:
        return availability.sufficiency
    if requirement.required_quantity is None or availability.available_quantity is None:
        return GuildOrderMaterialSufficiency.UNKNOWN
    reserve = _reserve_quantity(
        policy,
        normalized_material_id=requirement.normalized_material_id,
        material_label=requirement.material_label,
    )
    return (
        GuildOrderMaterialSufficiency.SUFFICIENT
        if availability.available_quantity - reserve >= requirement.required_quantity
        else GuildOrderMaterialSufficiency.INSUFFICIENT
    )


def _resolve_custom_option_sufficiency(
    option: GuildOrderCustomOption,
    policy: GuildOrderMaterialPolicy,
) -> GuildOrderMaterialSufficiency:
    if option.sufficiency is not GuildOrderMaterialSufficiency.UNKNOWN:
        return option.sufficiency
    if option.required_quantity is None or option.available_quantity is None:
        return GuildOrderMaterialSufficiency.UNKNOWN
    reserve = _reserve_quantity(
        policy,
        normalized_material_id=option.normalized_material_id,
        material_label=option.material_label,
    )
    return (
        GuildOrderMaterialSufficiency.SUFFICIENT
        if option.available_quantity - reserve >= option.required_quantity
        else GuildOrderMaterialSufficiency.INSUFFICIENT
    )


def _reserve_quantity(
    policy: GuildOrderMaterialPolicy,
    *,
    normalized_material_id: str | None,
    material_label: str,
) -> int:
    if normalized_material_id and normalized_material_id in policy.reserve_quantity_by_material_id:
        return int(policy.reserve_quantity_by_material_id[normalized_material_id])
    return int(policy.reserve_quantity_by_material_label.get(material_label, 0))


def _is_material_allowed(
    policy: GuildOrderMaterialPolicy,
    *,
    normalized_material_id: str | None,
    material_label: str,
) -> bool:
    if normalized_material_id and normalized_material_id in policy.blocked_material_ids:
        return False
    if material_label in policy.blocked_material_labels:
        return False
    if policy.allowed_material_ids and normalized_material_id not in policy.allowed_material_ids:
        return False
    if policy.allowed_material_labels and material_label not in policy.allowed_material_labels:
        return False
    return True


def _material_preference_rank(
    *,
    normalized_material_id: str | None,
    material_label: str,
    preferred_ids: list[str],
    preferred_labels: list[str],
) -> int:
    if normalized_material_id and normalized_material_id in preferred_ids:
        return preferred_ids.index(normalized_material_id)
    if material_label in preferred_labels:
        return len(preferred_ids) + preferred_labels.index(material_label)
    return len(preferred_ids) + len(preferred_labels) + 1


def _clone_custom_option_with_sufficiency(
    option: GuildOrderCustomOption,
    sufficiency: GuildOrderMaterialSufficiency,
) -> GuildOrderCustomOption:
    return GuildOrderCustomOption(
        candidate_index=option.candidate_index,
        material_label=option.material_label,
        normalized_material_id=option.normalized_material_id,
        required_quantity=option.required_quantity,
        available_quantity=option.available_quantity,
        sufficiency=sufficiency,
        evidence=dict(option.evidence),
    )
