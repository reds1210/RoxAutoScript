from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

from roxauto.core.serde import to_primitive
from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import (
    TaskBlueprint,
    TaskFixtureProfile,
    TaskReadinessReport,
    TaskRuntimeBuilderInput,
)


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


def _select_fixture_profile_path(builder_input: TaskRuntimeBuilderInput) -> str:
    if not builder_input.fixture_profile_paths:
        raise ValueError(
            "Merchant commission meow specification requires at least one fixture profile path"
        )
    return builder_input.fixture_profile_paths[0]
