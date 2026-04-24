from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Self

from roxauto.core.serde import to_primitive
from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import (
    TaskBlueprint,
    TaskFixtureProfile,
    TaskReadinessReport,
    TaskRuntimeBuilderInput,
)


class MerchantCommissionMeowDecisionValue(str, Enum):
    DIRECT_SUBMIT = "direct_submit"
    IMMEDIATE_BUY_THEN_SUBMIT = "immediate_buy_then_submit"
    STOP_FOR_OPERATOR = "stop_for_operator"


class MerchantCommissionMeowDecisionReason(str, Enum):
    MATERIALS_READY = "materials_ready"
    BUY_REQUIRED = "buy_required"
    SUBMIT_PANEL_UNAVAILABLE = "submit_panel_unavailable"
    SUBMIT_BUTTON_UNAVAILABLE = "submit_button_unavailable"
    BUY_NOW_UNAVAILABLE = "buy_now_unavailable"
    IMMEDIATE_BUY_DISABLED = "immediate_buy_disabled"
    ROUND_STATE_UNKNOWN = "round_state_unknown"


@dataclass(slots=True)
class MerchantCommissionMeowRouteContract:
    entry_checkpoint_ids: list[str] = field(default_factory=list)
    preferred_reentry_checkpoint_ids: list[str] = field(default_factory=list)
    do_not_click_notes: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "entry_checkpoint_ids": self.entry_checkpoint_ids,
                "preferred_reentry_checkpoint_ids": self.preferred_reentry_checkpoint_ids,
                "do_not_click_notes": self.do_not_click_notes,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            entry_checkpoint_ids=[str(item) for item in data.get("entry_checkpoint_ids", [])],
            preferred_reentry_checkpoint_ids=[
                str(item) for item in data.get("preferred_reentry_checkpoint_ids", [])
            ],
            do_not_click_notes=[str(item) for item in data.get("do_not_click_notes", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class MerchantCommissionMeowLoopContract:
    merchant_group_label: str = ""
    task_list_label: str = ""
    round_limit: int = 0
    verified_round_count: int = 0
    preferred_reentry_mode: str = ""
    submit_panel_title: str = ""
    buy_now_label: str = ""
    buy_confirm_label: str = ""
    submit_label: str = ""
    task_round_pattern: str = ""
    verified_material_labels: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "merchant_group_label": self.merchant_group_label,
                "task_list_label": self.task_list_label,
                "round_limit": self.round_limit,
                "verified_round_count": self.verified_round_count,
                "preferred_reentry_mode": self.preferred_reentry_mode,
                "submit_panel_title": self.submit_panel_title,
                "buy_now_label": self.buy_now_label,
                "buy_confirm_label": self.buy_confirm_label,
                "submit_label": self.submit_label,
                "task_round_pattern": self.task_round_pattern,
                "verified_material_labels": self.verified_material_labels,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            merchant_group_label=str(data.get("merchant_group_label", "")),
            task_list_label=str(data.get("task_list_label", "")),
            round_limit=int(data.get("round_limit", 0)),
            verified_round_count=int(data.get("verified_round_count", 0)),
            preferred_reentry_mode=str(data.get("preferred_reentry_mode", "")),
            submit_panel_title=str(data.get("submit_panel_title", "")),
            buy_now_label=str(data.get("buy_now_label", "")),
            buy_confirm_label=str(data.get("buy_confirm_label", "")),
            submit_label=str(data.get("submit_label", "")),
            task_round_pattern=str(data.get("task_round_pattern", "")),
            verified_material_labels=[
                str(item) for item in data.get("verified_material_labels", [])
            ],
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class MerchantCommissionMeowSubmissionPolicy:
    allow_immediate_buy: bool = True
    allow_partial_inventory_buy: bool = True
    buy_flow_requires_confirmation: bool = True
    verified_reentry_mode: str = ""
    disallowed_behaviors: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "allow_immediate_buy": self.allow_immediate_buy,
                "allow_partial_inventory_buy": self.allow_partial_inventory_buy,
                "buy_flow_requires_confirmation": self.buy_flow_requires_confirmation,
                "verified_reentry_mode": self.verified_reentry_mode,
                "disallowed_behaviors": self.disallowed_behaviors,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            allow_immediate_buy=bool(data.get("allow_immediate_buy", True)),
            allow_partial_inventory_buy=bool(data.get("allow_partial_inventory_buy", True)),
            buy_flow_requires_confirmation=bool(data.get("buy_flow_requires_confirmation", True)),
            verified_reentry_mode=str(data.get("verified_reentry_mode", "")),
            disallowed_behaviors=[str(item) for item in data.get("disallowed_behaviors", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class MerchantCommissionMeowDecisionContract:
    allowed_decisions: list[str] = field(default_factory=list)
    reason_ids: list[str] = field(default_factory=list)
    decision_signal_keys: list[str] = field(default_factory=list)
    required_evidence_fields: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "allowed_decisions": self.allowed_decisions,
                "reason_ids": self.reason_ids,
                "decision_signal_keys": self.decision_signal_keys,
                "required_evidence_fields": self.required_evidence_fields,
                "notes": self.notes,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            allowed_decisions=[str(item) for item in data.get("allowed_decisions", [])],
            reason_ids=[str(item) for item in data.get("reason_ids", [])],
            decision_signal_keys=[str(item) for item in data.get("decision_signal_keys", [])],
            required_evidence_fields=[str(item) for item in data.get("required_evidence_fields", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class MerchantCommissionMeowRoundEvidence:
    round_index: int = 0
    material_label: str = ""
    current_quantity: int | None = None
    required_quantity: int | None = None
    submit_panel_visible: bool = False
    buy_now_visible: bool = False
    submit_button_visible: bool = False
    empty_inventory_feedback_visible: bool = False
    buy_confirmation_visible: bool = False
    buy_confirm_button_visible: bool = False
    zeny_cost: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def material_progress(self) -> str:
        if self.current_quantity is None or self.required_quantity is None:
            return ""
        return f"{self.current_quantity}/{self.required_quantity}"

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "round_index": self.round_index,
                "material_label": self.material_label,
                "current_quantity": self.current_quantity,
                "required_quantity": self.required_quantity,
                "submit_panel_visible": self.submit_panel_visible,
                "buy_now_visible": self.buy_now_visible,
                "submit_button_visible": self.submit_button_visible,
                "empty_inventory_feedback_visible": self.empty_inventory_feedback_visible,
                "buy_confirmation_visible": self.buy_confirmation_visible,
                "buy_confirm_button_visible": self.buy_confirm_button_visible,
                "zeny_cost": self.zeny_cost,
                "material_progress": self.material_progress,
                "evidence": self.evidence,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            round_index=int(data.get("round_index", 0)),
            material_label=str(data.get("material_label", "")),
            current_quantity=_optional_int(data.get("current_quantity")),
            required_quantity=_optional_int(data.get("required_quantity")),
            submit_panel_visible=bool(data.get("submit_panel_visible", False)),
            buy_now_visible=bool(data.get("buy_now_visible", False)),
            submit_button_visible=bool(data.get("submit_button_visible", False)),
            empty_inventory_feedback_visible=bool(
                data.get("empty_inventory_feedback_visible", False)
            ),
            buy_confirmation_visible=bool(data.get("buy_confirmation_visible", False)),
            buy_confirm_button_visible=bool(data.get("buy_confirm_button_visible", False)),
            zeny_cost=_optional_int(data.get("zeny_cost")),
            evidence=dict(data.get("evidence", {})),
        )


@dataclass(slots=True)
class MerchantCommissionMeowRoundDecision:
    decision: MerchantCommissionMeowDecisionValue
    reason_id: str
    round_index: int
    material_label: str = ""
    material_progress: str = ""
    buy_required: bool = False
    zeny_cost: int | None = None
    reentry_mode: str = ""
    requires_buy_confirmation: bool = False
    evidence: MerchantCommissionMeowRoundEvidence = field(
        default_factory=MerchantCommissionMeowRoundEvidence
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "decision": self.decision.value,
                "reason_id": self.reason_id,
                "round_index": self.round_index,
                "material_label": self.material_label,
                "material_progress": self.material_progress,
                "buy_required": self.buy_required,
                "zeny_cost": self.zeny_cost,
                "reentry_mode": self.reentry_mode,
                "requires_buy_confirmation": self.requires_buy_confirmation,
                "evidence": self.evidence.to_dict(),
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_decision = data.get(
            "decision", MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR.value
        )
        decision = (
            raw_decision
            if isinstance(raw_decision, MerchantCommissionMeowDecisionValue)
            else MerchantCommissionMeowDecisionValue(str(raw_decision))
        )
        return cls(
            decision=decision,
            reason_id=str(data.get("reason_id", "")),
            round_index=int(data.get("round_index", 0)),
            material_label=str(data.get("material_label", "")),
            material_progress=str(data.get("material_progress", "")),
            buy_required=bool(data.get("buy_required", False)),
            zeny_cost=_optional_int(data.get("zeny_cost")),
            reentry_mode=str(data.get("reentry_mode", "")),
            requires_buy_confirmation=bool(data.get("requires_buy_confirmation", False)),
            evidence=MerchantCommissionMeowRoundEvidence.from_dict(
                dict(data.get("evidence", {}))
            ),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class MerchantCommissionMeowSpecification:
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
    route_contract: MerchantCommissionMeowRouteContract = field(
        default_factory=MerchantCommissionMeowRouteContract
    )
    loop_contract: MerchantCommissionMeowLoopContract = field(
        default_factory=MerchantCommissionMeowLoopContract
    )
    submission_policy: MerchantCommissionMeowSubmissionPolicy = field(
        default_factory=MerchantCommissionMeowSubmissionPolicy
    )
    decision_contract: MerchantCommissionMeowDecisionContract = field(
        default_factory=MerchantCommissionMeowDecisionContract
    )
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
                "route_contract": self.route_contract.to_dict(),
                "loop_contract": self.loop_contract.to_dict(),
                "submission_policy": self.submission_policy.to_dict(),
                "decision_contract": self.decision_contract.to_dict(),
                "metadata": self.metadata,
            }
        )


def load_merchant_commission_meow_blueprint(
    repository: TaskFoundationRepository | None = None,
) -> TaskBlueprint:
    repo = repository or TaskFoundationRepository.load_default()
    return repo.load_blueprint(repo.root / "packs" / "daily_ui" / "merchant_commission_meow.task.json")


def load_merchant_commission_meow_route_contract(
    repository: TaskFoundationRepository | None = None,
) -> MerchantCommissionMeowRouteContract:
    blueprint = load_merchant_commission_meow_blueprint(repository)
    return MerchantCommissionMeowRouteContract.from_dict(
        _metadata_dict(blueprint.metadata, "merchant_commission_meow_route_contract"),
    )


def load_merchant_commission_meow_loop_contract(
    repository: TaskFoundationRepository | None = None,
) -> MerchantCommissionMeowLoopContract:
    blueprint = load_merchant_commission_meow_blueprint(repository)
    return MerchantCommissionMeowLoopContract.from_dict(
        _metadata_dict(blueprint.metadata, "merchant_commission_meow_loop_contract"),
    )


def load_merchant_commission_meow_submission_policy(
    repository: TaskFoundationRepository | None = None,
) -> MerchantCommissionMeowSubmissionPolicy:
    blueprint = load_merchant_commission_meow_blueprint(repository)
    return MerchantCommissionMeowSubmissionPolicy.from_dict(
        _metadata_dict(blueprint.metadata, "merchant_commission_meow_submission_policy"),
    )


def load_merchant_commission_meow_decision_contract(
    repository: TaskFoundationRepository | None = None,
) -> MerchantCommissionMeowDecisionContract:
    blueprint = load_merchant_commission_meow_blueprint(repository)
    return MerchantCommissionMeowDecisionContract.from_dict(
        _metadata_dict(blueprint.metadata, "merchant_commission_meow_decision_contract"),
    )


def evaluate_merchant_commission_meow_round_decision(
    *,
    round_evidence: MerchantCommissionMeowRoundEvidence,
    submission_policy: MerchantCommissionMeowSubmissionPolicy | None = None,
    loop_contract: MerchantCommissionMeowLoopContract | None = None,
) -> MerchantCommissionMeowRoundDecision:
    policy = submission_policy or load_merchant_commission_meow_submission_policy()
    resolved_loop_contract = loop_contract or load_merchant_commission_meow_loop_contract()
    material_progress = round_evidence.material_progress
    base_metadata = {
        "merchant_group_label": resolved_loop_contract.merchant_group_label,
        "round_limit": resolved_loop_contract.round_limit,
        "material_progress": material_progress,
        "buy_confirmation_visible": round_evidence.buy_confirmation_visible,
        "buy_confirm_button_visible": round_evidence.buy_confirm_button_visible,
        "submit_panel_visible": round_evidence.submit_panel_visible,
    }

    if not round_evidence.submit_panel_visible:
        return _build_round_decision(
            decision=MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR,
            reason=MerchantCommissionMeowDecisionReason.SUBMIT_PANEL_UNAVAILABLE,
            round_evidence=round_evidence,
            loop_contract=resolved_loop_contract,
            metadata=base_metadata,
        )

    if (
        round_evidence.current_quantity is not None
        and round_evidence.required_quantity is not None
        and round_evidence.current_quantity >= round_evidence.required_quantity
    ):
        if round_evidence.submit_button_visible:
            return _build_round_decision(
                decision=MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT,
                reason=MerchantCommissionMeowDecisionReason.MATERIALS_READY,
                round_evidence=round_evidence,
                loop_contract=resolved_loop_contract,
                metadata=base_metadata,
            )
        return _build_round_decision(
            decision=MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR,
            reason=MerchantCommissionMeowDecisionReason.SUBMIT_BUTTON_UNAVAILABLE,
            round_evidence=round_evidence,
            loop_contract=resolved_loop_contract,
            metadata=base_metadata,
        )

    if not policy.allow_immediate_buy:
        return _build_round_decision(
            decision=MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR,
            reason=MerchantCommissionMeowDecisionReason.IMMEDIATE_BUY_DISABLED,
            round_evidence=round_evidence,
            loop_contract=resolved_loop_contract,
            buy_required=True,
            metadata=base_metadata,
        )

    if round_evidence.buy_now_visible:
        return _build_round_decision(
            decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT,
            reason=MerchantCommissionMeowDecisionReason.BUY_REQUIRED,
            round_evidence=round_evidence,
            loop_contract=resolved_loop_contract,
            buy_required=True,
            requires_buy_confirmation=policy.buy_flow_requires_confirmation,
            metadata=base_metadata,
        )

    if round_evidence.empty_inventory_feedback_visible or not round_evidence.submit_button_visible:
        return _build_round_decision(
            decision=MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR,
            reason=MerchantCommissionMeowDecisionReason.BUY_NOW_UNAVAILABLE,
            round_evidence=round_evidence,
            loop_contract=resolved_loop_contract,
            buy_required=True,
            metadata=base_metadata,
        )

    return _build_round_decision(
        decision=MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR,
        reason=MerchantCommissionMeowDecisionReason.ROUND_STATE_UNKNOWN,
        round_evidence=round_evidence,
        loop_contract=resolved_loop_contract,
        metadata=base_metadata,
    )


def build_merchant_commission_meow_specification(
    *,
    builder_input: TaskRuntimeBuilderInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> MerchantCommissionMeowSpecification:
    repo = foundation_repository or TaskFoundationRepository.load_default()
    resolved_builder_input = builder_input or repo.build_runtime_builder_input(
        "daily_ui.merchant_commission_meow"
    )
    if resolved_builder_input.task_id != "daily_ui.merchant_commission_meow":
        raise ValueError(
            "build_merchant_commission_meow_specification only supports daily_ui.merchant_commission_meow"
        )

    resolved_readiness_report = readiness_report or repo.evaluate_task_readiness(
        resolved_builder_input.task_id
    )
    if resolved_readiness_report.task_id != resolved_builder_input.task_id:
        raise ValueError(
            "Merchant commission meow readiness report does not match the runtime builder input task id"
        )

    blueprint = load_merchant_commission_meow_blueprint(repo)
    fixture_profile_path = _select_fixture_profile_path(resolved_builder_input)
    fixture_profile = repo.load_fixture_profile(repo.root / fixture_profile_path)
    metadata_source = dict(resolved_builder_input.metadata)
    blueprint_metadata = dict(blueprint.metadata)

    return MerchantCommissionMeowSpecification(
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
            if case.screen_slug
            not in _metadata_string_list(metadata_source, "supporting_golden_screen_slugs")
        ],
        supporting_screen_slugs=_metadata_string_list(
            metadata_source, "supporting_golden_screen_slugs"
        ),
        route_contract=MerchantCommissionMeowRouteContract.from_dict(
            _metadata_dict(metadata_source, "merchant_commission_meow_route_contract")
            or _metadata_dict(blueprint_metadata, "merchant_commission_meow_route_contract")
        ),
        loop_contract=MerchantCommissionMeowLoopContract.from_dict(
            _metadata_dict(metadata_source, "merchant_commission_meow_loop_contract")
            or _metadata_dict(blueprint_metadata, "merchant_commission_meow_loop_contract")
        ),
        submission_policy=MerchantCommissionMeowSubmissionPolicy.from_dict(
            _metadata_dict(metadata_source, "merchant_commission_meow_submission_policy")
            or _metadata_dict(blueprint_metadata, "merchant_commission_meow_submission_policy")
        ),
        decision_contract=MerchantCommissionMeowDecisionContract.from_dict(
            _metadata_dict(metadata_source, "merchant_commission_meow_decision_contract")
            or _metadata_dict(blueprint_metadata, "merchant_commission_meow_decision_contract")
        ),
        metadata={
            "signal_contract_version": str(metadata_source.get("signal_contract_version", "")),
            "merchant_commission_meow_spec_builders": _metadata_dict(
                metadata_source, "merchant_commission_meow_spec_builders"
            ),
            "merchant_commission_meow_handoff_fields": _metadata_string_list(
                metadata_source, "merchant_commission_meow_handoff_fields"
            ),
            "implementation_state": str(
                resolved_readiness_report.metadata.get("implementation_state", "")
            ),
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
    if value in ("", None):
        return None
    return int(value)


def _select_fixture_profile_path(builder_input: TaskRuntimeBuilderInput) -> str:
    if not builder_input.fixture_profile_paths:
        raise ValueError(
            "Merchant commission meow specification requires at least one fixture profile path"
        )
    return builder_input.fixture_profile_paths[0]


def _build_round_decision(
    *,
    decision: MerchantCommissionMeowDecisionValue,
    reason: MerchantCommissionMeowDecisionReason,
    round_evidence: MerchantCommissionMeowRoundEvidence,
    loop_contract: MerchantCommissionMeowLoopContract,
    buy_required: bool = False,
    requires_buy_confirmation: bool = False,
    metadata: dict[str, Any] | None = None,
) -> MerchantCommissionMeowRoundDecision:
    return MerchantCommissionMeowRoundDecision(
        decision=decision,
        reason_id=reason.value,
        round_index=round_evidence.round_index,
        material_label=round_evidence.material_label,
        material_progress=round_evidence.material_progress,
        buy_required=buy_required,
        zeny_cost=round_evidence.zeny_cost,
        reentry_mode=loop_contract.preferred_reentry_mode,
        requires_buy_confirmation=requires_buy_confirmation,
        evidence=round_evidence,
        metadata=dict(metadata or {}),
    )
