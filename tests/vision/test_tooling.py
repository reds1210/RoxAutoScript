from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.core.models import VisionMatch
from roxauto.vision import (
    AnchorAssetProvenanceKind,
    AnchorRepository,
    CalibrationProfile,
    CaptureArtifactKind,
    InspectionOverlayKind,
    MatchStatus,
    RecordingAction,
    RecordingActionType,
    ReplayScript,
    TemplateReadinessStatus,
    build_anchor_inspector,
    build_capture_inspector,
    build_failure_inspection,
    build_failure_inspector,
    build_match_result,
    build_template_workspace_catalog,
    build_vision_tooling_state,
    create_capture_artifact,
    create_capture_session,
    validate_template_repository,
)


class VisionToolingTests(unittest.TestCase):
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

    def test_build_template_workspace_catalog_prefers_selected_valid_repository(self) -> None:
        workspace = build_template_workspace_catalog(
            self.templates_root,
            selected_repository_id="daily_ui",
            asset_inventory_path=self.asset_inventory_path,
        )

        self.assertEqual(workspace.selected_repository_id, "daily_ui")
        self.assertEqual(workspace.selected_repository.version, "0.1.0")
        self.assertEqual(len(workspace.repositories), 3)
        self.assertTrue(all(entry.is_valid for entry in workspace.repositories))
        self.assertEqual(workspace.repository_count, 3)
        self.assertEqual(workspace.readiness.inventory_mismatch_count, 0)
        claim_dependency = next(
            dependency
            for dependency in workspace.readiness.template_dependencies
            if dependency.anchor_id == "daily_ui.claim_reward"
        )
        self.assertEqual(claim_dependency.readiness_status, TemplateReadinessStatus.READY)
        self.assertEqual(claim_dependency.curation_status.value, "curated")
        self.assertEqual(claim_dependency.provenance_kind, AnchorAssetProvenanceKind.LIVE_CAPTURE)
        self.assertTrue(claim_dependency.golden_catalog_path.endswith("goldens\\claim_rewards\\catalog.json"))
        self.assertEqual(claim_dependency.selected_golden_id, "reward_panel_claimable_baseline_v1")
        self.assertEqual(claim_dependency.selected_reference_id, "claim_button_baseline_v1")
        self.assertEqual(claim_dependency.selected_reference_kind, "live_capture")
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
        self.assertEqual(claim_dependency.failure_case, "claim_button_missing_or_not_tappable")
        self.assertTrue(
            claim_dependency.live_reference_image_paths[0].endswith(
                "daily_ui_claim_rewards__claim_button__baseline__v1.png"
            )
        )
        self.assertIn("locale=zh-TW", claim_dependency.provenance_summary)
        self.assertIn("intent=claim_rewards_claim_button", claim_dependency.curation_summary)
        self.assertIn("live_refs=1", claim_dependency.curation_summary)
        self.assertEqual(
            workspace.readiness.metadata["claim_rewards_capture_inventory"]["landed_device_serials"],
            ["emulator-5556", "emulator-5560", "127.0.0.1:5559", "127.0.0.1:5563"],
        )
        self.assertEqual(
            workspace.readiness.metadata["claim_rewards_post_tap_contract"]["dispatch_recommendation"],
            "direct_result_overlay_is_valid",
        )
        self.assertEqual(
            workspace.readiness.metadata["guild_order_scene_contract"]["evidence_state"],
            "partial_reviewed_live_evidence",
        )
        self.assertEqual(
            workspace.readiness.metadata["guild_order_scene_contract"]["decision_surface_state"],
            "submit_refresh_decision_surfaces_captured_failure_states_pending",
        )
        self.assertEqual(
            workspace.readiness.metadata["guild_order_scene_contract"]["blocked_scene_ids"],
            [],
        )

    def test_build_anchor_inspector_applies_calibration_override_and_validation_issues(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "broken_pack"
            repository_root.mkdir()
            (repository_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "repository_id": "broken_pack",
                        "display_name": "Broken Pack",
                        "version": "0.1.0",
                        "anchors": [
                            {
                                "anchor_id": "broken_pack.close_button",
                                "label": "Close",
                                "template_path": "anchors/missing.svg",
                                "confidence_threshold": 0.82,
                                "match_region": [0, 0, 10, 10],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            repository = AnchorRepository.load(repository_root)
            validation = validate_template_repository(repository)
            profile = CalibrationProfile(
                profile_id="profile-1",
                anchor_overrides={
                    "broken_pack.close_button": {
                        "confidence_threshold": 0.96,
                        "match_region": [5, 6, 7, 8],
                    }
                },
            )

            inspector = build_anchor_inspector(
                repository,
                validation_report=validation,
                calibration_profile=profile,
            )

        self.assertEqual(inspector.selected_anchor_id, "broken_pack.close_button")
        self.assertEqual(inspector.selected_anchor.effective_confidence_threshold, 0.96)
        self.assertEqual(inspector.selected_anchor.effective_match_region, (5, 6, 7, 8))
        self.assertIn("missing_template_asset", inspector.selected_anchor.issue_codes)
        self.assertFalse(inspector.selected_anchor.asset_exists)
        self.assertIn("threshold=0.96", inspector.selected_anchor_summary)
        self.assertEqual(inspector.selected_anchor.calibration_resolution.profile_id, "profile-1")
        self.assertEqual(inspector.selected_overlay.kind, InspectionOverlayKind.EXPECTED_ANCHOR)
        self.assertEqual(inspector.selected_overlay.region.to_tuple(), (5, 6, 7, 8))

    def test_capture_and_failure_inspectors_expose_selected_items(self) -> None:
        session = create_capture_session(
            session_id="capture-1",
            instance_id="mumu-1",
            source_image="captures/source.png",
            selected_anchor_id="common.close_button",
            crop_region=(10, 20, 30, 40),
        )
        session.append_artifact(
            create_capture_artifact(
                artifact_id="artifact-1",
                image_path="captures/source.png",
                source_image=session.source_image,
                kind=CaptureArtifactKind.SCREENSHOT,
            )
        )
        session.append_artifact(
            create_capture_artifact(
                artifact_id="artifact-2",
                image_path="captures/crop.png",
                source_image=session.source_image,
                kind=CaptureArtifactKind.CROP,
                crop_region=(10, 20, 30, 40),
            )
        )

        capture = build_capture_inspector(session, selected_artifact_id="artifact-2")
        repository = AnchorRepository.load(self.templates_root / "common")
        anchor = repository.get_anchor("common.close_button")
        match_result = build_match_result(
            source_image="captures/failure.png",
            candidates=[
                VisionMatch(
                    anchor_id=anchor.anchor_id,
                    confidence=0.91,
                    bbox=(10, 20, 30, 40),
                    source_image="captures/failure.png",
                )
            ],
            expected_anchor=anchor,
            message="Matched close button",
        )
        failure_record = build_failure_inspection(
            failure_id="failure-1",
            instance_id="mumu-1",
            screenshot_path="captures/failure.png",
            preview_image_path="captures/failure-preview.png",
            match_result=match_result,
        )

        failure = build_failure_inspector(failure_record, repository=repository)

        self.assertEqual(capture.selected_artifact_id, "artifact-2")
        self.assertEqual(capture.selected_artifact.kind, CaptureArtifactKind.CROP)
        self.assertEqual(capture.selected_artifact.crop_region.to_tuple(), (10, 20, 30, 40))
        self.assertEqual(capture.artifact_kind_counts["screenshot"], 1)
        self.assertEqual(capture.artifact_kind_counts["crop"], 1)
        self.assertIn("crop", capture.selected_artifact_summary)
        self.assertEqual(capture.source_inspection.selected_overlay.kind, InspectionOverlayKind.CROP_REGION)
        self.assertEqual(capture.selected_artifact_inspection.selected_overlay.kind, InspectionOverlayKind.CROP_REGION)
        self.assertEqual(failure.status, MatchStatus.MATCHED)
        self.assertEqual(failure.selected_anchor.anchor_id, "common.close_button")
        self.assertEqual(failure.best_candidate.anchor_id, "common.close_button")
        self.assertEqual(failure.candidate_count, 1)
        self.assertIn("confidence=0.910", failure.best_candidate_summary)
        self.assertEqual(failure.calibration_resolution.anchor_id, "common.close_button")
        self.assertEqual(failure.inspection.selected_overlay.kind, InspectionOverlayKind.MATCHED_ANCHOR)
        self.assertEqual(failure.selected_region.to_tuple(), (10, 20, 30, 40))
        self.assertEqual(failure.selected_region_summary, "10,20,30,40")

    def test_build_vision_tooling_state_stitches_workspace_capture_replay_and_failure(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "common")
        anchor = repository.get_anchor("common.close_button")
        profile = CalibrationProfile(
            profile_id="profile.common",
            instance_id="mumu-0",
            crop_region=(1, 2, 3, 4),
            anchor_overrides={"common.close_button": {"confidence_threshold": 0.95}},
        )
        session = create_capture_session(
            session_id="capture-1",
            instance_id="mumu-0",
            source_image="preview://sample",
            selected_anchor_id="common.close_button",
            crop_region=(1, 2, 3, 4),
        )
        session.append_artifact(
            create_capture_artifact(
                artifact_id="artifact-1",
                image_path="captures/source.png",
                source_image="preview://sample",
                kind=CaptureArtifactKind.SCREENSHOT,
            )
        )
        script = ReplayScript(
            script_id="script-1",
            name="Replay Script",
            actions=[
                RecordingAction(
                    action_id="action-1",
                    action_type=RecordingActionType.CAPTURE,
                    target="preview",
                    payload={"note": "capture"},
                    occurred_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
                ),
                RecordingAction(
                    action_id="action-2",
                    action_type=RecordingActionType.ANNOTATE,
                    target="common.close_button",
                    payload={"note": "select"},
                    occurred_at=datetime(2026, 4, 21, 10, 1, tzinfo=timezone.utc),
                ),
            ],
        )
        match_result = build_match_result(
            source_image="preview://sample",
            candidates=[
                VisionMatch(
                    anchor_id=anchor.anchor_id,
                    confidence=0.96,
                    bbox=(10, 20, 30, 40),
                    source_image="preview://sample",
                )
            ],
            expected_anchor=anchor,
            message="Matched close button",
        )
        failure_record = build_failure_inspection(
            failure_id="failure-1",
            instance_id="mumu-0",
            screenshot_path="captures/failure.png",
            match_result=match_result,
            message="matched",
        )

        tooling = build_vision_tooling_state(
            templates_root=self.templates_root,
            repository=repository,
            calibration_profile=profile,
            capture_session=session,
            replay_script=script,
            match_result=match_result,
            failure_record=failure_record,
            asset_inventory_path=self.asset_inventory_path,
            selected_repository_id="common",
            selected_action_id="action-2",
            source_image="preview://sample",
        )

        self.assertEqual(tooling.workspace.selected_repository_id, "common")
        self.assertEqual(tooling.readiness.inventory_mismatch_count, 0)
        self.assertEqual(tooling.anchors.selected_anchor.anchor_id, "common.close_button")
        self.assertIn("threshold=0.95", tooling.anchors.selected_anchor_summary)
        self.assertEqual(tooling.calibration.selected_anchor.effective_confidence_threshold, 0.95)
        self.assertEqual(tooling.calibration.scale_summary, "1.00 x 1.00")
        self.assertEqual(tooling.calibration.crop_summary, "1,2,3,4")
        self.assertEqual(tooling.calibration.selected_resolution.effective_confidence_threshold, 0.95)
        self.assertEqual(tooling.capture.selected_artifact.artifact_id, "artifact-1")
        self.assertTrue(tooling.capture.selected_artifact.is_selected)
        self.assertEqual(tooling.capture.source_inspection.selected_overlay.kind, InspectionOverlayKind.CROP_REGION)
        self.assertEqual(tooling.replay.selected_action_id, "action-2")
        self.assertEqual(tooling.match.matched_candidate.anchor_id, "common.close_button")
        self.assertEqual(tooling.match.candidate_count, 1)
        self.assertIn("confidence=0.960", tooling.match.matched_candidate_summary)
        self.assertEqual(tooling.match.calibration_resolution.effective_confidence_threshold, 0.95)
        self.assertEqual(tooling.match.inspection.selected_overlay.kind, InspectionOverlayKind.MATCHED_ANCHOR)
        self.assertEqual(tooling.match.selected_image_path, "preview://sample")
        self.assertEqual(tooling.match.selected_source_image, "preview://sample")
        self.assertEqual(tooling.match.selected_overlay.kind, InspectionOverlayKind.MATCHED_ANCHOR)
        self.assertEqual(tooling.match.selected_region.to_tuple(), (10, 20, 30, 40))
        self.assertEqual(tooling.match.selected_region_summary, "10,20,30,40")
        self.assertIn("Matched close button", tooling.match.failure_explanation)
        self.assertEqual(tooling.match.curation_summary, "")
        self.assertEqual(tooling.preview.selected_overlay.kind, InspectionOverlayKind.MATCHED_ANCHOR)
        self.assertEqual(tooling.failure.best_candidate.anchor_id, "common.close_button")
        self.assertEqual(tooling.failure.inspection.selected_overlay.kind, InspectionOverlayKind.MATCHED_ANCHOR)
        self.assertEqual(tooling.to_dict()["workspace"]["selected_repository_id"], "common")

    def test_build_failure_inspector_exposes_claim_rewards_checks(self) -> None:
        repository = AnchorRepository.load(self.templates_root / "daily_ui")
        failure_record = build_failure_inspection(
            failure_id="failure-claim-rewards",
            instance_id="mumu-0",
            screenshot_path="captures/reward-failure.png",
            preview_image_path="captures/reward-preview.png",
            metadata={
                "task_id": "daily_ui.claim_rewards",
                "claim_rewards": {
                    "current_check_id": "confirm_state",
                    "checks": {
                        "reward_panel": {
                            "source_image": "captures/reward-preview.png",
                            "message": "Reward panel frame matched.",
                            "candidates": [
                                {
                                    "anchor_id": "daily_ui.reward_panel",
                                    "confidence": 0.97,
                                    "bbox": [420, 120, 1080, 840],
                                    "source_image": "captures/reward-preview.png",
                                }
                            ],
                        },
                        "claim_reward_button": {
                            "source_image": "captures/reward-preview.png",
                            "message": "Claim button fell below threshold.",
                            "candidates": [
                                {
                                    "anchor_id": "daily_ui.claim_reward",
                                    "confidence": 0.88,
                                    "bbox": [760, 760, 360, 140],
                                    "source_image": "captures/reward-preview.png",
                                }
                            ],
                        },
                        "confirm_state": {
                            "source_image": "captures/reward-preview.png",
                            "message": "Confirm modal was not stable enough.",
                            "candidates": [
                                {
                                    "anchor_id": "daily_ui.reward_confirm_state",
                                    "confidence": 0.89,
                                    "bbox": [560, 260, 760, 420],
                                    "source_image": "captures/reward-preview.png",
                                }
                            ],
                        },
                    },
                },
            },
        )

        failure = build_failure_inspector(failure_record, repository=repository)

        self.assertEqual(failure.anchor_id, "daily_ui.reward_confirm_state")
        self.assertEqual(failure.status, MatchStatus.MISSED)
        self.assertIsNotNone(failure.claim_rewards)
        self.assertEqual(failure.claim_rewards.current_check_id, "confirm_state")
        self.assertEqual(failure.claim_rewards.check_count, 3)
        self.assertEqual(failure.claim_rewards.matched_check_count, 1)
        self.assertEqual(failure.claim_rewards.selected_anchor_id, "daily_ui.reward_confirm_state")
        self.assertEqual(failure.claim_rewards.selected_stage, "verify_claim_affordance")
        self.assertEqual(failure.claim_rewards.selected_threshold, 0.92)
        self.assertEqual(failure.claim_rewards.selected_image_path, "captures/reward-preview.png")
        self.assertEqual(failure.claim_rewards.selected_source_image, "captures/reward-preview.png")
        self.assertEqual(failure.claim_rewards.selected_anchor_label, "Reward Confirm State")
        self.assertTrue(failure.claim_rewards.golden_catalog_path.endswith("goldens\\claim_rewards\\catalog.json"))
        self.assertEqual(failure.claim_rewards.selected_golden_id, "reward_confirm_modal_baseline_v1")
        self.assertTrue(
            failure.claim_rewards.selected_golden_image_path.endswith(
                "daily_ui_claim_rewards__confirm_state__baseline__v1.png"
            )
        )
        self.assertTrue(failure.claim_rewards.selected_template_path.endswith("daily_reward_confirm_state.png"))
        self.assertEqual(failure.claim_rewards.selected_reference_id, "confirm_state_baseline_v1")
        self.assertEqual(failure.claim_rewards.selected_reference_kind, "curated_stand_in")
        self.assertTrue(
            failure.claim_rewards.selected_reference_image_path.endswith(
                "daily_ui_claim_rewards__confirm_state__baseline__v1.png"
            )
        )
        self.assertEqual(failure.claim_rewards.live_reference_count, 0)
        self.assertEqual(failure.claim_rewards.selected_check.anchor_id, "daily_ui.reward_confirm_state")
        self.assertTrue(failure.claim_rewards.selected_check.is_selected)
        self.assertEqual(failure.claim_rewards.selected_check.selected_image_path, "captures/reward-preview.png")
        self.assertEqual(failure.claim_rewards.selected_check.threshold, 0.92)
        self.assertIn("below threshold 0.920", failure.claim_rewards.selected_check.failure_explanation)
        self.assertEqual(failure.claim_rewards.selected_check.anchor_label, "Reward Confirm State")
        self.assertEqual(failure.claim_rewards.selected_check.selected_region.to_tuple(), (520, 220, 880, 520))
        self.assertEqual(failure.claim_rewards.selected_check.selected_region_summary, "520,220,880,520")
        self.assertTrue(failure.claim_rewards.selected_check.selected_template_path.endswith("daily_reward_confirm_state.png"))
        self.assertEqual(
            failure.claim_rewards.selected_check.selected_golden_id,
            "reward_confirm_modal_baseline_v1",
        )
        self.assertEqual(failure.claim_rewards.selected_check.selected_reference_id, "confirm_state_baseline_v1")
        self.assertEqual(failure.claim_rewards.selected_check.selected_reference_kind, "curated_stand_in")
        self.assertTrue(
            failure.claim_rewards.selected_check.selected_reference_image_path.endswith(
                "daily_ui_claim_rewards__confirm_state__baseline__v1.png"
            )
        )
        self.assertEqual(failure.claim_rewards.selected_check.live_reference_count, 0)
        self.assertEqual(failure.claim_rewards.selected_check.supporting_capture_count, 5)
        self.assertEqual(
            failure.claim_rewards.selected_check.supporting_capture_ids,
            [
                "non_reward_confirm_modal_live_capture_emulator_5560_exit_game_prompt",
                "post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22",
                "post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap",
                "post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap",
                "post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap",
            ],
        )
        self.assertEqual(
            failure.claim_rewards.selected_check.supporting_capture_evidence_roles,
            [
                "negative_case",
                "alternate_post_tap_outcome",
                "alternate_post_tap_outcome",
                "alternate_post_tap_outcome",
                "alternate_post_tap_outcome",
            ],
        )
        self.assertEqual(failure.claim_rewards.selected_check.curation_status.value, "curated")
        self.assertEqual(
            failure.claim_rewards.selected_check.provenance_kind,
            AnchorAssetProvenanceKind.CURATED_STAND_IN,
        )
        self.assertIn("locale=zh-TW", failure.claim_rewards.selected_check.provenance_summary)
        self.assertIn("scene=reward_confirm_modal", failure.claim_rewards.selected_check.curation_summary)
        self.assertEqual(
            failure.claim_rewards.selected_check.failure_case,
            "confirm_modal_missing_after_claim_tap",
        )
        self.assertEqual(
            failure.claim_rewards.selected_provenance_kind,
            AnchorAssetProvenanceKind.CURATED_STAND_IN,
        )
        self.assertIn("locale=zh-TW", failure.claim_rewards.selected_provenance_summary)
        self.assertEqual(
            failure.claim_rewards.selected_failure_case,
            "confirm_modal_missing_after_claim_tap",
        )
        self.assertEqual(failure.claim_rewards.selected_region.to_tuple(), (520, 220, 880, 520))
        self.assertEqual(failure.claim_rewards.selected_region_summary, "520,220,880,520")
        self.assertIn("threshold=0.920", failure.claim_rewards.selected_check_summary)
        self.assertIn("image=captures/reward-preview.png", failure.claim_rewards.selected_check_summary)
        self.assertIn("region=520,220,880,520", failure.claim_rewards.selected_check_summary)
        self.assertIn("golden_id=reward_confirm_modal_baseline_v1", failure.claim_rewards.selected_check_summary)
        self.assertIn("failure_case=confirm_modal_missing_after_claim_tap", failure.claim_rewards.selected_check_summary)
        self.assertIn("provenance=curated_stand_in", failure.claim_rewards.selected_check_summary)
        self.assertIn("below threshold 0.920", failure.claim_rewards.failure_explanation)
        self.assertIn("Reward Confirm State (daily_ui.reward_confirm_state)", failure.claim_rewards.failure_explanation)
        self.assertIn("template=", failure.claim_rewards.failure_explanation)
        self.assertIn("reference=", failure.claim_rewards.failure_explanation)
        self.assertEqual(
            failure.claim_rewards.post_tap_contract_recommendation,
            "direct_result_overlay_is_valid",
        )
        self.assertEqual(
            failure.claim_rewards.post_tap_contract_observed_scene_ids,
            ["reward_post_tap_overlay", "reward_claimed_result_state"],
        )
        self.assertEqual(
            failure.claim_rewards.post_tap_contract_observed_capture_ids,
            [
                "post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22",
                "post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap",
                "post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap",
                "post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap",
            ],
        )
        self.assertIn("recommendation=direct_result_overlay_is_valid", failure.claim_rewards.post_tap_contract_summary)
        reward_panel_check = next(
            check for check in failure.claim_rewards.checks if check.check_id == "reward_panel"
        )
        self.assertEqual(reward_panel_check.anchor_id, "daily_ui.reward_panel")
        self.assertEqual(reward_panel_check.provenance_kind, AnchorAssetProvenanceKind.LIVE_CAPTURE)
        self.assertIn("locale=zh-TW", reward_panel_check.provenance_summary)
        self.assertEqual(reward_panel_check.selected_region.to_tuple(), (420, 120, 1080, 840))
        self.assertEqual(reward_panel_check.selected_region_summary, "420,120,1080,840")
        self.assertTrue(reward_panel_check.selected_template_path.endswith("daily_reward_panel.png"))
        self.assertTrue(
            reward_panel_check.selected_reference_image_path.endswith(
                "daily_ui_claim_rewards__reward_panel__baseline__v1.png"
            )
        )
        self.assertEqual(reward_panel_check.selected_golden_id, "reward_panel_open_baseline_v1")
        self.assertEqual(reward_panel_check.selected_reference_id, "reward_panel_baseline_v1")
        self.assertEqual(reward_panel_check.selected_reference_kind, "live_capture")
        self.assertEqual(reward_panel_check.live_reference_count, 3)
        self.assertEqual(
            reward_panel_check.live_reference_ids,
            [
                "reward_panel_baseline_v1",
                "reward_panel_live_5560_daily_signin_v1",
                "reward_panel_entry_context_live_v1",
            ],
        )
        self.assertEqual(reward_panel_check.supporting_capture_count, 3)
        self.assertEqual(
            reward_panel_check.supporting_capture_evidence_roles,
            ["descriptive_copy", "scene_context_only", "negative_case"],
        )
        self.assertEqual(
            reward_panel_check.failure_case,
            "reward_panel_not_open_or_wrong_surface",
        )
        self.assertNotIn("curated stand-in", reward_panel_check.failure_explanation.lower())
        claim_button_check = next(
            check for check in failure.claim_rewards.checks if check.check_id == "claim_reward_button"
        )
        self.assertEqual(claim_button_check.anchor_id, "daily_ui.claim_reward")
        self.assertEqual(claim_button_check.selected_reference_id, "claim_button_baseline_v1")
        self.assertEqual(claim_button_check.selected_reference_kind, "live_capture")
        self.assertEqual(
            claim_button_check.reference_ids,
            ["claim_button_baseline_v1"],
        )
        self.assertEqual(claim_button_check.live_reference_count, 1)
        self.assertEqual(
            claim_button_check.live_reference_ids,
            ["claim_button_baseline_v1"],
        )
        self.assertEqual(claim_button_check.selected_golden_id, "reward_panel_claimable_baseline_v1")
        self.assertEqual(claim_button_check.supporting_capture_count, 1)
        self.assertEqual(
            claim_button_check.supporting_capture_ids,
            [
                "non_claimable_daily_signin_live_capture_emulator_5556_after_daily_tab_attempt_2",
            ],
        )
        self.assertEqual(
            claim_button_check.supporting_capture_evidence_roles,
            ["negative_case"],
        )
        self.assertTrue(
            claim_button_check.live_reference_image_paths[0].endswith(
                "daily_ui_claim_rewards__claim_button__baseline__v1.png"
            )
        )
        self.assertEqual(failure.best_candidate.anchor_id, "daily_ui.reward_confirm_state")
        self.assertEqual(failure.candidate_count, 1)
        self.assertEqual(failure.focus_check_id, "confirm_state")
        self.assertEqual(failure.focus_check_label, "Reward Confirm State")
        self.assertEqual(failure.focus_stage, "verify_claim_affordance")
        self.assertEqual(failure.selected_threshold, 0.92)
        self.assertEqual(failure.selected_image_path, "captures/reward-preview.png")
        self.assertEqual(failure.selected_source_image, "captures/reward-preview.png")
        self.assertEqual(failure.selected_overlay.kind, InspectionOverlayKind.EXPECTED_ANCHOR)
        self.assertIn("expected:daily_ui.reward_confirm_state", failure.selected_overlay_summary)
        self.assertEqual(failure.selected_region.to_tuple(), (520, 220, 880, 520))
        self.assertEqual(failure.selected_region_summary, "520,220,880,520")
        self.assertEqual(failure.selected_anchor_label, "Reward Confirm State")
        self.assertTrue(failure.golden_catalog_path.endswith("goldens\\claim_rewards\\catalog.json"))
        self.assertEqual(failure.selected_golden_id, "reward_confirm_modal_baseline_v1")
        self.assertTrue(failure.selected_template_path.endswith("daily_reward_confirm_state.png"))
        self.assertEqual(failure.selected_reference_id, "confirm_state_baseline_v1")
        self.assertEqual(failure.selected_reference_kind, "curated_stand_in")
        self.assertTrue(
            failure.selected_reference_image_path.endswith(
                "daily_ui_claim_rewards__confirm_state__baseline__v1.png"
            )
        )
        self.assertEqual(failure.live_reference_count, 0)
        self.assertEqual(failure.supporting_capture_count, 5)
        self.assertEqual(
            failure.supporting_capture_ids,
            [
                "non_reward_confirm_modal_live_capture_emulator_5560_exit_game_prompt",
                "post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22",
                "post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap",
                "post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap",
                "post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap",
            ],
        )
        self.assertEqual(failure.curation_status.value, "curated")
        self.assertEqual(failure.provenance_kind, AnchorAssetProvenanceKind.CURATED_STAND_IN)
        self.assertIn("locale=zh-TW", failure.provenance_summary)
        self.assertIn("scene=reward_confirm_modal", failure.curation_summary)
        self.assertEqual(failure.failure_case, "confirm_modal_missing_after_claim_tap")
        self.assertIn("below threshold 0.920", failure.failure_explanation)
        self.assertIn("curated stand-in", failure.failure_explanation)
        self.assertIn("template=", failure.failure_explanation)
        self.assertIn("reference=", failure.failure_explanation)
        self.assertEqual(failure.post_tap_contract_recommendation, "direct_result_overlay_is_valid")
        self.assertEqual(
            failure.post_tap_contract_observed_capture_ids,
            [
                "post_tap_reward_overlay_live_capture_emulator_5556_after_day7_claim_tap_2026_04_22",
                "post_tap_claimed_result_live_capture_127_0_0_1_5559_after_claim_tap",
                "post_tap_claimed_result_live_capture_127_0_0_1_5563_after_claim_tap",
                "post_tap_claimed_result_live_capture_emulator_5560_after_claim_tap",
            ],
        )
        self.assertIn("recommendation=direct_result_overlay_is_valid", failure.post_tap_contract_summary)
        self.assertEqual(failure.inspection.selected_overlay.kind, InspectionOverlayKind.EXPECTED_ANCHOR)
        self.assertEqual(failure.inspection.selected_overlay.metadata["anchor_id"], "daily_ui.reward_confirm_state")
