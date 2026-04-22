from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository, TaskReadinessState
from roxauto.tasks.daily_ui import (
    GuildOrderAvailability,
    GuildOrderDecision,
    GuildOrderDecisionValue,
    GuildOrderMaterialPolicy,
    GuildOrderMaterialSufficiency,
    GuildOrderRequirement,
    GuildOrderVerificationState,
    build_guild_order_submit_specification,
    load_guild_order_submit_blueprint,
    load_guild_order_submit_decision_contract,
    load_guild_order_submit_material_policy,
    load_guild_order_submit_visibility_contract,
)


class GuildOrderSubmitFoundationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = TaskFoundationRepository.load_default()

    def test_loads_guild_order_blueprint_and_contracts(self) -> None:
        blueprint = load_guild_order_submit_blueprint(self.repository)
        material_policy = load_guild_order_submit_material_policy(self.repository)
        decision_contract = load_guild_order_submit_decision_contract(self.repository)
        visibility_contract = load_guild_order_submit_visibility_contract(self.repository)

        self.assertEqual(blueprint.task_id, "daily_ui.guild_order_submit")
        self.assertEqual(blueprint.implementation_state.value, "spec_only")
        self.assertEqual(
            blueprint.required_anchors,
            [
                "common.close_button",
                "daily_ui.guild_order_list_panel",
                "daily_ui.guild_order_detail_panel",
                "daily_ui.guild_order_submit_button",
                "daily_ui.guild_order_refresh_button",
            ],
        )
        self.assertEqual(
            blueprint.metadata["supporting_anchor_ids"],
            [
                "daily_ui.guild_order_material_label",
                "daily_ui.guild_order_required_quantity",
                "daily_ui.guild_order_available_quantity",
                "daily_ui.guild_order_unavailable_state",
                "daily_ui.guild_order_insufficient_material_feedback",
                "daily_ui.guild_order_submit_result_state",
            ],
        )
        self.assertEqual(material_policy.decision_boundary, "visible_material_evidence_only")
        self.assertEqual(material_policy.max_refresh_attempts_per_run, 1)
        self.assertEqual(decision_contract.allowed_decisions, ["submit", "skip", "refresh"])
        self.assertIn("materials_sufficient", decision_contract.reason_ids)
        self.assertIn("verification_state", decision_contract.decision_signal_keys)
        self.assertEqual(
            visibility_contract.foundation_requirement_ids,
            [
                "foundation.daily_ui.guild_order_visible_quantity_contract",
                "foundation.daily_ui.guild_order_result_state_contract",
            ],
        )

    def test_builds_guild_order_specification_from_builder_input_and_readiness(self) -> None:
        builder_input = self.repository.build_runtime_builder_input("daily_ui.guild_order_submit")
        readiness = self.repository.evaluate_task_readiness("daily_ui.guild_order_submit")

        specification = build_guild_order_submit_specification(
            builder_input=builder_input,
            readiness_report=readiness,
            foundation_repository=self.repository,
        )

        self.assertEqual(specification.task_id, "daily_ui.guild_order_submit")
        self.assertEqual(specification.fixture_profile.fixture_id, "fixture.tw.guild.default")
        self.assertEqual(specification.metadata["signal_contract_version"], "guild_order_submit.v1")
        self.assertEqual(
            specification.metadata["guild_order_handoff_fields"],
            [
                "decision",
                "reason_id",
                "slot_index",
                "requirements",
                "availability",
                "refresh_attempted",
                "verification_state",
            ],
        )
        self.assertEqual(specification.required_screen_slugs, ["order_list", "order_detail"])
        self.assertEqual(
            specification.supporting_screen_slugs,
            ["insufficient_material_state", "completed_state", "submit_result"],
        )
        self.assertEqual(
            specification.readiness_report.builder_readiness_state,
            TaskReadinessState.BLOCKED_BY_FOUNDATION,
        )
        self.assertEqual(
            specification.readiness_report.implementation_readiness_state,
            TaskReadinessState.BLOCKED_BY_FOUNDATION,
        )
        self.assertEqual(specification.decision_contract.allowed_decisions, ["submit", "skip", "refresh"])
        self.assertEqual(
            specification.visibility_contract.required_anchor_ids,
            specification.required_anchor_ids,
        )

    def test_round_trips_machine_readable_guild_order_decision(self) -> None:
        decision = GuildOrderDecision(
            decision=GuildOrderDecisionValue.REFRESH,
            reason_id="materials_insufficient",
            slot_index=2,
            requirements=[
                GuildOrderRequirement(
                    slot_index=2,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=3,
                    evidence={"source": "detail_panel"},
                )
            ],
            availability=[
                GuildOrderAvailability(
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    available_quantity=1,
                    sufficiency=GuildOrderMaterialSufficiency.INSUFFICIENT,
                    evidence={"source": "inventory_chip"},
                )
            ],
            refresh_attempted=True,
            verification_state=GuildOrderVerificationState.REFRESH_VERIFIED,
            metadata={"refresh_attempt_count": 1},
        )

        restored = GuildOrderDecision.from_dict(decision.to_dict())

        self.assertEqual(restored.decision, GuildOrderDecisionValue.REFRESH)
        self.assertEqual(restored.reason_id, "materials_insufficient")
        self.assertEqual(restored.requirements[0].required_quantity, 3)
        self.assertEqual(restored.availability[0].sufficiency, GuildOrderMaterialSufficiency.INSUFFICIENT)
        self.assertTrue(restored.refresh_attempted)
        self.assertEqual(restored.verification_state, GuildOrderVerificationState.REFRESH_VERIFIED)

    def test_round_trips_material_policy(self) -> None:
        policy = GuildOrderMaterialPolicy(
            blocked_material_labels=["Rare Herb"],
            reserve_quantity_by_material_label={"Copper Ore": 5},
            refresh_allowed=False,
            max_refresh_attempts_per_run=0,
            decision_priority=["submit", "skip"],
            decision_boundary="visible_material_evidence_only",
            disallowed_behaviors=["crafting", "buying"],
        )

        restored = GuildOrderMaterialPolicy.from_dict(policy.to_dict())

        self.assertEqual(restored.blocked_material_labels, ["Rare Herb"])
        self.assertEqual(restored.reserve_quantity_by_material_label["Copper Ore"], 5)
        self.assertFalse(restored.refresh_allowed)
        self.assertEqual(restored.max_refresh_attempts_per_run, 0)
