from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.tasks import TaskFoundationRepository, TaskReadinessState
from roxauto.tasks.daily_ui import (
    GuildOrderAvailability,
    GuildOrderCustomOption,
    GuildOrderDecision,
    GuildOrderDecisionValue,
    GuildOrderMaterialPolicy,
    GuildOrderMaterialSufficiency,
    GuildOrderOrderKind,
    GuildOrderRequirement,
    GuildOrderVerificationState,
    build_guild_order_submit_specification,
    evaluate_guild_order_submit_decision,
    load_guild_order_submit_blueprint,
    load_guild_order_submit_decision_contract,
    load_guild_order_submit_material_policy,
    load_guild_order_submit_visibility_contract,
    select_guild_order_custom_option,
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
        self.assertEqual(blueprint.metadata["shared_entry_route_id"], "daily_ui.shared_carnival_entry")
        self.assertEqual(
            blueprint.metadata["shared_checkpoint_pack_id"],
            "daily_ui.shared_carnival_entry.checkpoints",
        )
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
                "daily_ui.guild_order_custom_list_button",
                "daily_ui.guild_order_custom_list_panel",
                "daily_ui.guild_order_custom_option_material_label",
                "daily_ui.guild_order_custom_option_required_quantity",
                "daily_ui.guild_order_custom_option_available_quantity",
                "daily_ui.guild_order_custom_option_selected_state",
                "daily_ui.guild_order_unavailable_state",
                "daily_ui.guild_order_insufficient_material_feedback",
                "daily_ui.guild_order_submit_result_state",
            ],
        )
        self.assertEqual(material_policy.decision_boundary, "visible_material_evidence_only")
        self.assertTrue(material_policy.custom_order_enabled)
        self.assertEqual(material_policy.custom_order_selected_candidate_index, 1)
        self.assertEqual(material_policy.custom_order_selection_boundary, "visible_custom_order_candidate_evidence_only")
        self.assertEqual(material_policy.max_refresh_attempts_per_run, 1)
        self.assertEqual(decision_contract.allowed_decisions, ["submit", "skip", "refresh"])
        self.assertIn("custom_order_option_selected", decision_contract.reason_ids)
        self.assertIn("custom_order_selected_candidate_missing", decision_contract.reason_ids)
        self.assertIn("custom_order_selected_candidate_blocked", decision_contract.reason_ids)
        self.assertIn("custom_order_selected_candidate_insufficient", decision_contract.reason_ids)
        self.assertIn("order_kind", decision_contract.decision_signal_keys)
        self.assertIn("materials_sufficient", decision_contract.reason_ids)
        self.assertIn("verification_state", decision_contract.decision_signal_keys)
        self.assertEqual(
            visibility_contract.foundation_requirement_ids,
            [
                "foundation.daily_ui.guild_order_visible_quantity_contract",
                "foundation.daily_ui.guild_order_result_state_contract",
                "foundation.daily_ui.guild_order_custom_option_contract",
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
        self.assertEqual(specification.metadata["signal_contract_version"], "guild_order_submit.v2")
        self.assertEqual(specification.metadata["shared_entry_route_id"], "daily_ui.shared_carnival_entry")
        self.assertEqual(
            specification.metadata["shared_checkpoint_pack_id"],
            "daily_ui.shared_carnival_entry.checkpoints",
        )
        self.assertEqual(
            specification.metadata["guild_order_handoff_fields"],
            [
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
            ],
        )
        self.assertEqual(
            specification.shared_entry_route_contract.feature_overrides["daily_ui.guild_order_submit"][
                "post_go_checkpoint_id"
            ],
            "guild_panel_landing",
        )
        self.assertEqual(
            specification.shared_checkpoint_pack.required_anchor_ids,
            ["common.close_button"],
        )
        self.assertEqual(specification.required_screen_slugs, ["order_list", "order_detail"])
        self.assertEqual(
            specification.supporting_screen_slugs,
            [
                "custom_order_detail",
                "custom_order_list",
                "insufficient_material_state",
                "completed_state",
                "submit_result",
            ],
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
            order_kind=GuildOrderOrderKind.CUSTOM,
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
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=25,
                    sufficiency=GuildOrderMaterialSufficiency.SUFFICIENT,
                    evidence={"source": "custom_list"},
                )
            ],
            selected_custom_option=GuildOrderCustomOption(
                candidate_index=1,
                material_label="Copper Ore",
                normalized_material_id="copper_ore",
                required_quantity=10,
                available_quantity=25,
                sufficiency=GuildOrderMaterialSufficiency.SUFFICIENT,
                evidence={"source": "custom_list"},
            ),
            refresh_attempted=True,
            verification_state=GuildOrderVerificationState.REFRESH_VERIFIED,
            metadata={"refresh_attempt_count": 1},
        )

        restored = GuildOrderDecision.from_dict(decision.to_dict())

        self.assertEqual(restored.decision, GuildOrderDecisionValue.REFRESH)
        self.assertEqual(restored.reason_id, "materials_insufficient")
        self.assertEqual(restored.order_kind, GuildOrderOrderKind.CUSTOM)
        self.assertEqual(restored.requirements[0].required_quantity, 3)
        self.assertEqual(restored.availability[0].sufficiency, GuildOrderMaterialSufficiency.INSUFFICIENT)
        self.assertEqual(restored.custom_options[0].candidate_index, 1)
        self.assertEqual(restored.selected_custom_option.material_label, "Copper Ore")
        self.assertTrue(restored.refresh_attempted)
        self.assertEqual(restored.verification_state, GuildOrderVerificationState.REFRESH_VERIFIED)

    def test_round_trips_material_policy(self) -> None:
        policy = GuildOrderMaterialPolicy(
            blocked_material_labels=["Rare Herb"],
            reserve_quantity_by_material_label={"Copper Ore": 5},
            refresh_allowed=False,
            max_refresh_attempts_per_run=0,
            custom_order_enabled=True,
            custom_order_preferred_material_labels=["Copper Ore"],
            custom_order_selected_candidate_index=2,
            custom_order_max_candidates_to_inspect=3,
            decision_priority=["submit", "skip"],
            decision_boundary="visible_material_evidence_only",
            disallowed_behaviors=["crafting", "buying"],
        )

        restored = GuildOrderMaterialPolicy.from_dict(policy.to_dict())

        self.assertEqual(restored.blocked_material_labels, ["Rare Herb"])
        self.assertEqual(restored.reserve_quantity_by_material_label["Copper Ore"], 5)
        self.assertFalse(restored.refresh_allowed)
        self.assertEqual(restored.max_refresh_attempts_per_run, 0)
        self.assertTrue(restored.custom_order_enabled)
        self.assertEqual(restored.custom_order_preferred_material_labels, ["Copper Ore"])
        self.assertEqual(restored.custom_order_selected_candidate_index, 2)
        self.assertEqual(restored.custom_order_max_candidates_to_inspect, 3)

    def test_selects_explicit_custom_order_candidate_by_1_based_index(self) -> None:
        policy = GuildOrderMaterialPolicy(
            custom_order_enabled=True,
            custom_order_selected_candidate_index=2,
        )

        selected = select_guild_order_custom_option(
            policy=policy,
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
            ],
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected.material_label, "Copper Ore")
        self.assertEqual(selected.sufficiency, GuildOrderMaterialSufficiency.SUFFICIENT)

    def test_explicit_custom_order_candidate_does_not_fallback_to_another_option(self) -> None:
        policy = GuildOrderMaterialPolicy(
            custom_order_enabled=True,
            custom_order_selected_candidate_index=2,
        )

        selected = select_guild_order_custom_option(
            policy=policy,
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=0,
                ),
            ],
        )

        self.assertIsNone(selected)

    def test_selects_preferred_viable_custom_order_option_when_explicit_index_disabled(self) -> None:
        policy = GuildOrderMaterialPolicy(
            custom_order_enabled=True,
            custom_order_selected_candidate_index=None,
            custom_order_preferred_material_labels=["Copper Ore"],
            reserve_quantity_by_material_label={"Copper Ore": 5},
        )

        selected = select_guild_order_custom_option(
            policy=policy,
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
            ],
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected.material_label, "Copper Ore")
        self.assertEqual(selected.sufficiency, GuildOrderMaterialSufficiency.SUFFICIENT)

    def test_evaluates_custom_order_submit_with_selected_option(self) -> None:
        decision = evaluate_guild_order_submit_decision(
            slot_index=9,
            order_kind=GuildOrderOrderKind.CUSTOM,
            policy=GuildOrderMaterialPolicy(
                custom_order_enabled=True,
                custom_order_selected_candidate_index=2,
            ),
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=0,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
            ],
        )

        self.assertEqual(decision.decision, GuildOrderDecisionValue.SUBMIT)
        self.assertEqual(decision.reason_id, "custom_order_option_selected")
        self.assertEqual(decision.order_kind, GuildOrderOrderKind.CUSTOM)
        self.assertIsNotNone(decision.selected_custom_option)
        self.assertEqual(decision.selected_custom_option.material_label, "Copper Ore")
        self.assertEqual(decision.requirements[0].material_label, "Copper Ore")

    def test_evaluates_custom_order_refresh_when_no_viable_option_exists(self) -> None:
        decision = evaluate_guild_order_submit_decision(
            slot_index=9,
            order_kind=GuildOrderOrderKind.CUSTOM,
            policy=GuildOrderMaterialPolicy(
                custom_order_enabled=True,
                custom_order_selected_candidate_index=None,
                refresh_allowed=True,
                max_refresh_attempts_per_run=1,
            ),
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=0,
                )
            ],
        )

        self.assertEqual(decision.decision, GuildOrderDecisionValue.REFRESH)
        self.assertEqual(decision.reason_id, "custom_order_no_viable_option")

    def test_evaluates_custom_order_refresh_when_selected_candidate_is_missing(self) -> None:
        decision = evaluate_guild_order_submit_decision(
            slot_index=9,
            order_kind=GuildOrderOrderKind.CUSTOM,
            policy=GuildOrderMaterialPolicy(
                custom_order_enabled=True,
                custom_order_selected_candidate_index=3,
                refresh_allowed=True,
                max_refresh_attempts_per_run=1,
            ),
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
            ],
        )

        self.assertEqual(decision.decision, GuildOrderDecisionValue.REFRESH)
        self.assertEqual(decision.reason_id, "custom_order_selected_candidate_missing")

    def test_evaluates_custom_order_refresh_when_selected_candidate_exceeds_inspection_cap(self) -> None:
        decision = evaluate_guild_order_submit_decision(
            slot_index=9,
            order_kind=GuildOrderOrderKind.CUSTOM,
            policy=GuildOrderMaterialPolicy(
                custom_order_enabled=True,
                custom_order_selected_candidate_index=2,
                custom_order_max_candidates_to_inspect=1,
                refresh_allowed=True,
                max_refresh_attempts_per_run=1,
            ),
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=0,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
            ],
        )

        self.assertEqual(decision.decision, GuildOrderDecisionValue.REFRESH)
        self.assertEqual(decision.reason_id, "custom_order_selected_candidate_missing")
        self.assertIsNone(decision.selected_custom_option)

    def test_evaluates_custom_order_refresh_when_selected_candidate_is_blocked(self) -> None:
        decision = evaluate_guild_order_submit_decision(
            slot_index=9,
            order_kind=GuildOrderOrderKind.CUSTOM,
            policy=GuildOrderMaterialPolicy(
                custom_order_enabled=True,
                custom_order_selected_candidate_index=2,
                blocked_material_ids=["copper_ore"],
                refresh_allowed=True,
                max_refresh_attempts_per_run=1,
            ),
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
            ],
        )

        self.assertEqual(decision.decision, GuildOrderDecisionValue.REFRESH)
        self.assertEqual(decision.reason_id, "custom_order_selected_candidate_blocked")

    def test_evaluates_custom_order_skip_when_selected_candidate_is_insufficient_and_refresh_is_exhausted(self) -> None:
        decision = evaluate_guild_order_submit_decision(
            slot_index=9,
            order_kind=GuildOrderOrderKind.CUSTOM,
            policy=GuildOrderMaterialPolicy(
                custom_order_enabled=True,
                custom_order_selected_candidate_index=2,
                refresh_allowed=True,
                max_refresh_attempts_per_run=1,
            ),
            custom_options=[
                GuildOrderCustomOption(
                    candidate_index=1,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                    available_quantity=20,
                ),
                GuildOrderCustomOption(
                    candidate_index=2,
                    material_label="Copper Ore",
                    normalized_material_id="copper_ore",
                    required_quantity=10,
                    available_quantity=0,
                ),
            ],
            refresh_attempt_count=1,
        )

        self.assertEqual(decision.decision, GuildOrderDecisionValue.SKIP)
        self.assertEqual(decision.reason_id, "refresh_limit_reached")
        self.assertEqual(decision.metadata["fallback_reason_id"], "custom_order_selected_candidate_insufficient")

    def test_evaluates_standard_order_skip_after_refresh_limit(self) -> None:
        decision = evaluate_guild_order_submit_decision(
            slot_index=2,
            order_kind=GuildOrderOrderKind.STANDARD,
            policy=GuildOrderMaterialPolicy(
                refresh_allowed=True,
                max_refresh_attempts_per_run=1,
            ),
            requirements=[
                GuildOrderRequirement(
                    slot_index=2,
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    required_quantity=10,
                )
            ],
            availability=[
                GuildOrderAvailability(
                    material_label="Iron Ore",
                    normalized_material_id="iron_ore",
                    available_quantity=1,
                )
            ],
            refresh_attempt_count=1,
        )

        self.assertEqual(decision.decision, GuildOrderDecisionValue.SKIP)
        self.assertEqual(decision.reason_id, "refresh_limit_reached")
        self.assertEqual(decision.metadata["fallback_reason_id"], "materials_insufficient")
