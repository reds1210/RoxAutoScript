from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Protocol, Self

from roxauto.core.serde import to_primitive

_SHARED_CARNIVAL_ENTRY_ROUTE = {
    "route_id": "daily_ui.shared_carnival_entry",
    "entry_checkpoints": [
        "main_screen_idle",
        "top_right_expanded_icon_group",
        "carnival_hub",
        "feature_description_card",
        "shared_go_now_handoff",
    ],
    "reentry_checkpoints": [],
    "blocked_click_notes": [
        "Do not use the right-side function drawer as the shared entry route into Carnival.",
        "Do not treat the top-right expanded icon group as a generic activity-only launcher; select Carnival explicitly.",
        "Do not widen the shared segment past the first `Go now` tap; post-go navigation remains feature-specific.",
    ],
    "feature_overrides": {
        "daily_ui.guild_order_submit": {
            "feature_card_checkpoint_id": "guild_order_description_card",
            "feature_card_anchor_ids": [
                "daily_ui.guild_order_hub_entry",
            ],
            "post_go_checkpoint_id": "guild_panel_landing",
            "close_rule_id": "description_card_close_to_carnival_hub",
            "back_rule_id": "post_go_cleanup_feature_owned",
            "notes": "The shared segment stops after `Go now`; guild panel, Activity tab, and guild-order card navigation stay feature-specific.",
        },
        "daily_ui.merchant_commission_meow": {
            "feature_card_checkpoint_id": "merchant_commission_detail_modal",
            "feature_card_anchor_ids": [
                "daily_ui.merchant_commission_detail_modal",
            ],
            "post_go_checkpoint_id": "merchant_autopath_to_npc",
            "close_rule_id": "description_card_close_to_carnival_hub",
            "back_rule_id": "post_go_cleanup_feature_owned",
            "notes": "The shared segment stops after `Go now`; NPC dialog, merchant list, accept flow, and left-task re-entry stay merchant-specific.",
        },
    },
    "metadata": {
        "shared_hub_label": "CARNIVAL",
        "go_button_label": "立即前往",
        "verified_features": [
            "daily_ui.guild_order_submit",
            "daily_ui.merchant_commission_meow",
        ],
        "checkpoint_truth": {
            "main_screen_idle": "The reusable route starts from a stable main-world screen.",
            "top_right_expanded_icon_group": "Opened by the blue fold/unfold orb near the top-right corner.",
            "carnival_hub": "Shared upper-level hub validated for both guild order and merchant commission.",
            "feature_description_card": "Selecting the target feature card opens a description card.",
            "shared_go_now_handoff": "The shared helper taps `Go now` and hands control to feature-specific navigation.",
        },
        "close_back_rules": {
            "description_card_close_to_carnival_hub": "Use `common.close_button` to dismiss the feature description card back to the Carnival hub before switching targets.",
            "post_go_cleanup_feature_owned": "Any close/back cleanup after `Go now` is feature-owned and not part of the shared helper.",
        },
        "evidence_handoffs": [
            "docs/handoffs/live-entry-route-recon-2026-04-25.md",
            "docs/handoffs/merchant-commission-meow-full-route-2026-04-25.md",
            "docs/handoffs/task-daily-ui-guild-order.md",
        ],
    },
}

_SHARED_CARNIVAL_CHECKPOINT_PACK = {
    "pack_id": "daily_ui.shared_carnival_entry.checkpoints",
    "feature_ids": [
        "daily_ui.guild_order_submit",
        "daily_ui.merchant_commission_meow",
    ],
    "checkpoint_ids": [
        "main_screen_idle",
        "top_right_expanded_icon_group",
        "carnival_hub",
        "feature_description_card",
        "shared_go_now_handoff",
    ],
    "required_anchor_ids": [
        "common.close_button",
    ],
    "supporting_anchor_ids": [
        "daily_ui.guild_order_hub_entry",
        "daily_ui.merchant_commission_poring_button",
        "daily_ui.merchant_commission_carnival_entry",
        "daily_ui.merchant_commission_detail_modal",
        "daily_ui.merchant_commission_go_now_button",
    ],
    "metadata": {
        "feature_anchor_ids": {
            "daily_ui.guild_order_submit": [
                "daily_ui.guild_order_hub_entry",
            ],
            "daily_ui.merchant_commission_meow": [
                "daily_ui.merchant_commission_poring_button",
                "daily_ui.merchant_commission_carnival_entry",
                "daily_ui.merchant_commission_detail_modal",
                "daily_ui.merchant_commission_go_now_button",
            ],
        },
        "close_rule_anchor_ids": [
            "common.close_button",
        ],
        "notes": "This pack intentionally stays narrow: main screen, shared Carnival hub, feature description card, Go now, and shared close/back semantics only.",
    },
}


@dataclass(slots=True)
class SharedEntryRouteContract:
    route_id: str
    entry_checkpoints: list[str] = field(default_factory=list)
    reentry_checkpoints: list[str] = field(default_factory=list)
    blocked_click_notes: list[str] = field(default_factory=list)
    feature_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "route_id": self.route_id,
                "entry_checkpoints": self.entry_checkpoints,
                "reentry_checkpoints": self.reentry_checkpoints,
                "blocked_click_notes": self.blocked_click_notes,
                "feature_overrides": self.feature_overrides,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            route_id=str(data.get("route_id", "")),
            entry_checkpoints=[str(item) for item in data.get("entry_checkpoints", [])],
            reentry_checkpoints=[str(item) for item in data.get("reentry_checkpoints", [])],
            blocked_click_notes=[str(item) for item in data.get("blocked_click_notes", [])],
            feature_overrides=_dict_of_dicts(data.get("feature_overrides", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class SharedCheckpointPack:
    pack_id: str
    feature_ids: list[str] = field(default_factory=list)
    checkpoint_ids: list[str] = field(default_factory=list)
    required_anchor_ids: list[str] = field(default_factory=list)
    supporting_anchor_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "pack_id": self.pack_id,
                "feature_ids": self.feature_ids,
                "checkpoint_ids": self.checkpoint_ids,
                "required_anchor_ids": self.required_anchor_ids,
                "supporting_anchor_ids": self.supporting_anchor_ids,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            pack_id=str(data.get("pack_id", "")),
            feature_ids=[str(item) for item in data.get("feature_ids", [])],
            checkpoint_ids=[str(item) for item in data.get("checkpoint_ids", [])],
            required_anchor_ids=[str(item) for item in data.get("required_anchor_ids", [])],
            supporting_anchor_ids=[str(item) for item in data.get("supporting_anchor_ids", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class SharedCarnivalEntryFeatureNavigationPlan:
    feature_id: str = ""
    feature_card_point: tuple[int, int] = (0, 0)
    go_now_point: tuple[int, int] = (0, 0)
    wait_after_feature_card_sec: float = 1.0
    wait_after_go_now_sec: float = 4.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "feature_id": self.feature_id,
                "feature_card_point": self.feature_card_point,
                "go_now_point": self.go_now_point,
                "wait_after_feature_card_sec": self.wait_after_feature_card_sec,
                "wait_after_go_now_sec": self.wait_after_go_now_sec,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            feature_id=str(data.get("feature_id", "")),
            feature_card_point=_tuple_int_pair(data.get("feature_card_point")),
            go_now_point=_tuple_int_pair(data.get("go_now_point")),
            wait_after_feature_card_sec=float(data.get("wait_after_feature_card_sec", 1.0)),
            wait_after_go_now_sec=float(data.get("wait_after_go_now_sec", 4.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class SharedCarnivalEntryNavigationPlan:
    top_right_entry_point: tuple[int, int] = (0, 0)
    carnival_hub_point: tuple[int, int] = (0, 0)
    wait_after_top_right_entry_sec: float = 1.0
    wait_after_carnival_hub_sec: float = 1.0
    feature_plan: SharedCarnivalEntryFeatureNavigationPlan = field(
        default_factory=SharedCarnivalEntryFeatureNavigationPlan
    )

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "top_right_entry_point": self.top_right_entry_point,
                "carnival_hub_point": self.carnival_hub_point,
                "wait_after_top_right_entry_sec": self.wait_after_top_right_entry_sec,
                "wait_after_carnival_hub_sec": self.wait_after_carnival_hub_sec,
                "feature_plan": self.feature_plan.to_dict(),
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            top_right_entry_point=_tuple_int_pair(data.get("top_right_entry_point")),
            carnival_hub_point=_tuple_int_pair(data.get("carnival_hub_point")),
            wait_after_top_right_entry_sec=float(data.get("wait_after_top_right_entry_sec", 1.0)),
            wait_after_carnival_hub_sec=float(data.get("wait_after_carnival_hub_sec", 1.0)),
            feature_plan=SharedCarnivalEntryFeatureNavigationPlan.from_dict(
                dict(data.get("feature_plan", {}))
            ),
        )


@dataclass(slots=True)
class SharedCarnivalEntryResolution:
    feature_id: str
    checkpoint_ids: list[str] = field(default_factory=list)
    executed_points: list[tuple[int, int]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(
            {
                "feature_id": self.feature_id,
                "checkpoint_ids": self.checkpoint_ids,
                "executed_points": self.executed_points,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            feature_id=str(data.get("feature_id", "")),
            checkpoint_ids=[str(item) for item in data.get("checkpoint_ids", [])],
            executed_points=[_tuple_int_pair(item) for item in data.get("executed_points", [])],
            metadata=dict(data.get("metadata", {})),
        )


class SharedCarnivalEntryAdapter(Protocol):
    def tap(self, instance: object, point: tuple[int, int]) -> None:
        """Tap one screen coordinate."""


def load_shared_carnival_entry_route_contract() -> SharedEntryRouteContract:
    return SharedEntryRouteContract.from_dict(_SHARED_CARNIVAL_ENTRY_ROUTE)


def load_shared_carnival_entry_checkpoint_pack() -> SharedCheckpointPack:
    return SharedCheckpointPack.from_dict(_SHARED_CARNIVAL_CHECKPOINT_PACK)


def resolve_shared_carnival_entry(
    *,
    adapter: SharedCarnivalEntryAdapter,
    instance: object,
    navigation_plan: SharedCarnivalEntryNavigationPlan,
    sleep_fn: Any = time.sleep,
) -> SharedCarnivalEntryResolution:
    feature_id = str(navigation_plan.feature_plan.feature_id).strip()
    if not feature_id:
        raise ValueError("Shared Carnival entry requires a non-empty feature_id.")

    route_contract = load_shared_carnival_entry_route_contract()
    checkpoint_pack = load_shared_carnival_entry_checkpoint_pack()
    feature_override = dict(route_contract.feature_overrides.get(feature_id, {}))

    executed_points: list[tuple[int, int]] = []
    checkpoint_ids = ["main_screen_idle"]

    def _tap(point: tuple[int, int], wait_sec: float, checkpoint_id: str) -> None:
        adapter.tap(instance, point)
        executed_points.append(point)
        checkpoint_ids.append(checkpoint_id)
        sleep_fn(wait_sec)

    _tap(
        navigation_plan.top_right_entry_point,
        navigation_plan.wait_after_top_right_entry_sec,
        "top_right_expanded_icon_group",
    )
    _tap(
        navigation_plan.carnival_hub_point,
        navigation_plan.wait_after_carnival_hub_sec,
        "carnival_hub",
    )
    _tap(
        navigation_plan.feature_plan.feature_card_point,
        navigation_plan.feature_plan.wait_after_feature_card_sec,
        "feature_description_card",
    )
    _tap(
        navigation_plan.feature_plan.go_now_point,
        navigation_plan.feature_plan.wait_after_go_now_sec,
        "shared_go_now_handoff",
    )

    return SharedCarnivalEntryResolution(
        feature_id=feature_id,
        checkpoint_ids=checkpoint_ids,
        executed_points=executed_points,
        metadata={
            "navigation_plan": navigation_plan.to_dict(),
            "route_contract": route_contract.to_dict(),
            "checkpoint_pack": checkpoint_pack.to_dict(),
            "feature_override": feature_override,
        },
    )


def _dict_of_dicts(value: object) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            normalized[str(key)] = dict(item)
    return normalized


def _tuple_int_pair(value: object, *, default: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    if isinstance(value, tuple) and len(value) == 2:
        return int(value[0]), int(value[1])
    if isinstance(value, list) and len(value) == 2:
        return int(value[0]), int(value[1])
    return default
