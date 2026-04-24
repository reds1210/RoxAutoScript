from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import time
from typing import Any, Protocol, Self

import cv2
import numpy as np

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


class MerchantCommissionMeowSubmitPanelProgressState(str, Enum):
    FULL = "full"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown"


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
class MerchantCommissionMeowSubmitPanelInspection:
    screenshot_path: str
    progress_state: MerchantCommissionMeowSubmitPanelProgressState
    numerator_ink: int = 0
    denominator_ink: int = 0
    normalized_similarity: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "screenshot_path": self.screenshot_path,
                "progress_state": self.progress_state.value,
                "numerator_ink": self.numerator_ink,
                "denominator_ink": self.denominator_ink,
                "normalized_similarity": self.normalized_similarity,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_state = data.get(
            "progress_state",
            MerchantCommissionMeowSubmitPanelProgressState.UNKNOWN.value,
        )
        progress_state = (
            raw_state
            if isinstance(raw_state, MerchantCommissionMeowSubmitPanelProgressState)
            else MerchantCommissionMeowSubmitPanelProgressState(str(raw_state))
        )
        return cls(
            screenshot_path=str(data.get("screenshot_path", "")),
            progress_state=progress_state,
            numerator_ink=int(data.get("numerator_ink", 0)),
            denominator_ink=int(data.get("denominator_ink", 0)),
            normalized_similarity=float(data.get("normalized_similarity", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class MerchantCommissionMeowSubmitPanelNavigationPlan:
    buy_now_point: tuple[int, int] = (1120, 610)
    buy_confirm_point: tuple[int, int] = (667, 611)
    submit_point: tuple[int, int] = (919, 609)
    wait_after_buy_sec: float = 1.4
    wait_after_confirm_sec: float = 1.6

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "buy_now_point": self.buy_now_point,
                "buy_confirm_point": self.buy_confirm_point,
                "submit_point": self.submit_point,
                "wait_after_buy_sec": self.wait_after_buy_sec,
                "wait_after_confirm_sec": self.wait_after_confirm_sec,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            buy_now_point=_tuple_int_pair(data.get("buy_now_point"), default=(1120, 610)),
            buy_confirm_point=_tuple_int_pair(data.get("buy_confirm_point"), default=(667, 611)),
            submit_point=_tuple_int_pair(data.get("submit_point"), default=(919, 609)),
            wait_after_buy_sec=float(data.get("wait_after_buy_sec", 1.4)),
            wait_after_confirm_sec=float(data.get("wait_after_confirm_sec", 1.6)),
        )


@dataclass(slots=True)
class MerchantCommissionMeowSubmitPanelResolution:
    decision: MerchantCommissionMeowDecisionValue
    inspection: MerchantCommissionMeowSubmitPanelInspection
    executed_points: list[tuple[int, int]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "decision": self.decision.value,
                "inspection": self.inspection.to_dict(),
                "executed_points": self.executed_points,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_decision = data.get(
            "decision",
            MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR.value,
        )
        decision = (
            raw_decision
            if isinstance(raw_decision, MerchantCommissionMeowDecisionValue)
            else MerchantCommissionMeowDecisionValue(str(raw_decision))
        )
        return cls(
            decision=decision,
            inspection=MerchantCommissionMeowSubmitPanelInspection.from_dict(
                dict(data.get("inspection", {}))
            ),
            executed_points=[
                _tuple_int_pair(item)
                for item in data.get("executed_points", [])
            ],
            metadata=dict(data.get("metadata", {})),
        )


class MerchantCommissionMeowSubmitPanelAdapter(Protocol):
    def capture_screenshot(self, instance: object) -> Path:
        """Capture the current screen."""

    def tap(self, instance: object, point: tuple[int, int]) -> None:
        """Tap one screen coordinate."""


class MerchantCommissionMeowRuntimeAdapter(MerchantCommissionMeowSubmitPanelAdapter, Protocol):
    def swipe(
        self,
        instance: object,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        """Swipe between two screen coordinates."""


_EMPTY_FEEDBACK_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[4]
    / "assets"
    / "templates"
    / "daily_ui"
    / "anchors"
    / "merchant_commission_empty_feedback.png"
)


@dataclass(slots=True)
class MerchantCommissionMeowActiveRoundNavigationPlan:
    task_entry_point: tuple[int, int] = (149, 390)
    submit_option_point: tuple[int, int] = (1109, 368)
    wait_after_task_entry_sec: float = 1.2
    wait_after_submit_option_sec: float = 1.2
    submit_panel_plan: MerchantCommissionMeowSubmitPanelNavigationPlan = field(
        default_factory=MerchantCommissionMeowSubmitPanelNavigationPlan
    )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "task_entry_point": self.task_entry_point,
                "submit_option_point": self.submit_option_point,
                "wait_after_task_entry_sec": self.wait_after_task_entry_sec,
                "wait_after_submit_option_sec": self.wait_after_submit_option_sec,
                "submit_panel_plan": self.submit_panel_plan.to_dict(),
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            task_entry_point=_tuple_int_pair(data.get("task_entry_point"), default=(149, 390)),
            submit_option_point=_tuple_int_pair(
                data.get("submit_option_point"),
                default=(1109, 368),
            ),
            wait_after_task_entry_sec=float(data.get("wait_after_task_entry_sec", 1.2)),
            wait_after_submit_option_sec=float(data.get("wait_after_submit_option_sec", 1.2)),
            submit_panel_plan=MerchantCommissionMeowSubmitPanelNavigationPlan.from_dict(
                dict(data.get("submit_panel_plan", {}))
            ),
        )


@dataclass(slots=True)
class MerchantCommissionMeowActiveRoundResolution:
    submit_panel_resolution: MerchantCommissionMeowSubmitPanelResolution
    executed_points: list[tuple[int, int]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "submit_panel_resolution": self.submit_panel_resolution.to_dict(),
                "executed_points": self.executed_points,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            submit_panel_resolution=MerchantCommissionMeowSubmitPanelResolution.from_dict(
                dict(data.get("submit_panel_resolution", {}))
            ),
            executed_points=[
                _tuple_int_pair(item)
                for item in data.get("executed_points", [])
            ],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class MerchantCommissionMeowEntryNavigationPlan:
    activity_button_point: tuple[int, int] = (1042, 47)
    carnival_entry_point: tuple[int, int] = (845, 47)
    merchant_commission_icon_point: tuple[int, int] = (129, 322)
    go_now_point: tuple[int, int] = (640, 605)
    npc_commission_option_point: tuple[int, int] = (1108, 512)
    meow_accept_point: tuple[int, int] = (970, 592)
    close_list_point: tuple[int, int] = (1237, 40)
    expand_task_tab_point: tuple[int, int] = (31, 255)
    task_list_swipe_start: tuple[int, int] = (149, 453)
    task_list_swipe_end: tuple[int, int] = (149, 283)
    task_list_swipe_duration_ms: int = 280
    wait_after_activity_open_sec: float = 1.0
    wait_after_carnival_sec: float = 1.0
    wait_after_merchant_detail_sec: float = 1.0
    wait_after_go_now_sec: float = 4.5
    wait_after_npc_option_sec: float = 1.0
    wait_after_accept_sec: float = 1.0
    wait_after_close_list_sec: float = 0.8
    wait_after_expand_task_tab_sec: float = 0.8
    wait_after_task_swipe_sec: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "activity_button_point": self.activity_button_point,
                "carnival_entry_point": self.carnival_entry_point,
                "merchant_commission_icon_point": self.merchant_commission_icon_point,
                "go_now_point": self.go_now_point,
                "npc_commission_option_point": self.npc_commission_option_point,
                "meow_accept_point": self.meow_accept_point,
                "close_list_point": self.close_list_point,
                "expand_task_tab_point": self.expand_task_tab_point,
                "task_list_swipe_start": self.task_list_swipe_start,
                "task_list_swipe_end": self.task_list_swipe_end,
                "task_list_swipe_duration_ms": self.task_list_swipe_duration_ms,
                "wait_after_activity_open_sec": self.wait_after_activity_open_sec,
                "wait_after_carnival_sec": self.wait_after_carnival_sec,
                "wait_after_merchant_detail_sec": self.wait_after_merchant_detail_sec,
                "wait_after_go_now_sec": self.wait_after_go_now_sec,
                "wait_after_npc_option_sec": self.wait_after_npc_option_sec,
                "wait_after_accept_sec": self.wait_after_accept_sec,
                "wait_after_close_list_sec": self.wait_after_close_list_sec,
                "wait_after_expand_task_tab_sec": self.wait_after_expand_task_tab_sec,
                "wait_after_task_swipe_sec": self.wait_after_task_swipe_sec,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            activity_button_point=_tuple_int_pair(
                data.get("activity_button_point"),
                default=(1042, 47),
            ),
            carnival_entry_point=_tuple_int_pair(
                data.get("carnival_entry_point"),
                default=(845, 47),
            ),
            merchant_commission_icon_point=_tuple_int_pair(
                data.get("merchant_commission_icon_point"),
                default=(129, 322),
            ),
            go_now_point=_tuple_int_pair(data.get("go_now_point"), default=(640, 605)),
            npc_commission_option_point=_tuple_int_pair(
                data.get("npc_commission_option_point"),
                default=(1108, 512),
            ),
            meow_accept_point=_tuple_int_pair(data.get("meow_accept_point"), default=(970, 592)),
            close_list_point=_tuple_int_pair(data.get("close_list_point"), default=(1237, 40)),
            expand_task_tab_point=_tuple_int_pair(
                data.get("expand_task_tab_point"),
                default=(31, 255),
            ),
            task_list_swipe_start=_tuple_int_pair(
                data.get("task_list_swipe_start"),
                default=(149, 453),
            ),
            task_list_swipe_end=_tuple_int_pair(
                data.get("task_list_swipe_end"),
                default=(149, 283),
            ),
            task_list_swipe_duration_ms=int(data.get("task_list_swipe_duration_ms", 280)),
            wait_after_activity_open_sec=float(data.get("wait_after_activity_open_sec", 1.0)),
            wait_after_carnival_sec=float(data.get("wait_after_carnival_sec", 1.0)),
            wait_after_merchant_detail_sec=float(data.get("wait_after_merchant_detail_sec", 1.0)),
            wait_after_go_now_sec=float(data.get("wait_after_go_now_sec", 4.5)),
            wait_after_npc_option_sec=float(data.get("wait_after_npc_option_sec", 1.0)),
            wait_after_accept_sec=float(data.get("wait_after_accept_sec", 1.0)),
            wait_after_close_list_sec=float(data.get("wait_after_close_list_sec", 0.8)),
            wait_after_expand_task_tab_sec=float(
                data.get("wait_after_expand_task_tab_sec", 0.8)
            ),
            wait_after_task_swipe_sec=float(data.get("wait_after_task_swipe_sec", 0.8)),
        )


@dataclass(slots=True)
class MerchantCommissionMeowEntryResolution:
    executed_points: list[tuple[int, int]] = field(default_factory=list)
    executed_swipes: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "executed_points": self.executed_points,
                "executed_swipes": self.executed_swipes,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            executed_points=[
                _tuple_int_pair(item)
                for item in data.get("executed_points", [])
            ],
            executed_swipes=[dict(item) for item in data.get("executed_swipes", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class MerchantCommissionMeowFullRunNavigationPlan:
    entry_plan: MerchantCommissionMeowEntryNavigationPlan = field(
        default_factory=MerchantCommissionMeowEntryNavigationPlan
    )
    active_round_plan: MerchantCommissionMeowActiveRoundNavigationPlan = field(
        default_factory=MerchantCommissionMeowActiveRoundNavigationPlan
    )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "entry_plan": self.entry_plan.to_dict(),
                "active_round_plan": self.active_round_plan.to_dict(),
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            entry_plan=MerchantCommissionMeowEntryNavigationPlan.from_dict(
                dict(data.get("entry_plan", {}))
            ),
            active_round_plan=MerchantCommissionMeowActiveRoundNavigationPlan.from_dict(
                dict(data.get("active_round_plan", {}))
            ),
        )


@dataclass(slots=True)
class MerchantCommissionMeowFullRunResolution:
    entry_resolution: MerchantCommissionMeowEntryResolution
    active_round_resolution: MerchantCommissionMeowActiveRoundResolution
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "entry_resolution": self.entry_resolution.to_dict(),
                "active_round_resolution": self.active_round_resolution.to_dict(),
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            entry_resolution=MerchantCommissionMeowEntryResolution.from_dict(
                dict(data.get("entry_resolution", {}))
            ),
            active_round_resolution=MerchantCommissionMeowActiveRoundResolution.from_dict(
                dict(data.get("active_round_resolution", {}))
            ),
            metadata=dict(data.get("metadata", {})),
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


def inspect_merchant_commission_meow_submit_panel_progress(
    screenshot_path: Path | str,
) -> MerchantCommissionMeowSubmitPanelInspection:
    image_path = Path(screenshot_path)
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Unable to load merchant commission submit-panel screenshot: {image_path}")

    # These crops are validated on the current 1280x720 Meow Group submit panel.
    progress_band = image[179:201, 844:896]
    if progress_band.size == 0:
        return MerchantCommissionMeowSubmitPanelInspection(
            screenshot_path=str(image_path),
            progress_state=MerchantCommissionMeowSubmitPanelProgressState.UNKNOWN,
            metadata={"reason": "progress_band_empty"},
        )

    mask = (progress_band < 180).astype("uint8") * 255
    numerator = mask[:, 13:24]
    denominator = mask[:, 38:49]
    numerator_ink = int((numerator > 0).sum())
    denominator_ink = int((denominator > 0).sum())
    similarity = _normalized_binary_similarity(numerator, denominator)

    empty_feedback_score = _match_empty_feedback(image)

    if numerator_ink < 40 or denominator_ink < 40:
        progress_state = (
            MerchantCommissionMeowSubmitPanelProgressState.INCOMPLETE
            if empty_feedback_score >= 0.9
            else MerchantCommissionMeowSubmitPanelProgressState.UNKNOWN
        )
    elif similarity >= 0.5:
        progress_state = MerchantCommissionMeowSubmitPanelProgressState.FULL
    else:
        progress_state = MerchantCommissionMeowSubmitPanelProgressState.INCOMPLETE

    return MerchantCommissionMeowSubmitPanelInspection(
        screenshot_path=str(image_path),
        progress_state=progress_state,
        numerator_ink=numerator_ink,
        denominator_ink=denominator_ink,
        normalized_similarity=similarity,
        metadata={
            "progress_band": (844, 179, 52, 22),
            "numerator_region": (13, 0, 11, 22),
            "denominator_region": (38, 0, 11, 22),
            "empty_feedback_score": empty_feedback_score,
        },
    )


def resolve_merchant_commission_meow_submit_panel(
    *,
    adapter: MerchantCommissionMeowSubmitPanelAdapter,
    instance: object,
    navigation_plan: MerchantCommissionMeowSubmitPanelNavigationPlan | None = None,
    sleep_fn: Any = time.sleep,
) -> MerchantCommissionMeowSubmitPanelResolution:
    plan = navigation_plan or MerchantCommissionMeowSubmitPanelNavigationPlan()
    inspection = inspect_merchant_commission_meow_submit_panel_progress(
        adapter.capture_screenshot(instance)
    )
    executed_points: list[tuple[int, int]] = []

    if inspection.progress_state is MerchantCommissionMeowSubmitPanelProgressState.FULL:
        adapter.tap(instance, plan.submit_point)
        executed_points.append(plan.submit_point)
        return MerchantCommissionMeowSubmitPanelResolution(
            decision=MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT,
            inspection=inspection,
            executed_points=executed_points,
            metadata={"navigation_plan": plan.to_dict()},
        )

    if inspection.progress_state is MerchantCommissionMeowSubmitPanelProgressState.INCOMPLETE:
        adapter.tap(instance, plan.buy_now_point)
        executed_points.append(plan.buy_now_point)
        sleep_fn(plan.wait_after_buy_sec)
        adapter.tap(instance, plan.buy_confirm_point)
        executed_points.append(plan.buy_confirm_point)
        sleep_fn(plan.wait_after_confirm_sec)
        adapter.tap(instance, plan.submit_point)
        executed_points.append(plan.submit_point)
        return MerchantCommissionMeowSubmitPanelResolution(
            decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT,
            inspection=inspection,
            executed_points=executed_points,
            metadata={"navigation_plan": plan.to_dict()},
        )

    return MerchantCommissionMeowSubmitPanelResolution(
        decision=MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR,
        inspection=inspection,
        executed_points=executed_points,
        metadata={
            "navigation_plan": plan.to_dict(),
            "reason": MerchantCommissionMeowDecisionReason.ROUND_STATE_UNKNOWN.value,
        },
    )


def resolve_merchant_commission_meow_active_round(
    *,
    adapter: MerchantCommissionMeowSubmitPanelAdapter,
    instance: object,
    navigation_plan: MerchantCommissionMeowActiveRoundNavigationPlan | None = None,
    sleep_fn: Any = time.sleep,
) -> MerchantCommissionMeowActiveRoundResolution:
    plan = navigation_plan or MerchantCommissionMeowActiveRoundNavigationPlan()
    executed_points: list[tuple[int, int]] = []

    adapter.tap(instance, plan.task_entry_point)
    executed_points.append(plan.task_entry_point)
    sleep_fn(plan.wait_after_task_entry_sec)
    adapter.tap(instance, plan.submit_option_point)
    executed_points.append(plan.submit_option_point)
    sleep_fn(plan.wait_after_submit_option_sec)
    submit_panel_resolution = resolve_merchant_commission_meow_submit_panel(
        adapter=adapter,
        instance=instance,
        navigation_plan=plan.submit_panel_plan,
        sleep_fn=sleep_fn,
    )
    executed_points.extend(submit_panel_resolution.executed_points)
    return MerchantCommissionMeowActiveRoundResolution(
        submit_panel_resolution=submit_panel_resolution,
        executed_points=executed_points,
        metadata={"navigation_plan": plan.to_dict()},
    )


def resolve_merchant_commission_meow_entry_accept(
    *,
    adapter: MerchantCommissionMeowRuntimeAdapter,
    instance: object,
    navigation_plan: MerchantCommissionMeowEntryNavigationPlan | None = None,
    sleep_fn: Any = time.sleep,
) -> MerchantCommissionMeowEntryResolution:
    plan = navigation_plan or MerchantCommissionMeowEntryNavigationPlan()
    executed_points: list[tuple[int, int]] = []
    executed_swipes: list[dict[str, Any]] = []

    def _tap(point: tuple[int, int], wait_sec: float) -> None:
        adapter.tap(instance, point)
        executed_points.append(point)
        sleep_fn(wait_sec)

    _tap(plan.activity_button_point, plan.wait_after_activity_open_sec)
    _tap(plan.carnival_entry_point, plan.wait_after_carnival_sec)
    _tap(plan.merchant_commission_icon_point, plan.wait_after_merchant_detail_sec)
    _tap(plan.go_now_point, plan.wait_after_go_now_sec)
    _tap(plan.npc_commission_option_point, plan.wait_after_npc_option_sec)
    _tap(plan.meow_accept_point, plan.wait_after_accept_sec)
    _tap(plan.close_list_point, plan.wait_after_close_list_sec)
    _tap(plan.expand_task_tab_point, plan.wait_after_expand_task_tab_sec)
    adapter.swipe(
        instance,
        plan.task_list_swipe_start,
        plan.task_list_swipe_end,
        duration_ms=plan.task_list_swipe_duration_ms,
    )
    executed_swipes.append(
        {
            "start": plan.task_list_swipe_start,
            "end": plan.task_list_swipe_end,
            "duration_ms": plan.task_list_swipe_duration_ms,
        }
    )
    sleep_fn(plan.wait_after_task_swipe_sec)

    return MerchantCommissionMeowEntryResolution(
        executed_points=executed_points,
        executed_swipes=executed_swipes,
        metadata={"navigation_plan": plan.to_dict()},
    )


def resolve_merchant_commission_meow_from_main_screen(
    *,
    adapter: MerchantCommissionMeowRuntimeAdapter,
    instance: object,
    navigation_plan: MerchantCommissionMeowFullRunNavigationPlan | None = None,
    sleep_fn: Any = time.sleep,
) -> MerchantCommissionMeowFullRunResolution:
    plan = navigation_plan or MerchantCommissionMeowFullRunNavigationPlan()
    entry_resolution = resolve_merchant_commission_meow_entry_accept(
        adapter=adapter,
        instance=instance,
        navigation_plan=plan.entry_plan,
        sleep_fn=sleep_fn,
    )
    active_round_resolution = resolve_merchant_commission_meow_active_round(
        adapter=adapter,
        instance=instance,
        navigation_plan=plan.active_round_plan,
        sleep_fn=sleep_fn,
    )
    return MerchantCommissionMeowFullRunResolution(
        entry_resolution=entry_resolution,
        active_round_resolution=active_round_resolution,
        metadata={"navigation_plan": plan.to_dict()},
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


def _tuple_int_pair(value: object, *, default: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    if isinstance(value, tuple) and len(value) == 2:
        return int(value[0]), int(value[1])
    if isinstance(value, list) and len(value) == 2:
        return int(value[0]), int(value[1])
    return default


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


def _normalized_binary_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_crop = _tight_binary_crop(left)
    right_crop = _tight_binary_crop(right)
    if left_crop.size == 0 or right_crop.size == 0:
        return 0.0

    target_width = max(left_crop.shape[1], right_crop.shape[1])
    target_height = max(left_crop.shape[0], right_crop.shape[0])
    left_resized = cv2.resize(left_crop, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
    right_resized = cv2.resize(right_crop, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
    return float(np.mean((left_resized > 0) == (right_resized > 0)))


def _tight_binary_crop(image: np.ndarray) -> np.ndarray:
    ys, xs = np.where(image > 0)
    if len(xs) == 0 or len(ys) == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    return image[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def _match_empty_feedback(image: np.ndarray) -> float:
    if not _EMPTY_FEEDBACK_TEMPLATE_PATH.exists():
        return 0.0
    template = cv2.imread(str(_EMPTY_FEEDBACK_TEMPLATE_PATH), cv2.IMREAD_GRAYSCALE)
    if template is None:
        return 0.0
    region = image[255:466, 820:1180]
    if region.shape[0] < template.shape[0] or region.shape[1] < template.shape[1]:
        return 0.0
    result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
    return float(result.max(initial=0.0))
