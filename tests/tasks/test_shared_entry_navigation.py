from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import (
    SharedCarnivalEntryFeatureNavigationPlan,
    SharedCarnivalEntryNavigationPlan,
    SharedCarnivalEntryResolution,
    load_shared_carnival_entry_checkpoint_pack,
    load_shared_carnival_entry_route_contract,
    resolve_shared_carnival_entry,
)


class _FakeSharedEntryAdapter:
    def __init__(self) -> None:
        self.taps: list[tuple[int, int]] = []

    def tap(self, instance: object, point: tuple[int, int]) -> None:
        self.taps.append(point)


class SharedEntryNavigationTests(unittest.TestCase):
    def test_loads_shared_carnival_entry_contract_and_checkpoint_pack(self) -> None:
        route_contract = load_shared_carnival_entry_route_contract()
        checkpoint_pack = load_shared_carnival_entry_checkpoint_pack()

        self.assertEqual(route_contract.route_id, "daily_ui.shared_carnival_entry")
        self.assertEqual(
            route_contract.entry_checkpoints,
            [
                "main_screen_idle",
                "top_right_expanded_icon_group",
                "carnival_hub",
                "feature_description_card",
                "shared_go_now_handoff",
            ],
        )
        self.assertEqual(route_contract.feature_overrides["daily_ui.guild_order_submit"]["post_go_checkpoint_id"], "guild_panel_landing")
        self.assertEqual(
            route_contract.metadata["close_back_rules"]["description_card_close_to_carnival_hub"],
            "Use `common.close_button` to dismiss the feature description card back to the Carnival hub before switching targets.",
        )
        self.assertEqual(
            checkpoint_pack.feature_ids,
            ["daily_ui.guild_order_submit", "daily_ui.merchant_commission_meow"],
        )
        self.assertEqual(checkpoint_pack.required_anchor_ids, ["common.close_button"])
        self.assertIn("daily_ui.guild_order_hub_entry", checkpoint_pack.supporting_anchor_ids)

    def test_resolve_shared_carnival_entry_runs_only_the_shared_go_now_segment(self) -> None:
        adapter = _FakeSharedEntryAdapter()

        resolution = resolve_shared_carnival_entry(
            adapter=adapter,
            instance=object(),
            navigation_plan=SharedCarnivalEntryNavigationPlan(
                top_right_entry_point=(1, 2),
                carnival_hub_point=(3, 4),
                wait_after_top_right_entry_sec=0.0,
                wait_after_carnival_hub_sec=0.0,
                feature_plan=SharedCarnivalEntryFeatureNavigationPlan(
                    feature_id="daily_ui.merchant_commission_meow",
                    feature_card_point=(5, 6),
                    go_now_point=(7, 8),
                    wait_after_feature_card_sec=0.0,
                    wait_after_go_now_sec=0.0,
                ),
            ),
            sleep_fn=lambda seconds: None,
        )

        self.assertEqual(adapter.taps, [(1, 2), (3, 4), (5, 6), (7, 8)])
        self.assertEqual(
            resolution.checkpoint_ids,
            [
                "main_screen_idle",
                "top_right_expanded_icon_group",
                "carnival_hub",
                "feature_description_card",
                "shared_go_now_handoff",
            ],
        )
        self.assertEqual(
            resolution.metadata["feature_override"]["post_go_checkpoint_id"],
            "merchant_autopath_to_npc",
        )

    def test_round_trips_shared_carnival_entry_resolution(self) -> None:
        resolution = SharedCarnivalEntryResolution(
            feature_id="daily_ui.guild_order_submit",
            checkpoint_ids=["main_screen_idle", "carnival_hub"],
            executed_points=[(1, 2), (3, 4)],
            metadata={"route_id": "daily_ui.shared_carnival_entry"},
        )

        restored = SharedCarnivalEntryResolution.from_dict(resolution.to_dict())

        self.assertEqual(restored.feature_id, "daily_ui.guild_order_submit")
        self.assertEqual(restored.checkpoint_ids, ["main_screen_idle", "carnival_hub"])
        self.assertEqual(restored.executed_points, [(1, 2), (3, 4)])
        self.assertEqual(restored.metadata, {"route_id": "daily_ui.shared_carnival_entry"})
