from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from queue import Empty, Queue
import threading
import time
from typing import Callable
from uuid import uuid4

from roxauto.app.viewmodels import (
    ClaimRewardsEditorView,
    ClaimRewardsPaneView,
    ClaimRewardsStepView,
    ConsoleSnapshot,
    InstanceListEntryView,
    OperatorConsoleState,
    build_console_snapshot_from_runtime,
    build_instance_list_rows,
    build_manual_control_command,
    build_operator_console_state,
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
from roxauto.emulator import (
    EmulatorActionAdapter,
    LiveRuntimeSession,
    LiveRuntimeSnapshot,
    build_adb_live_runtime_session,
)
from roxauto.profiles import (
    CalibrationProfile as StoredCalibrationProfile,
    InstanceProfileOverride,
    JsonProfileStore,
    Profile,
)
from roxauto.tasks import TaskBlueprint, TaskFoundationRepository, TaskReadinessReport, TaskRuntimeBuilderInput
from roxauto.tasks.daily_ui import (
    ClaimRewardsInspection,
    ClaimRewardsNavigationPlan,
    ClaimRewardsPanelState,
    build_claim_rewards_task_display_model,
    build_claim_rewards_runtime_input,
    build_claim_rewards_task_spec,
)
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
    last_saved_at: object | None = None
    last_saved_path: str = ""
    last_saved_summary: str = ""


@dataclass(slots=True)
class _ClaimRewardsExecutionRecord:
    queue_id: str = ""
    queued_at: object | None = None
    source_image: str = ""
    match_result: TemplateMatchResult | None = None
    last_run: TaskRun | None = None
    last_queue_result: object | None = None
    inspection_history: list[tuple[str, ClaimRewardsInspection]] = field(default_factory=list)


class _BridgeClaimRewardsVisionGateway:
    def __init__(self, bridge: "OperatorConsoleRuntimeBridge", *, instance_id: str) -> None:
        self._bridge = bridge
        self._instance_id = instance_id

    def inspect(
        self,
        *,
        instance: InstanceState,
        screenshot_path: Path,
        anchor_specs,
        metadata: dict[str, object] | None = None,
    ) -> ClaimRewardsInspection:
        inspection = self._bridge._build_claim_rewards_inspection(
            instance_id=self._instance_id,
            screenshot_path=screenshot_path,
            anchor_specs=dict(anchor_specs),
            metadata=dict(metadata or {}),
        )
        self._bridge._record_claim_rewards_inspection(
            self._instance_id,
            reason=str((metadata or {}).get("reason", "")),
            inspection=inspection,
        )
        return inspection


class OperatorConsoleRuntimeBridge:
    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        profiles_root: Path | None = None,
        profile_store: JsonProfileStore | None = None,
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
        self._profiles_root = profiles_root or (self._workspace_root / "profiles")
        self._profile_store = profile_store or JsonProfileStore(self._profiles_root)
        self._doctor_report_provider = doctor_report_provider or build_doctor_report
        self._task_foundations = TaskFoundationRepository(self._task_foundations_root)
        self._adb_path = "not found"
        self._packages: dict[str, bool] = {}
        self._claim_rewards_blueprint_cache: TaskBlueprint | None = None
        self._claim_rewards_runtime_input = None
        self._claim_rewards_drafts: dict[str, _ClaimRewardsWorkflowDraft] = {}
        self._claim_rewards_records: dict[str, _ClaimRewardsExecutionRecord] = {}
        self._lock = threading.RLock()
        self._presentation_revision = 0
        self._scheduled_actions: Queue[tuple[str, dict[str, object]]] = Queue()
        self._schedule_stop = threading.Event()
        self._schedule_idle = threading.Event()
        self._schedule_idle.set()
        self._schedule_thread: threading.Thread | None = None
        self._schedule_poll_interval_sec = 2.0
        self._last_scheduled_error = ""
        resolved_profile_resolver = profile_resolver or self._default_profile_resolver
        if session is not None:
            self._session = session
        elif adapter is not None:
            self._session = LiveRuntimeSession(
                adapter,
                discovery=discovery,
                profile_resolver=resolved_profile_resolver,
            )
        else:
            self._session = build_adb_live_runtime_session(
                adb_executable=self._detect_adb_executable(),
                screenshot_dir=self._workspace_root / "runtime_logs" / "previews",
                discovery=discovery,
                profile_resolver=resolved_profile_resolver,
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

    @property
    def profiles_root(self) -> Path:
        return self._profiles_root

    @property
    def profile_store(self) -> JsonProfileStore:
        return self._profile_store

    def start_live_updates(
        self,
        *,
        poll_interval_sec: float = 2.0,
        bootstrap: bool = True,
    ) -> None:
        if self._schedule_thread is not None and self._schedule_thread.is_alive():
            return
        self._schedule_poll_interval_sec = max(0.25, float(poll_interval_sec))
        self._schedule_stop.clear()
        self._schedule_idle.set()
        self._schedule_thread = threading.Thread(
            target=self._run_schedule_loop,
            name="roxauto-app-live-runtime",
            daemon=True,
        )
        self._schedule_thread.start()
        if bootstrap:
            self.schedule_refresh()

    def stop_live_updates(self, *, join_timeout_sec: float = 2.0) -> None:
        self._schedule_stop.set()
        self._scheduled_actions.put(("noop", {}))
        if self._schedule_thread is not None and self._schedule_thread.is_alive():
            self._schedule_thread.join(timeout=join_timeout_sec)
        self._schedule_thread = None

    def wait_for_idle(self, *, timeout_sec: float = 2.0) -> bool:
        return self._schedule_idle.wait(timeout=max(0.1, float(timeout_sec)))

    def schedule_refresh(
        self,
        *,
        instance_id: str | None = None,
        run_health_check: bool = True,
        capture_preview: bool = True,
    ) -> None:
        self._enqueue_scheduled_action(
            "refresh",
            {
                "instance_id": instance_id,
                "run_health_check": run_health_check,
                "capture_preview": capture_preview,
            },
        )

    def schedule_command(
        self,
        action_key: str,
        *,
        instance_id: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        self._enqueue_scheduled_action(
            "command",
            {
                "action_key": action_key,
                "instance_id": instance_id,
                "payload": dict(payload or {}),
            },
        )

    def schedule_claim_rewards_queue(self, instance_id: str) -> None:
        self._enqueue_scheduled_action("claim_rewards.queue", {"instance_id": instance_id})

    def schedule_claim_rewards_run(self, instance_id: str) -> None:
        self._enqueue_scheduled_action("claim_rewards.run", {"instance_id": instance_id})

    def schedule_claim_rewards_capture_source(
        self,
        instance_id: str,
        *,
        source_kind: str = "preview",
    ) -> None:
        self._enqueue_scheduled_action(
            "claim_rewards.capture_source",
            {"instance_id": instance_id, "source_kind": source_kind},
        )

    def schedule_claim_rewards_editor_update(
        self,
        instance_id: str,
        *,
        workflow_mode: str | None = None,
        crop_region: tuple[int, int, int, int] | None = None,
        match_region: tuple[int, int, int, int] | None = None,
        confidence_threshold: float | None = None,
        capture_scale: float | None = None,
        capture_offset: tuple[int, int] | None = None,
    ) -> None:
        self._enqueue_scheduled_action(
            "claim_rewards.editor_update",
            {
                "instance_id": instance_id,
                "workflow_mode": workflow_mode,
                "crop_region": crop_region,
                "match_region": match_region,
                "confidence_threshold": confidence_threshold,
                "capture_scale": capture_scale,
                "capture_offset": capture_offset,
            },
        )

    def schedule_claim_rewards_editor_reset(self, instance_id: str) -> None:
        self._enqueue_scheduled_action("claim_rewards.editor_reset", {"instance_id": instance_id})

    def schedule_claim_rewards_editor_save(self, instance_id: str) -> None:
        self._enqueue_scheduled_action("claim_rewards.editor_save", {"instance_id": instance_id})

    def get_live_state(self, selected_instance_id: str = "") -> OperatorConsoleState:
        with self._lock:
            runtime_snapshot = self.snapshot()
            console_snapshot = self.console_snapshot()
            resolved_instance_id = selected_instance_id
            if not resolved_instance_id and runtime_snapshot.instance_snapshots:
                resolved_instance_id = runtime_snapshot.instance_snapshots[0].instance_id
            if not resolved_instance_id and console_snapshot.instances:
                resolved_instance_id = console_snapshot.instances[0].instance_id
            vision_state = self.vision_tooling_state(resolved_instance_id)
            task_readiness_reports = self.task_readiness_reports()
            task_runtime_builder_inputs = self.task_runtime_builder_inputs()
            claim_rewards = self.claim_rewards_pane(
                resolved_instance_id,
                runtime_snapshot=runtime_snapshot,
                vision_state=vision_state,
            )
            return build_operator_console_state(
                console_snapshot,
                runtime_snapshot,
                vision_state,
                selected_instance_id=resolved_instance_id,
                global_emergency_stop_active=self.global_emergency_stop_active(),
                task_readiness_reports=task_readiness_reports,
                task_runtime_builder_inputs=task_runtime_builder_inputs,
                claim_rewards=claim_rewards,
            )

    def get_instance_summaries(self) -> list[InstanceListEntryView]:
        with self._lock:
            return build_instance_list_rows(
                self.console_snapshot(),
                self.snapshot(),
            )

    def _enqueue_scheduled_action(self, action: str, payload: dict[str, object]) -> None:
        self._schedule_idle.clear()
        self._scheduled_actions.put((action, payload))

    def _run_schedule_loop(self) -> None:
        next_refresh_at = time.monotonic()
        while not self._schedule_stop.is_set():
            timeout = max(0.0, next_refresh_at - time.monotonic())
            try:
                action, payload = self._scheduled_actions.get(timeout=timeout)
            except Empty:
                action, payload = ("refresh", {})
            if self._schedule_stop.is_set():
                break
            try:
                self._execute_scheduled_action(action, payload)
                self._last_scheduled_error = ""
            except Exception as exc:
                self._last_scheduled_error = str(exc)
            finally:
                if self._scheduled_actions.empty():
                    self._schedule_idle.set()
                next_refresh_at = time.monotonic() + self._schedule_poll_interval_sec

    def _execute_scheduled_action(self, action: str, payload: dict[str, object]) -> None:
        if action == "noop":
            return
        if action == "refresh":
            self.refresh(
                instance_id=str(payload.get("instance_id") or "") or None,
                run_health_check=bool(payload.get("run_health_check", True)),
                capture_preview=bool(payload.get("capture_preview", True)),
            )
            return
        if action == "command":
            self.dispatch_manual_action(
                str(payload.get("action_key", "")),
                instance_id=str(payload.get("instance_id") or "") or None,
                payload=dict(payload.get("payload", {})) if isinstance(payload.get("payload", {}), dict) else None,
            )
            return
        if action == "claim_rewards.queue":
            self.queue_claim_rewards(str(payload.get("instance_id", "")))
            return
        if action == "claim_rewards.run":
            self.run_claim_rewards(str(payload.get("instance_id", "")))
            return
        if action == "claim_rewards.capture_source":
            self.capture_claim_rewards_source(
                str(payload.get("instance_id", "")),
                source_kind=str(payload.get("source_kind", "preview")),
            )
            return
        if action == "claim_rewards.editor_update":
            self.update_claim_rewards_workflow(
                str(payload.get("instance_id", "")),
                workflow_mode=str(payload.get("workflow_mode")) if payload.get("workflow_mode") is not None else None,
                crop_region=payload.get("crop_region"),
                match_region=payload.get("match_region"),
                confidence_threshold=payload.get("confidence_threshold"),
                capture_scale=payload.get("capture_scale"),
                capture_offset=payload.get("capture_offset"),
            )
            return
        if action == "claim_rewards.editor_reset":
            self.reset_claim_rewards_workflow(str(payload.get("instance_id", "")))
            return
        if action == "claim_rewards.editor_save":
            self.save_claim_rewards_editor_profile(str(payload.get("instance_id", "")))
            return

    def refresh(
        self,
        *,
        instance_id: str | None = None,
        run_health_check: bool = True,
        capture_preview: bool = True,
    ) -> LiveRuntimeSnapshot:
        with self._lock:
            self._load_environment_report()
            snapshot = self._session.poll(
                instance_id=instance_id,
                refresh_runtime=True,
                run_health_check=run_health_check,
                capture_preview=capture_preview,
            )
            self._touch_presentation_state()
            return snapshot

    def refresh_runtime_contexts(
        self,
        *,
        instance_id: str | None = None,
        run_health_check: bool = True,
        capture_preview: bool = True,
    ) -> LiveRuntimeSnapshot:
        with self._lock:
            self._load_environment_report()
            self._session.refresh_runtime_contexts(
                instance_id=instance_id,
                run_health_check=run_health_check,
                capture_preview=capture_preview,
            )
            self._touch_presentation_state()
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
        with self._lock:
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
            self._touch_presentation_state()

    def reset_claim_rewards_workflow(self, instance_id: str) -> None:
        with self._lock:
            self._claim_rewards_drafts.pop(instance_id, None)
            self._touch_presentation_state()

    def save_claim_rewards_editor_profile(self, instance_id: str) -> Path:
        with self._lock:
            snapshot = self.snapshot()
            instance_snapshot = snapshot.get_instance_snapshot(instance_id)
            if instance_snapshot is None:
                raise ValueError(f"Unknown instance_id: {instance_id}")
            binding = instance_snapshot.profile_binding or self._fallback_profile_binding(instance_snapshot.instance)
            calibration_profile = self._build_calibration_profile(instance_snapshot)
            profile = self._load_or_build_profile(instance_snapshot, binding=binding)
            if calibration_profile is not None:
                profile.calibration = self._to_stored_calibration_profile(
                    calibration_profile,
                    calibration_id=binding.calibration_id or binding.profile_id,
                )
            override = profile.instance_overrides.get(instance_id)
            if override is None:
                override = InstanceProfileOverride(
                    instance_id=instance_id,
                    adb_serial=instance_snapshot.instance.adb_serial,
                )
            override.adb_serial = instance_snapshot.instance.adb_serial
            override.calibration_id = (
                profile.calibration.calibration_id if profile.calibration is not None else binding.calibration_id
            )
            if calibration_profile is not None:
                override.capture_offset = (
                    int(calibration_profile.offset_x),
                    int(calibration_profile.offset_y),
                )
                override.capture_scale = float(calibration_profile.scale_x)
            else:
                override.capture_offset = binding.capture_offset
                override.capture_scale = binding.capture_scale
            override.notes = binding.notes
            override.metadata = dict(override.metadata)
            profile.instance_overrides[instance_id] = override
            saved_path = self._profile_store.save(profile)
            rebound = self._profile_store.resolve_binding(
                profile.profile_id,
                instance_id,
                adb_serial=instance_snapshot.instance.adb_serial,
            )
            if rebound is not None:
                self._session.bind_profile(instance_id, rebound)
            draft = self._claim_rewards_draft(instance_id)
            draft.last_saved_at = utc_now()
            draft.last_saved_path = str(saved_path)
            draft.last_saved_summary = f"已保存到 {self._display_path(saved_path)}"
            self._touch_presentation_state()
            return saved_path

    def capture_claim_rewards_source(
        self,
        instance_id: str,
        *,
        source_kind: str = "preview",
    ) -> str:
        with self._lock:
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
            self._touch_presentation_state()
            return source_image

    def queue_claim_rewards(
        self,
        instance_id: str,
        *,
        priority: int = _CLAIM_REWARDS_PRIORITY,
    ) -> QueuedTask:
        with self._lock:
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
                self._touch_presentation_state()
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
            record.inspection_history.clear()
            self._touch_presentation_state()
            return queued

    def run_claim_rewards(self, instance_id: str) -> CommandDispatchResult:
        with self._lock:
            self.queue_claim_rewards(instance_id)
            result = self.dispatch_manual_action("start_queue", instance_id=instance_id)
            self._sync_claim_rewards_record(instance_id)
            self._touch_presentation_state()
            return result

    def claim_rewards_pane(
        self,
        instance_id: str,
        *,
        runtime_snapshot: LiveRuntimeSnapshot | None = None,
        vision_state: VisionToolingState | None = None,
    ) -> ClaimRewardsPaneView:
        with self._lock:
            runtime_input = self._claim_rewards_runtime_input_spec()
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
            claim_failure = (
                vision_state.failure.claim_rewards
                if vision_state is not None and vision_state.failure is not None
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
            display_model = build_claim_rewards_task_display_model(
                run=last_run,
                runtime_input=runtime_input,
            )
            step_rows = self._claim_rewards_step_rows(
                runtime_input,
                record,
                display_model=display_model,
            )
            completed_count = sum(1 for row in step_rows if row.status == "succeeded")
            current_step_title = self._claim_rewards_current_step_title(
                workflow_status,
                step_rows=step_rows,
            )
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
                    "已套用本次工作階段的每日領獎編輯設定。"
                    if draft is not None and draft.last_applied_at is not None
                    else ""
                ),
                persistence_summary=self._claim_rewards_persistence_summary(
                    instance_id,
                    draft=draft,
                    profile_binding=selected_snapshot.profile_binding if selected_snapshot is not None else None,
                ),
            )
            return ClaimRewardsPaneView(
                task_id=runtime_input.task_id,
                task_name=display_model.display_name,
                task_label=display_model.display_name,
                manifest_path=runtime_input.manifest_path,
                workflow_status=workflow_status,
                workflow_banner=self._claim_rewards_banner(
                    selected_snapshot,
                    readiness=readiness,
                    workflow_status=workflow_status,
                    queued_items=queued_items,
                ),
                preset_summary=self._claim_rewards_preset_summary(display_model),
                progress_summary=f"已完成 {completed_count}/{len(step_rows)} 個步驟",
                progress_completed_count=completed_count,
                progress_total_count=len(step_rows),
                current_step_title=current_step_title,
                runtime_gate_summary=(
                    "; ".join(runtime_blockers)
                    if runtime_blockers
                    else "目前沒有阻擋執行的 runtime 條件。"
                ),
                queue_summary=(
                    f"每日領獎已排入 {len(queued_items)} 筆 | 此模擬器佇列深度 {selected_snapshot.queue_depth}"
                    if selected_snapshot is not None
                    else "請先選擇模擬器，再排入每日領獎。"
                ),
                last_run_summary=self._claim_rewards_last_run_summary(
                    last_run,
                    display_model=display_model,
                ),
                active_step_summary=self._claim_rewards_active_step_summary(
                    workflow_status,
                    step_rows=step_rows,
                    last_run=last_run,
                    display_model=display_model,
                ),
                failure_summary=self._claim_rewards_failure_summary(
                    failure_snapshot,
                    last_run,
                    display_model=display_model,
                    step_rows=step_rows,
                ),
                failure_check_summary=self._claim_rewards_failure_check_summary(
                    claim_failure,
                    step_rows=step_rows,
                ),
                next_action_summary=self._claim_rewards_next_action_summary(
                    selected_snapshot,
                    runtime_blockers=runtime_blockers,
                    workflow_status=workflow_status,
                    step_rows=step_rows,
                    display_model=display_model,
                    claim_failure=claim_failure,
                ),
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
                    display_model.failure_reason.title
                    if display_model.failure_reason is not None
                    else ""
                ),
                failure_step_id=failure_snapshot.step_id if failure_snapshot is not None and failure_snapshot.step_id else "",
                failure_snapshot_id=failure_snapshot.snapshot_id if failure_snapshot is not None else "",
                step_rows=step_rows,
                editor=editor,
            )

    def global_emergency_stop_active(self) -> bool:
        with self._lock:
            snapshots = self.snapshot().instance_snapshots
            return bool(snapshots) and all(item.context is not None and item.context.stop_requested for item in snapshots)

    def dispatch_manual_action(
        self,
        action_key: str,
        *,
        instance_id: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> CommandDispatchResult:
        with self._lock:
            command = build_manual_control_command(
                action_key,
                instance_id=instance_id,
                payload=payload,
            )
            result = self._session.dispatch_command(command)
            self._refresh_after_command(command.command_type, instance_id=instance_id)
            if command.command_type == InstanceCommandType.START_QUEUE and instance_id:
                self._sync_claim_rewards_record(instance_id)
            self._touch_presentation_state()
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
        runtime_input = self._claim_rewards_runtime_input_spec()
        draft = replace(self._claim_rewards_draft(instance_id))
        instance_snapshot = self.snapshot().get_instance_snapshot(instance_id)
        if instance_snapshot is None:
            raise ValueError(f"instance {instance_id} is not available in the live runtime snapshot")
        inspection_result = self.selected_inspection_result(instance_id)
        source_image = self._resolve_claim_rewards_source_image(
            instance_snapshot,
            inspection_result=inspection_result,
            draft=draft,
        )
        navigation_plan = self._claim_rewards_navigation_plan(instance_snapshot)
        spec = build_claim_rewards_task_spec(
            adapter=self.session.adapter,
            navigation_plan=navigation_plan,
            runtime_input=runtime_input,
            vision_gateway=_BridgeClaimRewardsVisionGateway(self, instance_id=instance_id),
        )
        manifest = replace(
            spec.manifest,
            metadata={
                **dict(spec.manifest.metadata),
                "operator_workflow": "claim_rewards",
                "source_image": source_image,
            },
        ) if spec.manifest is not None else None
        return replace(
            spec,
            manifest=manifest,
            metadata={
                **dict(spec.metadata),
                "operator_workflow": "claim_rewards",
                "workflow_mode": draft.workflow_mode.value,
                "source_image": source_image,
                "navigation_plan": navigation_plan.to_dict(),
            },
        )

    def _claim_rewards_step_title(self, step_blueprint) -> str:
        return step_blueprint.step_id.replace("_", " ").title()

    def _claim_rewards_runtime_input_spec(self):
        if self._claim_rewards_runtime_input is None:
            self._claim_rewards_runtime_input = build_claim_rewards_runtime_input(
                foundation_repository=self._task_foundations,
                templates_root=self._templates_root,
            )
        return self._claim_rewards_runtime_input

    def _claim_rewards_navigation_plan(self, instance_snapshot) -> ClaimRewardsNavigationPlan:
        runtime_input = self._claim_rewards_runtime_input_spec()
        width, height = runtime_input.fixture_profile.resolution
        bindings: list[dict[str, object]] = []
        if instance_snapshot is not None:
            bindings.append(dict(instance_snapshot.instance.metadata))
            if instance_snapshot.profile_binding is not None:
                bindings.append(dict(instance_snapshot.profile_binding.settings))
                bindings.append(dict(instance_snapshot.profile_binding.metadata))
        for binding in bindings:
            daily_ui_settings = binding.get("daily_ui")
            if isinstance(daily_ui_settings, dict):
                bindings.append(dict(daily_ui_settings))
        for binding in bindings:
            for key in (
                "claim_rewards_open_panel_point",
                "daily_ui_claim_rewards_open_panel_point",
                "open_panel_point",
            ):
                point = self._coerce_point(binding.get(key))
                if point is not None:
                    return ClaimRewardsNavigationPlan(open_panel_point=point)
        return ClaimRewardsNavigationPlan(
            open_panel_point=(max(48, width - 96), min(height - 48, 96)),
        )

    def _build_claim_rewards_inspection(
        self,
        *,
        instance_id: str,
        screenshot_path: Path,
        anchor_specs: dict[str, object],
        metadata: dict[str, object] | None = None,
    ) -> ClaimRewardsInspection:
        instance_snapshot = self.snapshot().get_instance_snapshot(instance_id)
        calibration_profile = self._build_calibration_profile(instance_snapshot)
        draft = replace(self._claim_rewards_draft(instance_id))
        reason = str((metadata or {}).get("reason") or "")
        panel_state = self._claim_rewards_state_for_reason(draft.workflow_mode, reason=reason)
        source_image = str(screenshot_path)
        match_results: dict[str, TemplateMatchResult] = {}

        def add_result(anchor_id: str, *, matched: bool, message: str) -> TemplateMatchResult | None:
            anchor = anchor_specs.get(anchor_id)
            if anchor is None:
                return None
            result = self._claim_rewards_anchor_result(
                anchor=anchor,
                source_image=source_image,
                calibration_profile=calibration_profile,
                matched=matched,
                message=message,
            )
            match_results[anchor_id] = result
            return result

        claim_result = add_result(
            "daily_ui.claim_reward",
            matched=panel_state in {
                ClaimRewardsPanelState.CLAIMABLE,
                ClaimRewardsPanelState.CONFIRM_REQUIRED,
            },
            message=self._claim_rewards_claim_button_message(panel_state),
        )
        confirm_result = add_result(
            "common.confirm_button",
            matched=panel_state is ClaimRewardsPanelState.CONFIRM_REQUIRED,
            message=self._claim_rewards_confirm_button_message(panel_state),
        )
        close_result = add_result(
            "common.close_button",
            matched=panel_state is ClaimRewardsPanelState.CLAIMED,
            message=self._claim_rewards_close_button_message(panel_state),
        )
        return ClaimRewardsInspection(
            state=panel_state,
            screenshot_path=source_image,
            message=self._claim_rewards_inspection_message(panel_state),
            match_results=match_results,
            claim_point=self._claim_rewards_match_point(claim_result),
            confirm_point=self._claim_rewards_match_point(confirm_result),
            close_point=self._claim_rewards_match_point(close_result),
            metadata={
                "instance_id": instance_id,
                "reason": reason,
                "workflow_mode": draft.workflow_mode.value,
                **dict(metadata or {}),
            },
        )

    def _record_claim_rewards_inspection(
        self,
        instance_id: str,
        *,
        reason: str,
        inspection: ClaimRewardsInspection,
    ) -> None:
        record = self._claim_rewards_record(instance_id)
        record.source_image = inspection.screenshot_path or record.source_image
        record.inspection_history.append((reason, inspection))
        if len(record.inspection_history) > 16:
            record.inspection_history = record.inspection_history[-16:]

    def _claim_rewards_state_for_reason(
        self,
        workflow_mode: _ClaimRewardsWorkflowMode,
        *,
        reason: str,
    ) -> ClaimRewardsPanelState:
        if workflow_mode == _ClaimRewardsWorkflowMode.PANEL_MISSING:
            return ClaimRewardsPanelState.UNAVAILABLE
        if workflow_mode == _ClaimRewardsWorkflowMode.ALREADY_CLAIMED:
            return ClaimRewardsPanelState.CLAIMED
        if workflow_mode == _ClaimRewardsWorkflowMode.AMBIGUOUS:
            if reason == "open_reward_panel":
                return ClaimRewardsPanelState.CONFIRM_REQUIRED
            return ClaimRewardsPanelState.UNAVAILABLE
        if reason in {
            "claim_reward.post_tap",
            "confirm_reward_claim.precheck",
            "confirm_reward_claim.post_tap",
            "verify_claimed",
        }:
            return ClaimRewardsPanelState.CLAIMED
        return ClaimRewardsPanelState.CLAIMABLE

    def _claim_rewards_anchor_result(
        self,
        *,
        anchor,
        source_image: str,
        calibration_profile: CalibrationProfile | None,
        matched: bool,
        message: str,
    ) -> TemplateMatchResult:
        resolution = resolve_calibration_override(
            anchor=anchor,
            calibration_profile=calibration_profile,
        )
        runtime_input = self._claim_rewards_runtime_input_spec()
        width, height = runtime_input.fixture_profile.resolution
        bbox = resolution.effective_match_region or anchor.match_region or (0, 0, width, height)
        candidates = [
            VisionMatch(
                anchor_id=anchor.anchor_id,
                confidence=min(0.99, resolution.effective_confidence_threshold + 0.05),
                bbox=bbox,
                source_image=source_image,
            )
        ] if matched else []
        result = build_match_result(
            source_image=source_image,
            candidates=candidates,
            expected_anchor=anchor,
            threshold=resolution.effective_confidence_threshold,
            message=message,
        )
        result.metadata.update({"task_id": _CLAIM_REWARDS_TASK_ID})
        return result

    def _claim_rewards_match_point(
        self,
        result: TemplateMatchResult | None,
    ) -> tuple[int, int] | None:
        candidate = result.matched_candidate() if result is not None else None
        if candidate is None:
            return None
        left, top, width, height = candidate.bbox
        return (left + width // 2, top + height // 2)

    def _claim_rewards_inspection_message(self, panel_state: ClaimRewardsPanelState) -> str:
        if panel_state is ClaimRewardsPanelState.CLAIMABLE:
            return "Claim button detected."
        if panel_state is ClaimRewardsPanelState.CLAIMED:
            return "Claimed reward state detected."
        if panel_state is ClaimRewardsPanelState.CONFIRM_REQUIRED:
            return "Confirmation modal is visible."
        return "Reward panel could not be confirmed."

    def _claim_rewards_claim_button_message(self, panel_state: ClaimRewardsPanelState) -> str:
        if panel_state in {
            ClaimRewardsPanelState.CLAIMABLE,
            ClaimRewardsPanelState.CONFIRM_REQUIRED,
        }:
            return "Claim reward affordance detected."
        if panel_state is ClaimRewardsPanelState.CLAIMED:
            return "Claim button is no longer available."
        return "Claim reward affordance was not detected."

    def _claim_rewards_confirm_button_message(self, panel_state: ClaimRewardsPanelState) -> str:
        if panel_state is ClaimRewardsPanelState.CONFIRM_REQUIRED:
            return "Claim confirmation is required."
        return "No confirmation modal detected."

    def _claim_rewards_close_button_message(self, panel_state: ClaimRewardsPanelState) -> str:
        if panel_state is ClaimRewardsPanelState.CLAIMED:
            return "Claimed state exposes the close affordance."
        return "Close affordance is not expected in the current panel state."

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
            claim_rewards_failure = self._claim_rewards_failure_payload(
                instance_id,
                failure_step_id=failure_snapshot.step_id or "",
                source_image=str(failure_snapshot.metadata.get("source_image") or record.source_image or ""),
                inspection_history=list(record.inspection_history),
            )
            if claim_rewards_failure:
                failure_snapshot.metadata["claim_rewards"] = claim_rewards_failure

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
        runtime_input,
        record: _ClaimRewardsExecutionRecord | None,
        *,
        display_model,
    ) -> list[ClaimRewardsStepView]:
        display_steps = {step.step_id: step for step in display_model.steps}
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
        current_step_id = failure_step_id or next(
            (
                step.step_id
                for step in runtime_input.step_specs
                if step.step_id not in results_by_step
            ),
            "",
        )
        rows: list[ClaimRewardsStepView] = []
        for step_spec in runtime_input.step_specs:
            result = results_by_step.get(step_spec.step_id)
            display_step = display_steps.get(step_spec.step_id)
            rows.append(
                ClaimRewardsStepView(
                    step_id=step_spec.step_id,
                    title=(
                        display_step.display_name
                        if display_step is not None and display_step.display_name
                        else step_spec.display_name or step_spec.step_id.replace("_", " ").title()
                    ),
                    action=step_spec.action,
                    status=display_step.status if display_step is not None else (result.status.value if result is not None else "pending"),
                    status_text=display_step.status_text if display_step is not None else "",
                    summary=(
                        display_step.summary
                        if display_step is not None and display_step.summary
                        else (
                            result.message
                            if result is not None
                            else step_spec.summary or step_spec.notes or step_spec.success_condition or step_spec.description
                        )
                    ),
                    success_condition=step_spec.success_condition,
                    failure_condition=step_spec.failure_condition,
                    screenshot_path=(result.screenshot_path or "") if result is not None else "",
                    is_current=bool(current_step_id) and current_step_id == step_spec.step_id,
                )
            )
        return rows

    def _claim_rewards_preset_summary(self, display_model) -> str:
        parts = [
            display_model.preset.category_label,
            display_model.preset.status_text,
            display_model.preset.description,
        ]
        return " | ".join(part for part in parts if part)

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
            return "請先選擇模擬器，再排入或執行每日領獎。"
        banner = "每日領獎操作流程已就緒。"
        if runtime_blockers:
            banner += f" 目前仍受以下 runtime 條件阻擋：{', '.join(runtime_blockers)}。"
        if workflow_status == "queued":
            banner += f" 目前已排入 {len(queued_items)} 筆。"
        elif workflow_status == "running":
            banner += " 佇列正在執行中。"
        elif workflow_status in {"failed", "aborted"}:
            banner += " 上次執行需要人工檢查。"
        elif workflow_status == "succeeded":
            banner += " 上次執行已完成。"
        else:
            banner += " 可在此面板排入或直接執行。"
        return banner

    def _claim_rewards_last_run_summary(
        self,
        last_run: TaskRun | None,
        *,
        display_model,
    ) -> str:
        if last_run is None:
            return "目前尚無每日領獎執行紀錄。"
        return (
            f"{display_model.status_text or last_run.status.value} | "
            f"執行編號：{last_run.run_id} | "
            f"已回報 {len(last_run.step_results)} 個步驟"
        )

    def _claim_rewards_active_step_summary(
        self,
        workflow_status: str,
        *,
        step_rows: list[ClaimRewardsStepView],
        last_run: TaskRun | None,
        display_model,
    ) -> str:
        if workflow_status == "queued" and step_rows:
            return f"已排入佇列，等待「{step_rows[0].title}」。"
        if workflow_status == "running":
            current = next((row for row in step_rows if row.is_current), None)
            if current is not None:
                return f"目前步驟：{current.title}"
        if last_run is None:
            return display_model.status_summary
        failed = next((row for row in step_rows if row.status == "failed"), None)
        if failed is not None:
            if display_model.failure_reason is not None:
                return f"{display_model.failure_reason.title}：{display_model.failure_reason.summary}"
            return f"卡在 {failed.title}：{failed.summary}"
        completed = [row for row in step_rows if row.status == "succeeded"]
        if len(completed) == len(step_rows):
            return display_model.status_summary
        pending = next((row for row in step_rows if row.is_current), None)
        if pending is None:
            pending = next((row for row in step_rows if row.status == "pending"), None)
        if pending is not None:
            return f"下一步：{pending.title}"
        return display_model.status_summary or "可在步驟列表查看完整執行軌跡。"

    def _claim_rewards_failure_summary(
        self,
        failure_snapshot: FailureSnapshotMetadata | None,
        last_run: TaskRun | None,
        *,
        display_model,
        step_rows: list[ClaimRewardsStepView],
    ) -> str:
        if display_model.failure_reason is not None:
            return f"{display_model.failure_reason.title}：{display_model.failure_reason.summary}"
        if failure_snapshot is None:
            if last_run is not None and last_run.status.value == "succeeded":
                return display_model.status_summary or "沒有失敗快照；上次執行成功。"
            return "目前沒有每日領獎失敗紀錄。"
        step_title = next(
            (row.title for row in step_rows if row.step_id == failure_snapshot.step_id),
            failure_snapshot.step_id or "未提供步驟",
        )
        message = str(failure_snapshot.metadata.get("message", "") or "").strip()
        if message:
            return f"{step_title}：{message}"
        return (
            f"{failure_snapshot.reason.value} | "
            f"step={failure_snapshot.step_id or 'n/a'} | "
            f"{failure_snapshot.metadata.get('message', '')}"
        )

    def _claim_rewards_failure_check_summary(
        self,
        claim_failure,
        *,
        step_rows: list[ClaimRewardsStepView],
    ) -> str:
        if claim_failure is None:
            return ""
        selected_check = claim_failure.selected_check
        current_check_id = (
            selected_check.check_id
            if selected_check is not None
            else str(claim_failure.current_check_id or claim_failure.selected_check_id or "")
        )
        if not current_check_id:
            return ""
        check_label = self._claim_rewards_check_label(current_check_id)
        parts = [check_label]
        stage_id = selected_check.stage if selected_check is not None else ""
        if stage_id:
            stage_title = next((row.title for row in step_rows if row.step_id == stage_id), stage_id)
            parts.append(f"對應步驟：{stage_title}")
        if selected_check is not None:
            parts.append(f"檢查結果：{self._claim_rewards_match_status_text(selected_check.status.value)}")
            localized_message = self._claim_rewards_visual_message(
                current_check_id,
                status=selected_check.status.value,
            )
            if localized_message:
                parts.append(localized_message)
        return " | ".join(part for part in parts if part)

    def _claim_rewards_next_action_summary(
        self,
        selected_snapshot,
        *,
        runtime_blockers: list[str],
        workflow_status: str,
        step_rows: list[ClaimRewardsStepView],
        display_model,
        claim_failure,
    ) -> str:
        if selected_snapshot is None:
            return "先選擇一台模擬器，才能開始每日領獎。"
        if runtime_blockers:
            return f"先補齊執行條件：{'；'.join(runtime_blockers)}。"
        if workflow_status == "queued":
            return "保持佇列啟動；如果長時間沒有開始，先按「啟動佇列」再重新同步。"
        if workflow_status == "running":
            current = next((row for row in step_rows if row.is_current), None)
            if current is not None:
                return f"先等待「{current.title}」完成；若畫面停住，再切到「卡關診斷」查看目前視覺檢查。"
            return "執行中；若畫面停住，再切到「卡關診斷」查看目前視覺檢查。"
        if workflow_status == "succeeded":
            return "本輪已完成；若要再跑一次，先確認遊戲仍停留在可開啟每日獎勵的主畫面。"
        if workflow_status in {"failed", "aborted"}:
            if display_model.failure_reason is not None:
                reason_id = display_model.failure_reason.reason_id
                if reason_id == "health_check_failed":
                    return "先重新同步並確認模擬器健康狀態，再重新執行。"
                if reason_id == "operator_stop":
                    return "若要繼續，重新排入佇列後再執行。"
            selected_check = claim_failure.selected_check if claim_failure is not None else None
            if selected_check is not None:
                guidance = self._claim_rewards_check_guidance(selected_check.check_id)
                if guidance:
                    return guidance
            return "先到「卡關診斷」確認失敗步驟與視覺檢查，再決定是否重新擷取或直接重跑。"
        return "確認畫面位於遊戲主流程後，即可排入或直接執行每日領獎。"

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
            f"門檻={selected_resolution.effective_confidence_threshold:.2f} | "
            f"區域={self._format_region(selected_resolution.effective_match_region)}"
        )

    def _claim_rewards_scope_summary(
        self,
        selected_snapshot,
        *,
        queued_items: list[QueuedTask],
    ) -> str:
        if selected_snapshot is None:
            return "尚未選擇模擬器。"
        scope_parts = [
            f"模擬器：{selected_snapshot.instance.label} ({selected_snapshot.instance_id})",
        ]
        if selected_snapshot.context is not None and selected_snapshot.context.active_task_id == _CLAIM_REWARDS_TASK_ID:
            scope_parts.append("執行中")
        if queued_items:
            scope_parts.append(f"佇列中 {len(queued_items)} 筆")
        if selected_snapshot.profile_binding is not None:
            scope_parts.append(f"設定檔：{selected_snapshot.profile_binding.display_name}")
        return " | ".join(scope_parts)

    def _claim_rewards_current_step_title(
        self,
        workflow_status: str,
        *,
        step_rows: list[ClaimRewardsStepView],
    ) -> str:
        if not step_rows:
            return ""
        if workflow_status == "queued":
            return step_rows[0].title or step_rows[0].step_id
        failed = next((row for row in step_rows if row.status == "failed"), None)
        if failed is not None:
            return failed.title or failed.step_id
        pending = next((row for row in step_rows if row.status == "pending"), None)
        if pending is not None:
            return pending.title or pending.step_id
        completed = next((row for row in reversed(step_rows) if row.status == "succeeded"), None)
        if completed is not None:
            return completed.title or completed.step_id
        return step_rows[0].title or step_rows[0].step_id

    def _claim_rewards_check_label(self, check_id: str) -> str:
        mapping = {
            "reward_panel": "獎勵面板",
            "claim_reward_button": "領獎按鈕",
            "confirm_state": "確認彈窗",
        }
        return mapping.get(check_id, check_id)

    def _claim_rewards_match_status_text(self, status: str) -> str:
        mapping = {
            MatchStatus.MATCHED.value: "已命中",
            MatchStatus.MISSED.value: "未命中",
        }
        return mapping.get(status, "結果不明" if status else "")

    def _claim_rewards_visual_message(
        self,
        check_id: str,
        *,
        status: str,
    ) -> str:
        messages = {
            "reward_panel": {
                MatchStatus.MATCHED.value: "已看到每日獎勵面板。",
                MatchStatus.MISSED.value: "還沒看到每日獎勵面板。",
            },
            "claim_reward_button": {
                MatchStatus.MATCHED.value: "已找到可點擊的領獎按鈕。",
                MatchStatus.MISSED.value: "還沒找到可點擊的領獎按鈕。",
            },
            "confirm_state": {
                MatchStatus.MATCHED.value: "已看到確認彈窗。",
                MatchStatus.MISSED.value: "還沒看到確認彈窗。",
            },
        }
        return messages.get(check_id, {}).get(status, "視覺訊號仍不穩定。")

    def _claim_rewards_check_guidance(self, check_id: str) -> str:
        mapping = {
            "reward_panel": "先確認遊戲回到主畫面且每日獎勵入口可見，再重新執行。",
            "claim_reward_button": "先重新擷取目前畫面，確認領獎按鈕的比對區域與門檻；必要時到「校準工具」調整後再執行。",
            "confirm_state": "先確認是否真的出現確認彈窗；若有，重擷取失敗畫面並檢查確認按鈕的比對區域後再執行。",
        }
        return mapping.get(check_id, "")

    def _claim_rewards_failure_payload(
        self,
        instance_id: str,
        *,
        failure_step_id: str,
        source_image: str,
        inspection_history: list[tuple[str, ClaimRewardsInspection]],
    ) -> dict[str, object]:
        if not inspection_history:
            return {}
        reason, inspection = inspection_history[-1]
        repository = self._claim_rewards_repository()
        if repository is None:
            return {}
        state = inspection.state
        draft = self._claim_rewards_draft(instance_id)
        claim_result = inspection.match_results.get("daily_ui.claim_reward")
        reward_panel_result = self._claim_rewards_repository_result(
            instance_id=instance_id,
            anchor_id="daily_ui.reward_panel",
            source_image=source_image or inspection.screenshot_path,
            matched=state is not ClaimRewardsPanelState.UNAVAILABLE,
            message=(
                "Reward panel detected."
                if state is not ClaimRewardsPanelState.UNAVAILABLE
                else "Reward panel is not visible."
            ),
        )
        confirm_result = self._claim_rewards_repository_result(
            instance_id=instance_id,
            anchor_id="daily_ui.reward_confirm_state",
            source_image=source_image or inspection.screenshot_path,
            matched=state is ClaimRewardsPanelState.CONFIRM_REQUIRED,
            message=(
                "Confirmation modal detected."
                if state is ClaimRewardsPanelState.CONFIRM_REQUIRED
                else "Confirmation modal is not visible."
            ),
        )
        checks = {
            "reward_panel": self._claim_rewards_check_payload(
                reward_panel_result,
                source_image=source_image or inspection.screenshot_path,
                message=reward_panel_result.message if reward_panel_result is not None else "",
                metadata={
                    "workflow_mode": draft.workflow_mode.value,
                    "panel_state": state.value,
                    "inspection_reason": reason,
                },
            ),
            "claim_reward_button": self._claim_rewards_check_payload(
                claim_result,
                source_image=source_image or inspection.screenshot_path,
                message=self._claim_rewards_claim_button_message(state),
                metadata={
                    "workflow_mode": draft.workflow_mode.value,
                    "panel_state": state.value,
                    "inspection_reason": reason,
                },
            ),
            "confirm_state": self._claim_rewards_check_payload(
                confirm_result,
                source_image=source_image or inspection.screenshot_path,
                message=confirm_result.message if confirm_result is not None else "",
                metadata={
                    "workflow_mode": draft.workflow_mode.value,
                    "panel_state": state.value,
                    "inspection_reason": reason,
                },
            ),
        }
        current_check_id = self._claim_rewards_check_id_for_step(failure_step_id)
        if not current_check_id:
            current_check_id = self._claim_rewards_check_id_for_reason(reason)
        if failure_step_id == "verify_claim_affordance" and state is ClaimRewardsPanelState.CONFIRM_REQUIRED:
            current_check_id = "confirm_state"
        return {
            "task_id": _CLAIM_REWARDS_TASK_ID,
            "workflow_mode": draft.workflow_mode.value,
            "panel_state": state.value,
            "inspection_reason": reason,
            "current_check_id": current_check_id,
            "selected_check_id": current_check_id,
            "checks": checks,
        }

    def _claim_rewards_repository_result(
        self,
        *,
        instance_id: str,
        anchor_id: str,
        source_image: str,
        matched: bool,
        message: str,
    ) -> TemplateMatchResult | None:
        repository = self._claim_rewards_repository()
        if repository is None or not repository.has_anchor(anchor_id):
            return None
        instance_snapshot = self.snapshot().get_instance_snapshot(instance_id)
        return self._claim_rewards_anchor_result(
            anchor=repository.get_anchor(anchor_id),
            source_image=source_image,
            calibration_profile=self._build_calibration_profile(instance_snapshot),
            matched=matched,
            message=message,
        )

    def _claim_rewards_check_payload(
        self,
        result: TemplateMatchResult | None,
        *,
        source_image: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        candidates = []
        resolved_source = source_image
        payload: dict[str, object] = {
            "source_image": resolved_source,
            "message": message or (result.message if result is not None else ""),
            "candidates": candidates,
            "metadata": dict(metadata or {}),
        }
        if result is not None:
            resolved_source = result.source_image or resolved_source
            candidates = [
                {
                    "anchor_id": candidate.anchor_id,
                    "confidence": candidate.confidence,
                    "bbox": list(candidate.bbox),
                    "source_image": candidate.source_image,
                }
                for candidate in result.candidates
            ]
            payload["threshold"] = result.threshold
        payload["source_image"] = resolved_source
        payload["candidates"] = candidates
        return payload

    def _claim_rewards_check_id_for_step(self, step_id: str) -> str:
        mapping = {
            "open_reward_panel": "reward_panel",
            "verify_claim_affordance": "claim_reward_button",
            "claim_reward": "claim_reward_button",
            "confirm_reward_claim": "confirm_state",
            "verify_claimed": "reward_panel",
        }
        return mapping.get(step_id, "")

    def _claim_rewards_check_id_for_reason(self, reason: str) -> str:
        mapping = {
            "open_reward_panel": "reward_panel",
            "verify_claim_affordance": "claim_reward_button",
            "claim_reward.precheck": "claim_reward_button",
            "claim_reward.post_tap": "claim_reward_button",
            "confirm_reward_claim.precheck": "confirm_state",
            "confirm_reward_claim.post_tap": "confirm_state",
            "verify_claimed": "reward_panel",
        }
        return mapping.get(reason, "")

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

    def _coerce_point(self, value: object) -> tuple[int, int] | None:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return None
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None

    def _touch_presentation_state(self) -> None:
        self._presentation_revision += 1

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._workspace_root))
        except ValueError:
            return str(path)

    def _load_or_build_profile(
        self,
        instance_snapshot,
        *,
        binding: ProfileBinding,
    ) -> Profile:
        profile = self._profile_store.load(binding.profile_id)
        if profile is None:
            profile = Profile(
                profile_id=binding.profile_id,
                display_name=binding.display_name or f"{instance_snapshot.instance.label} Profile",
                server_name=binding.server_name,
                character_name=binding.character_name,
                allowed_tasks=list(binding.allowed_tasks),
                settings=dict(binding.settings),
            )
        else:
            if not profile.display_name:
                profile.display_name = binding.display_name or f"{instance_snapshot.instance.label} Profile"
            if not profile.server_name:
                profile.server_name = binding.server_name
            if not profile.character_name:
                profile.character_name = binding.character_name
            if not profile.allowed_tasks and binding.allowed_tasks:
                profile.allowed_tasks = list(binding.allowed_tasks)
            if not profile.settings and binding.settings:
                profile.settings = dict(binding.settings)
        return profile

    def _to_stored_calibration_profile(
        self,
        calibration_profile: CalibrationProfile,
        *,
        calibration_id: str,
    ) -> StoredCalibrationProfile:
        return StoredCalibrationProfile(
            calibration_id=calibration_id,
            description="Saved from claim rewards editor",
            capture_offset=(int(calibration_profile.offset_x), int(calibration_profile.offset_y)),
            capture_scale=float(calibration_profile.scale_x),
            crop_box=tuple(calibration_profile.crop_region) if calibration_profile.crop_region is not None else None,
            anchor_overrides={
                str(anchor_id): dict(override)
                for anchor_id, override in calibration_profile.anchor_overrides.items()
            },
            metadata={
                **dict(calibration_profile.metadata),
                "emulator_name": calibration_profile.emulator_name,
                "instance_id": calibration_profile.instance_id,
                "saved_from": "claim_rewards_editor",
            },
        )

    def _claim_rewards_persistence_summary(
        self,
        instance_id: str,
        *,
        draft: _ClaimRewardsWorkflowDraft | None,
        profile_binding: ProfileBinding | None,
    ) -> str:
        if draft is not None and draft.last_saved_summary:
            return draft.last_saved_summary
        if profile_binding is None:
            return ""
        profile_path = self._profiles_root / f"{profile_binding.profile_id}.json"
        if profile_path.exists():
            return f"已綁定設定檔：{self._display_path(profile_path)}"
        return ""

    def _detect_adb_executable(self) -> Path | str | None:
        try:
            report = self._doctor_report_provider()
        except Exception:
            return None
        adb = report.get("adb", {})
        value = adb.get("path")
        if not value:
            return None
        return str(value)

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

    def _fallback_profile_binding(self, instance: InstanceState) -> ProfileBinding:
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

    def _default_profile_resolver(self, instance: InstanceState) -> ProfileBinding:
        preferred_profile_id = instance.metadata.get("profile_id")
        binding = self._profile_store.resolve_binding_for_instance(
            instance.instance_id,
            adb_serial=instance.adb_serial,
            profile_id=str(preferred_profile_id) if preferred_profile_id else None,
        )
        if binding is not None:
            return binding
        return self._fallback_profile_binding(instance)

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
        if crop_region is None:
            crop_region = binding.metadata.get("calibration_crop_box")
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
