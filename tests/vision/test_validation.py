from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.vision import (
    AnchorAssetProvenanceKind,
    AnchorRepository,
    TemplateReadinessStatus,
    TemplateWorkspaceValidationReport,
    VisionWorkspaceReadinessReport,
    build_vision_workspace_readiness_report,
    validate_template_repository,
    validate_template_workspace,
)


class TemplateValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.templates_root = Path(__file__).resolve().parents[2] / "assets" / "templates"
        self.asset_inventory_path = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "roxauto"
            / "tasks"
            / "foundations"
            / "asset_inventory.json"
        )

    def test_validate_template_repository_accepts_sample_common_pack(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "common")

        report = validate_template_repository(repository)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.repository_id, "common")
        self.assertEqual(report.anchor_count, 2)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.warning_count, 0)

    def test_validate_template_repository_accepts_claim_rewards_task_support_contract(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "daily_ui")

        report = validate_template_repository(repository)
        issue_codes = {
            issue.code
            for issue in report.issues
            if issue.metadata.get("task_id") == "daily_ui.claim_rewards"
        }

        self.assertTrue(report.is_valid)
        self.assertEqual(report.anchor_count, 12)
        self.assertNotIn("missing_task_support_anchor_role", issue_codes)
        self.assertNotIn("duplicate_task_support_anchor_role", issue_codes)
        self.assertNotIn("missing_anchor_task_support_role", issue_codes)
        self.assertNotIn("missing_anchor_curation_metadata", issue_codes)
        self.assertNotIn("missing_anchor_curation_field", issue_codes)
        self.assertNotIn("missing_anchor_curation_provenance", issue_codes)
        self.assertNotIn("missing_anchor_failure_case", issue_codes)
        self.assertNotIn("missing_curation_reference_asset", issue_codes)
        self.assertNotIn("missing_claim_rewards_golden_catalog", issue_codes)
        self.assertNotIn("invalid_claim_rewards_golden_catalog_json", issue_codes)
        self.assertNotIn("invalid_claim_rewards_golden_catalog_entries", issue_codes)
        self.assertNotIn("missing_anchor_golden_id", issue_codes)
        self.assertNotIn("missing_anchor_golden_catalog_entry", issue_codes)
        self.assertNotIn("anchor_golden_catalog_live_capture_mismatch", issue_codes)
        self.assertNotIn("anchor_golden_catalog_source_kind_mismatch", issue_codes)
        self.assertNotIn("anchor_golden_catalog_failure_case_mismatch", issue_codes)
        self.assertNotIn("invalid_claim_rewards_supporting_capture_entries", issue_codes)
        self.assertNotIn("missing_claim_rewards_supporting_capture_failure_case", issue_codes)
        self.assertNotIn("missing_claim_rewards_supporting_capture_evidence_role", issue_codes)
        self.assertNotIn("missing_claim_rewards_golden_supporting_capture_entry", issue_codes)
        self.assertNotIn("claim_rewards_supporting_capture_anchor_mismatch", issue_codes)
        self.assertNotIn("missing_claim_rewards_golden_sha256", issue_codes)
        self.assertNotIn("claim_rewards_golden_sha256_mismatch", issue_codes)
        self.assertNotIn("missing_claim_rewards_supporting_capture_sha256", issue_codes)
        self.assertNotIn("claim_rewards_supporting_capture_sha256_mismatch", issue_codes)
        self.assertNotIn("missing_claim_rewards_live_capture_coverage", issue_codes)
        self.assertNotIn("claim_rewards_live_anchor_missing_from_coverage", issue_codes)
        self.assertNotIn("claim_rewards_stand_in_anchor_missing_from_coverage", issue_codes)
        self.assertNotIn("claim_rewards_live_context_coverage_overlap", issue_codes)
        self.assertNotIn("claim_rewards_live_context_anchor_not_stand_in", issue_codes)
        self.assertNotIn("claim_rewards_live_context_anchor_missing_from_coverage", issue_codes)
        self.assertNotIn("claim_rewards_live_context_anchor_missing_live_reference", issue_codes)
        self.assertNotIn("claim_rewards_blocked_scene_missing_from_coverage", issue_codes)
        self.assertNotIn("missing_claim_rewards_post_tap_contract", issue_codes)
        self.assertNotIn("invalid_claim_rewards_post_tap_contract_kind", issue_codes)
        self.assertNotIn("invalid_claim_rewards_post_tap_contract_recommendation", issue_codes)
        self.assertNotIn("missing_claim_rewards_catalog_post_tap_contract", issue_codes)
        self.assertNotIn("claim_rewards_post_tap_contract_catalog_mismatch", issue_codes)
        self.assertNotIn("unknown_claim_rewards_post_tap_contract_capture", issue_codes)
        self.assertNotIn("claim_rewards_post_tap_contract_capture_anchor_mismatch", issue_codes)

    def test_validate_template_repository_accepts_guild_order_scene_contract(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "daily_ui")

        report = validate_template_repository(repository)
        issue_codes = {
            issue.code
            for issue in report.issues
            if issue.metadata.get("task_id") == "daily_ui.guild_order_submit"
        }

        self.assertTrue(report.is_valid)
        self.assertNotIn("missing_task_support_anchor_role", issue_codes)
        self.assertNotIn("duplicate_task_support_anchor_role", issue_codes)
        self.assertNotIn("missing_anchor_task_support_role", issue_codes)
        self.assertNotIn("missing_guild_order_scene_contract", issue_codes)
        self.assertNotIn("guild_order_scene_contract_ready_placeholder_overlap", issue_codes)
        self.assertNotIn("guild_order_scene_contract_ready_blocked_overlap", issue_codes)
        self.assertNotIn("guild_order_scene_contract_placeholder_blocked_overlap", issue_codes)
        self.assertNotIn("unknown_guild_order_scene_contract_anchor", issue_codes)
        self.assertNotIn("missing_guild_order_scene_contract_required_scenes", issue_codes)
        self.assertNotIn("missing_guild_order_scene_contract_evidence_state", issue_codes)
        self.assertNotIn("missing_guild_order_scene_contract_decision_surface_state", issue_codes)
        self.assertNotIn("missing_guild_order_scene_contract_summary", issue_codes)
        self.assertNotIn("guild_order_placeholder_anchor_missing_from_scene_contract", issue_codes)
        self.assertNotIn("guild_order_ready_anchor_marked_placeholder", issue_codes)
        self.assertNotIn("guild_order_placeholder_anchor_not_placeholder", issue_codes)
        self.assertNotIn("guild_order_ready_anchor_missing_from_scene_contract", issue_codes)

    def test_validate_template_repository_rejects_guild_order_scene_contract_drift(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "daily_ui"
            shutil.copytree(self.templates_root / "daily_ui", repository_root)
            manifest_path = repository_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            contract = manifest["metadata"]["task_support"]["daily_ui.guild_order_submit"]["scene_contract"]
            contract["ready_anchor_ids"] = ["daily_ui.guild_order_hub_entry"]
            contract["placeholder_anchor_ids"] = [
                anchor_id
                for anchor_id in contract["placeholder_anchor_ids"]
                if anchor_id != "daily_ui.guild_order_hub_entry"
            ]
            contract["summary"] = ""
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            report = validate_template_repository(AnchorRepository.load(repository_root))

        issue_codes = {issue.code for issue in report.issues}
        self.assertFalse(report.is_valid)
        self.assertIn("guild_order_placeholder_anchor_missing_from_scene_contract", issue_codes)
        self.assertIn("guild_order_ready_anchor_marked_placeholder", issue_codes)
        self.assertIn("missing_guild_order_scene_contract_summary", issue_codes)

    def test_validate_template_repository_rejects_claim_rewards_catalog_hash_drift(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "daily_ui"
            shutil.copytree(self.templates_root / "daily_ui", repository_root)
            catalog_path = repository_root / "goldens" / "claim_rewards" / "catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["goldens"][0]["sha256"] = "0" * 64
            catalog["supporting_captures"][0]["sha256"] = "f" * 64
            catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

            report = validate_template_repository(AnchorRepository.load(repository_root))

        issue_codes = {issue.code for issue in report.issues}
        self.assertFalse(report.is_valid)
        self.assertIn("claim_rewards_golden_sha256_mismatch", issue_codes)
        self.assertIn("claim_rewards_supporting_capture_sha256_mismatch", issue_codes)

    def test_validate_template_repository_reports_invalid_anchor_configuration(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "broken_pack"
            anchors_root = repository_root / "anchors"
            anchors_root.mkdir(parents=True)
            (anchors_root / "MixedCase-Button.PNG").write_text("placeholder", encoding="utf-8")

            manifest = {
                "repository_id": "broken_pack",
                "display_name": "Broken Pack",
                "version": "0.1.0",
                "anchors": [
                    {
                        "anchor_id": "misgrouped.anchor",
                        "label": "",
                        "template_path": "anchors/MixedCase-Button.PNG",
                        "confidence_threshold": 1.2,
                        "match_region": [0, 0, 0, 10],
                    },
                    {
                        "anchor_id": "broken_pack.outside",
                        "label": "Outside",
                        "template_path": "../escape.png",
                        "confidence_threshold": 0.8,
                    },
                ],
            }
            (repository_root / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            report = validate_template_repository(AnchorRepository.load(repository_root))

        issue_codes = {issue.code for issue in report.issues}
        self.assertFalse(report.is_valid)
        self.assertIn("anchor_id_prefix_mismatch", issue_codes)
        self.assertIn("missing_anchor_label", issue_codes)
        self.assertIn("invalid_confidence_threshold", issue_codes)
        self.assertIn("invalid_match_region", issue_codes)
        self.assertIn("invalid_template_asset_name", issue_codes)
        self.assertIn("template_path_outside_repository", issue_codes)

    def test_validate_template_repository_reports_missing_task_support_roles(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "daily_ui"
            anchors_root = repository_root / "anchors"
            anchors_root.mkdir(parents=True)
            (anchors_root / "claim.svg").write_text("<svg />", encoding="utf-8")
            manifest = {
                "repository_id": "daily_ui",
                "display_name": "Daily UI Templates",
                "version": "0.1.0",
                "metadata": {
                    "task_support": {
                        "daily_ui.claim_rewards": {
                            "required_anchor_roles": [
                                "reward_panel",
                                "claim_reward_button",
                                "confirm_state",
                            ]
                        }
                    }
                },
                "anchors": [
                    {
                        "anchor_id": "daily_ui.claim_reward",
                        "label": "Claim",
                        "template_path": "anchors/claim.svg",
                        "confidence_threshold": 0.91,
                        "match_region": [1, 2, 3, 4],
                        "metadata": {
                            "task_id": "daily_ui.claim_rewards",
                            "inspection_role": "claim_reward_button",
                        },
                    }
                ],
            }
            (repository_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            report = validate_template_repository(AnchorRepository.load(repository_root))

        task_support_issues = [
            issue
            for issue in report.issues
            if issue.code == "missing_task_support_anchor_role"
            and issue.metadata.get("task_id") == "daily_ui.claim_rewards"
        ]
        missing_roles = {issue.metadata["inspection_role"] for issue in task_support_issues}

        self.assertFalse(report.is_valid)
        self.assertEqual(missing_roles, {"reward_panel", "confirm_state"})

    def test_validate_template_repository_requires_claim_rewards_curation_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "daily_ui"
            anchors_root = repository_root / "anchors"
            anchors_root.mkdir(parents=True)
            (anchors_root / "reward_panel.svg").write_text("<svg />", encoding="utf-8")
            manifest = {
                "repository_id": "daily_ui",
                "display_name": "Daily UI Templates",
                "version": "0.1.0",
                "anchors": [
                    {
                        "anchor_id": "daily_ui.reward_panel",
                        "label": "Reward Panel",
                        "template_path": "anchors/reward_panel.svg",
                        "confidence_threshold": 0.93,
                        "match_region": [1, 2, 3, 4],
                        "metadata": {
                            "task_id": "daily_ui.claim_rewards",
                            "inspection_role": "reward_panel",
                            "placeholder": True,
                        },
                    }
                ],
            }
            (repository_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            report = validate_template_repository(AnchorRepository.load(repository_root))

        issue_codes = {issue.code for issue in report.issues}
        self.assertFalse(report.is_valid)
        self.assertIn("missing_anchor_curation_metadata", issue_codes)

    def test_validate_template_repository_rejects_curated_claim_rewards_svg_without_references(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "daily_ui"
            anchors_root = repository_root / "anchors"
            anchors_root.mkdir(parents=True)
            (anchors_root / "reward_panel.svg").write_text("<svg />", encoding="utf-8")
            manifest = {
                "repository_id": "daily_ui",
                "display_name": "Daily UI Templates",
                "version": "0.1.0",
                "anchors": [
                    {
                        "anchor_id": "daily_ui.reward_panel",
                        "label": "Reward Panel",
                        "template_path": "anchors/reward_panel.svg",
                        "confidence_threshold": 0.93,
                        "match_region": [1, 2, 3, 4],
                        "metadata": {
                            "task_id": "daily_ui.claim_rewards",
                            "inspection_role": "reward_panel",
                            "placeholder": False,
                            "curation": {
                                "status": "curated",
                                "intent_id": "claim_rewards_reward_panel",
                                "scene_id": "reward_panel_open",
                                "variant_id": "tw_baseline",
                                "provenance": {
                                    "kind": "curated_stand_in",
                                    "source": "repo_curated_baseline",
                                    "locale": "zh-TW"
                                },
                                "references": [],
                            },
                        },
                    }
                ],
            }
            (repository_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            report = validate_template_repository(AnchorRepository.load(repository_root))

        issue_codes = {issue.code for issue in report.issues}
        self.assertFalse(report.is_valid)
        self.assertIn("curated_anchor_missing_references", issue_codes)
        self.assertIn("curated_anchor_requires_raster_template", issue_codes)

    def test_validate_template_repository_requires_claim_rewards_curation_provenance(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "daily_ui"
            anchors_root = repository_root / "anchors"
            anchors_root.mkdir(parents=True)
            (anchors_root / "reward_panel.png").write_text("placeholder", encoding="utf-8")
            (repository_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "repository_id": "daily_ui",
                        "display_name": "Daily UI Templates",
                        "version": "0.1.0",
                        "anchors": [
                            {
                                "anchor_id": "daily_ui.reward_panel",
                                "label": "Reward Panel",
                                "template_path": "anchors/reward_panel.png",
                                "confidence_threshold": 0.93,
                                "match_region": [1, 2, 3, 4],
                                "metadata": {
                                    "task_id": "daily_ui.claim_rewards",
                                    "inspection_role": "reward_panel",
                                    "placeholder": False,
                                    "curation": {
                                        "status": "curated",
                                        "intent_id": "claim_rewards_reward_panel",
                                        "scene_id": "reward_panel_open",
                                        "variant_id": "tw_baseline",
                                        "references": [
                                            {
                                                "reference_id": "reward_panel_baseline_v1",
                                                "image_path": "goldens/reward_panel.png",
                                                "kind": "golden_screenshot",
                                            }
                                        ],
                                    },
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = validate_template_repository(AnchorRepository.load(repository_root))

        issue_codes = {issue.code for issue in report.issues}
        self.assertFalse(report.is_valid)
        self.assertIn("missing_anchor_curation_provenance", issue_codes)

    def test_validate_template_workspace_reports_missing_and_invalid_manifests(self) -> None:
        with TemporaryDirectory() as temp_dir:
            templates_root = Path(temp_dir)
            valid_root = templates_root / "valid_pack"
            valid_anchors = valid_root / "anchors"
            valid_anchors.mkdir(parents=True)
            (valid_anchors / "valid_button.svg").write_text("<svg />", encoding="utf-8")
            (valid_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "repository_id": "valid_pack",
                        "display_name": "Valid Pack",
                        "version": "0.1.0",
                        "anchors": [
                            {
                                "anchor_id": "valid_pack.valid_button",
                                "label": "Valid Button",
                                "template_path": "anchors/valid_button.svg",
                                "confidence_threshold": 0.9,
                                "match_region": [0, 0, 10, 10],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            (templates_root / "missing_manifest").mkdir()
            invalid_root = templates_root / "invalid_manifest"
            invalid_root.mkdir()
            (invalid_root / "manifest.json").write_text("{ invalid json", encoding="utf-8")

            workspace_report = validate_template_workspace(templates_root)

        self.assertEqual(workspace_report.repository_count, 3)
        self.assertEqual(workspace_report.valid_repository_ids, ["valid_pack"])
        self.assertEqual(set(workspace_report.invalid_repository_ids), {"invalid_manifest", "missing_manifest"})

        restored = TemplateWorkspaceValidationReport.from_dict(workspace_report.to_dict())
        self.assertEqual(restored.valid_repository_ids, workspace_report.valid_repository_ids)

        report_by_id = {
            report.repository_id or Path(report.repository_root).name: report
            for report in workspace_report.reports
        }
        self.assertEqual(report_by_id["missing_manifest"].issues[0].code, "missing_manifest")
        self.assertEqual(report_by_id["invalid_manifest"].issues[0].code, "invalid_manifest_json")

    def test_validate_template_workspace_handles_missing_root(self) -> None:
        missing_root = self.templates_root / "__missing_validation_root__"

        report = validate_template_workspace(missing_root)

        self.assertEqual(report.repository_count, 0)
        self.assertEqual(report.error_count, 0)
        self.assertFalse(report.metadata["templates_root_exists"])
        self.assertFalse(report.metadata["templates_root_is_dir"])

    def test_build_vision_workspace_readiness_report_tracks_inventory_alignment(self) -> None:
        report = build_vision_workspace_readiness_report(
            self.templates_root,
            self.asset_inventory_path,
        )

        dependency_by_anchor = {
            dependency.anchor_id: dependency for dependency in report.template_dependencies
        }
        guild_dependency = dependency_by_anchor["daily_ui.guild_check_in_button"]
        claim_dependency = dependency_by_anchor["daily_ui.claim_reward"]

        self.assertEqual(report.template_dependency_count, 9)
        self.assertEqual(report.ready_count, 7)
        self.assertEqual(report.placeholder_count, 2)
        self.assertEqual(report.missing_count, 0)
        self.assertEqual(report.inventory_mismatch_count, 0)
        self.assertEqual(guild_dependency.readiness_status, TemplateReadinessStatus.PLACEHOLDER)
        self.assertTrue(guild_dependency.anchor_present)
        self.assertTrue(guild_dependency.asset_exists)
        self.assertFalse(guild_dependency.inventory_mismatch)
        self.assertEqual(claim_dependency.readiness_status, TemplateReadinessStatus.READY)
        self.assertFalse(claim_dependency.inventory_mismatch)
        self.assertEqual(claim_dependency.curation_status.value, "curated")
        self.assertEqual(claim_dependency.provenance_kind, AnchorAssetProvenanceKind.LIVE_CAPTURE)
        self.assertEqual(claim_dependency.curation_reference_count, 1)
        self.assertTrue(claim_dependency.golden_catalog_path.endswith("goldens\\claim_rewards\\catalog.json"))
        self.assertEqual(claim_dependency.selected_golden_id, "reward_panel_claimable_baseline_v1")
        self.assertTrue(
            claim_dependency.selected_golden_image_path.endswith(
                "daily_ui_claim_rewards__claim_button__baseline__v1.png"
            )
        )
        self.assertEqual(claim_dependency.selected_reference_id, "claim_button_baseline_v1")
        self.assertEqual(claim_dependency.selected_reference_kind, "live_capture")
        self.assertEqual(
            claim_dependency.reference_ids,
            ["claim_button_baseline_v1"],
        )
        self.assertEqual(claim_dependency.live_reference_count, 1)
        self.assertEqual(
            claim_dependency.live_reference_ids,
            ["claim_button_baseline_v1"],
        )
        self.assertEqual(claim_dependency.supporting_capture_count, 1)
        self.assertEqual(
            claim_dependency.supporting_capture_ids,
            [
                "non_claimable_daily_signin_live_capture_emulator_5556_after_daily_tab_attempt_2",
            ],
        )
        self.assertEqual(
            claim_dependency.supporting_capture_evidence_roles,
            ["negative_case"],
        )
        self.assertEqual(claim_dependency.live_supporting_capture_count, 1)
        self.assertEqual(
            claim_dependency.live_supporting_capture_ids,
            [
                "non_claimable_daily_signin_live_capture_emulator_5556_after_daily_tab_attempt_2",
            ],
        )
        self.assertEqual(claim_dependency.failure_case, "claim_button_missing_or_not_tappable")
        self.assertTrue(
            claim_dependency.live_reference_image_paths[0].endswith(
                "daily_ui_claim_rewards__claim_button__baseline__v1.png"
            )
        )
        self.assertEqual(
            [Path(path).name for path in claim_dependency.supporting_capture_image_paths],
            [
                "daily_ui_claim_rewards__non_claimable_daily_signin__live_capture__emulator_5556__after_daily_tab_attempt_2.png",
            ],
        )
        self.assertIn("locale=zh-TW", claim_dependency.provenance_summary)
        self.assertIn("scene=reward_panel_claimable", claim_dependency.curation_summary)
        self.assertIn("live_refs=1", claim_dependency.curation_summary)
        self.assertEqual(
            report.metadata["claim_rewards_live_capture_coverage"]["stand_in_anchor_ids"],
            ["daily_ui.reward_confirm_state"],
        )
        self.assertEqual(
            report.metadata["claim_rewards_live_capture_coverage"]["live_context_anchor_ids"],
            [],
        )
        self.assertEqual(
            report.metadata["claim_rewards_capture_inventory"]["landed_device_serials"],
            ["emulator-5556", "emulator-5560", "127.0.0.1:5559", "127.0.0.1:5563"],
        )
        self.assertEqual(
            report.metadata["claim_rewards_capture_inventory"]["missing_device_serials"],
            [],
        )
        self.assertEqual(
            report.metadata["claim_rewards_post_tap_contract"]["dispatch_recommendation"],
            "direct_result_overlay_is_valid",
        )
        self.assertEqual(
            report.metadata["claim_rewards_post_tap_contract"]["observed_live_outcome_capture_ids"],
            [
                "post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22",
                "post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap",
                "post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap",
                "post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap",
            ],
        )
        self.assertEqual(
            report.metadata["guild_order_scene_contract"]["evidence_state"],
            "placeholder_only",
        )
        self.assertEqual(
            report.metadata["guild_order_scene_contract"]["decision_surface_state"],
            "blocked_by_missing_material_evidence",
        )
        self.assertEqual(
            report.metadata["guild_order_scene_contract"]["blocked_scene_ids"],
            [
                "guild_order_requirement_material",
                "guild_order_required_quantity",
                "guild_order_available_material_count",
            ],
        )
        self.assertEqual(
            report.metadata["guild_order_scene_contract"]["placeholder_anchor_ids"],
            [
                "daily_ui.guild_order_hub_entry",
                "daily_ui.guild_order_list_panel",
                "daily_ui.guild_order_detail_panel",
                "daily_ui.guild_order_submit_button",
                "daily_ui.guild_order_refresh_button",
                "daily_ui.guild_order_unavailable_state",
                "daily_ui.guild_order_insufficient_material_feedback",
                "daily_ui.guild_order_submit_result_state",
            ],
        )

        restored = VisionWorkspaceReadinessReport.from_dict(report.to_dict())
        self.assertEqual(restored.inventory_mismatch_count, report.inventory_mismatch_count)

    def test_build_vision_workspace_readiness_report_distinguishes_live_claim_rewards_dependency(self) -> None:
        with TemporaryDirectory() as temp_dir:
            inventory_path = Path(temp_dir) / "asset_inventory.json"
            inventory_path.write_text(
                json.dumps(
                    {
                        "inventory_id": "test_inventory",
                        "version": "0.1.0",
                        "records": [
                            {
                                "asset_id": "daily_ui.claim_rewards:template:daily_ui.reward_panel",
                                "pack_id": "daily_ui",
                                "task_id": "daily_ui.claim_rewards",
                                "asset_kind": "template",
                                "status": "ready",
                                "source_path": "assets/templates/daily_ui/manifest.json#daily_ui.reward_panel",
                                "metadata": {
                                    "anchor_id": "daily_ui.reward_panel",
                                    "source": "test_inventory",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            report = build_vision_workspace_readiness_report(self.templates_root, inventory_path)

        dependency = next(
            dependency
            for dependency in report.template_dependencies
            if dependency.anchor_id == "daily_ui.reward_panel"
        )
        self.assertEqual(report.template_dependency_count, 1)
        self.assertEqual(report.ready_count, 1)
        self.assertEqual(report.inventory_mismatch_count, 0)
        self.assertEqual(dependency.readiness_status, TemplateReadinessStatus.READY)
        self.assertFalse(dependency.inventory_mismatch)
        self.assertEqual(dependency.curation_status.value, "curated")
        self.assertEqual(dependency.provenance_kind, AnchorAssetProvenanceKind.LIVE_CAPTURE)
        self.assertEqual(dependency.failure_case, "reward_panel_not_open_or_wrong_surface")
        self.assertIn("live_capture", dependency.provenance_summary)
        self.assertIn("scene=reward_panel_open", dependency.curation_summary)
