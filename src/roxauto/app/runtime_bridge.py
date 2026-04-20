from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from roxauto.app.viewmodels import ConsoleSnapshot, build_console_snapshot_from_runtime, build_manual_control_command
from roxauto.core.commands import CommandDispatchResult
from roxauto.core.models import FailureSnapshotMetadata, InstanceState, InstanceStatus, ProfileBinding
from roxauto.doctor import build_doctor_report
from roxauto.emulator import EmulatorActionAdapter, LiveRuntimeSession, LiveRuntimeSnapshot
from roxauto.vision import (
    CalibrationProfile,
    CaptureArtifactKind,
    VisionToolingState,
    build_failure_inspection,
    build_template_workspace_catalog,
    build_vision_tooling_state,
    build_vision_workspace_readiness_report,
    create_capture_artifact,
    create_capture_session,
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
        self._asset_inventory_path = (
            self._workspace_root / "src" / "roxauto" / "tasks" / "foundations" / "asset_inventory.json"
        )
        self._doctor_report_provider = doctor_report_provider or build_doctor_report
        self._adb_path = "not found"
        self._packages: dict[str, bool] = {}
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

    def refresh(self) -> LiveRuntimeSnapshot:
        self._load_environment_report()
        snapshot = self._session.poll()
        for instance_snapshot in snapshot.instance_snapshots:
            self._session.refresh(instance_snapshot.instance_id)
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
        return self._session.dispatch_command(command)

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
        catalog = self.vision_workspace_catalog(
            selected_repository_id=self._resolve_repository_id(instance_snapshot),
        )
        readiness = self.vision_workspace_readiness()
        selected_anchor_id = self._resolve_anchor_id(instance_snapshot)
        calibration_profile = self._build_calibration_profile(instance_snapshot)
        capture_session = self._build_capture_session(instance_snapshot, selected_anchor_id=selected_anchor_id)
        failure_record = self._build_failure_record(
            instance_snapshot,
            selected_anchor_id=selected_anchor_id,
        )
        source_image = capture_session.source_image if capture_session is not None else ""
        failure_message = failure_record.message if failure_record is not None else ""

        state = build_vision_tooling_state(
            templates_root=self._templates_root,
            calibration_profile=calibration_profile,
            capture_session=capture_session,
            failure_record=failure_record,
            asset_inventory_path=self._asset_inventory_path,
            selected_repository_id=catalog.selected_repository_id,
            selected_anchor_id=selected_anchor_id,
            source_image=source_image,
            failure_message=failure_message,
        )
        state.workspace = catalog
        state.readiness = readiness
        state.metadata["workspace_ready_blocking_count"] = readiness.blocking_count if readiness is not None else 0
        return state

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

    def _resolve_repository_id(self, instance_snapshot) -> str:
        candidates: list[str] = []
        if instance_snapshot is not None and instance_snapshot.failure_snapshot is not None:
            anchor_id = self._resolve_anchor_id(instance_snapshot)
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

    def _resolve_anchor_id(self, instance_snapshot) -> str:
        if instance_snapshot is None or instance_snapshot.failure_snapshot is None:
            return ""
        metadata = dict(instance_snapshot.failure_snapshot.metadata)
        anchor_id = metadata.get("anchor_id") or metadata.get("expected_anchor_id")
        return str(anchor_id or "")

    def _build_calibration_profile(self, instance_snapshot) -> CalibrationProfile | None:
        if instance_snapshot is None:
            return None
        binding = instance_snapshot.profile_binding
        if binding is None:
            return None
        offset_x, offset_y = binding.capture_offset
        crop_region = None
        preview_frame = instance_snapshot.preview_frame
        if preview_frame is not None:
            crop_region = preview_frame.metadata.get("crop_region")
        settings = dict(binding.settings)
        anchor_overrides = settings.get("anchor_overrides") or binding.metadata.get("anchor_overrides") or {}
        emulator_name = (
            instance_snapshot.instance.metadata.get("emulator_name")
            or binding.metadata.get("emulator_name")
            or "mumu"
        )
        return CalibrationProfile(
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

    def _build_capture_session(self, instance_snapshot, *, selected_anchor_id: str):
        if instance_snapshot is None:
            return None
        preview_frame = instance_snapshot.preview_frame
        failure_snapshot = instance_snapshot.failure_snapshot
        source_image = ""
        if preview_frame is not None:
            source_image = preview_frame.image_path
        elif failure_snapshot is not None and failure_snapshot.screenshot_path:
            source_image = str(failure_snapshot.screenshot_path)
        if not source_image:
            return None

        crop_region = None
        if preview_frame is not None:
            crop_region = preview_frame.metadata.get("crop_region")
        elif failure_snapshot is not None:
            crop_region = failure_snapshot.metadata.get("crop_region")
        session = create_capture_session(
            session_id=(preview_frame.frame_id if preview_frame is not None else failure_snapshot.snapshot_id),
            instance_id=instance_snapshot.instance_id,
            source_image=source_image,
            crop_region=crop_region,
            selected_anchor_id=selected_anchor_id,
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
        return session

    def _build_failure_record(
        self,
        instance_snapshot,
        *,
        selected_anchor_id: str,
    ):
        if instance_snapshot is None:
            return None
        failure_snapshot = instance_snapshot.failure_snapshot
        if failure_snapshot is None:
            return None
        preview_image_path = ""
        if failure_snapshot.preview_frame is not None:
            preview_image_path = failure_snapshot.preview_frame.image_path
        elif instance_snapshot.preview_frame is not None:
            preview_image_path = instance_snapshot.preview_frame.image_path
        screenshot_path = str(failure_snapshot.screenshot_path or preview_image_path)
        return build_failure_inspection(
            failure_id=failure_snapshot.snapshot_id,
            instance_id=instance_snapshot.instance_id,
            screenshot_path=screenshot_path,
            anchor_id=selected_anchor_id,
            preview_image_path=preview_image_path,
            message=self._failure_message(failure_snapshot),
            metadata=dict(failure_snapshot.metadata),
        )

    def _failure_message(self, failure_snapshot: FailureSnapshotMetadata) -> str:
        return str(failure_snapshot.metadata.get("message") or failure_snapshot.reason.value)
