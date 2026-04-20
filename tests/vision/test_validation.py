from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tests._bootstrap  # noqa: F401
from roxauto.vision import (
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

    def test_build_vision_workspace_readiness_report_tracks_inventory_mismatch(self) -> None:
        report = build_vision_workspace_readiness_report(
            self.templates_root,
            self.asset_inventory_path,
        )

        dependency_by_anchor = {
            dependency.anchor_id: dependency for dependency in report.template_dependencies
        }
        guild_dependency = dependency_by_anchor["daily_ui.guild_check_in_button"]

        self.assertEqual(report.template_dependency_count, 3)
        self.assertEqual(report.placeholder_count, 3)
        self.assertEqual(report.missing_count, 0)
        self.assertEqual(report.inventory_mismatch_count, 1)
        self.assertEqual(guild_dependency.readiness_status, TemplateReadinessStatus.PLACEHOLDER)
        self.assertTrue(guild_dependency.anchor_present)
        self.assertTrue(guild_dependency.asset_exists)
        self.assertTrue(guild_dependency.inventory_mismatch)

        restored = VisionWorkspaceReadinessReport.from_dict(report.to_dict())
        self.assertEqual(restored.inventory_mismatch_count, report.inventory_mismatch_count)
