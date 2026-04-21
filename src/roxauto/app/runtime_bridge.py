from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Callable
from uuid import uuid4

from roxauto.app.viewmodels import (
    ClaimRewardsEditorView,
    ClaimRewardsPaneView,
    ClaimRewardsStepView,
    ConsoleSnapshot,
    build_console_snapshot_from_runtime,
    build_manual_control_command,
)
from roxauto.core.commands import CommandDispatchResult, InstanceCommandType
from roxauto.core.models import (
    FailureSnapshotMetadata,
    FailureSnapshotReason,
    InstanceState,
    InstanceStatus,
    PreviewFrame,
    ProfileBinding,
    TaskManifest,
    TaskRun,
    TaskSpec,
    VisionMatch,
)
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import RuntimeInspectionResult, TaskStep, step_failure, step_success
from roxauto.core.time import utc_now
from roxauto.doctor import build_doctor_report
from roxauto.emulator import EmulatorActionAdapter, LiveRuntimeSession, LiveRuntimeSnapshot
from roxauto.tasks import TaskBlueprint, TaskFoundationRepository, TaskReadinessReport, TaskRuntimeBuilderInput
from roxauto.vision import (
    AnchorRepository,
    CalibrationProfile,
    CaptureArtifactKind,
    CropRegion,
    ImageInspectionState,
    MatchStatus,
    TemplateMatchResult,
    VisionToolingState,
    build_failure_inspection,
    build_image_inspection_state,
    build_match_result,
    build_template_workspace_catalog,
    build_vision_tooling_state,
    build_vision_workspace_readiness_report,
    create_capture_artifact,
    create_capture_session,
    resolve_calibration_override,
)


class _OperatorConsoleAdapter:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._capture_counts: dict[str, int] = defaultdict(int)

    def capture_screenshot(self, instance: InstanceState) -> Path:
        metadata = instance.metadata
        preview_path = metadata.get("preview_path") or metadata.get("preview_image_path")
        if preview_path:
            return Path(str(preview_path))
        self._capture_counts[instance.instance_id] += 1
        preview_dir = self._workspace_root / "runtime_logs" / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        return preview_dir / f"{instance.instance_id}-{self._capture_counts[instance.instance_id]}.png"

    def tap(self, instance: InstanceState, point: tuple[int, int]) -> None:
        instance.metadata["last_tap"] = point

    def swipe(
        self,
        instance: InstanceState,
        start: tuple[int, int],
        end: tuple[int, int],
        duration_ms: int = 250,
    ) -> None:
        instance.metadata["last_swipe"] = {
            "start": start,
            "end": end,
            "duration_ms": duration_ms,
        }

    def input_text(self, instance: InstanceState, text: str) -> None:
        instance.metadata["last_text"] = text

    def health_check(self, instance: InstanceState) -> bool:
        override = instance.metadata.get("health_check_ok")
        if override is not None:
            return bool(override)
        return instance.status != InstanceStatus.DISCONNECTED


_CLAIM_REWARDS_TASK_ID = "daily_ui.claim_rewards"
_CLAIM_REWARDS_ANCHOR_ID = "daily_ui.claim_reward"
_CLAIM_REWARDS_PRIORITY = 240


class _ClaimRewardsWorkflowMode(str, Enum):
    CLAIMABLE = "claimable"
    ALREADY_CLAIMED = "already_claimed"
    AMBIGUOUS = "ambiguous"
    PANEL_MISSING = "panel_missing"


@dataclass(slots=True)
class _ClaimRewardsArtifactDraft:
    artifact_id: str
    image_path: str
    source_kind: str
    crop_region: tuple[int, int, int, int] | None = None
    created_at: object = field(default_factory=utc_now)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class _ClaimRewardsWorkflowDraft:
    workflow_mode: _ClaimRewardsWorkflowMode = _ClaimRewardsWorkflowMode.CLAIMABLE
    selected_source_kind: str = "preview"
    selected_source_image: str = ""
    selected_anchor_id: str = _CLAIM_REWARDS_ANCHOR_ID
    crop_region: tuple[int, int, int, int] | None = None
    match_region: tuple[int, int, int, int] | None = None
    confidence_threshold: float | None = None
    capture_scale: float | None = None
    capture_offset: tuple[int, int] | None = None
    artifacts: list[_ClaimRewardsArtifactDraft] = field(default_factory=list)
    last_applied_at: object | None = None


@dataclass(slots=True)
class _ClaimRewardsExecutionRecord:
    queue_id: str = ""
    queued_at: object | None = None
    source_image: str = ""
    match_result: TemplateMatchResult | None = None
    last_run: TaskRun | None = None
    last_queue_result: object | None = None


class OperatorConsoleRuntimeBridge:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        doctor_report_provider: Callable[[], dict[str, object]] | None = None,
        session: LiveRuntimeSession | None = None,
        adapter: EmulatorActionAdapter | None = None,
        discovery: Callable[[], list[InstanceState]] | None = None,
        profile_resolver: Callable[[InstanceState], ProfileBinding | None] | None = None,
    ) -> None:
        self._workspace_root = workspace_root or Path(__file__).resolve().parents[3]
        self._templates_root = self._workspace_root / "assets" / "templates"
        self._task_foundations_root = self._workspace_root / "src" / "roxauto" / "tasks" / "foundations"
        self._asset_inventory_path = self._task_foundations_root / "asset_inventory.json"
        self._doctor_report_provider = doctor_report_provider or build_doctor_report
        self._task_foundations = TaskFoundationRepository(self._task_foundations_root)
        self._adb_path = "not found"
        self._packages: dict[str, bool] = {}
        self._claim_rewards_blueprint_cache: TaskBlueprint | None = None
        self._claim_rewards_drafts: dict[str, _ClaimRewardsWorkflowDraft] = {}
        self._claim_rewards_records: dict[str, _ClaimRewardsExecutionRecord] = {}
        self._session = session or LiveRuntimeSession(
            adapter or _OperatorConsoleAdapter(self._workspace_root),
            discovery=discovery,
            profile_resolver=profile_resolver or self._default_profile_resolver,
        )

    @property
    def session(self) -> LiveRuntimeSession:
        return self._session

    @property
    def adb_path(self) -> str:
        return self._adb_path

    @property
    def packages(self) -> dict[str, bool]:
        return dict(self._packages)

    @property
    def templates_root(self) -> Path:
        return self._templates_root

    @property
    def asset_inventory_path(self) -> Path:
        return self._asset_inventory_path

    def refresh(
        self,
        *,
        instance_id: str | None = None,
        run_health_check: bool = True,
        capture_preview: bool = True,
    ) -> LiveRuntimeSnapshot:
        self._load_environment_report()
        return self._session.poll(
            instance_id=instance_id,
            refresh_runtime=True,
            run_health_check=run_health_check,
            capture_preview=capture_preview,
        )

    def refresh_runtime_contexts(
        self,
        *,
        instance_id: str | None = None,
        run_health_check: bool = True,
        capture_preview: bool = True,
    ) -> LiveRuntimeSnapshot:
        self._load_environment_report()
        self._session.refresh_runtime_contexts(
            instance_id=instance_id,
            run_health_check=run_health_check,
            capture_preview=capture_preview,
        )
        return self.snapshot()

    def snapshot(self) -> LiveRuntimeSnapshot:
        return self._session.last_snapshot

    def console_snapshot(self) -> ConsoleSnapshot:
        return build_console_snapshot_from_runtime(
            self.snapshot(),
            adb_path=self._adb_path,
            packages=self._packages,
        )

    def queue_items(self, instance_id: str | None = None):
        if not instance_id:
            return list(self._session.last_snapshot.queue_items)
        instance_snapshot = self._session.last_snapshot.get_instance_snapshot(instance_id)
        return list(instance_snapshot.queue_items) if instance_snapshot is not None else []

    def inspection_results(self, instance_id: str | None = None) -> list[RuntimeInspectionResult]:
        snapshot = self.snapshot()
        if instance_id is None:
            return list(snapshot.last_inspection_results)
        return [
            result
            for result in snapshot.last_inspection_results
            if result.instance_id == instance_id
        ]

    def selected_inspection_result(self, instance_id: str) -> RuntimeInspectionResult | None:
        for result in self.snapshot().last_inspection_results:
            if result.instance_id == instance_id:
                return result
        return None

    def task_runtime_builder_inputs(self) -> list[TaskRuntimeBuilderInput]:
        return self._task_foundations.build_runtime_builder_inputs()

    def task_readiness_reports(self) -> list[TaskReadinessReport]:
        return self._task_foundations.evaluate_task_readinesses()

    def update_claim_rewards_workflow(
        self,
        instance_id: str,
        *,
        workflow_mode: str | None = None,
        crop_region: tuple[int, int, int, int] | None = None,
        match_region: tuple[int, int, int, int] | None = None,
        confidence_threshold: float | None = None,
        capture_scale: float | None = None,
        capture_offset: tuple[int, int] | None = None,
        selected_source_image: str | None = None,
        selected_source_kind: str | None = None,
    ) -> None:
        draft = self._claim_rewards_draft(instance_id)
        if workflow_mode is not None:
            draft.workflow_mode = _ClaimRewardsWorkflowMode(str(workflow_mode))
        if crop_region is not None:
            draft.crop_region = crop_region
        if match_region is not None:
            draft.match_region = match_region
        if confidence_threshold is not None:
            draft.confidence_threshold = confidence_threshold
        if capture_scale is not None:
            draft.capture_scale = capture_scale
        if capture_offset is not None:
            draft.capture_offset = capture_offset
        if selected_source_image is not None:
            draft.selected_source_image = selected_source_image
        if selected_source_kind is not None:
            draft.selected_source_kind = selected_source_kind
        draft.last_applied_at = utc_now()

    def reset_claim_rewards_workflow(self, instance_id: str) -> None:
        self._claim_rewards_drafts.pop(instance_id, None)

    def capture_claim_rewards_source(
        self,
        instance_id: str,
        *,
        source_kind: str = "preview",
    ) -> str:
        instance_snapshot = self.snapshot().get_instance_snapshot(instance_id)
        inspection_result = self.selected_inspection_result(instance_id)
        source_image = self._resolve_claim_rewards_source_image(
            instance_snapshot,
            inspection_result=inspection_result,
            source_kind=source_kind,
            draft=self._claim_rewards_draft(instance_id),
        )
        if not source_image:
            return ""
        crop_region = self._claim_rewards_crop_region(
            instance_snapshot,
            inspection_result=inspection_result,
            draft=self._claim_rewards_draft(instance_id),
        )
        draft = self._claim_rewards_draft(instance_id)
        artifact = _ClaimRewardsArtifactDraft(
            artifact_id=f"claim_rewards:{source_kind}:{len(draft.artifacts) + 1}",
            image_path=source_image,
            source_kind=source_kind,
            crop_region=crop_region,
            metadata={"task_id": _CLAIM_REWARDS_TASK_ID},
        )
        draft.artifacts.append(artifact)
        draft.selected_source_kind = source_kind
        draft.selected_source_image = source_image
        if draft.crop_region is None:
            draft.crop_region = crop_region
        draft.last_applied_at = utc_now()
        return source_image

    def queue_claim_rewards(
        self,
        instance_id: str,
        *,
        priority: int = _CLAIM_REWARDS_PRIORITY,
    ) -> QueuedTask:
        existing = self._queued_claim_rewards_item(instance_id)
        if existing is not None:
            record = self._claim_rewards_record(instance_id)
            record.queue_id = existing.queue_id
            record.queued_at = existing.enqueued_at
            if not record.source_image:
                record.source_image = self._resolve_claim_rewards_source_image(
                    self.snapshot().get_instance_snapshot(instance_id),
                    inspection_result=self.selected_inspection_result(instance_id),
                    draft=self._claim_rewards_draft(instance_id),
                )
            return existing
        spec = self._build_claim_rewards_task_spec(instance_id)
        queued = self._session.enqueue(
            QueuedTask(
                instance_id=instance_id,
                spec=spec,
                priority=priority,
                metadata={
                    "operator_workflow": "claim_rewards",
                    "workflow_mode": self._claim_rewards_draft(instance_id).workflow_mode.value,
                },
            )
        )
        record = self._claim_rewards_record(instance_id)
        record.queue_id = queued.queue_id
        record.queued_at = queued.enqueued_at
        record.source_image = self._resolve_claim_rewards_source_image(
            self.snapshot().get_instance_snapshot(instance_id),
            inspection_result=self.selected_inspection_result(instance_id),
            draft=self._claim_rewards_draft(instance_id),
        )
        record.match_result = self._build_claim_rewards_match_result(
            instance_id,
            self.snapshot().get_instance_snapshot(instance_id),
            inspection_result=self.selected_inspection_result(instance_id),
        )
        return queued

    def run_claim_rewards(self, instance_id: str) -> CommandDispatchResult:
        self.queue_claim_rewards(instance_id)
        result = self.dispatch_manual_action("start_queue", instance_id=instance_id)
        self._sync_claim_rewards_record(instance_id)
        return result

    def claim_rewards_pane(
        self,
        instance_id: str,
        *,
        runtime_snapshot: LiveRuntimeSnapshot | None = None,
        vision_state: VisionToolingState | None = None,
    ) -> ClaimRewardsPaneView:
        blueprint = self._claim_rewards_blueprint()
        builder_input = self._task_foundations.build_runtime_builder_input(_CLAIM_REWARDS_TASK_ID)
        readiness = self._task_foundations.evaluate_task_readiness(_CLAIM_REWARDS_TASK_ID)
        snapshot = runtime_snapshot or self.snapshot()
        selected_snapshot = snapshot.get_instance_snapshot(instance_id) if instance_id else None
        inspection_result = self.selected_inspection_result(instance_id) if instance_id else None
        if vision_state is None and instance_id:
            vision_state = self.vision_tooling_state(instance_id)

        queued_items = [
            item for item in self.queue_items(instance_id) if item.task_id == _CLAIM_REWARDS_TASK_ID
        ] if instance_id else []
        record = self._claim_rewards_records.get(instance_id)
        draft = self._claim_rewards_drafts.get(instance_id)
        workflow_status = self._claim_rewards_workflow_status(
            selected_snapshot,
            queued_items=queued_items,
            record=record,
        )
        step_rows = self._claim_rewards_step_rows(blueprint, record)
        failure_snapshot = record.last_run.failure_snapshot if record is not None and record.last_run is not None else None
        source_image = self._resolve_claim_rewards_source_image(
            selected_snapshot,
            inspection_result=inspection_result,
            draft=draft,
        )
        selected_resolution = (
            vision_state.calibration.selected_resolution
            if vision_state is not None and vision_state.calibration is not None
            else None
        )
        selected_anchor_id = (
            draft.selected_anchor_id
            if draft is not None
            else (
                vision_state.anchors.selected_anchor_id
                if vision_state is not None and vision_state.anchors is not None
                else _CLAIM_REWARDS_ANCHOR_ID
            )
        )
        runtime_blockers = [
            requirement.summary
            for requirement in readiness.implementation_requirements
            if requirement.blocking and not requirement.satisfied
        ]
        last_run = record.last_run if record is not None else None
        editor = ClaimRewardsEditorView(
            workflow_mode=(draft.workflow_mode.value if draft is not None else _ClaimRewardsWorkflowMode.CLAIMABLE.value),
            selected_source_kind=(draft.selected_source_kind if draft is not None else "preview"),
            selected_source_image=source_image,
            selected_anchor_id=selected_anchor_id,
            crop_region_text=self._format_region(
                draft.crop_region if draft is not None else (
                    selected_resolution.capture_crop_region.to_tuple()
                    if selected_resolution is not None and selected_resolution.capture_crop_region is not None
                    else None
                )
            ),
            match_region_text=self._format_region(
                draft.match_region if draft is not None else (
                    selected_resolution.effective_match_region if selected_resolution is not None else None
                )
            ),
            confidence_threshold_text=self._format_optional_float(
                draft.confidence_threshold if draft is not None else (
                    selected_resolution.effective_confidence_threshold if selected_resolution is not None else None
                )
            ),
            capture_scale_text=self._format_optional_float(
                draft.capture_scale if draft is not None else (
                    selected_snapshot.profile_binding.capture_scale
                    if selected_snapshot is not None and selected_snapshot.profile_binding is not None
                    else None
                )
            ),
            capture_offset_text=self._format_point(
                draft.capture_offset if draft is not None else (
                    selected_snapshot.profile_binding.capture_offset
                    if selected_snapshot is not None and selected_snapshot.profile_binding is not None
                    else None
                )
            ),
            artifact_count=len(draft.artifacts) if draft is not None else 0,
            last_applied_summary=(
                "Session-scoped claim rewards editor applied."
                if draft is not None and draft.last_applied_at is not None
                else ""
            ),
        )
        return ClaimRewardsPaneView(
            task_id=blueprint.task_id,
            task_name=blueprint.manifest.name,
            manifest_path=builder_input.manifest_path,
            workflow_status=workflow_status,
            workflow_banner=self._claim_rewards_banner(
                selected_snapshot,
                readiness=readiness,
                workflow_status=workflow_status,
                queued_items=queued_items,
            ),
            runtime_gate_summary=(
                "; ".join(runtime_blockers)
                if runtime_blockers
                else "No blocking runtime readiness requirement recorded."
            ),
            queue_summary=(
                f"claim_rewards queued={len(queued_items)} | instance queue depth={selected_snapshot.queue_depth}"
                if selected_snapshot is not None
                else "Select an instance to queue claim rewards."
            ),
            last_run_summary=self._claim_rewards_last_run_summary(last_run),
            active_step_summary=self._claim_rewards_active_step_summary(
                workflow_status,
                step_rows=step_rows,
                last_run=last_run,
            ),
            failure_summary=self._claim_rewards_failure_summary(failure_snapshot, last_run),
            preview_summary=(
                source_image
                or (
                    vision_state.preview.image_path
                    if vision_state is not None and vision_state.preview is not None
                    else ""
                )
            ),
            selected_anchor_summary=self._claim_rewards_anchor_summary(
                selected_anchor_id,
                selected_resolution=selected_resolution,
            ),
            selected_scope_summary=self._claim_rewards_scope_summary(
                selected_snapshot,
                queued_items=queued_items,
            ),
            can_queue=bool(selected_snapshot is not None),
            can_run_now=bool(selected_snapshot is not None),
            is_queued=bool(queued_items),
            queue_depth=selected_snapshot.queue_depth if selected_snapshot is not None else 0,
            last_run_id=last_run.run_id if last_run is not None else "",
            last_run_status=last_run.status.value if last_run is not None else "",
            failure_reason=(
                failure_snapshot.reason.value
                if failure_snapshot is not None
                else ""
            ),
            failure_step_id=failure_snapshot.step_id if failure_snapshot is not None and failure_snapshot.step_id else "",
            failure_snapshot_id=failure_snapshot.snapshot_id if failure_snapshot is not None else "",
            step_rows=step_rows,
            editor=editor,
        )

    def global_emergency_stop_active(self) -> bool:
        snapshots = self.snapshot().instance_snapshots
        return bool(snapshots) and all(item.context is not None and item.context.stop_requested for item in snapshots)

    def dispatch_manual_action(
        self,
        action_key: str,
        *,
        instance_id: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> CommandDispatchResult:
        command = build_manual_control_command(
            action_key,
            instance_id=instance_id,
            payload=payload,
        )
        result = self._session.dispatch_command(command)
        self._refresh_after_command(command.command_type, instance_id=instance_id)
        if command.command_type == InstanceCommandType.START_QUEUE and instance_id:
            self._sync_claim_rewards_record(instance_id)
        return result

    def vision_workspace_catalog(self, *, selected_repository_id: str = ""):
        return build_template_workspace_catalog(
            self._templates_root,
            selected_repository_id=selected_repository_id,
            asset_inventory_path=self._asset_inventory_path,
        )

    def vision_workspace_readiness(self):
        return build_vision_workspace_readiness_report(
            self._templates_root,
            self._asset_inventory_path,
        )

    def vision_tooling_state(self, instance_id: str = "") -> VisionToolingState:
        runtime_snapshot = self.snapshot()
        instance_snapshot = runtime_snapshot.get_instance_snapshot(instance_id) if instance_id else None
        inspection_result = self.selected_inspection_result(instance_id) if instance_id else None
        selected_repository_id = self._resolve_repository_id(instance_snapshot, inspection_result)
        catalog = self.vision_workspace_catalog(selected_repository_id=selected_repository_id)
        readiness = self.vision_workspace_readiness()
        selected_anchor_id = self._resolve_anchor_id(instance_snapshot, inspection_result)
        calibration_profile = self._build_calibration_profile(instance_snapshot, inspection_result)
        capture_session = self._build_capture_session(
            instance_snapshot,
            inspection_result=inspection_result,
            selected_anchor_id=selected_anchor_id,
        )
        match_result = self._build_claim_rewards_match_result(
            instance_id,
            instance_snapshot,
            inspection_result=inspection_result,
        ) if instance_id else None
        failure_record = self._build_failure_record(
            instance_snapshot,
            inspection_result=inspection_result,
            selected_anchor_id=selected_anchor_id,
            match_result=match_result,
        )
        source_image = self._resolve_source_image(
            instance_snapshot,
            inspection_result=inspection_result,
            capture_session=capture_session,
            failure_screenshot_path=failure_record.screenshot_path if failure_record is not None else "",
        )

        state = build_vision_tooling_state(
            templates_root=self._templates_root,
            calibration_profile=calibration_profile,
            capture_session=capture_session,
            match_result=match_result,
            failure_record=failure_record,
            asset_inventory_path=self._asset_inventory_path,
            selected_repository_id=catalog.selected_repository_id,
            selected_anchor_id=selected_anchor_id,
            source_image=source_image,
            failure_message=self._failure_message(
                self._failure_snapshot(instance_snapshot, inspection_result),
                inspection_result=inspection_result,
            ),
        )
        state.workspace = catalog
        state.readiness = readiness
        state.preview = self._build_preview_inspection(
            instance_snapshot,
            inspection_result=inspection_result,
            capture_session=capture_session,
            selected_anchor_id=selected_anchor_id,
            vision_state=state,
        )
        state.metadata.update(
            {
                "inspection_status": (
                    inspection_result.status.value if inspection_result is not None else ""
                ),
                "inspection_health_message": (
                    inspection_result.health_check_message if inspection_result is not None else ""
                ),
                "workspace_ready_blocking_count": (
                    readiness.blocking_count if readiness is not None else 0
                ),
            }
        )
        return state

    def _claim_rewards_draft(self, instance_id: str) -> _ClaimRewardsWorkflowDraft:
        return self._claim_rewards_drafts.setdefault(instance_id, _ClaimRewardsWorkflowDraft())

    def _claim_rewards_record(self, instance_id: str) -> _ClaimRewardsExecutionRecord:
        return self._claim_rewards_records.setdefault(instance_id, _ClaimRewardsExecutionRecord())

    def _claim_rewards_blueprint(self) -> TaskBlueprint:
        if self._claim_rewards_blueprint_cache is None:
            path = self._task_foundations_root / "packs" / "daily_ui" / "daily_claim_rewards.task.json"
            self._claim_rewards_blueprint_cache = self._task_foundations.load_blueprint(path)
        return self._claim_rewards_blueprint_cache

    def _queued_claim_rewards_item(self, instance_id: str) -> QueuedTask | None:
        for item in self.queue_items(instance_id):
            if item.task_id == _CLAIM_REWARDS_TASK_ID:
                return item
        return None

    def _build_claim_rewards_task_spec(self, instance_id: str) -> TaskSpec:
        blueprint = self._claim_rewards_blueprint()
        draft = replace(self._claim_rewards_draft(instance_id))
        instance_snapshot = self.snapshot().get_instance_snapshot(instance_id)
        inspection_result = self.selected_inspection_result(instance_id)
        source_image = self._resolve_claim_rewards_source_image(
            instance_snapshot,
            inspection_result=inspection_result,
            draft=draft,
        )
        match_result = self._build_claim_rewards_match_result(
            instance_id,
            instance_snapshot,
            inspection_result=inspection_result,
        )
        step_blueprints = {step.step_id: step for step in blueprint.steps}
        manifest = replace(
            blueprint.manifest,
            metadata={
                **dict(blueprint.manifest.metadata),
                "operator_workflow": "claim_rewards",
                "source_image": source_image,
            },
        )
        steps = [
            TaskStep(
                step_id="open_reward_panel",
                description=self._claim_rewards_step_title(step_blueprints["open_reward_panel"]),
                handler=lambda context, step_blueprint=step_blueprints["open_reward_panel"], resolved_source=source_image: self._claim_rewards_open_panel_step(
                    context,
                    step_blueprint=step_blueprint,
                    source_image=resolved_source,
                    workflow_mode=draft.workflow_mode,
                ),
            ),
            TaskStep(
                step_id="verify_claim_affordance",
                description=self._claim_rewards_step_title(step_blueprints["verify_claim_affordance"]),
                handler=lambda context, step_blueprint=step_blueprints["verify_claim_affordance"], resolved_source=source_image, resolved_match=match_result: self._claim_rewards_verify_affordance_step(
                    context,
                    step_blueprint=step_blueprint,
                    source_image=resolved_source,
                    workflow_mode=draft.workflow_mode,
                    match_result=resolved_match,
                ),
            ),
        ]
        return TaskSpec(
            task_id=blueprint.task_id,
            name=blueprint.manifest.name,
            version=blueprint.manifest.version,
            entry_state="ready",
            steps=steps,
            manifest=manifest,
            metadata={
                **dict(blueprint.metadata),
                "operator_workflow": "claim_rewards",
                "manifest_path": "packs/daily_ui/daily_claim_rewards.task.json",
                "source_image": source_image,
            },
        )

    def _claim_rewards_step_title(self, step_blueprint) -> str:
        return step_blueprint.step_id.replace("_", " ").title()

    def _claim_rewards_open_panel_step(
        self,
        context,
        *,
        step_blueprint,
        source_image: str,
        workflow_mode: _ClaimRewardsWorkflowMode,
    ):
        if not source_image:
            return step_failure(
                step_blueprint.step_id,
                "No preview or captured source is available. Refresh runtime or capture a source image first.",
            )
        if workflow_mode == _ClaimRewardsWorkflowMode.PANEL_MISSING:
            return step_failure(
                step_blueprint.step_id,
                (
                    f"{step_blueprint.failure_condition} "
                    "Operator workflow currently marks the reward panel as not visible."
                ),
                screenshot_path=source_image,
                data={"source_image": source_image, "workflow_mode": workflow_mode.value},
            )
        return step_success(
            step_blueprint.step_id,
            (
                f"{step_blueprint.success_condition} "
                f"Confirmed from {source_image} via the app-owned operator workflow."
            ),
            screenshot_path=source_image,
            data={"source_image": source_image, "workflow_mode": workflow_mode.value},
        )

    def _claim_rewards_verify_affordance_step(
        self,
        context,
        *,
        step_blueprint,
        source_image: str,
        workflow_mode: _ClaimRewardsWorkflowMode,
        match_result: TemplateMatchResult | None,
    ):
        if workflow_mode == _ClaimRewardsWorkflowMode.AMBIGUOUS or match_result is None or not match_result.is_match():
            return step_failure(
                step_blueprint.step_id,
                (
                    f"{step_blueprint.failure_condition} "
                    f"{match_result.message if match_result is not None else 'No claim affordance signal was produced.'}"
                ),
                screenshot_path=source_image or "",
                data={
                    "source_image": source_image,
                    "workflow_mode": workflow_mode.value,
                    "match_status": match_result.status.value if match_result is not None else MatchStatus.MISSED.value,
                },
            )
        claim_state = "already claimed" if workflow_mode == _ClaimRewardsWorkflowMode.ALREADY_CLAIMED else "claimable"
        return step_success(
            step_blueprint.step_id,
            (
                f"{step_blueprint.success_condition} "
                f"Operator workflow resolved the reward state as {claim_state}."
            ),
            screenshot_path=source_image,
            data={
                "source_image": source_image,
                "workflow_mode": workflow_mode.value,
                "match_status": match_result.status.value,
            },
        )

    def _resolve_claim_rewards_source_image(
        self,
        instance_snapshot,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
        draft: _ClaimRewardsWorkflowDraft | None = None,
        source_kind: str | None = None,
    ) -> str:
        selected_draft = draft or (
            self._claim_rewards_drafts.get(instance_snapshot.instance_id)
            if instance_snapshot is not None
            else None
        )
        if selected_draft is not None and selected_draft.selected_source_image:
            return selected_draft.selected_source_image
        preferred_source = source_kind or (
            selected_draft.selected_source_kind if selected_draft is not None else "preview"
        )
        preview_frame = self._preview_frame(instance_snapshot, inspection_result)
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        if preferred_source == "failure":
            if failure_snapshot is not None and failure_snapshot.screenshot_path:
                return str(failure_snapshot.screenshot_path)
            if failure_snapshot is not None and failure_snapshot.preview_frame is not None:
                return failure_snapshot.preview_frame.image_path
        if preview_frame is not None:
            return preview_frame.image_path
        if failure_snapshot is not None and failure_snapshot.screenshot_path:
            return str(failure_snapshot.screenshot_path)
        return ""

    def _claim_rewards_crop_region(
        self,
        instance_snapshot,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
        draft: _ClaimRewardsWorkflowDraft | None = None,
    ) -> tuple[int, int, int, int] | None:
        if draft is not None and draft.crop_region is not None:
            return draft.crop_region
        preview_frame = self._preview_frame(instance_snapshot, inspection_result)
        if preview_frame is not None and preview_frame.metadata.get("crop_region") is not None:
            region = CropRegion.from_value(preview_frame.metadata.get("crop_region"))
            if region is not None:
                return region.to_tuple()
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        if failure_snapshot is not None and failure_snapshot.metadata.get("crop_region") is not None:
            region = CropRegion.from_value(failure_snapshot.metadata.get("crop_region"))
            if region is not None:
                return region.to_tuple()
        return None

    def _claim_rewards_repository(self):
        for repository in AnchorRepository.discover(self._templates_root):
            if repository.repository_id == "daily_ui":
                return repository
        return None

    def _build_claim_rewards_match_result(
        self,
        instance_id: str,
        instance_snapshot,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
    ) -> TemplateMatchResult | None:
        if not instance_id:
            return None
        draft = self._claim_rewards_drafts.get(instance_id)
        has_claim_scope = bool(
            instance_snapshot is not None
            and (
                (
                    instance_snapshot.context is not None
                    and instance_snapshot.context.active_task_id == _CLAIM_REWARDS_TASK_ID
                )
                or any(item.task_id == _CLAIM_REWARDS_TASK_ID for item in instance_snapshot.queue_items)
            )
        )
        if draft is None and not has_claim_scope:
            return None
        repository = self._claim_rewards_repository()
        if repository is None or not repository.has_anchor(_CLAIM_REWARDS_ANCHOR_ID):
            return None
        selected_draft = draft or _ClaimRewardsWorkflowDraft()
        source_image = self._resolve_claim_rewards_source_image(
            instance_snapshot,
            inspection_result=inspection_result,
            draft=selected_draft,
        )
        if not source_image:
            return None
        calibration_profile = self._build_calibration_profile(instance_snapshot, inspection_result)
        anchor = repository.get_anchor(
            selected_draft.selected_anchor_id
            if repository.has_anchor(selected_draft.selected_anchor_id)
            else _CLAIM_REWARDS_ANCHOR_ID
        )
        resolution = resolve_calibration_override(anchor=anchor, calibration_profile=calibration_profile)
        threshold = resolution.effective_confidence_threshold
        bbox = resolution.effective_match_region or anchor.match_region or (0, 0, 1920, 1080)
        candidates: list[VisionMatch] = []
        message = ""
        if selected_draft.workflow_mode == _ClaimRewardsWorkflowMode.CLAIMABLE:
            candidates = [
                VisionMatch(
                    anchor_id=anchor.anchor_id,
                    confidence=min(0.99, threshold + 0.05),
                    bbox=bbox,
                    source_image=source_image,
                )
            ]
            message = "Operator workflow marked the reward as claimable."
        elif selected_draft.workflow_mode == _ClaimRewardsWorkflowMode.ALREADY_CLAIMED:
            candidates = [
                VisionMatch(
                    anchor_id=anchor.anchor_id,
                    confidence=min(0.99, threshold + 0.03),
                    bbox=bbox,
                    source_image=source_image,
                )
            ]
            message = "Operator workflow marked the reward as already claimed."
        elif selected_draft.workflow_mode == _ClaimRewardsWorkflowMode.AMBIGUOUS:
            candidates = [
                VisionMatch(
                    anchor_id=anchor.anchor_id,
                    confidence=max(0.1, threshold - 0.25),
                    bbox=bbox,
                    source_image=source_image,
                )
            ]
            message = "Operator workflow marked the claim affordance as ambiguous."
        else:
            message = "Operator workflow marked the reward panel as not visible."
        result = build_match_result(
            source_image=source_image,
            candidates=candidates,
            expected_anchor=anchor,
            threshold=threshold,
            message=message,
        )
        result.metadata.update(
            {
                "task_id": _CLAIM_REWARDS_TASK_ID,
                "workflow_mode": selected_draft.workflow_mode.value,
            }
        )
        return result

    def _sync_claim_rewards_record(self, instance_id: str) -> None:
        queue_result = self.snapshot().last_queue_result
        if queue_result is None or queue_result.instance_id != instance_id:
            return
        claim_run = next(
            (run for run in queue_result.runs if run.task_id == _CLAIM_REWARDS_TASK_ID),
            None,
        )
        if claim_run is None:
            return
        record = self._claim_rewards_record(instance_id)
        record.last_queue_result = queue_result
        record.last_run = claim_run
        record.source_image = record.source_image or self._resolve_claim_rewards_source_image(
            self.snapshot().get_instance_snapshot(instance_id),
            inspection_result=self.selected_inspection_result(instance_id),
            draft=self._claim_rewards_draft(instance_id),
        )
        record.match_result = self._build_claim_rewards_match_result(
            instance_id,
            self.snapshot().get_instance_snapshot(instance_id),
            inspection_result=self.selected_inspection_result(instance_id),
        )
        failure_snapshot = claim_run.failure_snapshot
        if failure_snapshot is not None:
            failure_snapshot.metadata.setdefault("anchor_id", self._claim_rewards_draft(instance_id).selected_anchor_id)
            failure_snapshot.metadata.setdefault("expected_anchor_id", self._claim_rewards_draft(instance_id).selected_anchor_id)
            failure_snapshot.metadata.setdefault("workflow_mode", self._claim_rewards_draft(instance_id).workflow_mode.value)
            failure_snapshot.metadata.setdefault("source_image", record.source_image or self._resolve_claim_rewards_source_image(
                self.snapshot().get_instance_snapshot(instance_id),
                inspection_result=self.selected_inspection_result(instance_id),
                draft=self._claim_rewards_draft(instance_id),
            ))
            crop_region = self._claim_rewards_draft(instance_id).crop_region
            if crop_region is not None:
                failure_snapshot.metadata.setdefault("crop_region", crop_region)
            if failure_snapshot.reason == FailureSnapshotReason.STEP_FAILED and not failure_snapshot.step_id and claim_run.step_results:
                failure_snapshot.step_id = claim_run.step_results[-1].step_id

    def _claim_rewards_workflow_status(
        self,
        selected_snapshot,
        *,
        queued_items: list[QueuedTask],
        record: _ClaimRewardsExecutionRecord | None,
    ) -> str:
        if selected_snapshot is None:
            return "idle"
        if selected_snapshot.context is not None and selected_snapshot.context.active_task_id == _CLAIM_REWARDS_TASK_ID:
            return "running"
        if queued_items:
            return "queued"
        if record is not None and record.last_run is not None:
            return record.last_run.status.value
        return "idle"

    def _claim_rewards_step_rows(
        self,
        blueprint: TaskBlueprint,
        record: _ClaimRewardsExecutionRecord | None,
    ) -> list[ClaimRewardsStepView]:
        results_by_step = {
            result.step_id: result
            for result in (record.last_run.step_results if record is not None and record.last_run is not None else [])
        }
        failure_step_id = (
            record.last_run.failure_snapshot.step_id
            if record is not None
            and record.last_run is not None
            and record.last_run.failure_snapshot is not None
            else ""
        )
        rows: list[ClaimRewardsStepView] = []
        for step_blueprint in blueprint.steps:
            result = results_by_step.get(step_blueprint.step_id)
            rows.append(
                ClaimRewardsStepView(
                    step_id=step_blueprint.step_id,
                    title=self._claim_rewards_step_title(step_blueprint),
                    action=step_blueprint.action,
                    status=result.status.value if result is not None else "pending",
                    summary=(
                        result.message
                        if result is not None
                        else step_blueprint.notes or step_blueprint.success_condition
                    ),
                    success_condition=step_blueprint.success_condition,
                    failure_condition=step_blueprint.failure_condition,
                    screenshot_path=(result.screenshot_path or "") if result is not None else "",
                    is_current=(
                        bool(failure_step_id) and failure_step_id == step_blueprint.step_id
                    ),
                )
            )
        return rows

    def _claim_rewards_banner(
        self,
        selected_snapshot,
        *,
        readiness: TaskReadinessReport,
        workflow_status: str,
        queued_items: list[QueuedTask],
    ) -> str:
        runtime_blockers = [
            requirement.requirement_id
            for requirement in readiness.implementation_requirements
            if requirement.blocking and not requirement.satisfied
        ]
        if selected_snapshot is None:
            return "Select an instance to queue or run claim rewards."
        banner = "App-owned claim rewards operator workflow."
        if runtime_blockers:
            banner += f" Production readiness still blocked by {', '.join(runtime_blockers)}."
        if workflow_status == "queued":
            banner += f" Queued items: {len(queued_items)}."
        elif workflow_status == "running":
            banner += " Queue execution is currently in progress."
        elif workflow_status in {"failed", "aborted"}:
            banner += " Last run needs operator review."
        elif workflow_status == "succeeded":
            banner += " Last run completed successfully."
        else:
            banner += " Queue or run the task from this panel."
        return banner

    def _claim_rewards_last_run_summary(self, last_run: TaskRun | None) -> str:
        if last_run is None:
            return "No claim rewards run recorded yet."
        return (
            f"{last_run.status.value} | run_id={last_run.run_id} | "
            f"steps={len(last_run.step_results)}"
        )

    def _claim_rewards_active_step_summary(
        self,
        workflow_status: str,
        *,
        step_rows: list[ClaimRewardsStepView],
        last_run: TaskRun | None,
    ) -> str:
        if workflow_status == "queued" and step_rows:
            return f"Queued before {step_rows[0].step_id}."
        if last_run is None:
            return "No step execution recorded yet."
        failed = next((row for row in step_rows if row.status == "failed"), None)
        if failed is not None:
            return f"Blocked at {failed.step_id}: {failed.summary}"
        completed = [row for row in step_rows if row.status == "succeeded"]
        if len(completed) == len(step_rows):
            return "All claim rewards steps completed."
        pending = next((row for row in step_rows if row.status == "pending"), None)
        if pending is not None:
            return f"Next step: {pending.step_id}"
        return "Execution trace available in step rows."

    def _claim_rewards_failure_summary(
        self,
        failure_snapshot: FailureSnapshotMetadata | None,
        last_run: TaskRun | None,
    ) -> str:
        if failure_snapshot is None:
            if last_run is not None and last_run.status.value == "succeeded":
                return "No failure snapshot. Last run succeeded."
            return "No claim rewards failure recorded."
        return (
            f"{failure_snapshot.reason.value} | "
            f"step={failure_snapshot.step_id or 'n/a'} | "
            f"{failure_snapshot.metadata.get('message', '')}"
        )

    def _claim_rewards_anchor_summary(
        self,
        anchor_id: str,
        *,
        selected_resolution,
    ) -> str:
        if selected_resolution is None:
            return anchor_id or _CLAIM_REWARDS_ANCHOR_ID
        return (
            f"{anchor_id or _CLAIM_REWARDS_ANCHOR_ID} | "
            f"threshold={selected_resolution.effective_confidence_threshold:.2f} | "
            f"region={self._format_region(selected_resolution.effective_match_region)}"
        )

    def _claim_rewards_scope_summary(
        self,
        selected_snapshot,
        *,
        queued_items: list[QueuedTask],
    ) -> str:
        if selected_snapshot is None:
            return "No selected instance."
        scope_parts = [f"instance={selected_snapshot.instance_id}"]
        if selected_snapshot.context is not None and selected_snapshot.context.active_task_id == _CLAIM_REWARDS_TASK_ID:
            scope_parts.append("active")
        if queued_items:
            scope_parts.append(f"queued={len(queued_items)}")
        if selected_snapshot.profile_binding is not None:
            scope_parts.append(f"profile={selected_snapshot.profile_binding.profile_id}")
        return " | ".join(scope_parts)

    def _format_region(
        self,
        region: tuple[int, int, int, int] | None,
    ) -> str:
        if region is None:
            return ""
        return ",".join(str(value) for value in region)

    def _format_optional_float(self, value: float | None) -> str:
        return "" if value is None else f"{value:.2f}"

    def _format_point(self, value: tuple[int, int] | None) -> str:
        if value is None:
            return ""
        return f"{value[0]},{value[1]}"

    def _load_environment_report(self) -> None:
        try:
            report = self._doctor_report_provider()
        except Exception:
            self._adb_path = "not found"
            self._packages = {}
            return
        adb = report.get("adb", {})
        self._adb_path = str(adb.get("path") or "not found")
        self._packages = {
            str(name): bool(installed)
            for name, installed in dict(report.get("packages", {})).items()
        }

    def _default_profile_resolver(self, instance: InstanceState) -> ProfileBinding:
        capture_offset = instance.metadata.get("capture_offset") or (0, 0)
        if not isinstance(capture_offset, (list, tuple)) or len(capture_offset) != 2:
            capture_offset = (0, 0)
        capture_scale = instance.metadata.get("capture_scale", 1.0)
        return ProfileBinding(
            profile_id=f"profile.{instance.instance_id}",
            display_name=f"{instance.label} Profile",
            server_name=str(instance.metadata.get("server", "")),
            character_name=str(instance.metadata.get("character_name", instance.label)),
            allowed_tasks=[str(task_id) for task_id in instance.metadata.get("allowed_tasks", [])],
            calibration_id=str(instance.metadata.get("calibration_id") or f"calibration.{instance.instance_id}"),
            capture_offset=(int(capture_offset[0]), int(capture_offset[1])),
            capture_scale=float(capture_scale),
            settings=dict(instance.metadata.get("settings", {})),
            metadata=dict(instance.metadata.get("profile_metadata", {})),
        )

    def _refresh_after_command(
        self,
        command_type: InstanceCommandType,
        *,
        instance_id: str | None,
    ) -> None:
        if command_type == InstanceCommandType.REFRESH:
            return
        if command_type == InstanceCommandType.EMERGENCY_STOP:
            self._session.refresh_runtime_contexts(
                run_health_check=True,
                capture_preview=True,
            )
            return
        if command_type in {InstanceCommandType.TAP, InstanceCommandType.SWIPE, InstanceCommandType.INPUT_TEXT}:
            self._session.refresh_runtime_contexts(
                instance_id=instance_id,
                run_health_check=False,
                capture_preview=True,
            )
            return
        if command_type in {
            InstanceCommandType.START_QUEUE,
            InstanceCommandType.PAUSE,
            InstanceCommandType.STOP,
        }:
            self._session.refresh_runtime_contexts(
                instance_id=instance_id,
                run_health_check=True,
                capture_preview=True,
            )

    def _resolve_repository_id(
        self,
        instance_snapshot,
        inspection_result: RuntimeInspectionResult | None = None,
    ) -> str:
        candidates: list[str] = []
        if instance_snapshot is not None and (
            (
                instance_snapshot.context is not None
                and instance_snapshot.context.active_task_id == _CLAIM_REWARDS_TASK_ID
            )
            or any(item.task_id == _CLAIM_REWARDS_TASK_ID for item in instance_snapshot.queue_items)
            or instance_snapshot.instance_id in self._claim_rewards_drafts
        ):
            candidates.append("daily_ui")
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        if failure_snapshot is not None:
            anchor_id = self._anchor_id_from_failure(failure_snapshot)
            if anchor_id and "." in anchor_id:
                candidates.append(anchor_id.split(".", maxsplit=1)[0])
        context = instance_snapshot.context if instance_snapshot is not None else None
        if context is not None and context.active_task_id:
            candidates.append(str(context.active_task_id).split(".", maxsplit=1)[0])
        binding = instance_snapshot.profile_binding if instance_snapshot is not None else None
        if binding is not None:
            metadata = dict(binding.metadata)
            for key in ("repository_id", "template_repository_id", "task_pack_id"):
                value = metadata.get(key)
                if value:
                    candidates.append(str(value))
            for task_id in binding.allowed_tasks:
                candidates.append(str(task_id).split(".", maxsplit=1)[0])
        workspace = self.vision_workspace_catalog()
        valid_ids = {entry.repository_id for entry in workspace.repositories}
        for candidate in candidates:
            if candidate in valid_ids:
                return candidate
        if "common" in valid_ids:
            return "common"
        return workspace.selected_repository_id

    def _resolve_anchor_id(
        self,
        instance_snapshot,
        inspection_result: RuntimeInspectionResult | None = None,
    ) -> str:
        if instance_snapshot is not None and instance_snapshot.instance_id in self._claim_rewards_drafts:
            return self._claim_rewards_drafts[instance_snapshot.instance_id].selected_anchor_id
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        if failure_snapshot is None:
            return ""
        return self._anchor_id_from_failure(failure_snapshot)

    def _anchor_id_from_failure(self, failure_snapshot: FailureSnapshotMetadata) -> str:
        metadata = dict(failure_snapshot.metadata)
        anchor_id = metadata.get("anchor_id") or metadata.get("expected_anchor_id")
        return str(anchor_id or "")

    def _build_calibration_profile(
        self,
        instance_snapshot,
        inspection_result: RuntimeInspectionResult | None = None,
    ) -> CalibrationProfile | None:
        if instance_snapshot is None:
            return None
        binding = instance_snapshot.profile_binding
        if binding is None:
            return None
        offset_x, offset_y = binding.capture_offset
        crop_region = None
        preview_frame = self._preview_frame(instance_snapshot, inspection_result)
        if preview_frame is not None:
            crop_region = preview_frame.metadata.get("crop_region")
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        if crop_region is None and failure_snapshot is not None:
            crop_region = failure_snapshot.metadata.get("crop_region")
        settings = dict(binding.settings)
        anchor_overrides = settings.get("anchor_overrides") or binding.metadata.get("anchor_overrides") or {}
        emulator_name = (
            instance_snapshot.instance.metadata.get("emulator_name")
            or binding.metadata.get("emulator_name")
            or "mumu"
        )
        profile = CalibrationProfile(
            profile_id=binding.calibration_id or binding.profile_id,
            instance_id=instance_snapshot.instance_id,
            emulator_name=str(emulator_name),
            scale_x=float(binding.capture_scale),
            scale_y=float(binding.capture_scale),
            offset_x=int(offset_x),
            offset_y=int(offset_y),
            crop_region=crop_region,
            anchor_overrides={str(key): dict(value) for key, value in dict(anchor_overrides).items()},
            metadata={
                "profile_id": binding.profile_id,
                "server_name": binding.server_name,
                "character_name": binding.character_name,
            },
        )

        draft = self._claim_rewards_drafts.get(instance_snapshot.instance_id)
        if draft is None:
            return profile
        if draft.capture_scale is not None:
            profile.scale_x = float(draft.capture_scale)
            profile.scale_y = float(draft.capture_scale)
        if draft.capture_offset is not None:
            profile.offset_x = int(draft.capture_offset[0])
            profile.offset_y = int(draft.capture_offset[1])
        if draft.crop_region is not None:
            profile.crop_region = draft.crop_region
        override = dict(profile.anchor_overrides.get(draft.selected_anchor_id, {}))
        if draft.confidence_threshold is not None:
            override["confidence_threshold"] = float(draft.confidence_threshold)
        if draft.match_region is not None:
            override["match_region"] = draft.match_region
        if draft.crop_region is not None:
            override["crop_region"] = draft.crop_region
        if override:
            profile.anchor_overrides[draft.selected_anchor_id] = override
        profile.metadata["claim_rewards_editor"] = {
            "workflow_mode": draft.workflow_mode.value,
            "selected_anchor_id": draft.selected_anchor_id,
        }
        return profile

    def _build_capture_session(
        self,
        instance_snapshot,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
        selected_anchor_id: str,
    ):
        if instance_snapshot is None:
            return None
        draft = self._claim_rewards_drafts.get(instance_snapshot.instance_id)
        preview_frame = self._preview_frame(instance_snapshot, inspection_result)
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        source_image = self._resolve_claim_rewards_source_image(
            instance_snapshot,
            inspection_result=inspection_result,
            draft=draft,
        )
        if not source_image:
            return None

        crop_region = self._claim_rewards_crop_region(
            instance_snapshot,
            inspection_result=inspection_result,
            draft=draft,
        )
        session = create_capture_session(
            session_id=(
                preview_frame.frame_id
                if preview_frame is not None
                else (
                    failure_snapshot.snapshot_id
                    if failure_snapshot is not None
                    else f"claim_rewards:{instance_snapshot.instance_id}"
                )
            ),
            instance_id=instance_snapshot.instance_id,
            source_image=source_image,
            crop_region=crop_region,
            selected_anchor_id=(draft.selected_anchor_id if draft is not None else selected_anchor_id),
            metadata={"source": "operator_console"},
        )
        if preview_frame is not None:
            session.append_artifact(
                create_capture_artifact(
                    artifact_id=preview_frame.frame_id,
                    image_path=preview_frame.image_path,
                    source_image=source_image,
                    kind=CaptureArtifactKind.SCREENSHOT,
                    crop_region=crop_region,
                    metadata={"source": "preview_frame"},
                )
            )
        if (
            failure_snapshot is not None
            and failure_snapshot.screenshot_path
            and str(failure_snapshot.screenshot_path) != source_image
        ):
            session.append_artifact(
                create_capture_artifact(
                    artifact_id=failure_snapshot.snapshot_id,
                    image_path=str(failure_snapshot.screenshot_path),
                    source_image=source_image,
                    kind=CaptureArtifactKind.SCREENSHOT,
                    crop_region=failure_snapshot.metadata.get("crop_region"),
                    metadata={"source": "failure_snapshot"},
                )
            )
        if draft is not None:
            for artifact in draft.artifacts:
                session.append_artifact(
                    create_capture_artifact(
                        artifact_id=artifact.artifact_id,
                        image_path=artifact.image_path,
                        source_image=artifact.image_path,
                        kind=CaptureArtifactKind.SCREENSHOT,
                        crop_region=artifact.crop_region,
                        metadata={
                            "source": f"claim_rewards.{artifact.source_kind}",
                            **dict(artifact.metadata),
                        },
                    )
                )
        return session

    def _build_failure_record(
        self,
        instance_snapshot,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
        selected_anchor_id: str,
        match_result: TemplateMatchResult | None = None,
    ):
        if instance_snapshot is None:
            return None
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        if failure_snapshot is None:
            return None
        preview_frame = self._preview_frame(instance_snapshot, inspection_result)
        preview_image_path = ""
        if failure_snapshot.preview_frame is not None:
            preview_image_path = failure_snapshot.preview_frame.image_path
        elif preview_frame is not None:
            preview_image_path = preview_frame.image_path
        screenshot_path = str(failure_snapshot.screenshot_path or preview_image_path)
        return build_failure_inspection(
            failure_id=failure_snapshot.snapshot_id,
            instance_id=instance_snapshot.instance_id,
            screenshot_path=screenshot_path,
            match_result=match_result,
            anchor_id=selected_anchor_id,
            preview_image_path=preview_image_path,
            message=self._failure_message(failure_snapshot, inspection_result=inspection_result),
            metadata=dict(failure_snapshot.metadata),
        )

    def _build_preview_inspection(
        self,
        instance_snapshot,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
        capture_session,
        selected_anchor_id: str,
        vision_state: VisionToolingState,
    ) -> ImageInspectionState | None:
        image_path = self._resolve_source_image(
            instance_snapshot,
            inspection_result=inspection_result,
            capture_session=capture_session,
            failure_screenshot_path=vision_state.failure.screenshot_path,
        )
        if not image_path:
            return None
        selected_overlay_id = ""
        if capture_session is not None and capture_session.crop_region is not None:
            selected_overlay_id = f"{capture_session.session_id}:crop"
        elif selected_anchor_id:
            selected_overlay_id = f"{selected_anchor_id}:expected"
        return build_image_inspection_state(
            inspection_id=f"preview:{instance_snapshot.instance_id if instance_snapshot is not None else 'global'}",
            image_path=image_path,
            source_image=image_path,
            capture_session=capture_session,
            calibration=vision_state.calibration.selected_resolution,
            selected_overlay_id=selected_overlay_id,
            metadata={
                "kind": "runtime_preview",
                "instance_id": instance_snapshot.instance_id if instance_snapshot is not None else "",
                "inspection_status": inspection_result.status.value if inspection_result is not None else "",
                "health_check_ok": inspection_result.health_check_ok if inspection_result is not None else None,
            },
        )

    def _resolve_source_image(
        self,
        instance_snapshot,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
        capture_session=None,
        failure_screenshot_path: str = "",
    ) -> str:
        if capture_session is not None and capture_session.source_image:
            return capture_session.source_image
        preview_frame = self._preview_frame(instance_snapshot, inspection_result)
        if preview_frame is not None:
            return preview_frame.image_path
        if failure_screenshot_path:
            return failure_screenshot_path
        failure_snapshot = self._failure_snapshot(instance_snapshot, inspection_result)
        if failure_snapshot is not None and failure_snapshot.screenshot_path:
            return str(failure_snapshot.screenshot_path)
        return ""

    def _preview_frame(
        self,
        instance_snapshot,
        inspection_result: RuntimeInspectionResult | None = None,
    ) -> PreviewFrame | None:
        if inspection_result is not None and inspection_result.preview_frame is not None:
            return inspection_result.preview_frame
        if instance_snapshot is None:
            return None
        return instance_snapshot.preview_frame

    def _failure_snapshot(
        self,
        instance_snapshot,
        inspection_result: RuntimeInspectionResult | None = None,
    ) -> FailureSnapshotMetadata | None:
        if inspection_result is not None and inspection_result.failure_snapshot is not None:
            return inspection_result.failure_snapshot
        if instance_snapshot is None:
            return None
        return instance_snapshot.failure_snapshot

    def _failure_message(
        self,
        failure_snapshot: FailureSnapshotMetadata | None,
        *,
        inspection_result: RuntimeInspectionResult | None = None,
    ) -> str:
        if failure_snapshot is None:
            return inspection_result.health_check_message if inspection_result is not None else ""
        return str(
            failure_snapshot.metadata.get("message")
            or (inspection_result.health_check_message if inspection_result is not None else "")
            or failure_snapshot.reason.value
        )
