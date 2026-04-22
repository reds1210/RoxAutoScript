from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from roxauto.core.commands import CommandDispatchResult, InstanceCommand, InstanceCommandType
from roxauto.core.events import AppEvent, EVENT_INSTANCE_ERROR, EVENT_TASK_FAILURE_SNAPSHOT_RECORDED
from roxauto.core.runtime import QueueRunResult, RuntimeInspectionResult
from roxauto.emulator import LiveRuntimeEventRecord, LiveRuntimeInstanceSnapshot, LiveRuntimeSnapshot
from roxauto.tasks import TaskReadinessReport, TaskRuntimeBuilderInput
from roxauto.vision import VisionToolingState


@dataclass(slots=True)
class InstanceCardView:
    instance_id: str
    label: str
    adb_serial: str
    status: str
    last_seen_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConsoleSnapshot:
    adb_path: str
    instance_count: int
    packages: dict[str, bool]
    instances: list[InstanceCardView]

    @property
    def available_runtime_features(self) -> list[str]:
        return [package_name for package_name, installed in self.packages.items() if installed]


@dataclass(slots=True)
class ConsoleSummaryView:
    total_instances: int
    ready_count: int
    busy_count: int
    paused_count: int
    error_count: int
    disconnected_count: int
    queued_count: int
    failure_count: int
    selected_instance_label: str = ""
    selected_instance_status: str = ""
    selected_queue_depth: int = 0
    global_status_message: str = ""


@dataclass(slots=True)
class InstanceListEntryView:
    instance_id: str
    label: str
    status: str
    subtitle: str
    queue_depth: int = 0
    active_task_id: str = ""
    profile_summary: str = ""
    health_summary: str = ""
    preview_summary: str = ""
    warning: str = ""


@dataclass(slots=True)
class InstanceDetailView:
    instance_id: str
    label: str
    status: str
    adb_serial: str
    last_seen_at: str
    queue_depth: int
    metadata_lines: list[str] = field(default_factory=list)
    warning: str = ""
    inspection_summary: str = ""


@dataclass(slots=True)
class QueueItemView:
    queue_id: str
    task_id: str
    task_name: str
    priority: int
    recovery_policy: str
    enqueued_at: str
    requirements_summary: str = ""


@dataclass(slots=True)
class QueuePaneView:
    selected_instance_id: str
    total_count: int
    items: list[QueueItemView] = field(default_factory=list)
    empty_message: str = "No queued work for the selected instance."
    last_queue_status: str = "idle"
    last_queue_summary: str = ""


@dataclass(slots=True)
class LogEntryView:
    event_name: str
    emitted_at: str
    level: str
    instance_id: str
    summary: str


@dataclass(slots=True)
class LogPaneView:
    total_count: int
    filtered_count: int
    failure_count: int
    entries: list[LogEntryView] = field(default_factory=list)
    empty_message: str = "No operator activity yet."
    latest_summary: str = ""


@dataclass(slots=True)
class ManualControlButtonView:
    action_key: str
    label: str
    command_type: str
    requires_instance: bool
    enabled: bool
    help_text: str


@dataclass(slots=True)
class ManualControlsView:
    selected_instance_id: str
    selected_instance_label: str
    available_actions: list[ManualControlButtonView] = field(default_factory=list)
    enabled: bool = False
    banner: str = ""
    last_command_summary: str = ""
    last_command_status: str = "idle"


@dataclass(slots=True)
class TaskReadinessRowView:
    task_id: str
    pack_id: str
    manifest_path: str
    builder_state: str
    implementation_state: str
    builder_blockers: list[str] = field(default_factory=list)
    implementation_blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_anchors: list[str] = field(default_factory=list)
    fixture_profile_paths: list[str] = field(default_factory=list)
    asset_requirement_ids: list[str] = field(default_factory=list)
    runtime_requirement_ids: list[str] = field(default_factory=list)
    calibration_requirement_ids: list[str] = field(default_factory=list)
    foundation_requirement_ids: list[str] = field(default_factory=list)
    is_related_to_selected_instance: bool = False
    scope_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TaskReadinessPaneView:
    total_tasks: int
    builder_ready_count: int
    builder_blocked_count: int
    implementation_ready_count: int
    implementation_blocked_count: int
    blocked_by_asset_count: int
    blocked_by_runtime_count: int
    blocked_by_calibration_count: int
    blocked_by_foundation_count: int
    selected_task_ids: list[str] = field(default_factory=list)
    rows: list[TaskReadinessRowView] = field(default_factory=list)
    empty_message: str = "No task readiness data available."


@dataclass(slots=True)
class ClaimRewardsStepView:
    step_id: str = ""
    title: str = ""
    action: str = ""
    status: str = "pending"
    status_text: str = ""
    summary: str = ""
    success_condition: str = ""
    failure_condition: str = ""
    screenshot_path: str = ""
    is_current: bool = False


@dataclass(slots=True)
class ClaimRewardsEditorView:
    workflow_mode: str = "claimable"
    selected_source_kind: str = "preview"
    selected_source_image: str = ""
    selected_anchor_id: str = "daily_ui.claim_reward"
    crop_region_text: str = ""
    match_region_text: str = ""
    confidence_threshold_text: str = ""
    capture_scale_text: str = ""
    capture_offset_text: str = ""
    artifact_count: int = 0
    last_applied_summary: str = ""
    persistence_summary: str = ""


@dataclass(slots=True)
class ClaimRewardsPaneView:
    task_id: str = "daily_ui.claim_rewards"
    task_name: str = "每日領獎"
    task_label: str = "每日領獎"
    manifest_path: str = ""
    workflow_status: str = "idle"
    workflow_banner: str = "請先選擇模擬器，再查看每日領獎流程。"
    preset_summary: str = ""
    progress_summary: str = ""
    progress_completed_count: int = 0
    progress_total_count: int = 0
    current_step_title: str = ""
    runtime_gate_summary: str = ""
    queue_summary: str = ""
    last_run_summary: str = ""
    active_step_summary: str = ""
    failure_summary: str = ""
    failure_check_summary: str = ""
    next_action_summary: str = ""
    preview_summary: str = ""
    focus_step_summary: str = ""
    focus_anchor_summary: str = ""
    focus_region_summary: str = ""
    focus_threshold_summary: str = ""
    selected_anchor_summary: str = ""
    selected_scope_summary: str = ""
    selected_provenance_summary: str = ""
    selected_curation_summary: str = ""
    failure_explanation: str = ""
    can_queue: bool = False
    can_run_now: bool = False
    is_queued: bool = False
    queue_depth: int = 0
    last_run_id: str = ""
    last_run_status: str = ""
    failure_reason: str = ""
    failure_step_id: str = ""
    failure_snapshot_id: str = ""
    step_rows: list[ClaimRewardsStepView] = field(default_factory=list)
    editor: ClaimRewardsEditorView = field(default_factory=ClaimRewardsEditorView)

    def __post_init__(self) -> None:
        if self.task_id != "daily_ui.claim_rewards":
            return
        if not self.task_name.strip() or "?" in self.task_name:
            self.task_name = "每日領獎"
        if not self.task_label.strip() or "?" in self.task_label:
            self.task_label = "每日領獎"


@dataclass(slots=True)
class OperatorConsoleState:
    snapshot: ConsoleSnapshot
    runtime_snapshot: LiveRuntimeSnapshot
    selected_instance_snapshot: LiveRuntimeInstanceSnapshot | None
    selected_inspection_result: RuntimeInspectionResult | None
    summary: ConsoleSummaryView
    instance_rows: list[InstanceListEntryView]
    selected_instance_id: str
    detail: InstanceDetailView
    queue: QueuePaneView
    logs: LogPaneView
    manual_controls: ManualControlsView
    task_readiness: TaskReadinessPaneView
    claim_rewards: ClaimRewardsPaneView
    vision: VisionToolingState
    global_emergency_stop_active: bool = False


@dataclass(slots=True)
class ManualActionSpec:
    action_key: str
    label: str
    command_type: InstanceCommandType
    requires_instance: bool
    help_text: str


_ACTION_SPECS: dict[str, ManualActionSpec] = {
    "refresh": ManualActionSpec(
        action_key="refresh",
        label="重新同步",
        command_type=InstanceCommandType.REFRESH,
        requires_instance=False,
        help_text="重新同步環境並輪詢 runtime 健康狀態。",
    ),
    "start_queue": ManualActionSpec(
        action_key="start_queue",
        label="啟動佇列",
        command_type=InstanceCommandType.START_QUEUE,
        requires_instance=True,
        help_text="在選取的模擬器上恢復佇列工作。",
    ),
    "pause": ManualActionSpec(
        action_key="pause",
        label="暫停",
        command_type=InstanceCommandType.PAUSE,
        requires_instance=True,
        help_text="暫停選取模擬器上的目前工作。",
    ),
    "stop": ManualActionSpec(
        action_key="stop",
        label="停止",
        command_type=InstanceCommandType.STOP,
        requires_instance=True,
        help_text="停止選取模擬器上的目前任務。",
    ),
    "tap": ManualActionSpec(
        action_key="tap",
        label="點擊",
        command_type=InstanceCommandType.TAP,
        requires_instance=True,
        help_text="對選取的模擬器送出一次點擊。",
    ),
    "swipe": ManualActionSpec(
        action_key="swipe",
        label="滑動",
        command_type=InstanceCommandType.SWIPE,
        requires_instance=True,
        help_text="對選取的模擬器送出一次滑動手勢。",
    ),
    "input_text": ManualActionSpec(
        action_key="input_text",
        label="輸入文字",
        command_type=InstanceCommandType.INPUT_TEXT,
        requires_instance=True,
        help_text="對目前控制項送出文字輸入。",
    ),
    "emergency_stop": ManualActionSpec(
        action_key="emergency_stop",
        label="全域停止",
        command_type=InstanceCommandType.EMERGENCY_STOP,
        requires_instance=False,
        help_text="對所有模擬器要求全域緊急停止。",
    ),
}


def _status_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def build_console_snapshot(report: dict[str, Any]) -> ConsoleSnapshot:
    adb = report.get("adb", {})
    packages = dict(report.get("packages", {}))
    instances = [
        InstanceCardView(
            instance_id=str(instance.get("instance_id", "")),
            label=str(instance.get("label", "")),
            adb_serial=str(instance.get("adb_serial", "")),
            status=_status_value(instance.get("status", "")),
            last_seen_at=str(instance.get("last_seen_at", "")),
            metadata=dict(instance.get("metadata", {})),
        )
        for instance in report.get("instances", [])
    ]
    return ConsoleSnapshot(
        adb_path=str(adb.get("path") or "not found"),
        instance_count=int(adb.get("instances_found") or len(instances)),
        packages=packages,
        instances=instances,
    )


def build_console_snapshot_from_runtime(
    runtime_snapshot: LiveRuntimeSnapshot,
    *,
    adb_path: str,
    packages: dict[str, bool] | None = None,
) -> ConsoleSnapshot:
    cards: list[InstanceCardView] = []
    by_id = {item.instance_id: item for item in runtime_snapshot.instance_snapshots}
    inspection_by_id = _inspection_lookup(runtime_snapshot)
    for instance in runtime_snapshot.instances:
        snapshot = by_id.get(instance.instance_id)
        inspection = inspection_by_id.get(instance.instance_id)
        metadata = dict(instance.metadata)
        if snapshot is not None:
            metadata["queue_depth"] = snapshot.queue_depth
            metadata["stop_requested"] = bool(snapshot.context is not None and snapshot.context.stop_requested)
            if snapshot.health_check_ok is not None:
                metadata["health_check_ok"] = snapshot.health_check_ok
            if snapshot.profile_binding is not None:
                metadata["profile_id"] = snapshot.profile_binding.profile_id
            if snapshot.preview_frame is not None:
                metadata["preview_frame"] = snapshot.preview_frame.image_path
            if snapshot.failure_snapshot is not None:
                metadata["failure_snapshot"] = snapshot.failure_snapshot.snapshot_id
        if inspection is not None:
            metadata["last_inspection_status"] = inspection.status.value
            metadata["last_inspection_health_ok"] = inspection.health_check_ok
            if inspection.health_check_message:
                metadata["last_inspection_message"] = inspection.health_check_message
        cards.append(
            InstanceCardView(
                instance_id=instance.instance_id,
                label=instance.label,
                adb_serial=instance.adb_serial,
                status=_status_value(instance.status),
                last_seen_at=str(instance.last_seen_at),
                metadata=metadata,
            )
        )
    return ConsoleSnapshot(
        adb_path=adb_path,
        instance_count=len(cards),
        packages=dict(packages or {}),
        instances=cards,
    )


def build_queue_pane(
    runtime_snapshot: LiveRuntimeSnapshot,
    *,
    selected_instance_id: str = "",
) -> QueuePaneView:
    if selected_instance_id:
        selected_snapshot = runtime_snapshot.get_instance_snapshot(selected_instance_id)
        filtered = list(selected_snapshot.queue_items) if selected_snapshot is not None else []
    else:
        filtered = list(runtime_snapshot.queue_items)
    items = [
        QueueItemView(
            queue_id=item.queue_id,
            task_id=item.task_id,
            task_name=item.spec.name,
            priority=item.priority,
            recovery_policy=item.spec.manifest.recovery_policy if item.spec.manifest is not None else "default",
            enqueued_at=str(item.enqueued_at),
            requirements_summary=", ".join(item.spec.manifest.requires)
            if item.spec.manifest is not None and item.spec.manifest.requires
            else "",
        )
        for item in filtered
    ]
    empty_message = "No queued work for the selected instance." if selected_instance_id else "No queued work available."
    last_queue_result = runtime_snapshot.last_queue_result
    last_queue_status = "idle"
    last_queue_summary = ""
    if last_queue_result is not None and (
        not selected_instance_id or last_queue_result.instance_id == selected_instance_id
    ):
        statuses = sorted({run.status.value for run in last_queue_result.runs})
        if last_queue_result.stopped:
            last_queue_status = "stopped"
        elif statuses:
            last_queue_status = ",".join(statuses)
        last_queue_summary = (
            last_queue_result.message
            or (
                f"queue result for {last_queue_result.instance_id}: "
                f"runs={len(last_queue_result.runs)} "
                f"remaining={last_queue_result.remaining_queue_depth}"
            )
        )
    return QueuePaneView(
        selected_instance_id=selected_instance_id,
        total_count=len(items),
        items=items,
        empty_message=empty_message,
        last_queue_status=last_queue_status,
        last_queue_summary=last_queue_summary,
    )


def build_log_pane(
    events: Iterable[AppEvent | LiveRuntimeEventRecord],
    *,
    selected_instance_id: str = "",
) -> LogPaneView:
    event_list = list(events)
    filtered_events = [
        event
        for event in event_list
        if not selected_instance_id or _event_instance_id(event) in {"", selected_instance_id}
    ]
    entries = [_build_log_entry(event) for event in reversed(filtered_events)]
    failure_count = sum(1 for entry in entries if entry.level == "error")
    empty_message = "No operator activity for the selected instance." if selected_instance_id else "No operator activity yet."
    return LogPaneView(
        total_count=len(event_list),
        filtered_count=len(filtered_events),
        failure_count=failure_count,
        entries=entries,
        empty_message=empty_message,
        latest_summary=entries[0].summary if entries else empty_message,
    )


def _build_log_entry(event: AppEvent | LiveRuntimeEventRecord) -> LogEntryView:
    payload = _event_payload(event)
    event_name = _event_name(event)
    level = "info"
    status = str(payload.get("status", "")).lower()
    if event_name in {EVENT_TASK_FAILURE_SNAPSHOT_RECORDED, EVENT_INSTANCE_ERROR} or status in {"failed", "aborted", "rejected"}:
        level = "error"
    elif event_name.endswith("alert_raised") or payload.get("healthy") is False:
        level = "warning"

    summary_parts = [event_name]
    for key in ("message", "task_id", "run_id", "step_id", "status", "command_type", "snapshot_id", "frame_id"):
        value = payload.get(key)
        if value:
            summary_parts.append(f"{key}={value}")
    if "healthy" in payload:
        summary_parts.append(f"healthy={payload['healthy']}")

    return LogEntryView(
        event_name=event_name,
        emitted_at=str(_event_emitted_at(event)),
        level=level,
        instance_id=_event_instance_id(event),
        summary=" | ".join(summary_parts),
    )


def build_instance_detail(
    snapshot: ConsoleSnapshot,
    *,
    selected_instance_snapshot: LiveRuntimeInstanceSnapshot | None = None,
    selected_inspection_result: RuntimeInspectionResult | None = None,
    queue: QueuePaneView | None = None,
    global_emergency_stop_active: bool = False,
) -> InstanceDetailView:
    if selected_instance_snapshot is None:
        return InstanceDetailView(
            instance_id="",
            label="No instance selected",
            status="unknown",
            adb_serial="",
            last_seen_at="",
            queue_depth=0,
            metadata_lines=["Select one emulator instance to inspect."],
            warning="Emergency stop requested." if global_emergency_stop_active else "",
        )

    instance = _instance_lookup(snapshot).get(selected_instance_snapshot.instance_id)
    if instance is None:
        return InstanceDetailView(
            instance_id=selected_instance_snapshot.instance_id,
            label=selected_instance_snapshot.instance.label,
            status=_status_value(selected_instance_snapshot.instance.status),
            adb_serial=selected_instance_snapshot.instance.adb_serial,
            last_seen_at=str(selected_instance_snapshot.instance.last_seen_at),
            queue_depth=selected_instance_snapshot.queue_depth,
            metadata_lines=["Selected instance missing from console snapshot."],
        )

    metadata_lines = [f"{key}: {value}" for key, value in sorted(instance.metadata.items())]
    context = selected_instance_snapshot.context
    if context is not None:
        metadata_lines.extend(
            [
                f"stop_requested: {context.stop_requested}",
                f"health_check_ok: {context.health_check_ok}",
            ]
        )
        if context.active_task_id:
            metadata_lines.append(f"active_task_id: {context.active_task_id}")
        if context.active_run_id:
            metadata_lines.append(f"active_run_id: {context.active_run_id}")
        if context.profile_binding is not None:
            metadata_lines.append(
                f"profile_binding: {context.profile_binding.display_name} [{context.profile_binding.profile_id}]"
            )
        if context.preview_frame is not None:
            metadata_lines.append(f"preview_frame: {context.preview_frame.image_path}")
        if context.failure_snapshot is not None:
            metadata_lines.append(
                "failure_snapshot: "
                f"{context.failure_snapshot.snapshot_id} "
                f"({context.failure_snapshot.reason.value})"
            )
        for key, value in sorted(context.metadata.items()):
            metadata_lines.append(f"context.{key}: {value}")
    if selected_inspection_result is not None:
        metadata_lines.extend(
            [
                f"inspection.status: {selected_inspection_result.status.value}",
                f"inspection.inspected_at: {selected_inspection_result.inspected_at}",
                f"inspection.health_check_ok: {selected_inspection_result.health_check_ok}",
            ]
        )
        if selected_inspection_result.health_check_message:
            metadata_lines.append(
                f"inspection.health_check_message: {selected_inspection_result.health_check_message}"
            )
        if selected_inspection_result.preview_frame is not None:
            metadata_lines.append(
                f"inspection.preview_frame: {selected_inspection_result.preview_frame.image_path}"
            )
        if selected_inspection_result.failure_snapshot is not None:
            metadata_lines.append(
                "inspection.failure_snapshot: "
                f"{selected_inspection_result.failure_snapshot.snapshot_id}"
            )
        for key, value in sorted(selected_inspection_result.metadata.items()):
            metadata_lines.append(f"inspection.{key}: {value}")

    warning_parts: list[str] = []
    if global_emergency_stop_active:
        warning_parts.append("Emergency stop requested. Waiting for runtime acknowledgement.")
    elif context is not None and context.stop_requested:
        warning_parts.append("Stop requested for this instance.")
    if selected_inspection_result is not None and selected_inspection_result.health_check_ok is False:
        warning_parts.append(
            selected_inspection_result.health_check_message or "Latest health check failed."
        )
    elif context is not None and context.health_check_ok is False:
        warning_parts.append("Latest health check failed.")

    inspection_summary = "No inspection result captured yet."
    if selected_inspection_result is not None:
        inspection_summary = (
            f"{selected_inspection_result.status.value} | "
            f"healthy={selected_inspection_result.health_check_ok}"
        )
        if selected_inspection_result.health_check_message:
            inspection_summary += f" | {selected_inspection_result.health_check_message}"

    return InstanceDetailView(
        instance_id=instance.instance_id,
        label=instance.label,
        status=instance.status,
        adb_serial=instance.adb_serial,
        last_seen_at=instance.last_seen_at,
        queue_depth=selected_instance_snapshot.queue_depth if selected_instance_snapshot is not None else (queue.total_count if queue is not None else 0),
        metadata_lines=metadata_lines,
        warning=" ".join(warning_parts),
        inspection_summary=inspection_summary,
    )


def build_manual_controls(
    *,
    selected_instance_id: str = "",
    selected_instance_label: str = "",
    last_command_result: CommandDispatchResult | None = None,
    last_queue_result: QueueRunResult | None = None,
    global_emergency_stop_active: bool = False,
) -> ManualControlsView:
    last_command_summary, last_command_status = _latest_command_feedback(
        selected_instance_id=selected_instance_id,
        last_command_result=last_command_result,
        last_queue_result=last_queue_result,
    )
    buttons = [
        ManualControlButtonView(
            action_key=spec.action_key,
            label=spec.label,
            command_type=spec.command_type.value,
            requires_instance=spec.requires_instance,
            enabled=(not spec.requires_instance or bool(selected_instance_id))
            and (
                not global_emergency_stop_active
                or spec.command_type
                in {
                    InstanceCommandType.REFRESH,
                    InstanceCommandType.START_QUEUE,
                    InstanceCommandType.EMERGENCY_STOP,
                }
            ),
            help_text=spec.help_text,
        )
        for spec in _ACTION_SPECS.values()
    ]
    if global_emergency_stop_active:
        banner = "已要求全域停止；確認狀態後可重新同步或重新啟動佇列。"
    elif selected_instance_id:
        banner = f"目前手動控制目標：{selected_instance_label or selected_instance_id}。"
    else:
        banner = "請先選擇模擬器，才能使用佇列與互動控制。"
    return ManualControlsView(
        selected_instance_id=selected_instance_id,
        selected_instance_label=selected_instance_label,
        available_actions=buttons,
        enabled=any(button.enabled for button in buttons),
        banner=banner,
        last_command_summary=last_command_summary,
        last_command_status=last_command_status,
    )


def _latest_command_feedback(
    *,
    selected_instance_id: str,
    last_command_result: CommandDispatchResult | None,
    last_queue_result: QueueRunResult | None,
) -> tuple[str, str]:
    if last_queue_result is not None and (
        not selected_instance_id or last_queue_result.instance_id == selected_instance_id
    ):
        statuses = sorted({run.status.value for run in last_queue_result.runs})
        queue_status = ",".join(statuses) if statuses else ("stopped" if last_queue_result.stopped else "idle")
        return (
            last_queue_result.message
            or (
                f"{last_queue_result.instance_id} 的啟動佇列已完成："
                f"{len(last_queue_result.runs)} 次執行，剩餘佇列 {last_queue_result.remaining_queue_depth}"
            ),
            queue_status,
        )
    if last_command_result is not None and (
        not selected_instance_id
        or not last_command_result.instance_ids
        or selected_instance_id in last_command_result.instance_ids
    ):
        return (
            last_command_result.message or f"{last_command_result.command_type.value} 已完成",
            last_command_result.status.value,
        )
    return ("目前尚未送出任何操作指令。", "idle")


def build_console_summary(
    snapshot: ConsoleSnapshot,
    runtime_snapshot: LiveRuntimeSnapshot,
    *,
    selected_instance_id: str = "",
    queue: QueuePaneView | None = None,
    logs: LogPaneView | None = None,
    global_emergency_stop_active: bool = False,
) -> ConsoleSummaryView:
    status_counts = {
        "ready": 0,
        "busy": 0,
        "paused": 0,
        "error": 0,
        "disconnected": 0,
    }
    for instance in snapshot.instances:
        normalized = instance.status.lower()
        if normalized in status_counts:
            status_counts[normalized] += 1

    selected_instance = _instance_lookup(snapshot).get(selected_instance_id)
    selected_snapshot = runtime_snapshot.get_instance_snapshot(selected_instance_id) if selected_instance_id else None
    if not runtime_snapshot.last_sync_ok:
        status_message = f"探索同步失敗：{runtime_snapshot.last_sync_error or '未知錯誤'}"
    elif global_emergency_stop_active:
        status_message = "全域停止啟用中。"
    elif selected_snapshot is not None and selected_snapshot.context is not None and selected_snapshot.context.stop_requested:
        status_message = f"{selected_instance.label if selected_instance is not None else selected_instance_id} 已停止。"
    elif selected_instance is not None:
        status_message = f"{selected_instance.label} 目前為 {selected_instance.status}。"
    else:
        status_message = "請先選擇模擬器，查看 runtime 狀態。"

    return ConsoleSummaryView(
        total_instances=snapshot.instance_count,
        ready_count=status_counts["ready"],
        busy_count=status_counts["busy"],
        paused_count=status_counts["paused"],
        error_count=status_counts["error"],
        disconnected_count=status_counts["disconnected"],
        queued_count=len(runtime_snapshot.queue_items),
        failure_count=logs.failure_count if logs is not None else 0,
        selected_instance_label=selected_instance.label if selected_instance is not None else "",
        selected_instance_status=selected_instance.status if selected_instance is not None else "",
        selected_queue_depth=selected_snapshot.queue_depth if selected_snapshot is not None else (queue.total_count if queue is not None else 0),
        global_status_message=status_message,
    )


def build_instance_list_rows(
    snapshot: ConsoleSnapshot,
    runtime_snapshot: LiveRuntimeSnapshot,
) -> list[InstanceListEntryView]:
    runtime_by_id = {item.instance_id: item for item in runtime_snapshot.instance_snapshots}
    inspection_by_id = _inspection_lookup(runtime_snapshot)
    rows: list[InstanceListEntryView] = []
    for instance in snapshot.instances:
        runtime_item = runtime_by_id.get(instance.instance_id)
        inspection = inspection_by_id.get(instance.instance_id)
        context = runtime_item.context if runtime_item is not None else None
        health_summary = "health unknown"
        if runtime_item is not None:
            if runtime_item.health_check_ok is True:
                health_summary = "healthy"
            elif runtime_item.health_check_ok is False:
                health_summary = "health check failed"
        if inspection is not None and inspection.health_check_message:
            health_summary = f"{health_summary} ({inspection.health_check_message})"
        profile_summary = context.profile_binding.display_name if context is not None and context.profile_binding is not None else ""
        preview_summary = ""
        if inspection is not None and inspection.preview_frame is not None:
            preview_summary = inspection.preview_frame.image_path
        elif runtime_item is not None and runtime_item.preview_frame is not None:
            preview_summary = runtime_item.preview_frame.image_path
        warning = ""
        if context is not None and context.stop_requested:
            warning = "stop requested"
        elif inspection is not None and inspection.health_check_ok is False:
            warning = inspection.health_check_message or "runtime health check failed"
        elif instance.status.lower() == "error":
            warning = "runtime error"
        rows.append(
            InstanceListEntryView(
                instance_id=instance.instance_id,
                label=instance.label,
                status=instance.status,
                subtitle=instance.adb_serial,
                queue_depth=runtime_item.queue_depth if runtime_item is not None else int(instance.metadata.get("queue_depth", 0) or 0),
                active_task_id=context.active_task_id if context is not None and context.active_task_id else "",
                profile_summary=profile_summary,
                health_summary=health_summary,
                preview_summary=preview_summary,
                warning=warning,
            )
        )
    return rows


def build_task_readiness_pane(
    reports: Iterable[TaskReadinessReport],
    builder_inputs: Iterable[TaskRuntimeBuilderInput],
    *,
    selected_instance_snapshot: LiveRuntimeInstanceSnapshot | None = None,
) -> TaskReadinessPaneView:
    report_list = list(reports)
    builder_inputs_by_task = {item.task_id: item for item in builder_inputs}
    selected_task_scope = _selected_task_scope(
        selected_instance_snapshot,
        known_task_ids={report.task_id for report in report_list},
    )
    selected_task_ids = list(selected_task_scope)

    rows = [
        TaskReadinessRowView(
            task_id=report.task_id,
            pack_id=report.pack_id,
            manifest_path=builder_inputs_by_task.get(report.task_id).manifest_path
            if report.task_id in builder_inputs_by_task
            else "",
            builder_state=report.builder_readiness_state.value,
            implementation_state=report.implementation_readiness_state.value,
            builder_blockers=[
                _format_requirement_summary(requirement)
                for requirement in report.builder_requirements
                if requirement.blocking and not requirement.satisfied
            ],
            implementation_blockers=[
                _format_requirement_summary(requirement)
                for requirement in report.implementation_requirements
                if requirement.blocking and not requirement.satisfied
            ],
            warnings=[
                _format_requirement_summary(requirement)
                for requirement in report.warning_requirements
            ],
            required_anchors=list(builder_inputs_by_task.get(report.task_id).required_anchors)
            if report.task_id in builder_inputs_by_task
            else [],
            fixture_profile_paths=list(builder_inputs_by_task.get(report.task_id).fixture_profile_paths)
            if report.task_id in builder_inputs_by_task
            else [],
            asset_requirement_ids=list(builder_inputs_by_task.get(report.task_id).asset_requirement_ids)
            if report.task_id in builder_inputs_by_task
            else [],
            runtime_requirement_ids=list(builder_inputs_by_task.get(report.task_id).runtime_requirement_ids)
            if report.task_id in builder_inputs_by_task
            else [],
            calibration_requirement_ids=list(builder_inputs_by_task.get(report.task_id).calibration_requirement_ids)
            if report.task_id in builder_inputs_by_task
            else [],
            foundation_requirement_ids=list(builder_inputs_by_task.get(report.task_id).foundation_requirement_ids)
            if report.task_id in builder_inputs_by_task
            else [],
            is_related_to_selected_instance=report.task_id in selected_task_scope,
            scope_reasons=list(selected_task_scope.get(report.task_id, [])),
        )
        for report in report_list
    ]
    rows.sort(
        key=lambda row: (
            not row.is_related_to_selected_instance,
            "active" not in row.scope_reasons,
            "queued" not in row.scope_reasons,
            row.task_id,
        )
    )

    return TaskReadinessPaneView(
        total_tasks=len(report_list),
        builder_ready_count=sum(1 for report in report_list if report.builder_readiness_state.value == "ready"),
        builder_blocked_count=sum(1 for report in report_list if report.builder_readiness_state.value != "ready"),
        implementation_ready_count=sum(
            1 for report in report_list if report.implementation_readiness_state.value == "ready"
        ),
        implementation_blocked_count=sum(
            1 for report in report_list if report.implementation_readiness_state.value != "ready"
        ),
        blocked_by_asset_count=sum(
            1
            for report in report_list
            if "blocked_by_asset"
            in {report.builder_readiness_state.value, report.implementation_readiness_state.value}
        ),
        blocked_by_runtime_count=sum(
            1
            for report in report_list
            if "blocked_by_runtime"
            in {report.builder_readiness_state.value, report.implementation_readiness_state.value}
        ),
        blocked_by_calibration_count=sum(
            1
            for report in report_list
            if "blocked_by_calibration"
            in {report.builder_readiness_state.value, report.implementation_readiness_state.value}
        ),
        blocked_by_foundation_count=sum(
            1
            for report in report_list
            if "blocked_by_foundation"
            in {report.builder_readiness_state.value, report.implementation_readiness_state.value}
        ),
        selected_task_ids=selected_task_ids,
        rows=rows,
    )


def build_operator_console_state(
    snapshot: ConsoleSnapshot,
    runtime_snapshot: LiveRuntimeSnapshot,
    vision_state: VisionToolingState,
    *,
    selected_instance_id: str = "",
    global_emergency_stop_active: bool = False,
    task_readiness_reports: Iterable[TaskReadinessReport] = (),
    task_runtime_builder_inputs: Iterable[TaskRuntimeBuilderInput] = (),
    claim_rewards: ClaimRewardsPaneView | None = None,
) -> OperatorConsoleState:
    resolved_instance_id = selected_instance_id
    if not resolved_instance_id and runtime_snapshot.instance_snapshots:
        resolved_instance_id = runtime_snapshot.instance_snapshots[0].instance_id
    if not resolved_instance_id and snapshot.instances:
        resolved_instance_id = snapshot.instances[0].instance_id

    selected_snapshot = runtime_snapshot.get_instance_snapshot(resolved_instance_id) if resolved_instance_id else None
    selected_inspection = _inspection_lookup(runtime_snapshot).get(resolved_instance_id)
    queue = build_queue_pane(runtime_snapshot, selected_instance_id=resolved_instance_id)
    logs = build_log_pane(runtime_snapshot.recent_events, selected_instance_id=resolved_instance_id)
    instance = _instance_lookup(snapshot).get(resolved_instance_id)
    manual_controls = build_manual_controls(
        selected_instance_id=resolved_instance_id,
        selected_instance_label=instance.label if instance is not None else "",
        last_command_result=runtime_snapshot.last_command_result,
        last_queue_result=runtime_snapshot.last_queue_result,
        global_emergency_stop_active=global_emergency_stop_active,
    )
    detail = build_instance_detail(
        snapshot,
        selected_instance_snapshot=selected_snapshot,
        selected_inspection_result=selected_inspection,
        queue=queue,
        global_emergency_stop_active=global_emergency_stop_active,
    )
    summary = build_console_summary(
        snapshot,
        runtime_snapshot,
        selected_instance_id=resolved_instance_id,
        queue=queue,
        logs=logs,
        global_emergency_stop_active=global_emergency_stop_active,
    )
    instance_rows = build_instance_list_rows(snapshot, runtime_snapshot)
    task_readiness = build_task_readiness_pane(
        task_readiness_reports,
        task_runtime_builder_inputs,
        selected_instance_snapshot=selected_snapshot,
    )
    return OperatorConsoleState(
        snapshot=snapshot,
        runtime_snapshot=runtime_snapshot,
        selected_instance_snapshot=selected_snapshot,
        selected_inspection_result=selected_inspection,
        summary=summary,
        instance_rows=instance_rows,
        selected_instance_id=resolved_instance_id,
        detail=detail,
        queue=queue,
        logs=logs,
        manual_controls=manual_controls,
        task_readiness=task_readiness,
        claim_rewards=claim_rewards or ClaimRewardsPaneView(),
        vision=vision_state,
        global_emergency_stop_active=global_emergency_stop_active,
    )


def create_instance_command(
    command_type: InstanceCommandType,
    *,
    instance_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> InstanceCommand:
    return InstanceCommand(
        command_type=command_type,
        instance_id=instance_id,
        payload=dict(payload or {}),
    )


def build_manual_control_command(
    action_key: str,
    *,
    instance_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> InstanceCommand:
    spec = _ACTION_SPECS[action_key]
    if spec.requires_instance and not instance_id:
        raise ValueError(f"{action_key} requires an instance_id")
    return create_instance_command(
        spec.command_type,
        instance_id=instance_id,
        payload=payload,
    )


def _instance_lookup(snapshot: ConsoleSnapshot) -> dict[str, InstanceCardView]:
    return {instance.instance_id: instance for instance in snapshot.instances}


def _inspection_lookup(runtime_snapshot: LiveRuntimeSnapshot) -> dict[str, RuntimeInspectionResult]:
    return {inspection.instance_id: inspection for inspection in runtime_snapshot.last_inspection_results}


def _event_name(event: AppEvent | LiveRuntimeEventRecord) -> str:
    return str(event.name)


def _event_payload(event: AppEvent | LiveRuntimeEventRecord) -> dict[str, Any]:
    return dict(event.payload)


def _event_instance_id(event: AppEvent | LiveRuntimeEventRecord) -> str:
    if isinstance(event, LiveRuntimeEventRecord):
        return str(event.instance_id)
    return str(event.payload.get("instance_id", ""))


def _event_emitted_at(event: AppEvent | LiveRuntimeEventRecord) -> object:
    return event.emitted_at


def _selected_task_scope(
    selected_instance_snapshot: LiveRuntimeInstanceSnapshot | None,
    *,
    known_task_ids: set[str],
) -> dict[str, list[str]]:
    if selected_instance_snapshot is None:
        return {}
    scope: dict[str, list[str]] = {}
    context = selected_instance_snapshot.context
    if context is not None and context.active_task_id:
        scope[str(context.active_task_id)] = ["active"]
    for queue_item in selected_instance_snapshot.queue_items:
        reasons = scope.setdefault(queue_item.task_id, [])
        if "queued" not in reasons:
            reasons.append("queued")
    return {
        task_id: reasons
        for task_id, reasons in scope.items()
        if task_id in known_task_ids
    }


def _format_requirement_summary(requirement) -> str:
    summary = f"{requirement.domain.value} | {requirement.requirement_id} | {requirement.summary}"
    if requirement.details:
        summary += f" | {requirement.details}"
    return summary
