from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from json import loads
from pathlib import Path
import re
import subprocess
import textwrap
import time
from typing import Any, Protocol, Self

from roxauto.core.models import InstanceState, TaskManifest, TaskSpec
from roxauto.core.runtime import TaskExecutionContext, TaskStep, step_failure, step_success
from roxauto.core.serde import to_primitive
from roxauto.emulator.execution import EmulatorActionAdapter
from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import (
    TaskBlueprint,
    TaskFixtureProfile,
    TaskReadinessReport,
    TaskRuntimeBuilderInput,
    TaskStepBlueprint,
)

_GUILD_ORDER_TASK_ID = "daily_ui.guild_order_submit"
_INSPECTION_CONTEXT_KEY = "daily_ui.guild_order_submit.inspection"
_DECISION_CONTEXT_KEY = "daily_ui.guild_order_submit.decision"
_PRE_ACTION_SIGNATURE_CONTEXT_KEY = "daily_ui.guild_order_submit.pre_action_signature"
_REFRESH_COUNT_CONTEXT_KEY = "daily_ui.guild_order_submit.refresh_attempt_count"
_RUNTIME_INPUT_BUILDER_PATH = (
    "roxauto.tasks.daily_ui.guild_order_submit.build_guild_order_submit_runtime_input"
)
_RUNTIME_SEAM_BUILDER_PATH = (
    "roxauto.tasks.daily_ui.guild_order_submit.build_guild_order_submit_runtime_seam"
)
_TASK_SPEC_BUILDER_PATH = "roxauto.tasks.daily_ui.guild_order_submit.build_guild_order_submit_task_spec"
_RUNTIME_BRIDGE_PROBE_PATH = (
    "roxauto.tasks.daily_ui.guild_order_submit.has_guild_order_submit_runtime_bridge"
)
_SIGNAL_CONTRACT_VERSION = "guild_order_submit.v2"
_ACTION_DISPATCH_SUCCESS_STATUSES = frozenset({"completed", "partial", "executed", "routed"})
_ROUTE_ATTEMPT_LIMIT = 8
_STATE_VERIFICATION_RETRY_LIMIT = 2
_RESULT_SIGNAL_KEYS = (
    "decision",
    "reason_id",
    "slot_index",
    "order_kind",
    "requirements",
    "availability",
    "custom_options",
    "selected_custom_option",
    "refresh_attempted",
    "verification_state",
    "failure_reason_id",
    "inspection_attempts",
    "outcome_code",
    "step_outcome",
    "task_action",
    "telemetry",
    "text_evidence",
)
_GUILD_ORDER_SLOT_POINTS: tuple[tuple[int, int], ...] = (
    (110, 359),
    (279, 359),
    (478, 359),
    (677, 359),
    (845, 359),
    (110, 615),
    (279, 615),
    (478, 615),
    (677, 615),
    (845, 615),
)


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
    CUSTOM_ORDER_SELECTED_CANDIDATE_MISSING = "custom_order_selected_candidate_missing"
    CUSTOM_ORDER_SELECTED_CANDIDATE_BLOCKED = "custom_order_selected_candidate_blocked"
    CUSTOM_ORDER_SELECTED_CANDIDATE_INSUFFICIENT = "custom_order_selected_candidate_insufficient"
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


class GuildOrderSceneState(str, Enum):
    UNKNOWN = "unknown"
    CARNIVAL_HUB = "carnival_hub"
    GUILD_ORDER_CARD_MODAL = "guild_order_card_modal"
    GUILD_PANEL = "guild_panel"
    GUILD_ACTIVITY = "guild_activity"
    GUILD_ORDER_SCENE = "guild_order_scene"


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


@dataclass(slots=True)
class GuildOrderObservedTextEvidence:
    raw_text: str
    normalized_text: str
    bbox: tuple[int, int, int, int]
    confidence: float | None
    screenshot_ref: str
    reader: str

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "raw_text": self.raw_text,
                "normalized_text": self.normalized_text,
                "bbox": self.bbox,
                "confidence": self.confidence,
                "screenshot_ref": self.screenshot_ref,
                "reader": self.reader,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            raw_text=str(data.get("raw_text", "")),
            normalized_text=str(data.get("normalized_text", "")),
            bbox=_tuple_int_quad(data.get("bbox")),
            confidence=_optional_float(data.get("confidence")),
            screenshot_ref=str(data.get("screenshot_ref", "")),
            reader=str(data.get("reader", "")),
        )

    def canonical_text(self) -> str:
        return _canonical_text(self.normalized_text or self.raw_text)

    def center(self) -> tuple[int, int]:
        x, y, width, height = self.bbox
        return (x + width // 2, y + height // 2)


@dataclass(slots=True)
class GuildOrderInspection:
    scene_state: GuildOrderSceneState
    screenshot_path: str
    text_evidence: list[GuildOrderObservedTextEvidence] = field(default_factory=list)
    slot_index: int | None = None
    order_kind: GuildOrderOrderKind = GuildOrderOrderKind.STANDARD
    requirement: GuildOrderRequirement | None = None
    availability: GuildOrderAvailability | None = None
    detail_signature: str = ""
    order_state_known: bool = False
    order_completed: bool = False
    submit_affordance_visible: bool = False
    refresh_affordance_visible: bool = False
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "scene_state": self.scene_state.value,
                "screenshot_path": self.screenshot_path,
                "text_evidence": [item.to_dict() for item in self.text_evidence],
                "slot_index": self.slot_index,
                "order_kind": self.order_kind.value,
                "requirement": self.requirement.to_dict() if self.requirement is not None else None,
                "availability": self.availability.to_dict() if self.availability is not None else None,
                "detail_signature": self.detail_signature,
                "order_state_known": self.order_state_known,
                "order_completed": self.order_completed,
                "submit_affordance_visible": self.submit_affordance_visible,
                "refresh_affordance_visible": self.refresh_affordance_visible,
                "message": self.message,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_scene_state = data.get("scene_state", GuildOrderSceneState.UNKNOWN.value)
        raw_order_kind = data.get("order_kind", GuildOrderOrderKind.STANDARD.value)
        scene_state = (
            raw_scene_state
            if isinstance(raw_scene_state, GuildOrderSceneState)
            else GuildOrderSceneState(str(raw_scene_state))
        )
        order_kind = (
            raw_order_kind
            if isinstance(raw_order_kind, GuildOrderOrderKind)
            else GuildOrderOrderKind(str(raw_order_kind))
        )
        return cls(
            scene_state=scene_state,
            screenshot_path=str(data.get("screenshot_path", "")),
            text_evidence=[
                GuildOrderObservedTextEvidence.from_dict(dict(item))
                for item in data.get("text_evidence", [])
            ],
            slot_index=_optional_positive_int(data.get("slot_index")),
            order_kind=order_kind,
            requirement=(
                GuildOrderRequirement.from_dict(dict(item))
                if isinstance((item := data.get("requirement")), dict)
                else None
            ),
            availability=(
                GuildOrderAvailability.from_dict(dict(item))
                if isinstance((item := data.get("availability")), dict)
                else None
            ),
            detail_signature=str(data.get("detail_signature", "")),
            order_state_known=bool(data.get("order_state_known", False)),
            order_completed=bool(data.get("order_completed", False)),
            submit_affordance_visible=bool(data.get("submit_affordance_visible", False)),
            refresh_affordance_visible=bool(data.get("refresh_affordance_visible", False)),
            message=str(data.get("message", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class GuildOrderSubmitNavigationPlan:
    activity_button_point: tuple[int, int] = (1042, 47)
    carnival_entry_point: tuple[int, int] = (845, 47)
    guild_order_icon_point: tuple[int, int] = (1084, 392)
    go_now_point: tuple[int, int] = (640, 605)
    guild_activity_tab_point: tuple[int, int] = (573, 94)
    guild_order_card_point: tuple[int, int] = (379, 317)
    refresh_point: tuple[int, int] = (671, 94)
    submit_point: tuple[int, int] = (1115, 606)
    wait_after_activity_open_sec: float = 1.0
    wait_after_carnival_sec: float = 1.0
    wait_after_guild_order_icon_sec: float = 1.0
    wait_after_go_now_sec: float = 4.5
    wait_after_activity_tab_sec: float = 1.2
    wait_after_guild_order_card_sec: float = 1.0
    wait_after_refresh_sec: float = 1.8
    wait_after_submit_sec: float = 2.8
    slot_points: tuple[tuple[int, int], ...] = _GUILD_ORDER_SLOT_POINTS

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "activity_button_point": self.activity_button_point,
                "carnival_entry_point": self.carnival_entry_point,
                "guild_order_icon_point": self.guild_order_icon_point,
                "go_now_point": self.go_now_point,
                "guild_activity_tab_point": self.guild_activity_tab_point,
                "guild_order_card_point": self.guild_order_card_point,
                "refresh_point": self.refresh_point,
                "submit_point": self.submit_point,
                "wait_after_activity_open_sec": self.wait_after_activity_open_sec,
                "wait_after_carnival_sec": self.wait_after_carnival_sec,
                "wait_after_guild_order_icon_sec": self.wait_after_guild_order_icon_sec,
                "wait_after_go_now_sec": self.wait_after_go_now_sec,
                "wait_after_activity_tab_sec": self.wait_after_activity_tab_sec,
                "wait_after_guild_order_card_sec": self.wait_after_guild_order_card_sec,
                "wait_after_refresh_sec": self.wait_after_refresh_sec,
                "wait_after_submit_sec": self.wait_after_submit_sec,
                "slot_points": list(self.slot_points),
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_slot_points = data.get("slot_points")
        slot_points = (
            tuple(_tuple_int_pair(item) for item in raw_slot_points)
            if isinstance(raw_slot_points, list) and raw_slot_points
            else _GUILD_ORDER_SLOT_POINTS
        )
        return cls(
            activity_button_point=_tuple_int_pair(data.get("activity_button_point"), default=(1042, 47)),
            carnival_entry_point=_tuple_int_pair(data.get("carnival_entry_point"), default=(845, 47)),
            guild_order_icon_point=_tuple_int_pair(data.get("guild_order_icon_point"), default=(1084, 392)),
            go_now_point=_tuple_int_pair(data.get("go_now_point"), default=(640, 605)),
            guild_activity_tab_point=_tuple_int_pair(data.get("guild_activity_tab_point"), default=(573, 94)),
            guild_order_card_point=_tuple_int_pair(data.get("guild_order_card_point"), default=(379, 317)),
            refresh_point=_tuple_int_pair(data.get("refresh_point"), default=(671, 94)),
            submit_point=_tuple_int_pair(data.get("submit_point"), default=(1115, 606)),
            wait_after_activity_open_sec=float(data.get("wait_after_activity_open_sec", 1.0)),
            wait_after_carnival_sec=float(data.get("wait_after_carnival_sec", 1.0)),
            wait_after_guild_order_icon_sec=float(data.get("wait_after_guild_order_icon_sec", 1.0)),
            wait_after_go_now_sec=float(data.get("wait_after_go_now_sec", 4.5)),
            wait_after_activity_tab_sec=float(data.get("wait_after_activity_tab_sec", 1.2)),
            wait_after_guild_order_card_sec=float(data.get("wait_after_guild_order_card_sec", 1.0)),
            wait_after_refresh_sec=float(data.get("wait_after_refresh_sec", 1.8)),
            wait_after_submit_sec=float(data.get("wait_after_submit_sec", 2.8)),
            slot_points=slot_points,
        )


@dataclass(slots=True)
class GuildOrderRuntimeStepSpec:
    step_id: str
    action: str
    description: str
    display_name: str
    success_condition: str
    failure_condition: str = ""
    notes: str = ""
    summary: str = ""
    anchor_id: str = ""
    status_texts: dict[str, str] = field(default_factory=dict)
    failure_reason_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "step_id": self.step_id,
                "action": self.action,
                "description": self.description,
                "display_name": self.display_name,
                "success_condition": self.success_condition,
                "failure_condition": self.failure_condition,
                "notes": self.notes,
                "summary": self.summary,
                "anchor_id": self.anchor_id,
                "status_texts": self.status_texts,
                "failure_reason_id": self.failure_reason_id,
                "metadata": self.metadata,
            }
        )


@dataclass(slots=True)
class GuildOrderRuntimeInput:
    task_id: str
    pack_id: str
    manifest_path: str
    manifest: TaskManifest
    builder_input: TaskRuntimeBuilderInput
    readiness_report: TaskReadinessReport
    blueprint: TaskBlueprint
    fixture_profile_path: str
    fixture_profile: TaskFixtureProfile
    material_policy: GuildOrderMaterialPolicy
    decision_contract: GuildOrderDecisionContract
    visibility_contract: GuildOrderVisibilityContract
    required_anchor_ids: list[str] = field(default_factory=list)
    supporting_anchor_ids: list[str] = field(default_factory=list)
    step_specs: list[GuildOrderRuntimeStepSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "task_id": self.task_id,
                "pack_id": self.pack_id,
                "manifest_path": self.manifest_path,
                "fixture_profile_path": self.fixture_profile_path,
                "fixture_id": self.fixture_profile.fixture_id,
                "material_policy": self.material_policy.to_dict(),
                "decision_contract": self.decision_contract.to_dict(),
                "visibility_contract": self.visibility_contract.to_dict(),
                "required_anchor_ids": self.required_anchor_ids,
                "supporting_anchor_ids": self.supporting_anchor_ids,
                "step_specs": [step.to_dict() for step in self.step_specs],
                "builder_input": self.builder_input.to_dict(),
                "implementation_readiness_state": self.readiness_report.implementation_readiness_state.value,
                "warning_requirement_ids": [
                    requirement.requirement_id
                    for requirement in self.readiness_report.warning_requirements
                ],
                "metadata": self.metadata,
            }
        )


@dataclass(slots=True)
class GuildOrderRuntimeSeam:
    task_id: str
    pack_id: str
    runtime_input: GuildOrderRuntimeInput
    signal_contract_version: str
    result_signal_keys: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "task_id": self.task_id,
                "pack_id": self.pack_id,
                "signal_contract_version": self.signal_contract_version,
                "result_signal_keys": self.result_signal_keys,
                "builder_input": self.runtime_input.builder_input.to_dict(),
                "runtime_input": self.runtime_input.to_dict(),
                "metadata": self.metadata,
            }
        )

    def build_task_spec(
        self,
        *,
        adapter: EmulatorActionAdapter,
        navigation_plan: GuildOrderSubmitNavigationPlan | None = None,
        vision_gateway: GuildOrderVisionGateway | None = None,
    ) -> TaskSpec:
        return build_guild_order_submit_task_spec(
            adapter=adapter,
            navigation_plan=navigation_plan,
            runtime_seam=self,
            vision_gateway=vision_gateway,
        )


class GuildOrderVisionGateway(Protocol):
    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> GuildOrderInspection:
        """Inspect one guild-order screenshot and return bounded text evidence."""

def select_guild_order_custom_option(
    *,
    custom_options: list[GuildOrderCustomOption],
    policy: GuildOrderMaterialPolicy,
) -> GuildOrderCustomOption | None:
    ranked_options: list[tuple[tuple[int, int, int, str], GuildOrderCustomOption]] = []
    inspected_options = _limit_custom_order_candidates(custom_options=custom_options, policy=policy)
    explicit_candidate_index = policy.custom_order_selected_candidate_index

    if explicit_candidate_index is not None:
        selected_option, _ = _select_explicit_custom_order_candidate(
            custom_options=inspected_options,
            policy=policy,
        )
        return selected_option

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
            "signal_contract_version": str(
                _metadata_dict(metadata_source, "runtime_seam").get(
                    "signal_contract_version",
                    metadata_source.get("signal_contract_version", ""),
                )
            ),
            "runtime_seam": _metadata_dict(metadata_source, "runtime_seam")
            or _metadata_dict(blueprint_metadata, "runtime_seam"),
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

    inspected_options = _limit_custom_order_candidates(custom_options=custom_options, policy=policy)
    explicit_selection_failure: GuildOrderDecisionReason | None = None
    if policy.custom_order_selected_candidate_index is not None:
        selected_option, explicit_selection_failure = _select_explicit_custom_order_candidate(
            custom_options=inspected_options,
            policy=policy,
        )
    else:
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
        fallback_reason=explicit_selection_failure or GuildOrderDecisionReason.CUSTOM_ORDER_NO_VIABLE_OPTION,
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


def _select_explicit_custom_order_candidate(
    *,
    custom_options: list[GuildOrderCustomOption],
    policy: GuildOrderMaterialPolicy,
) -> tuple[GuildOrderCustomOption | None, GuildOrderDecisionReason | None]:
    explicit_candidate_index = policy.custom_order_selected_candidate_index
    if explicit_candidate_index is None:
        return None, None

    selected_option = next(
        (option for option in custom_options if option.candidate_index == explicit_candidate_index),
        None,
    )
    if selected_option is None:
        return None, GuildOrderDecisionReason.CUSTOM_ORDER_SELECTED_CANDIDATE_MISSING

    if not _is_material_allowed(
        policy,
        normalized_material_id=selected_option.normalized_material_id,
        material_label=selected_option.material_label,
    ):
        return None, GuildOrderDecisionReason.CUSTOM_ORDER_SELECTED_CANDIDATE_BLOCKED

    sufficiency = _resolve_custom_option_sufficiency(selected_option, policy)
    if sufficiency is not GuildOrderMaterialSufficiency.SUFFICIENT:
        return None, GuildOrderDecisionReason.CUSTOM_ORDER_SELECTED_CANDIDATE_INSUFFICIENT

    return _clone_custom_option_with_sufficiency(selected_option, sufficiency), None


def _limit_custom_order_candidates(
    *,
    custom_options: list[GuildOrderCustomOption],
    policy: GuildOrderMaterialPolicy,
) -> list[GuildOrderCustomOption]:
    max_candidates = max(0, policy.custom_order_max_candidates_to_inspect)
    return custom_options[:max_candidates] if max_candidates else []


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


class WindowsOcrGuildOrderVisionGateway:
    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> GuildOrderInspection:
        del instance, metadata
        return _build_guild_order_inspection(
            screenshot_path=screenshot_path,
            text_evidence=_run_windows_ocr_reader(screenshot_path),
        )


def build_guild_order_submit_runtime_input(
    *,
    builder_input: TaskRuntimeBuilderInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> GuildOrderRuntimeInput:
    repo = foundation_repository or TaskFoundationRepository.load_default()
    specification = build_guild_order_submit_specification(
        builder_input=builder_input,
        readiness_report=readiness_report,
        foundation_repository=repo,
    )
    runtime_seam_metadata = _resolve_runtime_seam_metadata(
        builder_input=specification.builder_input,
        blueprint=specification.blueprint,
    )
    material_policy = specification.material_policy
    if material_policy.custom_order_enabled:
        material_policy = replace(
            material_policy,
            custom_order_enabled=False,
            notes=(
                f"{material_policy.notes} V1 runtime explicitly disables custom-order "
                "candidate inspection and records that surface as a truthful skip."
            ).strip(),
        )
    result_signal_keys = runtime_seam_metadata.get("result_signal_keys", list(_RESULT_SIGNAL_KEYS))
    return GuildOrderRuntimeInput(
        task_id=specification.task_id,
        pack_id=specification.pack_id,
        manifest_path=specification.manifest_path,
        manifest=_build_runtime_manifest(specification.blueprint.manifest),
        builder_input=specification.builder_input,
        readiness_report=specification.readiness_report,
        blueprint=specification.blueprint,
        fixture_profile_path=specification.fixture_profile_path,
        fixture_profile=specification.fixture_profile,
        material_policy=material_policy,
        decision_contract=specification.decision_contract,
        visibility_contract=specification.visibility_contract,
        required_anchor_ids=list(specification.required_anchor_ids),
        supporting_anchor_ids=list(specification.supporting_anchor_ids),
        step_specs=_build_runtime_step_specs(specification.blueprint.steps),
        metadata={
            "implementation_state": specification.blueprint.implementation_state.value,
            "runtime_bridge": "roxauto.tasks.daily_ui.guild_order_submit",
            "golden_screen_slugs": [case.screen_slug for case in specification.blueprint.golden_cases],
            "supporting_anchor_ids": list(specification.supporting_anchor_ids),
            "supporting_golden_screen_slugs": list(specification.supporting_screen_slugs),
            "signal_contract_version": str(
                runtime_seam_metadata.get("signal_contract_version", _SIGNAL_CONTRACT_VERSION)
            ),
            "result_signal_keys": (
                [str(item) for item in result_signal_keys]
                if isinstance(result_signal_keys, list)
                else list(_RESULT_SIGNAL_KEYS)
            ),
            "runtime_seam": runtime_seam_metadata,
            "guild_order_spec_builders": dict(specification.metadata.get("guild_order_spec_builders", {})),
            "guild_order_handoff_fields": list(specification.metadata.get("guild_order_handoff_fields", [])),
            "route_basis": "reviewed_live_route_capture_2026_04_25",
            "evidence_contract": {
                "reader": "windows.media.ocr",
                "required_text_fields": [
                    "raw_text",
                    "normalized_text",
                    "bbox",
                    "confidence",
                    "screenshot_ref",
                    "reader",
                ],
            },
        },
    )


def build_guild_order_submit_runtime_seam(
    *,
    runtime_input: GuildOrderRuntimeInput | None = None,
    builder_input: TaskRuntimeBuilderInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> GuildOrderRuntimeSeam:
    resolved_runtime_input = runtime_input or build_guild_order_submit_runtime_input(
        builder_input=builder_input,
        readiness_report=readiness_report,
        foundation_repository=foundation_repository,
    )
    runtime_seam_metadata = dict(
        resolved_runtime_input.metadata.get("runtime_seam", _default_runtime_seam_metadata())
    )
    result_signal_keys = runtime_seam_metadata.get("result_signal_keys", list(_RESULT_SIGNAL_KEYS))
    return GuildOrderRuntimeSeam(
        task_id=resolved_runtime_input.task_id,
        pack_id=resolved_runtime_input.pack_id,
        runtime_input=resolved_runtime_input,
        signal_contract_version=str(
            runtime_seam_metadata.get("signal_contract_version", _SIGNAL_CONTRACT_VERSION)
        ),
        result_signal_keys=(
            [str(item) for item in result_signal_keys]
            if isinstance(result_signal_keys, list)
            else list(_RESULT_SIGNAL_KEYS)
        ),
        metadata={
            **runtime_seam_metadata,
            "implementation_state": str(resolved_runtime_input.metadata.get("implementation_state", "")),
            "required_anchor_ids": list(resolved_runtime_input.required_anchor_ids),
            "supporting_anchor_ids": list(resolved_runtime_input.supporting_anchor_ids),
        },
    )


def build_guild_order_submit_task_spec(
    *,
    adapter: EmulatorActionAdapter,
    navigation_plan: GuildOrderSubmitNavigationPlan | None = None,
    runtime_seam: GuildOrderRuntimeSeam | None = None,
    runtime_input: GuildOrderRuntimeInput | None = None,
    vision_gateway: GuildOrderVisionGateway | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> TaskSpec:
    resolved_runtime_input = runtime_input or (
        runtime_seam.runtime_input if runtime_seam is not None else None
    ) or build_guild_order_submit_runtime_input(
        foundation_repository=foundation_repository,
    )
    resolved_runtime_seam = runtime_seam or build_guild_order_submit_runtime_seam(
        runtime_input=resolved_runtime_input,
    )
    resolved_navigation_plan = navigation_plan or GuildOrderSubmitNavigationPlan()
    bridge = _GuildOrderTaskBridge(
        adapter=adapter,
        vision_gateway=vision_gateway or WindowsOcrGuildOrderVisionGateway(),
        navigation_plan=resolved_navigation_plan,
        runtime_input=resolved_runtime_input,
    )
    handlers = {
        "open_guild_order_list": bridge.open_guild_order_list,
        "inspect_visible_order": bridge.inspect_visible_order,
        "inspect_custom_order_options": bridge.inspect_custom_order_options,
        "decide_material_action": bridge.decide_material_action,
        "apply_material_decision": bridge.apply_material_decision,
        "verify_material_outcome": bridge.verify_material_outcome,
    }
    manifest = resolved_runtime_input.manifest
    return TaskSpec(
        task_id=manifest.task_id,
        name=manifest.name,
        version=manifest.version,
        entry_state="home_hud_visible",
        manifest=manifest,
        steps=[
            TaskStep(step.step_id, step.description, handlers[step.step_id])
            for step in resolved_runtime_input.step_specs
        ],
        metadata={
            **dict(resolved_runtime_input.blueprint.metadata),
            "implementation_state": "fixtured",
            "navigation_plan": resolved_navigation_plan.to_dict(),
            "required_anchor_ids": list(resolved_runtime_input.required_anchor_ids),
            "supporting_anchor_ids": list(resolved_runtime_input.supporting_anchor_ids),
            "runtime_bridge": "roxauto.tasks.daily_ui.guild_order_submit",
            "builder_input": resolved_runtime_input.builder_input.to_dict(),
            "runtime_input": resolved_runtime_input.to_dict(),
            "runtime_seam": resolved_runtime_seam.to_dict(),
            "implementation_readiness_state": (
                resolved_runtime_input.readiness_report.implementation_readiness_state.value
            ),
            "signal_contract_version": resolved_runtime_seam.signal_contract_version,
        },
    )


def has_guild_order_submit_runtime_bridge() -> bool:
    return True


class _GuildOrderTaskBridge:
    def __init__(
        self,
        *,
        adapter: EmulatorActionAdapter,
        vision_gateway: GuildOrderVisionGateway,
        navigation_plan: GuildOrderSubmitNavigationPlan,
        runtime_input: GuildOrderRuntimeInput,
    ) -> None:
        self._adapter = adapter
        self._vision_gateway = vision_gateway
        self._navigation_plan = navigation_plan
        self._runtime_input = runtime_input
        self._step_specs = {step.step_id: step for step in runtime_input.step_specs}

    def open_guild_order_list(self, context: TaskExecutionContext):
        step_id = "open_guild_order_list"
        inspection_attempts: list[dict[str, Any]] = []
        task_actions: list[dict[str, Any]] = []
        last_inspection: GuildOrderInspection | None = None
        for attempt in range(1, _ROUTE_ATTEMPT_LIMIT + 1):
            inspection = self._inspect(context, step_id=step_id, reason="route.inspect")
            inspection_attempts.append({"attempt": attempt, **inspection.to_dict()})
            last_inspection = inspection
            if inspection.scene_state is GuildOrderSceneState.GUILD_ORDER_SCENE:
                self._store_inspection(context, inspection)
                return step_success(
                    step_id,
                    "Guild-order detail scene is reachable through the bounded live route.",
                    screenshot_path=inspection.screenshot_path,
                    data=self._step_data(
                        step_id=step_id,
                        inspection=inspection,
                        inspection_attempts=inspection_attempts,
                        outcome_code="guild_order_scene_reached",
                        telemetry={"task_actions": task_actions},
                    ),
                )
            next_actions = self._route_actions_for_scene(inspection.scene_state)
            if not next_actions:
                break
            for point, wait_sec, reason in next_actions:
                task_action = self._tap(
                    context,
                    step_id=step_id,
                    point=point,
                    reason=reason,
                )
                task_actions.append(task_action)
                if self._dispatch_failed(task_action):
                    return step_failure(
                        step_id,
                        self._dispatch_failure_message(
                            action_name="guild-order route tap",
                            task_action=task_action,
                        ),
                        screenshot_path=inspection.screenshot_path,
                        data=self._step_data(
                            step_id=step_id,
                            inspection=inspection,
                            inspection_attempts=inspection_attempts,
                            failure_reason_id="runtime_dispatch_failed",
                            outcome_code="guild_order_route_dispatch_failed",
                            task_action=task_action,
                            step_outcome={
                                "kind": "dispatch_failed",
                                "failure_reason_id": "runtime_dispatch_failed",
                            },
                            telemetry={"task_actions": task_actions},
                        ),
                    )
                self._sleep(wait_sec)
        return step_failure(
            step_id,
            "Guild-order detail scene could not be reached through the bounded route.",
            screenshot_path=last_inspection.screenshot_path if last_inspection is not None else None,
            data=self._step_data(
                step_id=step_id,
                inspection=last_inspection,
                inspection_attempts=inspection_attempts,
                failure_reason_id="route_unavailable",
                outcome_code="guild_order_scene_unavailable",
                step_outcome={
                    "kind": "navigation_failed",
                    "failure_reason_id": "route_unavailable",
                },
                telemetry={"task_actions": task_actions},
            ),
        )

    def inspect_visible_order(self, context: TaskExecutionContext):
        step_id = "inspect_visible_order"
        inspection = self._inspect(context, step_id=step_id, reason="order.inspect")
        if inspection.scene_state is not GuildOrderSceneState.GUILD_ORDER_SCENE:
            return step_failure(
                step_id,
                "Guild-order detail scene is not visible for bounded material inspection.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    failure_reason_id="route_unavailable",
                    outcome_code="guild_order_scene_missing",
                    step_outcome={
                        "kind": "vision_failed",
                        "failure_reason_id": "route_unavailable",
                    },
                ),
            )
        if inspection.order_kind is GuildOrderOrderKind.CUSTOM:
            self._store_inspection(context, inspection)
            return step_success(
                step_id,
                "Detected a custom guild-order slot and preserved bounded text evidence for the skip decision.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    outcome_code="custom_order_detected",
                ),
            )
        if not inspection.order_state_known:
            return step_failure(
                step_id,
                "Visible guild-order requirement evidence is incomplete, so the task stays blocked.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    failure_reason_id=GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
                    outcome_code="order_state_unknown",
                    step_outcome={
                        "kind": "inspection_failed",
                        "failure_reason_id": GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
                    },
                ),
            )
        self._store_inspection(context, inspection)
        return step_success(
            step_id,
            "Captured bounded visible material evidence for the current standard guild order.",
            screenshot_path=inspection.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=inspection,
                outcome_code="standard_order_state_captured",
            ),
        )

    def inspect_custom_order_options(self, context: TaskExecutionContext):
        step_id = "inspect_custom_order_options"
        inspection = self._stored_inspection(context)
        if inspection is None:
            return step_failure(
                step_id,
                "Guild-order inspection state is unavailable for the custom-order checkpoint.",
                data=self._step_data(
                    step_id=step_id,
                    failure_reason_id="inspection_state_missing",
                    outcome_code="inspection_state_missing",
                    step_outcome={
                        "kind": "inspection_failed",
                        "failure_reason_id": "inspection_state_missing",
                    },
                ),
            )
        if inspection.order_kind is not GuildOrderOrderKind.CUSTOM:
            return step_success(
                step_id,
                "Current guild order is standard, so no custom-order candidate inspection is required.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    outcome_code="custom_order_not_present",
                ),
            )
        if not self._runtime_input.material_policy.custom_order_enabled:
            return step_success(
                step_id,
                "V1 runtime keeps custom-order option inspection disabled and will record a truthful skip.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    outcome_code="custom_order_disabled",
                ),
            )
        return step_failure(
            step_id,
            "Custom-order option inspection is intentionally blocked in V1.",
            screenshot_path=inspection.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=inspection,
                failure_reason_id="custom_order_blocked",
                outcome_code="custom_order_blocked",
                step_outcome={
                    "kind": "blocked",
                    "failure_reason_id": "custom_order_blocked",
                },
            ),
        )

    def decide_material_action(self, context: TaskExecutionContext):
        step_id = "decide_material_action"
        inspection = self._stored_inspection(context)
        if inspection is None:
            return step_failure(
                step_id,
                "Guild-order inspection state is unavailable for policy evaluation.",
                data=self._step_data(
                    step_id=step_id,
                    failure_reason_id="inspection_state_missing",
                    outcome_code="inspection_state_missing",
                    step_outcome={
                        "kind": "inspection_failed",
                        "failure_reason_id": "inspection_state_missing",
                    },
                ),
            )
        slot_index = inspection.slot_index or len(self._navigation_plan.slot_points)
        refresh_attempt_count = int(context.metadata.get(_REFRESH_COUNT_CONTEXT_KEY, 0))
        decision = evaluate_guild_order_submit_decision(
            slot_index=slot_index,
            order_kind=inspection.order_kind,
            policy=self._runtime_input.material_policy,
            requirements=[inspection.requirement] if inspection.requirement is not None else [],
            availability=[inspection.availability] if inspection.availability is not None else [],
            custom_options=[],
            refresh_attempt_count=refresh_attempt_count,
            order_completed=inspection.order_completed,
            order_state_known=inspection.order_kind is GuildOrderOrderKind.CUSTOM or inspection.order_state_known,
            custom_order_list_visible=False,
        )
        self._store_decision(context, decision)
        return step_success(
            step_id,
            f"Selected bounded guild-order action `{decision.decision.value}` from visible evidence only.",
            screenshot_path=inspection.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=inspection,
                decision=decision,
                outcome_code=f"decision_{decision.decision.value}",
                step_outcome={
                    "kind": "decision",
                    "decision": decision.decision.value,
                    "reason_id": decision.reason_id,
                },
            ),
        )

    def apply_material_decision(self, context: TaskExecutionContext):
        step_id = "apply_material_decision"
        inspection = self._stored_inspection(context)
        decision = self._stored_decision(context)
        if decision is None:
            return step_failure(
                step_id,
                "Guild-order decision state is unavailable for action application.",
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    failure_reason_id="decision_state_missing",
                    outcome_code="decision_state_missing",
                    step_outcome={
                        "kind": "decision_failed",
                        "failure_reason_id": "decision_state_missing",
                    },
                ),
            )
        if decision.decision is GuildOrderDecisionValue.SKIP:
            if inspection is not None and inspection.detail_signature:
                context.metadata[_PRE_ACTION_SIGNATURE_CONTEXT_KEY] = inspection.detail_signature
            verified_skip = replace(
                decision,
                verification_state=GuildOrderVerificationState.SKIP_RECORDED,
            )
            self._store_decision(context, verified_skip)
            return step_success(
                step_id,
                f"Recorded skip decision `{verified_skip.reason_id}` without widening the workflow.",
                screenshot_path=inspection.screenshot_path if inspection is not None else None,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    decision=verified_skip,
                    outcome_code="skip_recorded",
                    step_outcome={
                        "kind": "decision_applied",
                        "decision": verified_skip.decision.value,
                        "reason_id": verified_skip.reason_id,
                    },
                ),
            )
        if inspection is None or not inspection.detail_signature:
            return step_failure(
                step_id,
                "Guild-order detail signature is unavailable, so submit/refresh cannot be verified honestly.",
                screenshot_path=inspection.screenshot_path if inspection is not None else None,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    decision=decision,
                    failure_reason_id=GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
                    outcome_code="detail_signature_missing",
                    step_outcome={
                        "kind": "blocked",
                        "failure_reason_id": GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
                    },
                ),
            )
        context.metadata[_PRE_ACTION_SIGNATURE_CONTEXT_KEY] = inspection.detail_signature
        if decision.decision is GuildOrderDecisionValue.SUBMIT:
            task_action = self._tap(
                context,
                step_id=step_id,
                point=self._navigation_plan.submit_point,
                reason="decision.submit",
            )
            wait_sec = self._navigation_plan.wait_after_submit_sec
            outcome_code = "submit_applied"
            action_name = "guild-order submit tap"
        else:
            task_action = self._tap(
                context,
                step_id=step_id,
                point=self._navigation_plan.refresh_point,
                reason="decision.refresh",
            )
            wait_sec = self._navigation_plan.wait_after_refresh_sec
            outcome_code = "refresh_applied"
            action_name = "guild-order refresh tap"
            decision = replace(decision, refresh_attempted=True)
            context.metadata[_REFRESH_COUNT_CONTEXT_KEY] = int(context.metadata.get(_REFRESH_COUNT_CONTEXT_KEY, 0)) + 1
            self._store_decision(context, decision)
        if self._dispatch_failed(task_action):
            return step_failure(
                step_id,
                self._dispatch_failure_message(action_name=action_name, task_action=task_action),
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    decision=decision,
                    failure_reason_id="runtime_dispatch_failed",
                    outcome_code=f"{decision.decision.value}_dispatch_failed",
                    task_action=task_action,
                    step_outcome={
                        "kind": "dispatch_failed",
                        "failure_reason_id": "runtime_dispatch_failed",
                    },
                ),
            )
        self._sleep(wait_sec)
        return step_success(
            step_id,
            f"Applied bounded `{decision.decision.value}` action on the guild-order detail scene.",
            screenshot_path=inspection.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=inspection,
                decision=decision,
                outcome_code=outcome_code,
                task_action=task_action,
                step_outcome={
                    "kind": "decision_applied",
                    "decision": decision.decision.value,
                    "reason_id": decision.reason_id,
                },
                telemetry={"pre_action_signature": inspection.detail_signature},
            ),
        )

    def verify_material_outcome(self, context: TaskExecutionContext):
        step_id = "verify_material_outcome"
        inspection = self._stored_inspection(context)
        decision = self._stored_decision(context)
        if decision is None:
            return step_failure(
                step_id,
                "Guild-order decision state is unavailable for verification.",
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    failure_reason_id="decision_state_missing",
                    outcome_code="decision_state_missing",
                    step_outcome={
                        "kind": "verification_failed",
                        "failure_reason_id": "decision_state_missing",
                    },
                ),
            )
        if decision.decision is GuildOrderDecisionValue.SKIP:
            verified_skip = replace(
                decision,
                verification_state=GuildOrderVerificationState.SKIP_RECORDED,
            )
            self._store_decision(context, verified_skip)
            return step_success(
                step_id,
                "Skip path is explicit and requires no extra UI mutation.",
                screenshot_path=inspection.screenshot_path if inspection is not None else None,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    decision=verified_skip,
                    outcome_code="skip_verified",
                    step_outcome={
                        "kind": "verified",
                        "verification_state": verified_skip.verification_state.value,
                    },
                ),
            )
        pre_action_signature = str(context.metadata.get(_PRE_ACTION_SIGNATURE_CONTEXT_KEY, "")).strip()
        if not pre_action_signature:
            return step_failure(
                step_id,
                "Pre-action guild-order signature is missing, so verification stays blocked.",
                screenshot_path=inspection.screenshot_path if inspection is not None else None,
                data=self._step_data(
                    step_id=step_id,
                    inspection=inspection,
                    decision=decision,
                    failure_reason_id=GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
                    outcome_code="pre_action_signature_missing",
                    step_outcome={
                        "kind": "verification_failed",
                        "failure_reason_id": GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
                    },
                ),
            )
        inspection_attempts: list[dict[str, Any]] = []
        last_inspection = inspection
        for attempt in range(1, _STATE_VERIFICATION_RETRY_LIMIT + 1):
            current_inspection = self._inspect(
                context,
                step_id=step_id,
                reason=f"verify.{decision.decision.value}",
            )
            inspection_attempts.append({"attempt": attempt, **current_inspection.to_dict()})
            last_inspection = current_inspection
            if (
                current_inspection.scene_state is GuildOrderSceneState.GUILD_ORDER_SCENE
                and current_inspection.detail_signature
                and current_inspection.detail_signature != pre_action_signature
            ):
                verification_state = (
                    GuildOrderVerificationState.SUBMIT_VERIFIED
                    if decision.decision is GuildOrderDecisionValue.SUBMIT
                    else GuildOrderVerificationState.REFRESH_VERIFIED
                )
                verified_decision = replace(
                    decision,
                    verification_state=verification_state,
                    refresh_attempted=decision.refresh_attempted
                    or decision.decision is GuildOrderDecisionValue.REFRESH,
                )
                self._store_inspection(context, current_inspection)
                self._store_decision(context, verified_decision)
                return step_success(
                    step_id,
                    f"Verified `{decision.decision.value}` by observing a new guild-order detail signature.",
                    screenshot_path=current_inspection.screenshot_path,
                    data=self._step_data(
                        step_id=step_id,
                        inspection=current_inspection,
                        decision=verified_decision,
                        inspection_attempts=inspection_attempts,
                        outcome_code=f"{decision.decision.value}_verified",
                        step_outcome={
                            "kind": "verified",
                            "verification_state": verification_state.value,
                        },
                        telemetry={
                            "pre_action_signature": pre_action_signature,
                            "post_action_signature": current_inspection.detail_signature,
                        },
                    ),
                )
        failure_reason = (
            GuildOrderDecisionReason.SUBMIT_VERIFICATION_FAILED
            if decision.decision is GuildOrderDecisionValue.SUBMIT
            else GuildOrderDecisionReason.REFRESH_VERIFICATION_FAILED
        )
        failed_decision = replace(
            decision,
            reason_id=failure_reason.value,
            verification_state=GuildOrderVerificationState.VERIFICATION_FAILED,
            refresh_attempted=decision.refresh_attempted
            or decision.decision is GuildOrderDecisionValue.REFRESH,
        )
        if last_inspection is not None:
            self._store_inspection(context, last_inspection)
        self._store_decision(context, failed_decision)
        return step_failure(
            step_id,
            f"Could not verify `{decision.decision.value}` from bounded post-action guild-order evidence.",
            screenshot_path=last_inspection.screenshot_path if last_inspection is not None else None,
            data=self._step_data(
                step_id=step_id,
                inspection=last_inspection,
                decision=failed_decision,
                inspection_attempts=inspection_attempts,
                failure_reason_id=failure_reason.value,
                outcome_code=f"{decision.decision.value}_verification_failed",
                step_outcome={
                    "kind": "verification_failed",
                    "failure_reason_id": failure_reason.value,
                    "verification_state": GuildOrderVerificationState.VERIFICATION_FAILED.value,
                },
                telemetry={
                    "pre_action_signature": pre_action_signature,
                    "attempt_count": len(inspection_attempts),
                },
            ),
        )

    def _route_actions_for_scene(
        self,
        scene_state: GuildOrderSceneState,
    ) -> list[tuple[tuple[int, int], float, str]]:
        if scene_state is GuildOrderSceneState.UNKNOWN:
            return [
                (
                    self._navigation_plan.activity_button_point,
                    self._navigation_plan.wait_after_activity_open_sec,
                    "route.tap_activity_button",
                ),
                (
                    self._navigation_plan.carnival_entry_point,
                    self._navigation_plan.wait_after_carnival_sec,
                    "route.tap_carnival_entry",
                ),
            ]
        if scene_state is GuildOrderSceneState.CARNIVAL_HUB:
            return [
                (
                    self._navigation_plan.guild_order_icon_point,
                    self._navigation_plan.wait_after_guild_order_icon_sec,
                    "route.tap_guild_order_icon",
                )
            ]
        if scene_state is GuildOrderSceneState.GUILD_ORDER_CARD_MODAL:
            return [
                (
                    self._navigation_plan.go_now_point,
                    self._navigation_plan.wait_after_go_now_sec,
                    "route.tap_go_now",
                )
            ]
        if scene_state is GuildOrderSceneState.GUILD_PANEL:
            return [
                (
                    self._navigation_plan.guild_activity_tab_point,
                    self._navigation_plan.wait_after_activity_tab_sec,
                    "route.tap_activity_tab",
                )
            ]
        if scene_state is GuildOrderSceneState.GUILD_ACTIVITY:
            return [
                (
                    self._navigation_plan.guild_order_card_point,
                    self._navigation_plan.wait_after_guild_order_card_sec,
                    "route.tap_guild_order_card",
                )
            ]
        return []

    def _inspect(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        reason: str,
    ) -> GuildOrderInspection:
        screenshot_path = self._capture_screenshot(
            context,
            step_id=step_id,
            reason=reason,
        )
        inspection = self._vision_gateway.inspect(
            instance=context.instance,
            screenshot_path=screenshot_path,
            metadata={"source": self._runtime_input.task_id, "reason": reason},
        )
        if not inspection.screenshot_path:
            inspection = replace(inspection, screenshot_path=str(screenshot_path))
        return inspection

    def _capture_screenshot(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        reason: str,
    ) -> Path:
        metadata = {"source": self._runtime_input.task_id, "reason": reason}
        if context.action_bridge is not None:
            frame = context.require_action_bridge().capture_preview(step_id=step_id, metadata=metadata)
            if frame is not None:
                return Path(frame.image_path)
        return self._adapter.capture_screenshot(context.instance)

    def _tap(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        point: tuple[int, int],
        reason: str,
    ) -> dict[str, Any]:
        metadata = {"source": self._runtime_input.task_id, "reason": reason}
        if context.action_bridge is not None:
            result = context.require_action_bridge().tap(point, step_id=step_id, metadata=metadata)
            return {
                "action": "tap",
                "point": point,
                "status": result.status,
                "message": result.message,
                "source": "task_action_bridge",
                "payload": dict(result.payload),
                "metadata": dict(result.metadata),
            }
        self._adapter.tap(context.instance, point)
        return {
            "action": "tap",
            "point": point,
            "status": "executed",
            "message": "",
            "source": "adapter",
        }

    def _dispatch_failed(self, task_action: dict[str, Any]) -> bool:
        return str(task_action.get("status", "")) not in _ACTION_DISPATCH_SUCCESS_STATUSES

    def _dispatch_failure_message(self, *, action_name: str, task_action: dict[str, Any]) -> str:
        status = str(task_action.get("status", "")).strip() or "unknown"
        message = str(task_action.get("message", "")).strip()
        if message:
            return f"{action_name} failed through the runtime bridge: {message}"
        return f"{action_name} failed through the runtime bridge with status {status}."

    def _store_inspection(self, context: TaskExecutionContext, inspection: GuildOrderInspection) -> None:
        context.metadata[_INSPECTION_CONTEXT_KEY] = inspection.to_dict()

    def _stored_inspection(self, context: TaskExecutionContext) -> GuildOrderInspection | None:
        value = context.metadata.get(_INSPECTION_CONTEXT_KEY)
        return GuildOrderInspection.from_dict(dict(value)) if isinstance(value, dict) else None

    def _store_decision(self, context: TaskExecutionContext, decision: GuildOrderDecision) -> None:
        context.metadata[_DECISION_CONTEXT_KEY] = decision.to_dict()

    def _stored_decision(self, context: TaskExecutionContext) -> GuildOrderDecision | None:
        value = context.metadata.get(_DECISION_CONTEXT_KEY)
        return GuildOrderDecision.from_dict(dict(value)) if isinstance(value, dict) else None

    def _step_data(
        self,
        *,
        step_id: str,
        inspection: GuildOrderInspection | None = None,
        inspection_attempts: list[dict[str, Any]] | None = None,
        decision: GuildOrderDecision | None = None,
        failure_reason_id: str = "",
        outcome_code: str = "",
        task_action: dict[str, Any] | None = None,
        step_outcome: dict[str, Any] | None = None,
        telemetry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "anchor_id": self._step_specs[step_id].anchor_id,
            "inspection_attempts": list(inspection_attempts or []),
            "failure_reason_id": failure_reason_id,
            "outcome_code": outcome_code,
            "runtime_step_spec": self._step_specs[step_id].to_dict(),
            "text_evidence": [
                item.to_dict()
                for item in (inspection.text_evidence if inspection is not None else [])
            ],
        }
        if inspection is not None:
            payload["inspection"] = inspection.to_dict()
            payload["scene_state"] = inspection.scene_state.value
            payload["screenshot_path"] = inspection.screenshot_path
        if decision is not None:
            payload.update(decision.to_dict())
        if task_action is not None:
            payload["task_action"] = task_action
        if step_outcome is not None:
            payload["step_outcome"] = step_outcome
        if telemetry is not None:
            payload["telemetry"] = telemetry
        return payload

    def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


def _default_runtime_seam_metadata() -> dict[str, Any]:
    return {
        "runtime_input_builder": _RUNTIME_INPUT_BUILDER_PATH,
        "runtime_seam_builder": _RUNTIME_SEAM_BUILDER_PATH,
        "task_spec_builder": _TASK_SPEC_BUILDER_PATH,
        "runtime_bridge_probe": _RUNTIME_BRIDGE_PROBE_PATH,
        "signal_contract_version": _SIGNAL_CONTRACT_VERSION,
        "result_signal_keys": list(_RESULT_SIGNAL_KEYS),
    }


def _resolve_runtime_seam_metadata(
    *,
    builder_input: TaskRuntimeBuilderInput,
    blueprint: TaskBlueprint,
) -> dict[str, Any]:
    runtime_seam = _metadata_dict(builder_input.metadata, "runtime_seam") or _metadata_dict(
        blueprint.metadata,
        "runtime_seam",
    )
    return {
        **_default_runtime_seam_metadata(),
        **runtime_seam,
    }


def _build_runtime_manifest(manifest: TaskManifest) -> TaskManifest:
    metadata = dict(manifest.metadata)
    metadata["implementation_state"] = "fixtured"
    metadata["runtime_bridge"] = "roxauto.tasks.daily_ui.guild_order_submit"
    metadata["signal_contract_version"] = _SIGNAL_CONTRACT_VERSION
    return replace(manifest, metadata=metadata)


def _build_runtime_step_specs(
    steps: list[TaskStepBlueprint],
) -> list[GuildOrderRuntimeStepSpec]:
    display_names = {
        "open_guild_order_list": "開啟公會訂單",
        "inspect_visible_order": "讀取當前訂單",
        "inspect_custom_order_options": "確認自選訂單",
        "decide_material_action": "決定 submit / skip / refresh",
        "apply_material_decision": "執行訂單決策",
        "verify_material_outcome": "驗證訂單結果",
    }
    descriptions = {
        "open_guild_order_list": "透過固定入口將畫面帶到可檢查的公會訂單 detail scene。",
        "inspect_visible_order": "讀取目前可見的材料、數量與 slot 證據。",
        "inspect_custom_order_options": "V1 只確認是否落在自選訂單，不展開候選清單。",
        "decide_material_action": "只用目前可見證據與 task policy 產生 submit / skip / refresh。",
        "apply_material_decision": "執行 submit、refresh，或保留顯式 skip。",
        "verify_material_outcome": "驗證 submit / refresh 是否讓 detail signature 真正改變。",
    }
    anchor_ids = {
        "open_guild_order_list": "daily_ui.guild_order_detail_panel",
        "inspect_visible_order": "daily_ui.guild_order_detail_panel",
        "inspect_custom_order_options": "daily_ui.guild_order_custom_list_button",
        "decide_material_action": "daily_ui.guild_order_detail_panel",
        "apply_material_decision": "daily_ui.guild_order_submit_button",
        "verify_material_outcome": "daily_ui.guild_order_detail_panel",
    }
    failure_reason_ids = {
        "open_guild_order_list": "route_unavailable",
        "inspect_visible_order": GuildOrderDecisionReason.ORDER_STATE_UNKNOWN.value,
        "inspect_custom_order_options": "custom_order_blocked",
        "decide_material_action": "decision_state_missing",
        "apply_material_decision": "runtime_dispatch_failed",
        "verify_material_outcome": GuildOrderDecisionReason.SUBMIT_VERIFICATION_FAILED.value,
    }
    status_texts = {
        "open_guild_order_list": {"running": "正在開啟公會訂單"},
        "inspect_visible_order": {"running": "正在讀取當前訂單"},
        "inspect_custom_order_options": {"running": "正在確認自選訂單狀態"},
        "decide_material_action": {"running": "正在決定公會訂單動作"},
        "apply_material_decision": {"running": "正在執行公會訂單動作"},
        "verify_material_outcome": {"running": "正在驗證公會訂單結果"},
    }
    step_metadata = {
        "open_guild_order_list": {"inspection_retry_limit": _ROUTE_ATTEMPT_LIMIT},
        "verify_material_outcome": {"inspection_retry_limit": _STATE_VERIFICATION_RETRY_LIMIT},
    }
    return [
        GuildOrderRuntimeStepSpec(
            step_id=step.step_id,
            action=step.action,
            description=descriptions.get(step.step_id, step.step_id.replace("_", " ")),
            display_name=display_names.get(step.step_id, step.step_id),
            success_condition=step.success_condition,
            failure_condition=step.failure_condition,
            notes=step.notes,
            summary=descriptions.get(step.step_id, ""),
            anchor_id=anchor_ids.get(step.step_id, ""),
            status_texts=status_texts.get(step.step_id, {}),
            failure_reason_id=failure_reason_ids.get(step.step_id, ""),
            metadata={**dict(step.metadata), **step_metadata.get(step.step_id, {})},
        )
        for step in steps
    ]


def _build_guild_order_inspection(
    *,
    screenshot_path: Path,
    text_evidence: list[GuildOrderObservedTextEvidence],
) -> GuildOrderInspection:
    scene_state = _classify_scene_state(text_evidence)
    if scene_state is not GuildOrderSceneState.GUILD_ORDER_SCENE:
        return GuildOrderInspection(
            scene_state=scene_state,
            screenshot_path=str(screenshot_path),
            text_evidence=text_evidence,
            message=f"Detected `{scene_state.value}` from bounded OCR text evidence.",
        )
    custom_order_detected = any("自選" in evidence.canonical_text() for evidence in text_evidence)
    detail_label_evidence = _best_detail_label_evidence(text_evidence)
    selected_label_evidence = _best_selected_slot_label_evidence(
        text_evidence=text_evidence,
        detail_label_evidence=detail_label_evidence,
    )
    quantity_evidence = _best_selected_quantity_evidence(text_evidence)
    hold_evidence = _best_detail_hold_evidence(text_evidence)
    parsed_quantity = _parse_quantity_line(
        quantity_evidence.raw_text if quantity_evidence is not None else ""
    ) or _parse_quantity_line(quantity_evidence.normalized_text if quantity_evidence is not None else "")
    available_quantity = _parse_available_hold_line(
        hold_evidence.raw_text if hold_evidence is not None else ""
    ) or _parse_available_hold_line(hold_evidence.normalized_text if hold_evidence is not None else "")
    if available_quantity is None and parsed_quantity is not None:
        available_quantity = parsed_quantity[0]
    required_quantity = parsed_quantity[1] if parsed_quantity is not None else None
    slot_evidence = selected_label_evidence or quantity_evidence
    slot_index = _slot_index_for_evidence(slot_evidence, slot_points=_GUILD_ORDER_SLOT_POINTS)
    material_label = _collapse_text(detail_label_evidence.raw_text) if detail_label_evidence is not None else ""
    normalized_material_id = _optional_string(_canonical_text(material_label))
    requirement = (
        GuildOrderRequirement(
            slot_index=slot_index or 0,
            material_label=material_label,
            normalized_material_id=normalized_material_id,
            required_quantity=required_quantity,
            evidence={
                "detail_label_text": detail_label_evidence.to_dict() if detail_label_evidence is not None else None,
                "selected_slot_label_text": (
                    selected_label_evidence.to_dict() if selected_label_evidence is not None else None
                ),
                "selected_slot_quantity_text": quantity_evidence.to_dict() if quantity_evidence is not None else None,
            },
        )
        if material_label and required_quantity is not None and slot_index is not None
        else None
    )
    availability = (
        GuildOrderAvailability(
            material_label=material_label,
            normalized_material_id=normalized_material_id,
            available_quantity=available_quantity,
            sufficiency=GuildOrderMaterialSufficiency.UNKNOWN,
            evidence={
                "detail_hold_text": hold_evidence.to_dict() if hold_evidence is not None else None,
                "selected_slot_quantity_text": quantity_evidence.to_dict() if quantity_evidence is not None else None,
            },
        )
        if material_label and available_quantity is not None
        else None
    )
    order_kind = GuildOrderOrderKind.CUSTOM if custom_order_detected else GuildOrderOrderKind.STANDARD
    order_state_known = order_kind is GuildOrderOrderKind.CUSTOM or (
        requirement is not None and availability is not None and slot_index is not None
    )
    detail_signature = (
        f"{order_kind.value}|{slot_index}|{normalized_material_id}|"
        f"{availability.available_quantity if availability is not None else None}|"
        f"{requirement.required_quantity if requirement is not None else None}"
        if order_state_known
        else ""
    )
    return GuildOrderInspection(
        scene_state=scene_state,
        screenshot_path=str(screenshot_path),
        text_evidence=text_evidence,
        slot_index=slot_index,
        order_kind=order_kind,
        requirement=requirement,
        availability=availability,
        detail_signature=detail_signature,
        order_state_known=order_state_known,
        order_completed=False,
        submit_affordance_visible=_has_submit_affordance_text(text_evidence),
        refresh_affordance_visible=_has_refresh_affordance_text(text_evidence),
        message=(
            "Detected a custom guild-order slot from bounded OCR evidence."
            if order_kind is GuildOrderOrderKind.CUSTOM
            else (
                "Captured visible standard guild-order material evidence."
                if order_state_known
                else "Guild-order scene reached, but visible standard-order evidence is incomplete."
            )
        ),
        metadata={
            "detail_label_text": detail_label_evidence.to_dict() if detail_label_evidence is not None else None,
            "selected_slot_label_text": (
                selected_label_evidence.to_dict() if selected_label_evidence is not None else None
            ),
            "selected_slot_quantity_text": quantity_evidence.to_dict() if quantity_evidence is not None else None,
            "detail_hold_text": hold_evidence.to_dict() if hold_evidence is not None else None,
        },
    )


def _classify_scene_state(
    text_evidence: list[GuildOrderObservedTextEvidence],
) -> GuildOrderSceneState:
    canonical_texts = [item.canonical_text() for item in text_evidence if item.canonical_text()]
    if _contains_any(canonical_texts, ("持有",)) and _contains_any(canonical_texts, ("提交", "公會訂單", "2000")):
        return GuildOrderSceneState.GUILD_ORDER_SCENE
    if _contains_any(canonical_texts, ("捐獻材料",)):
        return GuildOrderSceneState.GUILD_ACTIVITY
    if _contains_any(canonical_texts, ("進入領地", "公會資金", "今日公告")):
        return GuildOrderSceneState.GUILD_PANEL
    if _contains_any(canonical_texts, ("立即前往", "公會訂單")):
        return GuildOrderSceneState.GUILD_ORDER_CARD_MODAL
    if _contains_any(canonical_texts, ("商會委託", "異界之門", "公會訂單")):
        return GuildOrderSceneState.CARNIVAL_HUB
    return GuildOrderSceneState.UNKNOWN


def _best_detail_label_evidence(
    text_evidence: list[GuildOrderObservedTextEvidence],
) -> GuildOrderObservedTextEvidence | None:
    candidates = [
        item
        for item in text_evidence
        if _bbox_in_region(item.bbox, min_x=1000, max_x=1225, min_y=230, max_y=340)
        and _looks_like_material_label(item)
    ]
    return _best_text_candidate(candidates)


def _best_selected_slot_label_evidence(
    *,
    text_evidence: list[GuildOrderObservedTextEvidence],
    detail_label_evidence: GuildOrderObservedTextEvidence | None,
) -> GuildOrderObservedTextEvidence | None:
    if detail_label_evidence is None:
        return None
    target = detail_label_evidence.canonical_text()
    candidates = [
        item
        for item in text_evidence
        if item.canonical_text() == target
        and _bbox_in_region(item.bbox, min_x=0, max_x=320, min_y=250, max_y=560)
    ]
    return _best_text_candidate(candidates)


def _best_selected_quantity_evidence(
    text_evidence: list[GuildOrderObservedTextEvidence],
) -> GuildOrderObservedTextEvidence | None:
    candidates = [
        item
        for item in text_evidence
        if _bbox_in_region(item.bbox, min_x=0, max_x=260, min_y=320, max_y=430)
        and _parse_quantity_line(item.raw_text or item.normalized_text) is not None
    ]
    return _best_text_candidate(candidates)


def _best_detail_hold_evidence(
    text_evidence: list[GuildOrderObservedTextEvidence],
) -> GuildOrderObservedTextEvidence | None:
    candidates = [
        item
        for item in text_evidence
        if _bbox_in_region(item.bbox, min_x=1000, max_x=1225, min_y=410, max_y=500)
        and _parse_available_hold_line(item.raw_text or item.normalized_text) is not None
    ]
    return _best_text_candidate(candidates)


def _best_text_candidate(
    candidates: list[GuildOrderObservedTextEvidence],
) -> GuildOrderObservedTextEvidence | None:
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            -(item.confidence if item.confidence is not None else -1.0),
            -len(item.canonical_text()),
            item.bbox[1],
            item.bbox[0],
        ),
    )[0]


def _looks_like_material_label(evidence: GuildOrderObservedTextEvidence) -> bool:
    canonical = evidence.canonical_text()
    if not canonical:
        return False
    if any(keyword in canonical for keyword in ("持有", "提交", "立即前往", "前往", "捐獻材料", "公會訂單")):
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in canonical)


def _has_submit_affordance_text(
    text_evidence: list[GuildOrderObservedTextEvidence],
) -> bool:
    return any(
        "提交" in item.canonical_text()
        and _bbox_in_region(item.bbox, min_x=1000, max_x=1235, min_y=560, max_y=710)
        for item in text_evidence
    )


def _has_refresh_affordance_text(
    text_evidence: list[GuildOrderObservedTextEvidence],
) -> bool:
    return any(
        (
            "刷新" in item.canonical_text()
            or bool(re.search(r"\d{3,5}", item.normalized_text or item.raw_text))
        )
        and _bbox_in_region(item.bbox, min_x=540, max_x=780, min_y=35, max_y=140)
        for item in text_evidence
    )


def _parse_quantity_line(text: str) -> tuple[int, int] | None:
    if not text:
        return None
    normalized_text = str(text).replace(" ", "")
    match = re.search(r"(\d+)\s*/\s*(\d+)", normalized_text)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _parse_available_hold_line(text: str) -> int | None:
    if not text:
        return None
    normalized_text = str(text).replace(" ", "")
    match = re.search(r"持有[:：]?(\d+)", normalized_text)
    if match is None:
        return None
    return int(match.group(1))


def _slot_index_for_evidence(
    evidence: GuildOrderObservedTextEvidence | None,
    *,
    slot_points: tuple[tuple[int, int], ...],
) -> int | None:
    if evidence is None:
        return None
    center_x, center_y = evidence.center()
    best_index: int | None = None
    best_distance: int | None = None
    for index, point in enumerate(slot_points, start=1):
        distance = abs(center_x - point[0]) + abs(center_y - point[1])
        if best_distance is None or distance < best_distance:
            best_index = index
            best_distance = distance
    return best_index


def _contains_any(canonical_texts: list[str], values: tuple[str, ...]) -> bool:
    return any(value in text for text in canonical_texts for value in values)


def _bbox_in_region(
    bbox: tuple[int, int, int, int],
    *,
    min_x: int,
    max_x: int,
    min_y: int,
    max_y: int,
) -> bool:
    x, y, width, height = bbox
    center_x = x + width // 2
    center_y = y + height // 2
    return min_x <= center_x <= max_x and min_y <= center_y <= max_y


def _canonical_text(text: str) -> str:
    return re.sub(r"[\s:：/／,，.。()\[\]{}<>|_\-]+", "", str(text or "")).lower()


def _collapse_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip()


def _run_windows_ocr_reader(screenshot_path: Path) -> list[GuildOrderObservedTextEvidence]:
    escaped_path = str(screenshot_path).replace("'", "''")
    script = textwrap.dedent(
        f"""
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        function AwaitWinRt([object]$Operation) {{
            $task = [System.WindowsRuntimeSystemExtensions]::AsTask($Operation)
            $task.Wait()
            return $task.Result
        }}

        $imagePath = '{escaped_path}'
        $storageFile = AwaitWinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($imagePath))
        $stream = AwaitWinRt ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read))
        $decoder = AwaitWinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream))
        $bitmap = AwaitWinRt ($decoder.GetSoftwareBitmapAsync())
        $bitmap = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert(
            $bitmap,
            [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
            [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied
        )

        $readerTag = ''
        $engine = $null
        foreach ($tag in @('zh-Hant', 'zh-Hans', 'en-US')) {{
            $candidate = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage(
                [Windows.Globalization.Language]::new($tag)
            )
            if ($null -ne $candidate) {{
                $engine = $candidate
                $readerTag = $tag
                break
            }}
        }}
        if ($null -eq $engine) {{
            $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
            $readerTag = 'user-profile'
        }}
        if ($null -eq $engine) {{
            throw 'Windows Media OCR engine is unavailable.'
        }}

        $result = AwaitWinRt ($engine.RecognizeAsync($bitmap))
        $output = @()
        foreach ($line in $result.Lines) {{
            if ($null -eq $line -or $null -eq $line.Words -or $line.Words.Count -eq 0) {{
                continue
            }}
            $boxes = @()
            foreach ($word in $line.Words) {{
                $rect = $word.BoundingRect
                $boxes += [pscustomobject]@{{
                    X = [int][math]::Round($rect.X)
                    Y = [int][math]::Round($rect.Y)
                    Width = [int][math]::Round($rect.Width)
                    Height = [int][math]::Round($rect.Height)
                }}
            }}
            $minX = ($boxes | Measure-Object -Property X -Minimum).Minimum
            $minY = ($boxes | Measure-Object -Property Y -Minimum).Minimum
            $maxX = ($boxes | ForEach-Object {{ $_.X + $_.Width }} | Measure-Object -Maximum).Maximum
            $maxY = ($boxes | ForEach-Object {{ $_.Y + $_.Height }} | Measure-Object -Maximum).Maximum
            $output += [pscustomobject]@{{
                raw_text = $line.Text
                normalized_text = ($line.Text -replace '\\s+', '')
                bbox = @($minX, $minY, [int]($maxX - $minX), [int]($maxY - $minY))
                confidence = $null
                screenshot_ref = $imagePath
                reader = "windows.media.ocr/$readerTag"
            }}
        }}
        $output | ConvertTo-Json -Depth 5 -Compress
        """
    ).strip()
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        return []
    raw_output = completed.stdout.strip()
    if not raw_output:
        return []
    try:
        payload = loads(raw_output)
    except Exception:
        return []
    items = payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])
    return [
        GuildOrderObservedTextEvidence.from_dict(dict(item))
        for item in items
        if isinstance(item, dict)
    ]


def _tuple_int_pair(
    value: object,
    *,
    default: tuple[int, int] = (0, 0),
) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0]), int(value[1])
    return default


def _tuple_int_quad(value: object) -> tuple[int, int, int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        return int(value[0]), int(value[1]), int(value[2]), int(value[3])
    return (0, 0, 0, 0)


def _optional_float(value: object) -> float | None:
    if value in ("", None):
        return None
    return float(value)
