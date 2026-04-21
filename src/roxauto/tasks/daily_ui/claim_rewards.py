from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Protocol

from roxauto.core.models import (
    FailureSnapshotReason,
    InstanceState,
    StepStatus,
    StopConditionKind,
    TaskManifest,
    TaskRun,
    TaskRunStatus,
    TaskSpec,
    TaskStepResult,
    VisionMatch,
)
from roxauto.core.runtime import TaskExecutionContext, TaskStep, step_failure, step_success
from roxauto.emulator.execution import EmulatorActionAdapter
from roxauto.tasks.catalog import TaskFoundationRepository
from roxauto.tasks.models import (
    TaskBlueprint,
    TaskFixtureProfile,
    TaskReadinessReport,
    TaskReadinessState,
    TaskRuntimeBuilderInput,
    TaskStepBlueprint,
)
from roxauto.vision import AnchorRepository, AnchorSpec, TemplateMatchResult, build_match_result

_REWARD_PANEL_ANCHOR_ID = "daily_ui.reward_panel"
_CLAIM_REWARD_ANCHOR_ID = "daily_ui.claim_reward"
_REWARD_CONFIRM_STATE_ANCHOR_ID = "daily_ui.reward_confirm_state"
_CLOSE_BUTTON_ANCHOR_ID = "common.close_button"
_CONFIRM_BUTTON_ANCHOR_ID = "common.confirm_button"
_INSPECTION_CONTEXT_KEY = "daily_ui.claim_rewards.inspection"
_INSPECTION_HISTORY_KEY = "daily_ui.claim_rewards.inspection_history"
_ACTION_DISPATCH_SUCCESS_STATUSES = frozenset({"completed", "partial", "executed", "routed"})
_STEP_INSPECTION_RETRY_LIMIT = 2


class ClaimRewardsPanelState(str, Enum):
    CLAIMABLE = "claimable"
    CLAIMED = "claimed"
    CONFIRM_REQUIRED = "confirm_required"
    UNAVAILABLE = "unavailable"


_VISIBLE_PANEL_STATES = (
    ClaimRewardsPanelState.CLAIMABLE,
    ClaimRewardsPanelState.CLAIMED,
    ClaimRewardsPanelState.CONFIRM_REQUIRED,
)
_POST_CLAIM_STATES = (
    ClaimRewardsPanelState.CLAIMED,
    ClaimRewardsPanelState.CONFIRM_REQUIRED,
)


@dataclass(slots=True)
class ClaimRewardsNavigationPlan:
    open_panel_point: tuple[int, int]

    def to_dict(self) -> dict[str, Any]:
        return {"open_panel_point": self.open_panel_point}


@dataclass(slots=True)
class ClaimRewardsInspection:
    state: ClaimRewardsPanelState
    screenshot_path: str
    message: str = ""
    match_results: dict[str, TemplateMatchResult] = field(default_factory=dict)
    signals: dict[str, bool] = field(default_factory=dict)
    claim_point: tuple[int, int] | None = None
    confirm_point: tuple[int, int] | None = None
    close_point: tuple[int, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "screenshot_path": self.screenshot_path,
            "message": self.message,
            "signals": {str(key): bool(value) for key, value in self.signals.items()},
            "claim_point": self.claim_point,
            "confirm_point": self.confirm_point,
            "close_point": self.close_point,
            "matched_anchor_ids": [
                anchor_id
                for anchor_id, result in self.match_results.items()
                if result.is_match()
            ],
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ClaimRewardsFailureReason:
    reason_id: str
    title: str
    summary: str
    retryable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason_id": self.reason_id,
            "title": self.title,
            "summary": self.summary,
            "retryable": self.retryable,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimRewardsFailureReason":
        return cls(
            reason_id=str(data.get("reason_id", "")),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            retryable=bool(data.get("retryable", True)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class ClaimRewardsDisplayMetadata:
    locale: str = "zh-TW"
    display_name: str = ""
    short_name: str = ""
    description: str = ""
    category_label: str = ""
    preset_id: str = ""
    preset_description: str = ""
    status_texts: dict[str, str] = field(default_factory=dict)
    failure_reasons: list[ClaimRewardsFailureReason] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "locale": self.locale,
            "display_name": self.display_name,
            "short_name": self.short_name,
            "description": self.description,
            "category_label": self.category_label,
            "preset_id": self.preset_id,
            "preset_description": self.preset_description,
            "status_texts": dict(self.status_texts),
            "failure_reasons": [item.to_dict() for item in self.failure_reasons],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimRewardsDisplayMetadata":
        return cls(
            locale=str(data.get("locale", "zh-TW")),
            display_name=str(data.get("display_name", "")),
            short_name=str(data.get("short_name", "")),
            description=str(data.get("description", "")),
            category_label=str(data.get("category_label", "")),
            preset_id=str(data.get("preset_id", "")),
            preset_description=str(data.get("preset_description", "")),
            status_texts={str(key): str(value) for key, value in dict(data.get("status_texts", {})).items()},
            failure_reasons=[
                ClaimRewardsFailureReason.from_dict(item)
                for item in data.get("failure_reasons", [])
            ],
            metadata=dict(data.get("metadata", {})),
        )

    def failure_reason_map(self) -> dict[str, ClaimRewardsFailureReason]:
        return {reason.reason_id: reason for reason in self.failure_reasons}


@dataclass(slots=True)
class ClaimRewardsTaskPreset:
    preset_id: str
    task_id: str
    pack_id: str
    display_name: str
    description: str
    category_label: str
    readiness_state: str
    status_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "task_id": self.task_id,
            "pack_id": self.pack_id,
            "display_name": self.display_name,
            "description": self.description,
            "category_label": self.category_label,
            "readiness_state": self.readiness_state,
            "status_text": self.status_text,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ClaimRewardsStepTelemetry:
    step_id: str
    display_name: str
    status: str
    status_text: str
    summary: str
    message: str = ""
    screenshot_path: str | None = None
    failure_reason: ClaimRewardsFailureReason | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "display_name": self.display_name,
            "status": self.status,
            "status_text": self.status_text,
            "summary": self.summary,
            "message": self.message,
            "screenshot_path": self.screenshot_path,
            "failure_reason": self.failure_reason.to_dict() if self.failure_reason is not None else None,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ClaimRewardsDisplayModel:
    task_id: str
    pack_id: str
    locale: str
    display_name: str
    description: str
    status: str
    status_text: str
    status_summary: str
    preset: ClaimRewardsTaskPreset
    steps: list[ClaimRewardsStepTelemetry] = field(default_factory=list)
    failure_reason: ClaimRewardsFailureReason | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "pack_id": self.pack_id,
            "locale": self.locale,
            "display_name": self.display_name,
            "description": self.description,
            "status": self.status,
            "status_text": self.status_text,
            "status_summary": self.status_summary,
            "preset": self.preset.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "failure_reason": self.failure_reason.to_dict() if self.failure_reason is not None else None,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ClaimRewardsRuntimeStepSpec:
    step_id: str
    action: str
    description: str
    display_name: str
    success_condition: str
    failure_condition: str = ""
    notes: str = ""
    summary: str = ""
    anchor_id: str = ""
    status_texts: dict[str, str] = field(default_factory=dict)
    failure_reason_id: str = ""
    expected_panel_states: tuple[ClaimRewardsPanelState, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "description": self.description,
            "display_name": self.display_name,
            "success_condition": self.success_condition,
            "failure_condition": self.failure_condition,
            "notes": self.notes,
            "summary": self.summary,
            "anchor_id": self.anchor_id,
            "status_texts": dict(self.status_texts),
            "failure_reason_id": self.failure_reason_id,
            "expected_panel_states": [state.value for state in self.expected_panel_states],
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ClaimRewardsRuntimeInput:
    task_id: str
    pack_id: str
    manifest_path: str
    manifest: TaskManifest
    builder_input: TaskRuntimeBuilderInput
    readiness_report: TaskReadinessReport
    blueprint: TaskBlueprint
    fixture_profile_path: str
    fixture_profile: TaskFixtureProfile
    display_metadata: ClaimRewardsDisplayMetadata
    required_anchor_ids: list[str] = field(default_factory=list)
    anchor_specs: dict[str, AnchorSpec] = field(default_factory=dict)
    step_specs: list[ClaimRewardsRuntimeStepSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "pack_id": self.pack_id,
            "manifest_path": self.manifest_path,
            "fixture_profile_path": self.fixture_profile_path,
            "fixture_id": self.fixture_profile.fixture_id,
            "display_metadata": self.display_metadata.to_dict(),
            "required_anchor_ids": list(self.required_anchor_ids),
            "step_specs": [step.to_dict() for step in self.step_specs],
            "builder_input": self.builder_input.to_dict(),
            "implementation_readiness_state": self.readiness_report.implementation_readiness_state.value,
            "warning_requirement_ids": [
                requirement.requirement_id
                for requirement in self.readiness_report.warning_requirements
            ],
            "metadata": dict(self.metadata),
        }


class ClaimRewardsTemplateMatcher(Protocol):
    def match(
        self,
        image_path: Path,
        anchor: AnchorSpec,
        *,
        instance: InstanceState,
        metadata: dict[str, Any] | None = None,
    ) -> Iterable[VisionMatch]:
        """Return candidate matches for one anchor against one screenshot."""


class ClaimRewardsVisionGateway(Protocol):
    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        anchor_specs: dict[str, AnchorSpec],
        metadata: dict[str, Any] | None = None,
    ) -> ClaimRewardsInspection:
        """Classify one reward-panel screenshot."""


class TemplateMatcherClaimRewardsVisionGateway:
    def __init__(self, matcher: ClaimRewardsTemplateMatcher) -> None:
        self._matcher = matcher

    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        anchor_specs: dict[str, AnchorSpec],
        metadata: dict[str, Any] | None = None,
    ) -> ClaimRewardsInspection:
        match_results = {
            anchor_id: self._match_anchor(
                screenshot_path=screenshot_path,
                anchor=anchor_specs[anchor_id],
                instance=instance,
                metadata=metadata,
            )
            for anchor_id in (
                _REWARD_PANEL_ANCHOR_ID,
                _CLAIM_REWARD_ANCHOR_ID,
                _REWARD_CONFIRM_STATE_ANCHOR_ID,
                _CONFIRM_BUTTON_ANCHOR_ID,
                _CLOSE_BUTTON_ANCHOR_ID,
            )
        }
        signals = _inspection_signals(match_results)
        state = _classify_panel_state(match_results)
        return ClaimRewardsInspection(
            state=state,
            screenshot_path=str(screenshot_path),
            message=_inspection_message(state),
            match_results=match_results,
            signals=signals,
            claim_point=_matched_point(match_results[_CLAIM_REWARD_ANCHOR_ID]),
            confirm_point=_matched_point(match_results[_CONFIRM_BUTTON_ANCHOR_ID]),
            close_point=_matched_point(match_results[_CLOSE_BUTTON_ANCHOR_ID]),
            metadata={"source": "template_matcher_gateway", **dict(metadata or {})},
        )

    def _match_anchor(
        self,
        *,
        screenshot_path: Path,
        anchor: AnchorSpec,
        instance: InstanceState,
        metadata: dict[str, Any] | None,
    ) -> TemplateMatchResult:
        return build_match_result(
            source_image=str(screenshot_path),
            candidates=self._matcher.match(
                screenshot_path,
                anchor,
                instance=instance,
                metadata=metadata,
            ),
            expected_anchor=anchor,
        )


class _ClaimRewardsTaskBridge:
    def __init__(
        self,
        *,
        adapter: EmulatorActionAdapter,
        vision_gateway: ClaimRewardsVisionGateway,
        navigation_plan: ClaimRewardsNavigationPlan,
        anchor_specs: dict[str, AnchorSpec],
    ) -> None:
        self._adapter = adapter
        self._vision_gateway = vision_gateway
        self._navigation_plan = navigation_plan
        self._anchor_specs = dict(anchor_specs)

    def open_reward_panel(self, context: TaskExecutionContext):
        precheck, precheck_attempts = self._inspect_until(
            context,
            step_id="open_reward_panel",
            reason="open_reward_panel.precheck",
            accepted_states=_VISIBLE_PANEL_STATES,
            max_attempts=1,
        )
        if precheck.state in _VISIBLE_PANEL_STATES:
            return step_success(
                "open_reward_panel",
                f"Reward panel was already open in {precheck.state.value} state.",
                screenshot_path=precheck.screenshot_path,
                data=self._step_data(
                    precheck,
                    step_id="open_reward_panel",
                    outcome_code=f"open_panel_already_{precheck.state.value}",
                    expected_panel_states=_VISIBLE_PANEL_STATES,
                    inspection_attempts=precheck_attempts,
                    open_panel_point=self._navigation_plan.open_panel_point,
                ),
            )

        task_action = self._tap(
            context,
            step_id="open_reward_panel",
            point=self._navigation_plan.open_panel_point,
            reason="open_reward_panel",
        )
        if self._dispatch_failed(task_action):
            return step_failure(
                "open_reward_panel",
                self._dispatch_failure_message(
                    action_name="reward panel navigation tap",
                    task_action=task_action,
                ),
                data={
                    **self._step_data(
                        precheck,
                        step_id="open_reward_panel",
                        outcome_code="open_panel_dispatch_failed",
                        failure_reason_id="runtime_dispatch_failed",
                        expected_panel_states=_VISIBLE_PANEL_STATES,
                        inspection_attempts=precheck_attempts,
                        task_action=task_action,
                        open_panel_point=self._navigation_plan.open_panel_point,
                    ),
                },
            )
        inspection, inspection_attempts = self._inspect_until(
            context,
            step_id="open_reward_panel",
            reason="open_reward_panel",
            accepted_states=_VISIBLE_PANEL_STATES,
            max_attempts=_STEP_INSPECTION_RETRY_LIMIT,
        )
        if inspection.state is ClaimRewardsPanelState.UNAVAILABLE:
            return step_failure(
                "open_reward_panel",
                "Reward panel could not be confirmed after deterministic navigation.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="open_reward_panel",
                    outcome_code="open_panel_unverified",
                    failure_reason_id="reward_panel_unavailable",
                    expected_panel_states=_VISIBLE_PANEL_STATES,
                    inspection_attempts=inspection_attempts,
                    task_action=task_action,
                    open_panel_point=self._navigation_plan.open_panel_point,
                    pre_action_inspection=precheck.to_dict(),
                ),
            )
        return step_success(
            "open_reward_panel",
            f"Reward panel detected in {inspection.state.value} state.",
            screenshot_path=inspection.screenshot_path,
            data=self._step_data(
                inspection,
                step_id="open_reward_panel",
                outcome_code=f"open_panel_verified_{inspection.state.value}",
                expected_panel_states=_VISIBLE_PANEL_STATES,
                inspection_attempts=inspection_attempts,
                task_action=task_action,
                open_panel_point=self._navigation_plan.open_panel_point,
                pre_action_inspection=precheck.to_dict(),
            ),
        )

    def verify_claim_affordance(self, context: TaskExecutionContext):
        inspection, inspection_attempts = self._inspect_until(
            context,
            step_id="verify_claim_affordance",
            reason="verify_claim_affordance",
            accepted_states=_VISIBLE_PANEL_STATES,
            initial_inspection=self._current_inspection(context),
            max_attempts=_STEP_INSPECTION_RETRY_LIMIT,
        )
        if (
            inspection.state is ClaimRewardsPanelState.CONFIRM_REQUIRED
            and not self._supports_confirmation_recovery(inspection)
        ):
            return step_failure(
                "verify_claim_affordance",
                "Claim button state remains ambiguous.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="verify_claim_affordance",
                    outcome_code="claim_state_ambiguous",
                    failure_reason_id="claim_state_ambiguous",
                    expected_panel_states=_VISIBLE_PANEL_STATES,
                    inspection_attempts=inspection_attempts,
                ),
            )
        if inspection.state in _VISIBLE_PANEL_STATES:
            message = (
                "Reward panel is already waiting for claim confirmation."
                if inspection.state is ClaimRewardsPanelState.CONFIRM_REQUIRED
                else f"Reward panel classified as {inspection.state.value}."
            )
            return step_success(
                "verify_claim_affordance",
                message,
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="verify_claim_affordance",
                    outcome_code=f"claim_state_{inspection.state.value}",
                    expected_panel_states=_VISIBLE_PANEL_STATES,
                    inspection_attempts=inspection_attempts,
                ),
            )
        return step_failure(
            "verify_claim_affordance",
            "Claim button state remains ambiguous.",
            screenshot_path=inspection.screenshot_path,
            data=self._step_data(
                inspection,
                step_id="verify_claim_affordance",
                outcome_code="claim_state_ambiguous",
                failure_reason_id="claim_state_ambiguous",
                expected_panel_states=_VISIBLE_PANEL_STATES,
                inspection_attempts=inspection_attempts,
            ),
        )

    def claim_reward(self, context: TaskExecutionContext):
        inspection, inspection_attempts = self._inspect_until(
            context,
            step_id="claim_reward",
            reason="claim_reward.precheck",
            accepted_states=_VISIBLE_PANEL_STATES,
            initial_inspection=self._current_inspection(context),
            max_attempts=_STEP_INSPECTION_RETRY_LIMIT,
        )
        if inspection.state is ClaimRewardsPanelState.CLAIMED:
            return step_success(
                "claim_reward",
                "Reward is already claimed; tap is not required.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="claim_reward",
                    outcome_code="claim_already_claimed",
                    expected_panel_states=_POST_CLAIM_STATES,
                    inspection_attempts=inspection_attempts,
                ),
            )
        if inspection.state is ClaimRewardsPanelState.CONFIRM_REQUIRED:
            if not self._supports_confirmation_recovery(inspection):
                return step_failure(
                    "claim_reward",
                    "Reward panel does not expose a tappable claim affordance.",
                    screenshot_path=inspection.screenshot_path,
                    data=self._step_data(
                        inspection,
                        step_id="claim_reward",
                        outcome_code="claim_affordance_missing",
                        failure_reason_id="claim_affordance_missing",
                        expected_panel_states=_POST_CLAIM_STATES,
                        inspection_attempts=inspection_attempts,
                    ),
                )
            return step_success(
                "claim_reward",
                "Claim action already advanced to the confirmation modal; tap is not required.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="claim_reward",
                    outcome_code="claim_already_confirm_required",
                    expected_panel_states=_POST_CLAIM_STATES,
                    inspection_attempts=inspection_attempts,
                ),
            )
        if inspection.state is not ClaimRewardsPanelState.CLAIMABLE or inspection.claim_point is None:
            return step_failure(
                "claim_reward",
                "Reward panel does not expose a tappable claim affordance.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="claim_reward",
                    outcome_code="claim_affordance_missing",
                    failure_reason_id="claim_affordance_missing",
                    expected_panel_states=_POST_CLAIM_STATES,
                    inspection_attempts=inspection_attempts,
                ),
            )

        task_action = self._tap(
            context,
            step_id="claim_reward",
            point=inspection.claim_point,
            reason="claim_reward.tap",
        )
        if self._dispatch_failed(task_action):
            return step_failure(
                "claim_reward",
                self._dispatch_failure_message(
                    action_name="claim tap",
                    task_action=task_action,
                ),
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="claim_reward",
                    outcome_code="claim_dispatch_failed",
                    failure_reason_id="runtime_dispatch_failed",
                    expected_panel_states=_POST_CLAIM_STATES,
                    inspection_attempts=inspection_attempts,
                    task_action=task_action,
                ),
            )
        follow_up, follow_up_attempts = self._inspect_until(
            context,
            step_id="claim_reward",
            reason="claim_reward.post_tap",
            accepted_states=_POST_CLAIM_STATES,
            max_attempts=_STEP_INSPECTION_RETRY_LIMIT,
        )
        if follow_up.state in _POST_CLAIM_STATES:
            return step_success(
                "claim_reward",
                f"Claim tap advanced panel to {follow_up.state.value}.",
                screenshot_path=follow_up.screenshot_path,
                data=self._step_data(
                    follow_up,
                    step_id="claim_reward",
                    outcome_code=f"claim_tap_advanced_to_{follow_up.state.value}",
                    expected_panel_states=_POST_CLAIM_STATES,
                    inspection_attempts=follow_up_attempts,
                    task_action=task_action,
                    pre_action_inspection=inspection.to_dict(),
                ),
            )
        return step_failure(
            "claim_reward",
            "Claim tap did not advance the reward panel.",
            screenshot_path=follow_up.screenshot_path,
            data=self._step_data(
                follow_up,
                step_id="claim_reward",
                outcome_code="claim_tap_no_effect",
                failure_reason_id="claim_tap_no_effect",
                expected_panel_states=_POST_CLAIM_STATES,
                inspection_attempts=follow_up_attempts,
                task_action=task_action,
                pre_action_inspection=inspection.to_dict(),
            ),
        )

    def confirm_reward_claim(self, context: TaskExecutionContext):
        inspection, inspection_attempts = self._inspect_until(
            context,
            step_id="confirm_reward_claim",
            reason="confirm_reward_claim.precheck",
            accepted_states=_POST_CLAIM_STATES,
            initial_inspection=self._current_inspection(context),
            max_attempts=_STEP_INSPECTION_RETRY_LIMIT,
        )
        if inspection.state is ClaimRewardsPanelState.CLAIMED:
            return step_success(
                "confirm_reward_claim",
                "Confirmation modal is not required.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="confirm_reward_claim",
                    outcome_code="confirm_not_required",
                    expected_panel_states=(ClaimRewardsPanelState.CLAIMED,),
                    inspection_attempts=inspection_attempts,
                ),
            )
        if inspection.state is not ClaimRewardsPanelState.CONFIRM_REQUIRED or inspection.confirm_point is None:
            return step_failure(
                "confirm_reward_claim",
                "Claim confirmation modal could not be verified.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="confirm_reward_claim",
                    outcome_code="confirm_modal_unavailable",
                    failure_reason_id="confirm_modal_unavailable",
                    expected_panel_states=(ClaimRewardsPanelState.CLAIMED,),
                    inspection_attempts=inspection_attempts,
                ),
            )

        task_action = self._tap(
            context,
            step_id="confirm_reward_claim",
            point=inspection.confirm_point,
            reason="confirm_reward_claim.tap",
        )
        if self._dispatch_failed(task_action):
            return step_failure(
                "confirm_reward_claim",
                self._dispatch_failure_message(
                    action_name="claim confirmation tap",
                    task_action=task_action,
                ),
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="confirm_reward_claim",
                    outcome_code="confirm_dispatch_failed",
                    failure_reason_id="runtime_dispatch_failed",
                    expected_panel_states=(ClaimRewardsPanelState.CLAIMED,),
                    inspection_attempts=inspection_attempts,
                    task_action=task_action,
                ),
            )
        follow_up, follow_up_attempts = self._inspect_until(
            context,
            step_id="confirm_reward_claim",
            reason="confirm_reward_claim.post_tap",
            accepted_states=(ClaimRewardsPanelState.CLAIMED,),
            max_attempts=_STEP_INSPECTION_RETRY_LIMIT,
        )
        if follow_up.state is ClaimRewardsPanelState.CLAIMED:
            return step_success(
                "confirm_reward_claim",
                "Claim confirmation completed.",
                screenshot_path=follow_up.screenshot_path,
                data=self._step_data(
                    follow_up,
                    step_id="confirm_reward_claim",
                    outcome_code="confirm_completed",
                    expected_panel_states=(ClaimRewardsPanelState.CLAIMED,),
                    inspection_attempts=follow_up_attempts,
                    task_action=task_action,
                    pre_action_inspection=inspection.to_dict(),
                ),
            )
        return step_failure(
            "confirm_reward_claim",
            "Confirmation tap did not produce a claimed reward state.",
            screenshot_path=follow_up.screenshot_path,
            data=self._step_data(
                follow_up,
                step_id="confirm_reward_claim",
                outcome_code="confirm_tap_no_effect",
                failure_reason_id="confirm_tap_no_effect",
                expected_panel_states=(ClaimRewardsPanelState.CLAIMED,),
                inspection_attempts=follow_up_attempts,
                task_action=task_action,
                pre_action_inspection=inspection.to_dict(),
            ),
        )

    def verify_claimed(self, context: TaskExecutionContext):
        inspection, inspection_attempts = self._inspect_until(
            context,
            step_id="verify_claimed",
            reason="verify_claimed",
            accepted_states=(ClaimRewardsPanelState.CLAIMED,),
            max_attempts=_STEP_INSPECTION_RETRY_LIMIT,
        )
        if inspection.state is ClaimRewardsPanelState.CLAIMED:
            return step_success(
                "verify_claimed",
                "Claimed reward state verified.",
                screenshot_path=inspection.screenshot_path,
                data=self._step_data(
                    inspection,
                    step_id="verify_claimed",
                    outcome_code="claimed_verified",
                    expected_panel_states=(ClaimRewardsPanelState.CLAIMED,),
                    inspection_attempts=inspection_attempts,
                ),
            )
        return step_failure(
            "verify_claimed",
            "Claimed reward state could not be verified.",
            screenshot_path=inspection.screenshot_path,
            data=self._step_data(
                inspection,
                step_id="verify_claimed",
                outcome_code="claimed_unverified",
                failure_reason_id="claimed_state_unverified",
                expected_panel_states=(ClaimRewardsPanelState.CLAIMED,),
                inspection_attempts=inspection_attempts,
            ),
        )

    def _capture_inspection(
        self,
        context: TaskExecutionContext,
        *,
        reason: str,
        step_id: str,
    ) -> ClaimRewardsInspection:
        screenshot_path, capture = self._capture_screenshot(
            context,
            step_id=step_id,
            reason=reason,
        )
        inspection = self._vision_gateway.inspect(
            instance=context.instance,
            screenshot_path=screenshot_path,
            anchor_specs=self._anchor_specs,
            metadata={
                "reason": reason,
                "task_id": "daily_ui.claim_rewards",
                "step_id": step_id,
                "capture": capture,
            },
        )
        if not inspection.screenshot_path:
            inspection = replace(inspection, screenshot_path=str(screenshot_path))
        inspection_metadata = dict(inspection.metadata)
        inspection_metadata.setdefault("capture", capture)
        inspection_metadata.setdefault("signal_contract_version", "claim_rewards.v2")
        inspection = self._normalize_inspection(
            replace(inspection, metadata=inspection_metadata),
        )
        self._store_inspection(context, inspection, reason=reason)
        return inspection

    def _inspect_until(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        reason: str,
        accepted_states: tuple[ClaimRewardsPanelState, ...],
        initial_inspection: ClaimRewardsInspection | None = None,
        max_attempts: int = _STEP_INSPECTION_RETRY_LIMIT,
    ) -> tuple[ClaimRewardsInspection, list[ClaimRewardsInspection]]:
        attempts: list[ClaimRewardsInspection] = []
        if initial_inspection is not None:
            inspection = self._normalize_inspection(initial_inspection)
            attempts.append(inspection)
            if inspection.state in accepted_states:
                return inspection, attempts

        while len(attempts) < max_attempts:
            attempt_reason = reason if not attempts else f"{reason}.retry_{len(attempts)}"
            inspection = self._capture_inspection(
                context,
                reason=attempt_reason,
                step_id=step_id,
            )
            attempts.append(inspection)
            if inspection.state in accepted_states:
                return inspection, attempts

        if not attempts:
            raise RuntimeError(f"No inspection attempts were captured for {step_id}")
        return attempts[-1], attempts

    def _current_inspection(self, context: TaskExecutionContext) -> ClaimRewardsInspection | None:
        inspection = context.metadata.get(_INSPECTION_CONTEXT_KEY)
        if isinstance(inspection, ClaimRewardsInspection):
            return self._normalize_inspection(inspection)
        return None

    def _store_inspection(
        self,
        context: TaskExecutionContext,
        inspection: ClaimRewardsInspection,
        *,
        reason: str,
    ) -> None:
        context.metadata[_INSPECTION_CONTEXT_KEY] = inspection
        history = context.metadata.setdefault(_INSPECTION_HISTORY_KEY, [])
        if isinstance(history, list):
            history.append(
                {
                    "reason": reason,
                    **inspection.to_dict(),
                }
            )

    def _normalize_inspection(self, inspection: ClaimRewardsInspection) -> ClaimRewardsInspection:
        metadata = dict(inspection.metadata)
        metadata.setdefault("signal_contract_version", "claim_rewards.v2")
        return replace(
            inspection,
            signals=_normalize_inspection_signals(inspection),
            metadata=metadata,
        )

    def _capture_screenshot(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        reason: str,
    ) -> tuple[Path, dict[str, Any]]:
        bridge = self._runtime_action_bridge(context)
        if bridge is not None:
            preview_frame = bridge.capture_preview(
                step_id=step_id,
                metadata=self._bridge_metadata(reason),
            )
            if preview_frame is not None and preview_frame.image_path:
                return Path(preview_frame.image_path), {
                    "source": "task_action_bridge",
                    "preview_frame_id": preview_frame.frame_id,
                    "preview_source": preview_frame.source,
                    "image_path": preview_frame.image_path,
                }
        screenshot_path = self._adapter.capture_screenshot(context.instance)
        return screenshot_path, {
            "source": "adapter_capture",
            "image_path": str(screenshot_path),
        }

    def _tap(
        self,
        context: TaskExecutionContext,
        *,
        step_id: str,
        point: tuple[int, int],
        reason: str,
    ) -> dict[str, Any]:
        bridge = self._runtime_action_bridge(context)
        if bridge is None:
            self._adapter.tap(context.instance, point)
            return {
                "source": "adapter",
                "status": "adapter_direct",
                "message": "",
                "point": point,
            }
        result = bridge.tap(
            point,
            step_id=step_id,
            metadata=self._bridge_metadata(reason),
        )
        return {
            "source": "task_action_bridge",
            "status": result.status,
            "message": result.message,
            "command_id": result.command_id,
            "command_type": result.command_type.value,
            "point": point,
            "payload": dict(result.payload),
            "metadata": dict(result.metadata),
        }

    def _runtime_action_bridge(self, context: TaskExecutionContext):
        try:
            return context.require_action_bridge()
        except RuntimeError:
            return None

    def _bridge_metadata(self, reason: str) -> dict[str, Any]:
        return {
            "reason": reason,
            "workflow": "claim_rewards",
        }

    def _dispatch_failed(self, task_action: dict[str, Any]) -> bool:
        if str(task_action.get("source", "")) != "task_action_bridge":
            return False
        return str(task_action.get("status", "")) not in _ACTION_DISPATCH_SUCCESS_STATUSES

    def _dispatch_failure_message(
        self,
        *,
        action_name: str,
        task_action: dict[str, Any],
    ) -> str:
        message = str(task_action.get("message", "")).strip()
        if message:
            return f"{action_name.capitalize()} could not be dispatched through the runtime bridge: {message}"
        return f"{action_name.capitalize()} could not be dispatched through the runtime bridge."

    def _step_data(
        self,
        inspection: ClaimRewardsInspection,
        *,
        step_id: str,
        outcome_code: str,
        failure_reason_id: str = "",
        expected_panel_states: tuple[ClaimRewardsPanelState, ...] = (),
        inspection_attempts: list[ClaimRewardsInspection] | None = None,
        task_action: dict[str, Any] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        data = inspection.to_dict()
        attempt_payloads = self._inspection_attempts_payload(inspection_attempts or [inspection])
        expected_states = [state.value for state in expected_panel_states]
        data["outcome_code"] = outcome_code
        data["failure_reason_id"] = failure_reason_id
        data["expected_panel_states"] = expected_states
        data["inspection_attempts"] = attempt_payloads
        data["step_outcome"] = {
            "step_id": step_id,
            "outcome_code": outcome_code,
            "failure_reason_id": failure_reason_id,
            "expected_panel_states": expected_states,
            "observed_panel_state": inspection.state.value,
            "attempt_count": len(attempt_payloads),
            "satisfied": not expected_states or inspection.state.value in expected_states,
        }
        data["telemetry"] = {
            "step_id": step_id,
            "outcome_code": outcome_code,
            "failure_reason_id": failure_reason_id,
            "inspection": {
                "panel_state": inspection.state.value,
                "signals": dict(inspection.signals),
                "matched_anchor_ids": list(data["matched_anchor_ids"]),
                "attempt_count": len(attempt_payloads),
                "attempts": attempt_payloads,
            },
        }
        if task_action is not None:
            data["task_action"] = dict(task_action)
            data["telemetry"]["task_action"] = dict(task_action)
        data.update(extra)
        return data

    def _inspection_attempts_payload(
        self,
        inspections: list[ClaimRewardsInspection],
    ) -> list[dict[str, Any]]:
        return [
            {
                "attempt": index + 1,
                **inspection.to_dict(),
            }
            for index, inspection in enumerate(inspections)
        ]

    def _supports_confirmation_recovery(self, inspection: ClaimRewardsInspection) -> bool:
        return str(inspection.metadata.get("workflow_mode", "")) != "ambiguous"


def load_claim_rewards_blueprint(
    repository: TaskFoundationRepository | None = None,
) -> TaskBlueprint:
    repo = repository or TaskFoundationRepository.load_default()
    return repo.load_blueprint(repo.root / "packs" / "daily_ui" / "daily_claim_rewards.task.json")


def load_claim_rewards_anchor_specs(
    templates_root: Path | str | None = None,
) -> dict[str, AnchorSpec]:
    root = (
        Path(templates_root)
        if templates_root is not None
        else Path(__file__).resolve().parents[4] / "assets" / "templates"
    )
    common_repository = AnchorRepository.load(root / "common")
    daily_ui_repository = AnchorRepository.load(root / "daily_ui")
    return {
        _REWARD_PANEL_ANCHOR_ID: daily_ui_repository.get_anchor(_REWARD_PANEL_ANCHOR_ID),
        _CLAIM_REWARD_ANCHOR_ID: daily_ui_repository.get_anchor(_CLAIM_REWARD_ANCHOR_ID),
        _REWARD_CONFIRM_STATE_ANCHOR_ID: daily_ui_repository.get_anchor(_REWARD_CONFIRM_STATE_ANCHOR_ID),
        _CONFIRM_BUTTON_ANCHOR_ID: common_repository.get_anchor(_CONFIRM_BUTTON_ANCHOR_ID),
        _CLOSE_BUTTON_ANCHOR_ID: common_repository.get_anchor(_CLOSE_BUTTON_ANCHOR_ID),
    }


def load_claim_rewards_display_metadata(
    repository: TaskFoundationRepository | None = None,
) -> ClaimRewardsDisplayMetadata:
    blueprint = load_claim_rewards_blueprint(repository)
    raw_display = dict(blueprint.metadata.get("product_display", {}))
    return ClaimRewardsDisplayMetadata.from_dict(raw_display)


def build_claim_rewards_runtime_input(
    *,
    builder_input: TaskRuntimeBuilderInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
    templates_root: Path | str | None = None,
) -> ClaimRewardsRuntimeInput:
    repo = foundation_repository or TaskFoundationRepository.load_default()
    resolved_builder_input = builder_input or repo.build_runtime_builder_input("daily_ui.claim_rewards")
    if resolved_builder_input.task_id != "daily_ui.claim_rewards":
        raise ValueError("build_claim_rewards_runtime_input only supports daily_ui.claim_rewards")

    resolved_readiness_report = readiness_report or repo.evaluate_task_readiness(resolved_builder_input.task_id)
    if resolved_readiness_report.task_id != resolved_builder_input.task_id:
        raise ValueError("Claim rewards readiness report does not match the runtime builder input task id")
    if resolved_readiness_report.implementation_readiness_state is not TaskReadinessState.READY:
        raise ValueError("Claim rewards runtime input requires implementation readiness to be ready")

    blueprint = load_claim_rewards_blueprint(repo)
    display_metadata = load_claim_rewards_display_metadata(repo)
    fixture_profile_path = _select_fixture_profile_path(resolved_builder_input)
    fixture_profile = repo.load_fixture_profile(repo.root / fixture_profile_path)
    discovered_anchor_specs = load_claim_rewards_anchor_specs(templates_root)
    anchor_specs = {
        anchor_id: discovered_anchor_specs[anchor_id]
        for anchor_id in resolved_builder_input.required_anchors
    }
    step_specs = _build_runtime_step_specs(blueprint.steps)

    return ClaimRewardsRuntimeInput(
        task_id=resolved_builder_input.task_id,
        pack_id=resolved_builder_input.pack_id,
        manifest_path=resolved_builder_input.manifest_path,
        manifest=_build_runtime_manifest(blueprint.manifest),
        builder_input=resolved_builder_input,
        readiness_report=resolved_readiness_report,
        blueprint=blueprint,
        fixture_profile_path=fixture_profile_path,
        fixture_profile=fixture_profile,
        display_metadata=display_metadata,
        required_anchor_ids=list(resolved_builder_input.required_anchors),
        anchor_specs=anchor_specs,
        step_specs=step_specs,
        metadata={
            "implementation_state": blueprint.implementation_state.value,
            "runtime_bridge": "roxauto.tasks.daily_ui.claim_rewards",
            "golden_screen_slugs": [case.screen_slug for case in blueprint.golden_cases],
            "display_name": display_metadata.display_name,
            "preset_id": display_metadata.preset_id,
        },
    )


def build_claim_rewards_task_preset(
    *,
    runtime_input: ClaimRewardsRuntimeInput | None = None,
    readiness_report: TaskReadinessReport | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
    templates_root: Path | str | None = None,
) -> ClaimRewardsTaskPreset:
    resolved_runtime_input = runtime_input or build_claim_rewards_runtime_input(
        foundation_repository=foundation_repository,
        templates_root=templates_root,
    )
    resolved_readiness = readiness_report or resolved_runtime_input.readiness_report
    display_metadata = resolved_runtime_input.display_metadata
    readiness_state = (
        "ready"
        if resolved_readiness.implementation_readiness_state is TaskReadinessState.READY
        else "blocked"
    )
    return ClaimRewardsTaskPreset(
        preset_id=display_metadata.preset_id,
        task_id=resolved_runtime_input.task_id,
        pack_id=resolved_runtime_input.pack_id,
        display_name=display_metadata.display_name,
        description=display_metadata.preset_description or display_metadata.description,
        category_label=display_metadata.category_label,
        readiness_state=readiness_state,
        status_text=display_metadata.status_texts.get(readiness_state, readiness_state),
        metadata={
            "locale": display_metadata.locale,
            "manifest_path": resolved_runtime_input.manifest_path,
        },
    )


def build_claim_rewards_step_telemetry(
    *,
    step_spec: ClaimRewardsRuntimeStepSpec,
    display_metadata: ClaimRewardsDisplayMetadata,
    step_result: TaskStepResult | None = None,
    running: bool = False,
    failure_reason: ClaimRewardsFailureReason | None = None,
) -> ClaimRewardsStepTelemetry:
    if step_result is not None:
        status = step_result.status.value
    elif running:
        status = "running"
    else:
        status = "pending"
    status_text = step_spec.status_texts.get(status, display_metadata.status_texts.get(status, status))
    summary = step_result.message if step_result is not None and step_result.message else step_spec.summary
    result_data = step_result.data if step_result is not None and isinstance(step_result.data, dict) else {}
    task_action = result_data.get("task_action", {})
    step_outcome = result_data.get("step_outcome", {})
    signals = result_data.get("signals", {})
    resolved_failure_reason_id = str(result_data.get("failure_reason_id", step_spec.failure_reason_id))
    return ClaimRewardsStepTelemetry(
        step_id=step_spec.step_id,
        display_name=step_spec.display_name,
        status=status,
        status_text=status_text,
        summary=summary,
        message=step_result.message if step_result is not None else "",
        screenshot_path=step_result.screenshot_path if step_result is not None else None,
        failure_reason=failure_reason,
        metadata={
            "action": step_spec.action,
            "failure_reason_id": resolved_failure_reason_id,
            "expected_panel_states": [state.value for state in step_spec.expected_panel_states],
            "outcome_code": str(result_data.get("outcome_code", "")),
            "signal_anchor_ids": list(step_spec.metadata.get("signal_anchor_ids", [])),
            "step_outcome": dict(step_outcome) if isinstance(step_outcome, dict) else {},
            "signals": dict(signals) if isinstance(signals, dict) else {},
            "task_action_status": str(task_action.get("status", "")) if isinstance(task_action, dict) else "",
        },
    )


def build_claim_rewards_task_display_model(
    *,
    run: TaskRun | None = None,
    runtime_input: ClaimRewardsRuntimeInput | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
    templates_root: Path | str | None = None,
) -> ClaimRewardsDisplayModel:
    resolved_runtime_input = runtime_input or build_claim_rewards_runtime_input(
        foundation_repository=foundation_repository,
        templates_root=templates_root,
    )
    display_metadata = resolved_runtime_input.display_metadata
    preset = build_claim_rewards_task_preset(runtime_input=resolved_runtime_input)
    failure_reason = _resolve_failure_reason(run, resolved_runtime_input) if run is not None else None
    status = _resolve_task_status(run, resolved_runtime_input.readiness_report)
    steps = _build_step_telemetry_items(run, resolved_runtime_input, failure_reason)
    return ClaimRewardsDisplayModel(
        task_id=resolved_runtime_input.task_id,
        pack_id=resolved_runtime_input.pack_id,
        locale=display_metadata.locale,
        display_name=display_metadata.display_name,
        description=display_metadata.description,
        status=status,
        status_text=display_metadata.status_texts.get(status, status),
        status_summary=_task_status_summary(status, display_metadata, failure_reason),
        preset=preset,
        steps=steps,
        failure_reason=failure_reason,
        metadata={
            "manifest_path": resolved_runtime_input.manifest_path,
            "fixture_id": resolved_runtime_input.fixture_profile.fixture_id,
            "readiness_state": resolved_runtime_input.readiness_report.implementation_readiness_state.value,
        },
    )


def build_claim_rewards_task_spec(
    *,
    adapter: EmulatorActionAdapter,
    navigation_plan: ClaimRewardsNavigationPlan,
    runtime_input: ClaimRewardsRuntimeInput | None = None,
    matcher: ClaimRewardsTemplateMatcher | None = None,
    vision_gateway: ClaimRewardsVisionGateway | None = None,
    foundation_repository: TaskFoundationRepository | None = None,
    templates_root: Path | str | None = None,
) -> TaskSpec:
    if matcher is None and vision_gateway is None:
        raise ValueError("build_claim_rewards_task_spec requires matcher or vision_gateway")

    resolved_runtime_input = runtime_input or build_claim_rewards_runtime_input(
        foundation_repository=foundation_repository,
        templates_root=templates_root,
    )
    gateway = vision_gateway or TemplateMatcherClaimRewardsVisionGateway(matcher)
    bridge = _ClaimRewardsTaskBridge(
        adapter=adapter,
        vision_gateway=gateway,
        navigation_plan=navigation_plan,
        anchor_specs=resolved_runtime_input.anchor_specs,
    )
    handlers = {
        "open_reward_panel": bridge.open_reward_panel,
        "verify_claim_affordance": bridge.verify_claim_affordance,
        "claim_reward": bridge.claim_reward,
        "confirm_reward_claim": bridge.confirm_reward_claim,
        "verify_claimed": bridge.verify_claimed,
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
            "navigation_plan": navigation_plan.to_dict(),
            "required_anchor_ids": list(resolved_runtime_input.required_anchor_ids),
            "runtime_bridge": "roxauto.tasks.daily_ui.claim_rewards",
            "builder_input": resolved_runtime_input.builder_input.to_dict(),
            "runtime_input": resolved_runtime_input.to_dict(),
            "product_display": resolved_runtime_input.display_metadata.to_dict(),
            "task_preset": build_claim_rewards_task_preset(runtime_input=resolved_runtime_input).to_dict(),
            "implementation_readiness_state": (
                resolved_runtime_input.readiness_report.implementation_readiness_state.value
            ),
        },
    )


def has_claim_rewards_runtime_bridge() -> bool:
    return True


def _build_runtime_manifest(manifest: TaskManifest) -> TaskManifest:
    metadata = dict(manifest.metadata)
    metadata["implementation_state"] = "fixtured"
    metadata["runtime_bridge"] = "roxauto.tasks.daily_ui.claim_rewards"
    return replace(manifest, metadata=metadata)


def _select_fixture_profile_path(builder_input: TaskRuntimeBuilderInput) -> str:
    if not builder_input.fixture_profile_paths:
        raise ValueError("Claim rewards runtime input requires at least one fixture profile path")
    return builder_input.fixture_profile_paths[0]


def _build_runtime_step_specs(
    steps: list[TaskStepBlueprint],
) -> list[ClaimRewardsRuntimeStepSpec]:
    descriptions = {
        "open_reward_panel": "開啟固定的每日獎勵面板。",
        "verify_claim_affordance": "確認目前畫面是可領取、已領取或需要確認。",
        "claim_reward": "在可領取狀態下點擊領獎按鈕。",
        "confirm_reward_claim": "當系統要求確認時完成確認點擊。",
        "verify_claimed": "驗證畫面已進入已領取狀態。",
    }
    display_names = {
        "open_reward_panel": "開啟每日獎勵",
        "verify_claim_affordance": "確認獎勵狀態",
        "claim_reward": "點擊領獎",
        "confirm_reward_claim": "確認領獎",
        "verify_claimed": "確認已領取",
    }
    anchor_ids = {
        "open_reward_panel": _REWARD_PANEL_ANCHOR_ID,
        "verify_claim_affordance": _REWARD_PANEL_ANCHOR_ID,
        "claim_reward": _CLAIM_REWARD_ANCHOR_ID,
        "confirm_reward_claim": _CONFIRM_BUTTON_ANCHOR_ID,
        "verify_claimed": _REWARD_PANEL_ANCHOR_ID,
    }
    signal_anchor_ids = {
        "open_reward_panel": [
            _REWARD_PANEL_ANCHOR_ID,
            _CLAIM_REWARD_ANCHOR_ID,
            _REWARD_CONFIRM_STATE_ANCHOR_ID,
            _CONFIRM_BUTTON_ANCHOR_ID,
            _CLOSE_BUTTON_ANCHOR_ID,
        ],
        "verify_claim_affordance": [
            _REWARD_PANEL_ANCHOR_ID,
            _CLAIM_REWARD_ANCHOR_ID,
            _REWARD_CONFIRM_STATE_ANCHOR_ID,
            _CONFIRM_BUTTON_ANCHOR_ID,
            _CLOSE_BUTTON_ANCHOR_ID,
        ],
        "claim_reward": [
            _REWARD_PANEL_ANCHOR_ID,
            _CLAIM_REWARD_ANCHOR_ID,
            _REWARD_CONFIRM_STATE_ANCHOR_ID,
        ],
        "confirm_reward_claim": [
            _REWARD_PANEL_ANCHOR_ID,
            _REWARD_CONFIRM_STATE_ANCHOR_ID,
            _CONFIRM_BUTTON_ANCHOR_ID,
        ],
        "verify_claimed": [
            _REWARD_PANEL_ANCHOR_ID,
            _CLAIM_REWARD_ANCHOR_ID,
            _REWARD_CONFIRM_STATE_ANCHOR_ID,
            _CLOSE_BUTTON_ANCHOR_ID,
        ],
    }
    expected_panel_states = {
        "open_reward_panel": (
            ClaimRewardsPanelState.CLAIMABLE,
            ClaimRewardsPanelState.CLAIMED,
            ClaimRewardsPanelState.CONFIRM_REQUIRED,
        ),
        "verify_claim_affordance": (
            ClaimRewardsPanelState.CLAIMABLE,
            ClaimRewardsPanelState.CLAIMED,
            ClaimRewardsPanelState.CONFIRM_REQUIRED,
        ),
        "claim_reward": (
            ClaimRewardsPanelState.CLAIMED,
            ClaimRewardsPanelState.CONFIRM_REQUIRED,
        ),
        "confirm_reward_claim": (
            ClaimRewardsPanelState.CLAIMED,
            ClaimRewardsPanelState.CONFIRM_REQUIRED,
        ),
        "verify_claimed": (ClaimRewardsPanelState.CLAIMED,),
    }
    return [
        ClaimRewardsRuntimeStepSpec(
            step_id=step.step_id,
            action=step.action,
            description=descriptions[step.step_id],
            display_name=str(step.metadata.get("display_name", display_names[step.step_id])),
            success_condition=step.success_condition,
            failure_condition=step.failure_condition,
            notes=step.notes,
            summary=str(step.metadata.get("summary", "")),
            anchor_id=anchor_ids.get(step.step_id, ""),
            status_texts={str(key): str(value) for key, value in dict(step.metadata.get("status_texts", {})).items()},
            failure_reason_id=str(step.metadata.get("failure_reason_id", "")),
            expected_panel_states=expected_panel_states.get(step.step_id, ()),
            metadata={
                **dict(step.metadata),
                "signal_anchor_ids": list(signal_anchor_ids.get(step.step_id, [])),
                "inspection_retry_limit": _STEP_INSPECTION_RETRY_LIMIT,
            },
        )
        for step in steps
    ]


def _inspection_message(state: ClaimRewardsPanelState) -> str:
    if state is ClaimRewardsPanelState.CONFIRM_REQUIRED:
        return "confirmation modal detected"
    if state is ClaimRewardsPanelState.CLAIMABLE:
        return "claim button detected"
    if state is ClaimRewardsPanelState.CLAIMED:
        return "claimed reward panel detected"
    return "reward panel could not be classified"


def _matched_point(result: TemplateMatchResult) -> tuple[int, int] | None:
    candidate = result.matched_candidate()
    if candidate is None:
        return None
    left, top, width, height = candidate.bbox
    return (left + width // 2, top + height // 2)


def _classify_panel_state(
    match_results: dict[str, TemplateMatchResult],
) -> ClaimRewardsPanelState:
    signals = _inspection_signals(match_results)
    # Confirmation modal takes precedence over the underlying panel because both layers can be visible together.
    if signals["confirm_state_visible"] or signals["confirm_button_visible"]:
        return ClaimRewardsPanelState.CONFIRM_REQUIRED
    if signals["reward_panel_visible"] and signals["claim_button_visible"]:
        return ClaimRewardsPanelState.CLAIMABLE
    if signals["reward_panel_visible"]:
        return ClaimRewardsPanelState.CLAIMED
    return ClaimRewardsPanelState.UNAVAILABLE


def _resolve_task_status(
    run: TaskRun | None,
    readiness_report: TaskReadinessReport,
) -> str:
    if run is None:
        return (
            "ready"
            if readiness_report.implementation_readiness_state is TaskReadinessState.READY
            else "blocked"
        )
    mapping = {
        TaskRunStatus.PENDING: "pending",
        TaskRunStatus.RUNNING: "running",
        TaskRunStatus.SUCCEEDED: "succeeded",
        TaskRunStatus.FAILED: "failed",
        TaskRunStatus.ABORTED: "aborted",
    }
    return mapping.get(run.status, "blocked")


def _task_status_summary(
    status: str,
    display_metadata: ClaimRewardsDisplayMetadata,
    failure_reason: ClaimRewardsFailureReason | None,
) -> str:
    if failure_reason is not None and status in {"failed", "aborted"}:
        return failure_reason.summary
    summaries = {
        "ready": f"{display_metadata.display_name}已準備好執行。",
        "blocked": f"{display_metadata.display_name}目前尚未就緒。",
        "pending": f"{display_metadata.display_name}正在等待執行。",
        "running": f"{display_metadata.display_name}正在執行。",
        "succeeded": f"{display_metadata.display_name}已完成。",
        "failed": f"{display_metadata.display_name}執行失敗。",
        "aborted": f"{display_metadata.display_name}已中止。",
    }
    return summaries.get(status, display_metadata.description)


def _build_step_telemetry_items(
    run: TaskRun | None,
    runtime_input: ClaimRewardsRuntimeInput,
    failure_reason: ClaimRewardsFailureReason | None,
) -> list[ClaimRewardsStepTelemetry]:
    display_metadata = runtime_input.display_metadata
    step_results = {result.step_id: result for result in run.step_results} if run is not None else {}
    running_index = (
        len(run.step_results)
        if run is not None and run.status is TaskRunStatus.RUNNING and len(run.step_results) < len(runtime_input.step_specs)
        else None
    )
    items: list[ClaimRewardsStepTelemetry] = []
    for index, step_spec in enumerate(runtime_input.step_specs):
        step_result = step_results.get(step_spec.step_id)
        step_failure_reason = (
            failure_reason
            if step_result is not None and step_result.status is StepStatus.FAILED
            else None
        )
        items.append(
            build_claim_rewards_step_telemetry(
                step_spec=step_spec,
                display_metadata=display_metadata,
                step_result=step_result,
                running=running_index == index,
                failure_reason=step_failure_reason,
            )
        )
    return items


def _resolve_failure_reason(
    run: TaskRun,
    runtime_input: ClaimRewardsRuntimeInput,
) -> ClaimRewardsFailureReason | None:
    reason_map = runtime_input.display_metadata.failure_reason_map()
    if run.stop_condition is not None:
        if run.stop_condition.kind is StopConditionKind.MANUAL:
            return reason_map.get("operator_stop")
        if run.stop_condition.kind is StopConditionKind.HEALTH_CHECK_FAILED:
            return reason_map.get("health_check_failed")
    if run.failure_snapshot is not None and run.failure_snapshot.reason is FailureSnapshotReason.STEP_EXCEPTION:
        return reason_map.get("step_exception")

    failed_result = next(
        (result for result in reversed(run.step_results) if result.status is StepStatus.FAILED),
        None,
    )
    if failed_result is None:
        return None
    step_spec = next(
        (item for item in runtime_input.step_specs if item.step_id == failed_result.step_id),
        None,
    )
    if step_spec is None:
        return None
    if isinstance(failed_result.data, dict):
        failure_reason_id = str(failed_result.data.get("failure_reason_id", "")).strip()
        if not failure_reason_id:
            step_outcome = failed_result.data.get("step_outcome")
            if isinstance(step_outcome, dict):
                failure_reason_id = str(step_outcome.get("failure_reason_id", "")).strip()
        if failure_reason_id:
            return reason_map.get(failure_reason_id)
    return reason_map.get(step_spec.failure_reason_id)


def _inspection_signals(
    match_results: dict[str, TemplateMatchResult],
) -> dict[str, bool]:
    return {
        "reward_panel_visible": match_results[_REWARD_PANEL_ANCHOR_ID].is_match(),
        "claim_button_visible": match_results[_CLAIM_REWARD_ANCHOR_ID].is_match(),
        "confirm_state_visible": match_results[_REWARD_CONFIRM_STATE_ANCHOR_ID].is_match(),
        "confirm_button_visible": match_results[_CONFIRM_BUTTON_ANCHOR_ID].is_match(),
        "close_button_visible": match_results[_CLOSE_BUTTON_ANCHOR_ID].is_match(),
    }


def _normalize_inspection_signals(
    inspection: ClaimRewardsInspection,
) -> dict[str, bool]:
    derived = {
        "reward_panel_visible": inspection.state is not ClaimRewardsPanelState.UNAVAILABLE,
        "claim_button_visible": (
            inspection.state is ClaimRewardsPanelState.CLAIMABLE or inspection.claim_point is not None
        ),
        "confirm_state_visible": inspection.state is ClaimRewardsPanelState.CONFIRM_REQUIRED,
        "confirm_button_visible": (
            inspection.state is ClaimRewardsPanelState.CONFIRM_REQUIRED or inspection.confirm_point is not None
        ),
        "close_button_visible": (
            inspection.state is ClaimRewardsPanelState.CLAIMED or inspection.close_point is not None
        ),
    }
    for key, value in inspection.signals.items():
        derived[str(key)] = bool(value)
    return derived
