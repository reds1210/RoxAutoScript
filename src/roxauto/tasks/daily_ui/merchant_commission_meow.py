from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
import re
import time
from typing import Any, Protocol, Self

import cv2
import numpy as np

from roxauto.core.models import InstanceState, TaskManifest, TaskSpec
from roxauto.core.runtime import TaskExecutionContext, TaskStep, step_failure, step_success
from roxauto.emulator.execution import EmulatorActionAdapter
from roxauto.core.serde import to_primitive
from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import (
    TaskBlueprint,
    TaskFixtureProfile,
    TaskReadinessReport,
    TaskRuntimeBuilderInput,
    TaskStepBlueprint,
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

_CLOSE_BUTTON_ANCHOR_ID = "common.close_button"
_PORING_BUTTON_ANCHOR_ID = "daily_ui.merchant_commission_poring_button"
_CARNIVAL_ENTRY_ANCHOR_ID = "daily_ui.merchant_commission_carnival_entry"
_DETAIL_MODAL_ANCHOR_ID = "daily_ui.merchant_commission_detail_modal"
_GO_NOW_BUTTON_ANCHOR_ID = "daily_ui.merchant_commission_go_now_button"
_NPC_DIALOG_ANCHOR_ID = "daily_ui.merchant_commission_npc_dialog"
_LIST_PANEL_ANCHOR_ID = "daily_ui.merchant_commission_list_panel"
_MEOW_ACCEPT_BUTTON_ANCHOR_ID = "daily_ui.merchant_commission_meow_accept_button"
_TASK_LIST_ENTRY_ANCHOR_ID = "daily_ui.merchant_commission_task_list_entry"
_MEOW_SUBMIT_OPTION_ANCHOR_ID = "daily_ui.merchant_commission_meow_submit_option"
_SUBMIT_ITEM_PANEL_ANCHOR_ID = "daily_ui.merchant_commission_submit_item_panel"
_BUY_NOW_BUTTON_ANCHOR_ID = "daily_ui.merchant_commission_buy_now_button"
_BUY_CONFIRMATION_DIALOG_ANCHOR_ID = "daily_ui.merchant_commission_buy_confirmation_dialog"
_BUY_CONFIRM_BUTTON_ANCHOR_ID = "daily_ui.merchant_commission_buy_confirm_button"
_SUBMIT_BUTTON_ANCHOR_ID = "daily_ui.merchant_commission_submit_button"
_ROUND_COUNTER_ANCHOR_ID = "daily_ui.merchant_commission_round_counter"
_SIGNAL_CONTRACT_VERSION = "merchant_commission_meow.v2"
_RUNTIME_INPUT_BUILDER_PATH = (
    "roxauto.tasks.daily_ui.merchant_commission_meow.build_merchant_commission_meow_runtime_input"
)
_RUNTIME_SEAM_BUILDER_PATH = (
    "roxauto.tasks.daily_ui.merchant_commission_meow.build_merchant_commission_meow_runtime_seam"
)
_TASK_SPEC_BUILDER_PATH = (
    "roxauto.tasks.daily_ui.merchant_commission_meow.build_merchant_commission_meow_task_spec"
)
_RUNTIME_BRIDGE_PROBE_PATH = (
    "roxauto.tasks.daily_ui.merchant_commission_meow.has_merchant_commission_meow_runtime_bridge"
)
_RESULT_SIGNAL_KEYS = (
    "anchor_id",
    "decision",
    "failure_reason_id",
    "inspection_attempts",
    "matched_anchor_ids",
    "outcome_code",
    "round_index",
    "step_outcome",
    "task_action",
    "telemetry",
    "text_evidence",
)
_ACTION_DISPATCH_SUCCESS_STATUSES = frozenset({"completed", "partial", "executed", "routed"})
_TEXT_EVIDENCE_CONFIDENCE_THRESHOLD = 0.85
_DEFAULT_INSPECTION_RETRY_LIMIT = 2
_PRE_SUBMIT_ROUND_CONTEXT_KEY = "daily_ui.merchant_commission_meow.pre_submit_round"


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


class MerchantCommissionMeowTaskFailureReason(str, Enum):
    ENTRY_MODAL_UNAVAILABLE = "entry_modal_unavailable"
    MEOW_ACCEPT_UNAVAILABLE = "meow_accept_unavailable"
    TASK_LIST_ENTRY_UNAVAILABLE = "task_list_entry_unavailable"
    REENTRY_UNAVAILABLE = "reentry_unavailable"
    SUBMIT_PANEL_UNAVAILABLE = "submit_panel_unavailable"
    BUY_CONFIRMATION_UNAVAILABLE = "buy_confirmation_unavailable"
    BUY_NOW_UNAVAILABLE = "buy_now_unavailable"
    SUBMIT_BUTTON_UNAVAILABLE = "submit_button_unavailable"
    PROGRESSION_UNVERIFIED = "progression_unverified"
    PROGRESSION_LOW_CONFIDENCE = "progression_low_confidence"
    RUNTIME_DISPATCH_FAILED = "runtime_dispatch_failed"


@dataclass(slots=True)
class MerchantCommissionMeowObservedTextEvidence:
    source_type: str
    raw_text: str
    normalized_text: str
    bbox: tuple[int, int, int, int]
    confidence: float
    screenshot_ref: str
    reader: str

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "source_type": self.source_type,
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
            source_type=str(data.get("source_type", "")),
            raw_text=str(data.get("raw_text", "")),
            normalized_text=str(data.get("normalized_text", "")),
            bbox=_tuple_int_quad(data.get("bbox")),
            confidence=float(data.get("confidence", 0.0)),
            screenshot_ref=str(data.get("screenshot_ref", "")),
            reader=str(data.get("reader", "")),
        )


@dataclass(slots=True)
class MerchantCommissionMeowCheckpointInspection:
    checkpoint_id: str
    screenshot_path: str
    matched_anchor_ids: list[str] = field(default_factory=list)
    anchor_points: dict[str, tuple[int, int]] = field(default_factory=dict)
    text_evidence: list[MerchantCommissionMeowObservedTextEvidence] = field(default_factory=list)
    round_index: int | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "checkpoint_id": self.checkpoint_id,
                "screenshot_path": self.screenshot_path,
                "matched_anchor_ids": self.matched_anchor_ids,
                "anchor_points": self.anchor_points,
                "text_evidence": [item.to_dict() for item in self.text_evidence],
                "round_index": self.round_index,
                "message": self.message,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        anchor_points = {
            str(anchor_id): _tuple_int_pair(point)
            for anchor_id, point in dict(data.get("anchor_points", {})).items()
        }
        return cls(
            checkpoint_id=str(data.get("checkpoint_id", "")),
            screenshot_path=str(data.get("screenshot_path", "")),
            matched_anchor_ids=[str(item) for item in data.get("matched_anchor_ids", [])],
            anchor_points=anchor_points,
            text_evidence=[
                MerchantCommissionMeowObservedTextEvidence.from_dict(dict(item))
                for item in data.get("text_evidence", [])
            ],
            round_index=_optional_int(data.get("round_index")),
            message=str(data.get("message", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def has_anchor(self, anchor_id: str) -> bool:
        return anchor_id in self.matched_anchor_ids


@dataclass(slots=True)
class MerchantCommissionMeowRuntimeStepSpec:
    step_id: str
    action: str
    description: str
    display_name: str
    success_condition: str
    failure_condition: str = ""
    notes: str = ""
    summary: str = ""
    anchor_id: str = ""
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
                "failure_reason_id": self.failure_reason_id,
                "metadata": self.metadata,
            }
        )


@dataclass(slots=True)
class MerchantCommissionMeowRuntimeInput:
    task_id: str
    pack_id: str
    manifest_path: str
    manifest: TaskManifest
    builder_input: TaskRuntimeBuilderInput
    readiness_report: TaskReadinessReport
    blueprint: TaskBlueprint
    fixture_profile_path: str
    fixture_profile: TaskFixtureProfile
    route_contract: MerchantCommissionMeowRouteContract
    loop_contract: MerchantCommissionMeowLoopContract
    submission_policy: MerchantCommissionMeowSubmissionPolicy
    decision_contract: MerchantCommissionMeowDecisionContract
    required_anchor_ids: list[str] = field(default_factory=list)
    supporting_anchor_ids: list[str] = field(default_factory=list)
    step_specs: list[MerchantCommissionMeowRuntimeStepSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "task_id": self.task_id,
                "pack_id": self.pack_id,
                "manifest_path": self.manifest_path,
                "fixture_profile_path": self.fixture_profile_path,
                "fixture_id": self.fixture_profile.fixture_id,
                "required_anchor_ids": self.required_anchor_ids,
                "supporting_anchor_ids": self.supporting_anchor_ids,
                "route_contract": self.route_contract.to_dict(),
                "loop_contract": self.loop_contract.to_dict(),
                "submission_policy": self.submission_policy.to_dict(),
                "decision_contract": self.decision_contract.to_dict(),
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
class MerchantCommissionMeowRuntimeSeam:
    task_id: str
    pack_id: str
    runtime_input: MerchantCommissionMeowRuntimeInput
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
        vision_gateway: "MerchantCommissionMeowVisionGateway",
        navigation_plan: MerchantCommissionMeowFullRunNavigationPlan | None = None,
    ) -> TaskSpec:
        return build_merchant_commission_meow_task_spec(
            adapter=adapter,
            vision_gateway=vision_gateway,
            navigation_plan=navigation_plan,
            runtime_seam=self,
        )


class MerchantCommissionMeowVisionGateway(Protocol):
    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        step_id: str,
        signal_anchor_ids: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> MerchantCommissionMeowCheckpointInspection:
        """Inspect one merchant-commission surface and return bounded evidence."""


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


def build_merchant_commission_meow_runtime_input(
    *,
    builder_input: TaskRuntimeBuilderInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> MerchantCommissionMeowRuntimeInput:
    repo = foundation_repository or TaskFoundationRepository.load_default()
    specification = build_merchant_commission_meow_specification(
        builder_input=builder_input,
        readiness_report=readiness_report,
        foundation_repository=repo,
    )
    runtime_seam_metadata = _resolve_runtime_seam_metadata(
        builder_input=specification.builder_input,
        blueprint=specification.blueprint,
    )
    return MerchantCommissionMeowRuntimeInput(
        task_id=specification.task_id,
        pack_id=specification.pack_id,
        manifest_path=specification.manifest_path,
        manifest=_build_runtime_manifest(specification.blueprint.manifest),
        builder_input=specification.builder_input,
        readiness_report=specification.readiness_report,
        blueprint=specification.blueprint,
        fixture_profile_path=specification.fixture_profile_path,
        fixture_profile=specification.fixture_profile,
        route_contract=specification.route_contract,
        loop_contract=specification.loop_contract,
        submission_policy=specification.submission_policy,
        decision_contract=specification.decision_contract,
        required_anchor_ids=list(specification.required_anchor_ids),
        supporting_anchor_ids=list(specification.supporting_anchor_ids),
        step_specs=_build_runtime_step_specs(specification.blueprint.steps),
        metadata={
            "implementation_state": specification.blueprint.implementation_state.value,
            "runtime_bridge": "roxauto.tasks.daily_ui.merchant_commission_meow",
            "golden_screen_slugs": [case.screen_slug for case in specification.blueprint.golden_cases],
            "supporting_anchor_ids": list(specification.supporting_anchor_ids),
            "supporting_golden_screen_slugs": list(specification.supporting_screen_slugs),
            "signal_contract_version": str(
                runtime_seam_metadata.get("signal_contract_version", _SIGNAL_CONTRACT_VERSION)
            ),
            "result_signal_keys": list(
                runtime_seam_metadata.get("result_signal_keys", list(_RESULT_SIGNAL_KEYS))
            ),
            "runtime_seam": dict(runtime_seam_metadata),
            "merchant_commission_meow_handoff_fields": _metadata_string_list(
                specification.builder_input.metadata,
                "merchant_commission_meow_handoff_fields",
            ),
        },
    )


def build_merchant_commission_meow_runtime_seam(
    *,
    runtime_input: MerchantCommissionMeowRuntimeInput | None = None,
    builder_input: TaskRuntimeBuilderInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> MerchantCommissionMeowRuntimeSeam:
    resolved_runtime_input = runtime_input or build_merchant_commission_meow_runtime_input(
        builder_input=builder_input,
        readiness_report=readiness_report,
        foundation_repository=foundation_repository,
    )
    runtime_seam_metadata = dict(
        resolved_runtime_input.metadata.get("runtime_seam", _default_runtime_seam_metadata())
    )
    result_signal_keys = runtime_seam_metadata.get("result_signal_keys", list(_RESULT_SIGNAL_KEYS))
    return MerchantCommissionMeowRuntimeSeam(
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
            "implementation_state": str(
                resolved_runtime_input.metadata.get("implementation_state", "")
            ),
            "required_anchor_ids": list(resolved_runtime_input.required_anchor_ids),
            "supporting_anchor_ids": list(resolved_runtime_input.supporting_anchor_ids),
        },
    )


def build_merchant_commission_meow_task_spec(
    *,
    adapter: EmulatorActionAdapter,
    vision_gateway: MerchantCommissionMeowVisionGateway,
    navigation_plan: MerchantCommissionMeowFullRunNavigationPlan | None = None,
    runtime_seam: MerchantCommissionMeowRuntimeSeam | None = None,
    runtime_input: MerchantCommissionMeowRuntimeInput | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
) -> TaskSpec:
    resolved_runtime_input = runtime_input or (
        runtime_seam.runtime_input if runtime_seam is not None else None
    ) or build_merchant_commission_meow_runtime_input(
        foundation_repository=foundation_repository,
    )
    resolved_runtime_seam = runtime_seam or build_merchant_commission_meow_runtime_seam(
        runtime_input=resolved_runtime_input,
    )
    resolved_navigation_plan = navigation_plan or MerchantCommissionMeowFullRunNavigationPlan()
    bridge = _MerchantCommissionMeowTaskBridge(
        adapter=adapter,
        vision_gateway=vision_gateway,
        runtime_input=resolved_runtime_input,
        navigation_plan=resolved_navigation_plan,
    )
    handlers = {
        "open_merchant_commission_entry": bridge.open_merchant_commission_entry,
        "accept_meow_group_commission": bridge.accept_meow_group_commission,
        "reenter_from_daily_task_list": bridge.reenter_from_daily_task_list,
        "resolve_round_material_submission": bridge.resolve_round_material_submission,
        "verify_round_progression": bridge.verify_round_progression,
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
            "runtime_bridge": "roxauto.tasks.daily_ui.merchant_commission_meow",
            "builder_input": resolved_runtime_input.builder_input.to_dict(),
            "runtime_input": resolved_runtime_input.to_dict(),
            "runtime_seam": resolved_runtime_seam.to_dict(),
            "implementation_readiness_state": (
                resolved_runtime_input.readiness_report.implementation_readiness_state.value
            ),
        },
    )


def has_merchant_commission_meow_runtime_bridge() -> bool:
    return True


class _MerchantCommissionMeowTaskBridge:
    def __init__(
        self,
        *,
        adapter: EmulatorActionAdapter,
        vision_gateway: MerchantCommissionMeowVisionGateway,
        runtime_input: MerchantCommissionMeowRuntimeInput,
        navigation_plan: MerchantCommissionMeowFullRunNavigationPlan,
    ) -> None:
        self._adapter = adapter
        self._vision_gateway = vision_gateway
        self._runtime_input = runtime_input
        self._navigation_plan = navigation_plan
        self._step_specs = {item.step_id: item for item in runtime_input.step_specs}

    def open_merchant_commission_entry(self, context: TaskExecutionContext):
        step_id = "open_merchant_commission_entry"
        attempts: list[dict[str, Any]] = []
        precheck, precheck_attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="entry.precheck",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_DETAIL_MODAL_ANCHOR_ID),
            max_attempts=1,
        )
        attempts.extend(precheck_attempts)
        if precheck.has_anchor(_DETAIL_MODAL_ANCHOR_ID):
            return step_success(
                step_id,
                "Merchant commission detail modal is already visible.",
                screenshot_path=precheck.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=precheck,
                    inspection_attempts=attempts,
                    outcome_code="entry_modal_already_visible",
                    telemetry={"reason": "entry.precheck"},
                ),
            )

        task_actions: list[dict[str, Any]] = []
        last_action: dict[str, Any] | None = None
        for point, wait_sec, reason in (
            (
                self._navigation_plan.entry_plan.activity_button_point,
                self._navigation_plan.entry_plan.wait_after_activity_open_sec,
                "entry.tap_activity",
            ),
            (
                self._navigation_plan.entry_plan.carnival_entry_point,
                self._navigation_plan.entry_plan.wait_after_carnival_sec,
                "entry.tap_carnival",
            ),
            (
                self._navigation_plan.entry_plan.merchant_commission_icon_point,
                self._navigation_plan.entry_plan.wait_after_merchant_detail_sec,
                "entry.tap_merchant_icon",
            ),
        ):
            last_action = self._tap(context, step_id=step_id, point=point, reason=reason)
            task_actions.append(last_action)
            if self._dispatch_failed(last_action):
                return step_failure(
                    step_id,
                    self._dispatch_failure_message(
                        action_name="merchant commission entry tap",
                        task_action=last_action,
                    ),
                    data=self._step_data(
                        step_id=step_id,
                        inspection=precheck,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                        outcome_code="entry_dispatch_failed",
                        task_action=last_action,
                        telemetry={"reason": reason, "task_actions": task_actions},
                    ),
                )
            self._sleep(wait_sec)

        postcheck, post_attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="entry.postcheck",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_DETAIL_MODAL_ANCHOR_ID),
            max_attempts=self._inspection_retry_limit(step_id),
        )
        attempts.extend(post_attempts)
        if postcheck.has_anchor(_DETAIL_MODAL_ANCHOR_ID):
            return step_success(
                step_id,
                "Fixed entry route reached the merchant commission detail modal.",
                screenshot_path=postcheck.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=postcheck,
                    inspection_attempts=attempts,
                    outcome_code="entry_modal_verified",
                    task_action=last_action,
                    telemetry={"reason": "entry.postcheck", "task_actions": task_actions},
                ),
            )
        return step_failure(
            step_id,
            "Merchant commission detail modal could not be verified after the fixed entry route.",
            screenshot_path=postcheck.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=postcheck,
                inspection_attempts=attempts,
                failure_reason_id=MerchantCommissionMeowTaskFailureReason.ENTRY_MODAL_UNAVAILABLE.value,
                outcome_code="entry_modal_unverified",
                task_action=last_action,
                step_outcome={
                    "kind": "verification_failed",
                    "failure_reason_id": MerchantCommissionMeowTaskFailureReason.ENTRY_MODAL_UNAVAILABLE.value,
                },
                telemetry={"reason": "entry.postcheck", "task_actions": task_actions},
            ),
        )

    def accept_meow_group_commission(self, context: TaskExecutionContext):
        step_id = "accept_meow_group_commission"
        attempts: list[dict[str, Any]] = []
        precheck, precheck_attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="accept.precheck",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_TASK_LIST_ENTRY_ANCHOR_ID),
            max_attempts=1,
        )
        attempts.extend(precheck_attempts)
        if precheck.has_anchor(_TASK_LIST_ENTRY_ANCHOR_ID):
            return step_success(
                step_id,
                "Meow Group commission is already accepted and ready in the task list.",
                screenshot_path=precheck.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=precheck,
                    inspection_attempts=attempts,
                    outcome_code="accept_already_prepared_task_list",
                    telemetry={"reason": "accept.precheck"},
                ),
            )

        task_actions: list[dict[str, Any]] = []
        last_action: dict[str, Any] | None = None
        list_inspection = precheck
        if not (
            list_inspection.has_anchor(_LIST_PANEL_ANCHOR_ID)
            and list_inspection.has_anchor(_MEOW_ACCEPT_BUTTON_ANCHOR_ID)
        ):
            for point, wait_sec, reason in (
                (
                    self._navigation_plan.entry_plan.go_now_point,
                    self._navigation_plan.entry_plan.wait_after_go_now_sec,
                    "accept.tap_go_now",
                ),
                (
                    self._navigation_plan.entry_plan.npc_commission_option_point,
                    self._navigation_plan.entry_plan.wait_after_npc_option_sec,
                    "accept.tap_npc_option",
                ),
            ):
                last_action = self._tap(context, step_id=step_id, point=point, reason=reason)
                task_actions.append(last_action)
                if self._dispatch_failed(last_action):
                    return step_failure(
                        step_id,
                        self._dispatch_failure_message(
                            action_name="meow accept preparation tap",
                            task_action=last_action,
                        ),
                        data=self._step_data(
                            step_id=step_id,
                            inspection=list_inspection,
                            inspection_attempts=attempts,
                            failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                            outcome_code="accept_dispatch_failed",
                            task_action=last_action,
                            telemetry={"reason": reason, "task_actions": task_actions},
                        ),
                    )
                self._sleep(wait_sec)

            list_inspection, list_attempts = self._inspect_until(
                context,
                step_id=step_id,
                reason="accept.list_panel",
                signal_anchor_ids=self._signal_anchor_ids(step_id),
                accepted=lambda inspection: inspection.has_anchor(_LIST_PANEL_ANCHOR_ID)
                and inspection.has_anchor(_MEOW_ACCEPT_BUTTON_ANCHOR_ID),
                max_attempts=self._inspection_retry_limit(step_id),
            )
            attempts.extend(list_attempts)

        if not (
            list_inspection.has_anchor(_LIST_PANEL_ANCHOR_ID)
            and list_inspection.has_anchor(_MEOW_ACCEPT_BUTTON_ANCHOR_ID)
        ):
            return step_failure(
                step_id,
                "Meow Group accept surface could not be verified.",
                screenshot_path=list_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=list_inspection,
                    inspection_attempts=attempts,
                    failure_reason_id=MerchantCommissionMeowTaskFailureReason.MEOW_ACCEPT_UNAVAILABLE.value,
                    outcome_code="accept_surface_unverified",
                    task_action=last_action,
                    step_outcome={
                        "kind": "verification_failed",
                        "failure_reason_id": MerchantCommissionMeowTaskFailureReason.MEOW_ACCEPT_UNAVAILABLE.value,
                    },
                    telemetry={"reason": "accept.list_panel", "task_actions": task_actions},
                ),
            )

        for action_kind, wait_sec, reason in (
            (
                ("tap", self._navigation_plan.entry_plan.meow_accept_point),
                self._navigation_plan.entry_plan.wait_after_accept_sec,
                "accept.tap_meow_accept",
            ),
            (
                ("tap", self._navigation_plan.entry_plan.close_list_point),
                self._navigation_plan.entry_plan.wait_after_close_list_sec,
                "accept.tap_close_list",
            ),
            (
                ("tap", self._navigation_plan.entry_plan.expand_task_tab_point),
                self._navigation_plan.entry_plan.wait_after_expand_task_tab_sec,
                "accept.tap_expand_task_tab",
            ),
            (
                (
                    "swipe",
                    (
                        self._navigation_plan.entry_plan.task_list_swipe_start,
                        self._navigation_plan.entry_plan.task_list_swipe_end,
                        self._navigation_plan.entry_plan.task_list_swipe_duration_ms,
                    ),
                ),
                self._navigation_plan.entry_plan.wait_after_task_swipe_sec,
                "accept.swipe_task_list",
            ),
        ):
            if action_kind[0] == "tap":
                last_action = self._tap(
                    context,
                    step_id=step_id,
                    point=action_kind[1],
                    reason=reason,
                )
            else:
                start, end, duration_ms = action_kind[1]
                last_action = self._swipe(
                    context,
                    step_id=step_id,
                    start=start,
                    end=end,
                    duration_ms=duration_ms,
                    reason=reason,
                )
            task_actions.append(last_action)
            if self._dispatch_failed(last_action):
                return step_failure(
                    step_id,
                    self._dispatch_failure_message(
                        action_name="meow accept follow-up action",
                        task_action=last_action,
                    ),
                    data=self._step_data(
                        step_id=step_id,
                        inspection=list_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                        outcome_code="accept_dispatch_failed",
                        task_action=last_action,
                        telemetry={"reason": reason, "task_actions": task_actions},
                    ),
                )
            self._sleep(wait_sec)

        task_list_inspection, task_list_attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="accept.task_list_ready",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_TASK_LIST_ENTRY_ANCHOR_ID),
            max_attempts=self._inspection_retry_limit(step_id),
        )
        attempts.extend(task_list_attempts)
        if task_list_inspection.has_anchor(_TASK_LIST_ENTRY_ANCHOR_ID):
            return step_success(
                step_id,
                "Meow Group commission was accepted and the task list re-entry route is ready.",
                screenshot_path=task_list_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=task_list_inspection,
                    inspection_attempts=attempts,
                    outcome_code="accept_prepared_task_list",
                    task_action=last_action,
                    telemetry={"reason": "accept.task_list_ready", "task_actions": task_actions},
                ),
            )
        return step_failure(
            step_id,
            "Accepted Meow Group commission could not be recovered to the task list route.",
            screenshot_path=task_list_inspection.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=task_list_inspection,
                inspection_attempts=attempts,
                failure_reason_id=MerchantCommissionMeowTaskFailureReason.TASK_LIST_ENTRY_UNAVAILABLE.value,
                outcome_code="task_list_entry_unverified",
                task_action=last_action,
                step_outcome={
                    "kind": "verification_failed",
                    "failure_reason_id": MerchantCommissionMeowTaskFailureReason.TASK_LIST_ENTRY_UNAVAILABLE.value,
                },
                telemetry={"reason": "accept.task_list_ready", "task_actions": task_actions},
            ),
        )

    def reenter_from_daily_task_list(self, context: TaskExecutionContext):
        step_id = "reenter_from_daily_task_list"
        precheck, attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="reenter.precheck",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_TASK_LIST_ENTRY_ANCHOR_ID),
            max_attempts=self._inspection_retry_limit(step_id),
        )
        if not precheck.has_anchor(_TASK_LIST_ENTRY_ANCHOR_ID):
            return step_failure(
                step_id,
                "Task-list re-entry surface is not visible for the accepted Meow Group commission.",
                screenshot_path=precheck.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=precheck,
                    inspection_attempts=attempts,
                    failure_reason_id=MerchantCommissionMeowTaskFailureReason.TASK_LIST_ENTRY_UNAVAILABLE.value,
                    outcome_code="reenter_task_list_missing",
                    step_outcome={
                        "kind": "verification_failed",
                        "failure_reason_id": MerchantCommissionMeowTaskFailureReason.TASK_LIST_ENTRY_UNAVAILABLE.value,
                    },
                    telemetry={"reason": "reenter.precheck"},
                ),
            )

        best_before_round = _best_round_index_evidence(
            precheck,
            round_limit=self._runtime_input.loop_contract.round_limit,
        )
        context.metadata[_PRE_SUBMIT_ROUND_CONTEXT_KEY] = {
            "inspection": precheck.to_dict(),
            "round_index": best_before_round[0] if best_before_round is not None else None,
            "confidence_ok": bool(
                best_before_round is not None
                and best_before_round[1].confidence >= _TEXT_EVIDENCE_CONFIDENCE_THRESHOLD
            ),
            "best_text_evidence": (
                best_before_round[1].to_dict() if best_before_round is not None else None
            ),
        }

        task_action = self._tap(
            context,
            step_id=step_id,
            point=self._navigation_plan.active_round_plan.task_entry_point,
            reason="reenter.tap_task_entry",
        )
        if self._dispatch_failed(task_action):
            return step_failure(
                step_id,
                self._dispatch_failure_message(
                    action_name="task-list re-entry tap",
                    task_action=task_action,
                ),
                data=self._step_data(
                    step_id=step_id,
                    inspection=precheck,
                    inspection_attempts=attempts,
                    failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                    outcome_code="reenter_dispatch_failed",
                    task_action=task_action,
                    text_evidence=precheck.text_evidence,
                    telemetry={"reason": "reenter.tap_task_entry"},
                ),
            )
        self._sleep(self._navigation_plan.active_round_plan.wait_after_task_entry_sec)

        postcheck, post_attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="reenter.postcheck",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_MEOW_SUBMIT_OPTION_ANCHOR_ID),
            max_attempts=self._inspection_retry_limit(step_id),
        )
        attempts.extend(post_attempts)
        if postcheck.has_anchor(_MEOW_SUBMIT_OPTION_ANCHOR_ID):
            return step_success(
                step_id,
                "Accepted Meow Group commission was re-entered from the task list.",
                screenshot_path=postcheck.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=postcheck,
                    inspection_attempts=attempts,
                    outcome_code="reentry_ready_for_submit",
                    task_action=task_action,
                    round_index=best_before_round[0] if best_before_round is not None else None,
                    text_evidence=precheck.text_evidence,
                    telemetry={
                        "reason": "reenter.postcheck",
                        "stored_pre_submit_round": dict(context.metadata[_PRE_SUBMIT_ROUND_CONTEXT_KEY]),
                    },
                ),
            )
        return step_failure(
            step_id,
            "Task-list re-entry did not reach the Meow Group submit shortcut.",
            screenshot_path=postcheck.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=postcheck,
                inspection_attempts=attempts,
                failure_reason_id=MerchantCommissionMeowTaskFailureReason.REENTRY_UNAVAILABLE.value,
                outcome_code="reentry_unverified",
                task_action=task_action,
                round_index=best_before_round[0] if best_before_round is not None else None,
                text_evidence=precheck.text_evidence,
                step_outcome={
                    "kind": "verification_failed",
                    "failure_reason_id": MerchantCommissionMeowTaskFailureReason.REENTRY_UNAVAILABLE.value,
                },
                telemetry={"reason": "reenter.postcheck"},
            ),
        )

    def resolve_round_material_submission(self, context: TaskExecutionContext):
        step_id = "resolve_round_material_submission"
        attempts: list[dict[str, Any]] = []
        task_actions: list[dict[str, Any]] = []
        last_action: dict[str, Any] | None = None

        panel_inspection, precheck_attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="submission.precheck",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_SUBMIT_ITEM_PANEL_ANCHOR_ID),
            max_attempts=1,
        )
        attempts.extend(precheck_attempts)
        if not panel_inspection.has_anchor(_SUBMIT_ITEM_PANEL_ANCHOR_ID):
            last_action = self._tap(
                context,
                step_id=step_id,
                point=self._navigation_plan.active_round_plan.submit_option_point,
                reason="submission.tap_submit_option",
            )
            task_actions.append(last_action)
            if self._dispatch_failed(last_action):
                return step_failure(
                    step_id,
                    self._dispatch_failure_message(
                        action_name="submit-option tap",
                        task_action=last_action,
                    ),
                    data=self._step_data(
                        step_id=step_id,
                        inspection=panel_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                        outcome_code="submission_dispatch_failed",
                        task_action=last_action,
                        telemetry={"reason": "submission.tap_submit_option", "task_actions": task_actions},
                    ),
                )
            self._sleep(self._navigation_plan.active_round_plan.wait_after_submit_option_sec)
            panel_inspection, panel_attempts = self._inspect_until(
                context,
                step_id=step_id,
                reason="submission.panel",
                signal_anchor_ids=self._signal_anchor_ids(step_id),
                accepted=lambda inspection: inspection.has_anchor(_SUBMIT_ITEM_PANEL_ANCHOR_ID),
                max_attempts=self._inspection_retry_limit(step_id),
            )
            attempts.extend(panel_attempts)

        if not panel_inspection.has_anchor(_SUBMIT_ITEM_PANEL_ANCHOR_ID):
            return step_failure(
                step_id,
                "Meow submit-item panel could not be verified.",
                screenshot_path=panel_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=panel_inspection,
                    inspection_attempts=attempts,
                    failure_reason_id=MerchantCommissionMeowTaskFailureReason.SUBMIT_PANEL_UNAVAILABLE.value,
                    outcome_code="submit_panel_unverified",
                    task_action=last_action,
                    step_outcome={
                        "kind": "verification_failed",
                        "failure_reason_id": MerchantCommissionMeowTaskFailureReason.SUBMIT_PANEL_UNAVAILABLE.value,
                    },
                    telemetry={"reason": "submission.panel", "task_actions": task_actions},
                ),
            )

        submit_panel_inspection = inspect_merchant_commission_meow_submit_panel_progress(
            panel_inspection.screenshot_path
        )
        if submit_panel_inspection.progress_state is MerchantCommissionMeowSubmitPanelProgressState.FULL:
            if not panel_inspection.has_anchor(_SUBMIT_BUTTON_ANCHOR_ID):
                return step_failure(
                    step_id,
                    "Submit button is not visible on the ready Meow submit panel.",
                    screenshot_path=panel_inspection.screenshot_path,
                    data=self._step_data(
                        step_id=step_id,
                        inspection=panel_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.SUBMIT_BUTTON_UNAVAILABLE.value,
                        outcome_code="submit_button_missing",
                        decision=MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT.value,
                        telemetry={
                            "reason": "submission.ready_panel",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )
            last_action = self._tap(
                context,
                step_id=step_id,
                point=self._navigation_plan.active_round_plan.submit_panel_plan.submit_point,
                reason="submission.tap_submit",
            )
            task_actions.append(last_action)
            if self._dispatch_failed(last_action):
                return step_failure(
                    step_id,
                    self._dispatch_failure_message(
                        action_name="submit tap",
                        task_action=last_action,
                    ),
                    data=self._step_data(
                        step_id=step_id,
                        inspection=panel_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                        outcome_code="submit_dispatch_failed",
                        decision=MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT.value,
                        task_action=last_action,
                        telemetry={
                            "reason": "submission.tap_submit",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )
            return step_success(
                step_id,
                "Ready Meow round was submitted directly.",
                screenshot_path=panel_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=panel_inspection,
                    inspection_attempts=attempts,
                    outcome_code="direct_submit_dispatched",
                    decision=MerchantCommissionMeowDecisionValue.DIRECT_SUBMIT.value,
                    reason_id=MerchantCommissionMeowDecisionReason.MATERIALS_READY.value,
                    task_action=last_action,
                    telemetry={
                        "reason": "submission.ready_panel",
                        "submit_panel_inspection": submit_panel_inspection.to_dict(),
                        "task_actions": task_actions,
                    },
                ),
            )

        if submit_panel_inspection.progress_state is MerchantCommissionMeowSubmitPanelProgressState.INCOMPLETE:
            if not panel_inspection.has_anchor(_BUY_NOW_BUTTON_ANCHOR_ID):
                return step_failure(
                    step_id,
                    "Buy-now affordance is unavailable on the incomplete Meow submit panel.",
                    screenshot_path=panel_inspection.screenshot_path,
                    data=self._step_data(
                        step_id=step_id,
                        inspection=panel_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.BUY_NOW_UNAVAILABLE.value,
                        outcome_code="buy_now_missing",
                        decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
                        telemetry={
                            "reason": "submission.incomplete_panel",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )
            last_action = self._tap(
                context,
                step_id=step_id,
                point=self._navigation_plan.active_round_plan.submit_panel_plan.buy_now_point,
                reason="submission.tap_buy_now",
            )
            task_actions.append(last_action)
            if self._dispatch_failed(last_action):
                return step_failure(
                    step_id,
                    self._dispatch_failure_message(
                        action_name="buy-now tap",
                        task_action=last_action,
                    ),
                    data=self._step_data(
                        step_id=step_id,
                        inspection=panel_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                        outcome_code="buy_now_dispatch_failed",
                        decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
                        task_action=last_action,
                        telemetry={
                            "reason": "submission.tap_buy_now",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )
            self._sleep(self._navigation_plan.active_round_plan.submit_panel_plan.wait_after_buy_sec)

            confirm_inspection, confirm_attempts = self._inspect_until(
                context,
                step_id=step_id,
                reason="submission.buy_confirmation",
                signal_anchor_ids=[_BUY_CONFIRMATION_DIALOG_ANCHOR_ID, _BUY_CONFIRM_BUTTON_ANCHOR_ID],
                accepted=lambda inspection: inspection.has_anchor(_BUY_CONFIRM_BUTTON_ANCHOR_ID),
                max_attempts=self._inspection_retry_limit(step_id),
            )
            attempts.extend(confirm_attempts)
            if not confirm_inspection.has_anchor(_BUY_CONFIRM_BUTTON_ANCHOR_ID):
                return step_failure(
                    step_id,
                    "Buy confirmation could not be verified for the Meow submit panel.",
                    screenshot_path=confirm_inspection.screenshot_path,
                    data=self._step_data(
                        step_id=step_id,
                        inspection=confirm_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.BUY_CONFIRMATION_UNAVAILABLE.value,
                        outcome_code="buy_confirmation_unverified",
                        decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
                        task_action=last_action,
                        step_outcome={
                            "kind": "verification_failed",
                            "failure_reason_id": MerchantCommissionMeowTaskFailureReason.BUY_CONFIRMATION_UNAVAILABLE.value,
                        },
                        telemetry={
                            "reason": "submission.buy_confirmation",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )

            last_action = self._tap(
                context,
                step_id=step_id,
                point=self._navigation_plan.active_round_plan.submit_panel_plan.buy_confirm_point,
                reason="submission.tap_buy_confirm",
            )
            task_actions.append(last_action)
            if self._dispatch_failed(last_action):
                return step_failure(
                    step_id,
                    self._dispatch_failure_message(
                        action_name="buy-confirm tap",
                        task_action=last_action,
                    ),
                    data=self._step_data(
                        step_id=step_id,
                        inspection=confirm_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                        outcome_code="buy_confirm_dispatch_failed",
                        decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
                        task_action=last_action,
                        telemetry={
                            "reason": "submission.tap_buy_confirm",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )
            self._sleep(
                self._navigation_plan.active_round_plan.submit_panel_plan.wait_after_confirm_sec
            )

            ready_panel_inspection, ready_panel_attempts = self._inspect_until(
                context,
                step_id=step_id,
                reason="submission.post_confirm",
                signal_anchor_ids=self._signal_anchor_ids(step_id),
                accepted=lambda inspection: inspection.has_anchor(_SUBMIT_ITEM_PANEL_ANCHOR_ID)
                and inspection.has_anchor(_SUBMIT_BUTTON_ANCHOR_ID),
                max_attempts=self._inspection_retry_limit(step_id),
            )
            attempts.extend(ready_panel_attempts)
            if not ready_panel_inspection.has_anchor(_SUBMIT_BUTTON_ANCHOR_ID):
                return step_failure(
                    step_id,
                    "Submit button did not recover after Meow immediate-buy confirmation.",
                    screenshot_path=ready_panel_inspection.screenshot_path,
                    data=self._step_data(
                        step_id=step_id,
                        inspection=ready_panel_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.SUBMIT_BUTTON_UNAVAILABLE.value,
                        outcome_code="submit_button_missing_after_buy",
                        decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
                        telemetry={
                            "reason": "submission.post_confirm",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )

            last_action = self._tap(
                context,
                step_id=step_id,
                point=self._navigation_plan.active_round_plan.submit_panel_plan.submit_point,
                reason="submission.tap_submit_after_buy",
            )
            task_actions.append(last_action)
            if self._dispatch_failed(last_action):
                return step_failure(
                    step_id,
                    self._dispatch_failure_message(
                        action_name="submit-after-buy tap",
                        task_action=last_action,
                    ),
                    data=self._step_data(
                        step_id=step_id,
                        inspection=ready_panel_inspection,
                        inspection_attempts=attempts,
                        failure_reason_id=MerchantCommissionMeowTaskFailureReason.RUNTIME_DISPATCH_FAILED.value,
                        outcome_code="submit_dispatch_failed_after_buy",
                        decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
                        task_action=last_action,
                        telemetry={
                            "reason": "submission.tap_submit_after_buy",
                            "submit_panel_inspection": submit_panel_inspection.to_dict(),
                            "task_actions": task_actions,
                        },
                    ),
                )
            return step_success(
                step_id,
                "Incomplete Meow round was bought and submitted.",
                screenshot_path=ready_panel_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=ready_panel_inspection,
                    inspection_attempts=attempts,
                    outcome_code="buy_then_submit_dispatched",
                    decision=MerchantCommissionMeowDecisionValue.IMMEDIATE_BUY_THEN_SUBMIT.value,
                    reason_id=MerchantCommissionMeowDecisionReason.BUY_REQUIRED.value,
                    task_action=last_action,
                    telemetry={
                        "reason": "submission.post_confirm",
                        "submit_panel_inspection": submit_panel_inspection.to_dict(),
                        "task_actions": task_actions,
                    },
                ),
            )

        return step_failure(
            step_id,
            "The Meow submit panel could not be classified truthfully.",
            screenshot_path=panel_inspection.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=panel_inspection,
                inspection_attempts=attempts,
                failure_reason_id=MerchantCommissionMeowDecisionReason.ROUND_STATE_UNKNOWN.value,
                outcome_code="submit_panel_state_unknown",
                decision=MerchantCommissionMeowDecisionValue.STOP_FOR_OPERATOR.value,
                step_outcome={
                    "kind": "verification_failed",
                    "failure_reason_id": MerchantCommissionMeowDecisionReason.ROUND_STATE_UNKNOWN.value,
                },
                telemetry={
                    "reason": "submission.panel",
                    "submit_panel_inspection": submit_panel_inspection.to_dict(),
                    "task_actions": task_actions,
                },
            ),
        )

    def verify_round_progression(self, context: TaskExecutionContext):
        step_id = "verify_round_progression"
        stored_pre_submit = self._stored_pre_submit_round(context)
        after_inspection, attempts = self._inspect_until(
            context,
            step_id=step_id,
            reason="progression.verify",
            signal_anchor_ids=self._signal_anchor_ids(step_id),
            accepted=lambda inspection: inspection.has_anchor(_TASK_LIST_ENTRY_ANCHOR_ID)
            or inspection.has_anchor(_ROUND_COUNTER_ANCHOR_ID),
            max_attempts=self._inspection_retry_limit(step_id),
        )
        before_inspection = (
            MerchantCommissionMeowCheckpointInspection.from_dict(
                dict(stored_pre_submit.get("inspection", {}))
            )
            if stored_pre_submit
            else None
        )
        before_round = (
            _best_round_index_evidence(
                before_inspection,
                round_limit=self._runtime_input.loop_contract.round_limit,
            )
            if before_inspection is not None
            else None
        )
        after_round = _best_round_index_evidence(
            after_inspection,
            round_limit=self._runtime_input.loop_contract.round_limit,
        )
        combined_text_evidence: list[MerchantCommissionMeowObservedTextEvidence] = []
        if before_inspection is not None:
            combined_text_evidence.extend(before_inspection.text_evidence)
        combined_text_evidence.extend(after_inspection.text_evidence)

        if before_round is None or after_round is None:
            return step_failure(
                step_id,
                "Round progression could not be verified from bounded task-list text evidence.",
                screenshot_path=after_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=after_inspection,
                    inspection_attempts=attempts,
                    failure_reason_id=MerchantCommissionMeowTaskFailureReason.PROGRESSION_UNVERIFIED.value,
                    outcome_code="round_progression_unverified",
                    text_evidence=combined_text_evidence,
                    step_outcome={
                        "kind": "verification_failed",
                        "failure_reason_id": MerchantCommissionMeowTaskFailureReason.PROGRESSION_UNVERIFIED.value,
                    },
                    telemetry={
                        "reason": "progression.verify",
                        "before_round_text_evidence": [
                            item.to_dict()
                            for item in (before_inspection.text_evidence if before_inspection else [])
                        ],
                        "after_round_text_evidence": [item.to_dict() for item in after_inspection.text_evidence],
                    },
                ),
            )

        if (
            before_round[1].confidence < _TEXT_EVIDENCE_CONFIDENCE_THRESHOLD
            or after_round[1].confidence < _TEXT_EVIDENCE_CONFIDENCE_THRESHOLD
        ):
            return step_failure(
                step_id,
                "Round progression text evidence is below the safe confidence threshold.",
                screenshot_path=after_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=after_inspection,
                    inspection_attempts=attempts,
                    failure_reason_id=MerchantCommissionMeowTaskFailureReason.PROGRESSION_LOW_CONFIDENCE.value,
                    outcome_code="round_progression_low_confidence",
                    round_index=after_round[0],
                    text_evidence=combined_text_evidence,
                    step_outcome={
                        "kind": "low_confidence_text_evidence",
                        "failure_reason_id": MerchantCommissionMeowTaskFailureReason.PROGRESSION_LOW_CONFIDENCE.value,
                        "previous_round_index": before_round[0],
                        "current_round_index": after_round[0],
                    },
                    telemetry={
                        "reason": "progression.verify",
                        "confidence_threshold": _TEXT_EVIDENCE_CONFIDENCE_THRESHOLD,
                        "before_round_text_evidence": [before_round[1].to_dict()],
                        "after_round_text_evidence": [after_round[1].to_dict()],
                    },
                ),
            )

        if after_round[0] != before_round[0] + 1:
            return step_failure(
                step_id,
                "Round progression text did not advance to the next Meow Group task-list state.",
                screenshot_path=after_inspection.screenshot_path,
                data=self._step_data(
                    step_id=step_id,
                    inspection=after_inspection,
                    inspection_attempts=attempts,
                    failure_reason_id=MerchantCommissionMeowTaskFailureReason.PROGRESSION_UNVERIFIED.value,
                    outcome_code="round_progression_not_advanced",
                    round_index=after_round[0],
                    text_evidence=combined_text_evidence,
                    step_outcome={
                        "kind": "verification_failed",
                        "failure_reason_id": MerchantCommissionMeowTaskFailureReason.PROGRESSION_UNVERIFIED.value,
                        "previous_round_index": before_round[0],
                        "current_round_index": after_round[0],
                    },
                    telemetry={
                        "reason": "progression.verify",
                        "before_round_text_evidence": [before_round[1].to_dict()],
                        "after_round_text_evidence": [after_round[1].to_dict()],
                    },
                ),
            )

        return step_success(
            step_id,
            f"Round progression verified: {before_round[0]} -> {after_round[0]}",
            screenshot_path=after_inspection.screenshot_path,
            data=self._step_data(
                step_id=step_id,
                inspection=after_inspection,
                inspection_attempts=attempts,
                outcome_code="round_progression_verified",
                round_index=after_round[0],
                text_evidence=combined_text_evidence,
                step_outcome={
                    "kind": "round_progression_verified",
                    "previous_round_index": before_round[0],
                    "current_round_index": after_round[0],
                },
                telemetry={
                    "reason": "progression.verify",
                    "confidence_threshold": _TEXT_EVIDENCE_CONFIDENCE_THRESHOLD,
                    "before_round_text_evidence": [before_round[1].to_dict()],
                    "after_round_text_evidence": [after_round[1].to_dict()],
                },
            ),
        )

    def _step_data(
        self,
        *,
        step_id: str,
        inspection: MerchantCommissionMeowCheckpointInspection | None = None,
        inspection_attempts: list[dict[str, Any]] | None = None,
        failure_reason_id: str = "",
        outcome_code: str = "",
        task_action: dict[str, Any] | None = None,
        step_outcome: dict[str, Any] | None = None,
        telemetry: dict[str, Any] | None = None,
        text_evidence: list[MerchantCommissionMeowObservedTextEvidence] | None = None,
        round_index: int | None = None,
        decision: str = "",
        reason_id: str = "",
    ) -> dict[str, Any]:
        step_spec = self._step_specs[step_id]
        resolved_text_evidence = (
            text_evidence if text_evidence is not None else (inspection.text_evidence if inspection is not None else [])
        )
        payload: dict[str, Any] = {
            "anchor_id": step_spec.anchor_id,
            "matched_anchor_ids": list(inspection.matched_anchor_ids) if inspection is not None else [],
            "inspection_attempts": list(inspection_attempts or []),
            "failure_reason_id": failure_reason_id,
            "outcome_code": outcome_code,
            "runtime_step_spec": step_spec.to_dict(),
            "text_evidence": [item.to_dict() for item in resolved_text_evidence],
        }
        if inspection is not None:
            payload["screenshot_path"] = inspection.screenshot_path
        if round_index is not None:
            payload["round_index"] = round_index
        elif inspection is not None and inspection.round_index is not None:
            payload["round_index"] = inspection.round_index
        if decision:
            payload["decision"] = decision
        if reason_id:
            payload["reason_id"] = reason_id
        if task_action is not None:
            payload["task_action"] = task_action
        if step_outcome is not None:
            payload["step_outcome"] = step_outcome
        if telemetry is not None:
            payload["telemetry"] = telemetry
        return payload

    def _inspect_until(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        reason: str,
        signal_anchor_ids: list[str],
        accepted,
        max_attempts: int,
    ) -> tuple[MerchantCommissionMeowCheckpointInspection, list[dict[str, Any]]]:
        attempts: list[dict[str, Any]] = []
        last_inspection: MerchantCommissionMeowCheckpointInspection | None = None
        for attempt in range(1, max(1, int(max_attempts)) + 1):
            inspection = self._inspect(
                context,
                step_id=step_id,
                reason=reason,
                signal_anchor_ids=signal_anchor_ids,
            )
            accepted_flag = bool(accepted(inspection))
            attempts.append(
                {
                    "attempt": attempt,
                    "accepted": accepted_flag,
                    **inspection.to_dict(),
                }
            )
            last_inspection = inspection
            if accepted_flag:
                return inspection, attempts
        if last_inspection is None:
            raise RuntimeError("merchant commission inspection unexpectedly produced no result")
        return last_inspection, attempts

    def _inspect(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        reason: str,
        signal_anchor_ids: list[str],
    ) -> MerchantCommissionMeowCheckpointInspection:
        screenshot_path = self._capture_screenshot(context, step_id=step_id, reason=reason)
        inspection = self._vision_gateway.inspect(
            instance=context.instance,
            screenshot_path=screenshot_path,
            step_id=step_id,
            signal_anchor_ids=list(signal_anchor_ids),
            metadata={
                "task_id": self._runtime_input.task_id,
                "reason": reason,
            },
        )
        if inspection.screenshot_path == str(screenshot_path):
            return inspection
        return replace(inspection, screenshot_path=str(screenshot_path))

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

    def _swipe(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int,
        reason: str,
    ) -> dict[str, Any]:
        metadata = {
            "source": self._runtime_input.task_id,
            "reason": reason,
            "duration_ms": duration_ms,
        }
        if context.action_bridge is not None:
            result = context.require_action_bridge().swipe(
                start,
                end,
                duration_ms=duration_ms,
                step_id=step_id,
                metadata=metadata,
            )
            return {
                "action": "swipe",
                "start": start,
                "end": end,
                "duration_ms": duration_ms,
                "status": result.status,
                "message": result.message,
                "source": "task_action_bridge",
                "payload": dict(result.payload),
                "metadata": dict(result.metadata),
            }
        self._adapter.swipe(context.instance, start, end, duration_ms=duration_ms)
        return {
            "action": "swipe",
            "start": start,
            "end": end,
            "duration_ms": duration_ms,
            "status": "executed",
            "message": "",
            "source": "adapter",
        }

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
            return Path(frame.image_path)
        return self._adapter.capture_screenshot(context.instance)

    def _dispatch_failed(self, task_action: dict[str, Any]) -> bool:
        return str(task_action.get("status", "")) not in _ACTION_DISPATCH_SUCCESS_STATUSES

    def _dispatch_failure_message(self, *, action_name: str, task_action: dict[str, Any]) -> str:
        status = str(task_action.get("status", "")).strip() or "unknown"
        message = str(task_action.get("message", "")).strip()
        if message:
            return f"{action_name} failed through the runtime bridge: {message}"
        return f"{action_name} failed through the runtime bridge with status {status}."

    def _signal_anchor_ids(self, step_id: str) -> list[str]:
        metadata = self._step_specs[step_id].metadata
        raw_value = metadata.get("signal_anchor_ids", [])
        if not isinstance(raw_value, list):
            return []
        return [str(item) for item in raw_value]

    def _inspection_retry_limit(self, step_id: str) -> int:
        metadata = self._step_specs[step_id].metadata
        try:
            return int(metadata.get("inspection_retry_limit", _DEFAULT_INSPECTION_RETRY_LIMIT))
        except (TypeError, ValueError):
            return _DEFAULT_INSPECTION_RETRY_LIMIT

    def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)

    def _stored_pre_submit_round(self, context: TaskExecutionContext) -> dict[str, Any]:
        value = context.metadata.get(_PRE_SUBMIT_ROUND_CONTEXT_KEY, {})
        return dict(value) if isinstance(value, dict) else {}


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
    metadata["runtime_bridge"] = "roxauto.tasks.daily_ui.merchant_commission_meow"
    metadata["signal_contract_version"] = _SIGNAL_CONTRACT_VERSION
    return replace(manifest, metadata=metadata)


def _build_runtime_step_specs(
    steps: list[TaskStepBlueprint],
) -> list[MerchantCommissionMeowRuntimeStepSpec]:
    display_names = {
        "open_merchant_commission_entry": "Open Merchant Entry",
        "accept_meow_group_commission": "Accept Meow Group",
        "reenter_from_daily_task_list": "Re-enter From Task List",
        "resolve_round_material_submission": "Resolve Material Submission",
        "verify_round_progression": "Verify Round Progression",
    }
    summaries = {
        "open_merchant_commission_entry": "Reach the merchant commission detail modal from the main-screen route.",
        "accept_meow_group_commission": "Accept the Meow Group commission and prepare the task-list route.",
        "reenter_from_daily_task_list": "Resume the accepted Meow Group commission from the left task list.",
        "resolve_round_material_submission": "Submit one Meow Group round with direct submit or immediate buy.",
        "verify_round_progression": "Confirm that the task-list round counter advances after submission.",
    }
    anchor_ids = {
        "open_merchant_commission_entry": _DETAIL_MODAL_ANCHOR_ID,
        "accept_meow_group_commission": _MEOW_ACCEPT_BUTTON_ANCHOR_ID,
        "reenter_from_daily_task_list": _TASK_LIST_ENTRY_ANCHOR_ID,
        "resolve_round_material_submission": _SUBMIT_ITEM_PANEL_ANCHOR_ID,
        "verify_round_progression": _ROUND_COUNTER_ANCHOR_ID,
    }
    failure_reason_ids = {
        "open_merchant_commission_entry": MerchantCommissionMeowTaskFailureReason.ENTRY_MODAL_UNAVAILABLE.value,
        "accept_meow_group_commission": MerchantCommissionMeowTaskFailureReason.MEOW_ACCEPT_UNAVAILABLE.value,
        "reenter_from_daily_task_list": MerchantCommissionMeowTaskFailureReason.REENTRY_UNAVAILABLE.value,
        "resolve_round_material_submission": MerchantCommissionMeowTaskFailureReason.SUBMIT_PANEL_UNAVAILABLE.value,
        "verify_round_progression": MerchantCommissionMeowTaskFailureReason.PROGRESSION_UNVERIFIED.value,
    }
    signal_anchor_ids = {
        "open_merchant_commission_entry": [
            _PORING_BUTTON_ANCHOR_ID,
            _CARNIVAL_ENTRY_ANCHOR_ID,
            _DETAIL_MODAL_ANCHOR_ID,
        ],
        "accept_meow_group_commission": [
            _GO_NOW_BUTTON_ANCHOR_ID,
            _NPC_DIALOG_ANCHOR_ID,
            _LIST_PANEL_ANCHOR_ID,
            _MEOW_ACCEPT_BUTTON_ANCHOR_ID,
            _CLOSE_BUTTON_ANCHOR_ID,
            _TASK_LIST_ENTRY_ANCHOR_ID,
            _ROUND_COUNTER_ANCHOR_ID,
        ],
        "reenter_from_daily_task_list": [
            _TASK_LIST_ENTRY_ANCHOR_ID,
            _ROUND_COUNTER_ANCHOR_ID,
            _MEOW_SUBMIT_OPTION_ANCHOR_ID,
        ],
        "resolve_round_material_submission": [
            _MEOW_SUBMIT_OPTION_ANCHOR_ID,
            _SUBMIT_ITEM_PANEL_ANCHOR_ID,
            _BUY_NOW_BUTTON_ANCHOR_ID,
            _BUY_CONFIRMATION_DIALOG_ANCHOR_ID,
            _BUY_CONFIRM_BUTTON_ANCHOR_ID,
            _SUBMIT_BUTTON_ANCHOR_ID,
        ],
        "verify_round_progression": [
            _TASK_LIST_ENTRY_ANCHOR_ID,
            _ROUND_COUNTER_ANCHOR_ID,
        ],
    }
    return [
        MerchantCommissionMeowRuntimeStepSpec(
            step_id=step.step_id,
            action=step.action,
            description=step.success_condition,
            display_name=display_names.get(step.step_id, step.step_id.replace("_", " ").title()),
            success_condition=step.success_condition,
            failure_condition=step.failure_condition,
            notes=step.notes,
            summary=summaries.get(step.step_id, ""),
            anchor_id=anchor_ids.get(step.step_id, ""),
            failure_reason_id=failure_reason_ids.get(step.step_id, ""),
            metadata={
                **dict(step.metadata),
                "signal_anchor_ids": list(signal_anchor_ids.get(step.step_id, [])),
                "inspection_retry_limit": _DEFAULT_INSPECTION_RETRY_LIMIT,
            },
        )
        for step in steps
    ]


def _best_round_index_evidence(
    inspection: MerchantCommissionMeowCheckpointInspection | None,
    *,
    round_limit: int,
) -> tuple[int, MerchantCommissionMeowObservedTextEvidence] | None:
    if inspection is None:
        return None
    best: tuple[int, MerchantCommissionMeowObservedTextEvidence] | None = None
    for evidence in inspection.text_evidence:
        round_index = _parse_round_index(evidence.normalized_text, round_limit=round_limit)
        if round_index is None:
            round_index = _parse_round_index(evidence.raw_text, round_limit=round_limit)
        if round_index is None:
            continue
        if best is None or evidence.confidence > best[1].confidence:
            best = (round_index, evidence)
    if best is not None:
        return best
    if inspection.round_index is None or not inspection.text_evidence:
        return None
    fallback_evidence = max(inspection.text_evidence, key=lambda item: item.confidence)
    return inspection.round_index, fallback_evidence


def _parse_round_index(text: str, *, round_limit: int) -> int | None:
    normalized_text = str(text).replace(" ", "")
    for pattern in (
        re.compile(r"\((\d+)/(\d+)\)"),
        re.compile(r"(\d+)/(\d+)"),
    ):
        match = pattern.search(normalized_text)
        if match is None:
            continue
        current = int(match.group(1))
        total = int(match.group(2))
        if total == round_limit and 1 <= current <= round_limit:
            return current
    return None


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


def _tuple_int_quad(
    value: object,
    *,
    default: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> tuple[int, int, int, int]:
    if isinstance(value, tuple) and len(value) == 4:
        return int(value[0]), int(value[1]), int(value[2]), int(value[3])
    if isinstance(value, list) and len(value) == 4:
        return int(value[0]), int(value[1]), int(value[2]), int(value[3])
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
