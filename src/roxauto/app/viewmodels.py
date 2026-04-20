from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from roxauto.core.commands import CommandDispatchResult, InstanceCommand, InstanceCommandType
from roxauto.core.events import AppEvent, EVENT_INSTANCE_ERROR, EVENT_TASK_FAILURE_SNAPSHOT_RECORDED
from roxauto.core.models import InstanceState
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import QueueRunResult
from roxauto.emulator import LiveRuntimeEventRecord, LiveRuntimeInstanceSnapshot, LiveRuntimeSnapshot
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
class OperatorConsoleState:
    snapshot: ConsoleSnapshot
    runtime_snapshot: LiveRuntimeSnapshot
    selected_instance_snapshot: LiveRuntimeInstanceSnapshot | None
    summary: ConsoleSummaryView
    instance_rows: list[InstanceListEntryView]
    selected_instance_id: str
    detail: InstanceDetailView
    queue: QueuePaneView
    logs: LogPaneView
    manual_controls: ManualControlsView
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
        label="Refresh",
        command_type=InstanceCommandType.REFRESH,
        requires_instance=False,
        help_text="Refresh environment and poll runtime health.",
    ),
    "start_queue": ManualActionSpec(
        action_key="start_queue",
        label="Start Queue",
        command_type=InstanceCommandType.START_QUEUE,
        requires_instance=True,
        help_text="Resume queued work on the selected instance.",
    ),
    "pause": ManualActionSpec(
        action_key="pause",
        label="Pause",
        command_type=InstanceCommandType.PAUSE,
        requires_instance=True,
        help_text="Pause active work on the selected instance.",
    ),
    "stop": ManualActionSpec(
        action_key="stop",
        label="Stop",
        command_type=InstanceCommandType.STOP,
        requires_instance=True,
        help_text="Stop the current task on the selected instance.",
    ),
    "tap": ManualActionSpec(
        action_key="tap",
        label="Tap",
        command_type=InstanceCommandType.TAP,
        requires_instance=True,
        help_text="Send one tap to the selected instance.",
    ),
    "swipe": ManualActionSpec(
        action_key="swipe",
        label="Swipe",
        command_type=InstanceCommandType.SWIPE,
        requires_instance=True,
        help_text="Send one swipe gesture to the selected instance.",
    ),
    "input_text": ManualActionSpec(
        action_key="input_text",
        label="Input Text",
        command_type=InstanceCommandType.INPUT_TEXT,
        requires_instance=True,
        help_text="Send text input to the active control.",
    ),
    "emergency_stop": ManualActionSpec(
        action_key="emergency_stop",
        label="Emergency Stop",
        command_type=InstanceCommandType.EMERGENCY_STOP,
        requires_instance=False,
        help_text="Request a global emergency stop across all instances.",
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
    for instance in runtime_snapshot.instances:
        snapshot = by_id.get(instance.instance_id)
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
    return QueuePaneView(
        selected_instance_id=selected_instance_id,
        total_count=len(items),
        items=items,
        empty_message=empty_message,
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

    warning_parts: list[str] = []
    if global_emergency_stop_active:
        warning_parts.append("Emergency stop requested. Waiting for runtime acknowledgement.")
    elif context is not None and context.stop_requested:
        warning_parts.append("Stop requested for this instance.")
    if context is not None and context.health_check_ok is False:
        warning_parts.append("Latest health check failed.")

    return InstanceDetailView(
        instance_id=instance.instance_id,
        label=instance.label,
        status=instance.status,
        adb_serial=instance.adb_serial,
        last_seen_at=instance.last_seen_at,
        queue_depth=selected_instance_snapshot.queue_depth if selected_instance_snapshot is not None else (queue.total_count if queue is not None else 0),
        metadata_lines=metadata_lines,
        warning=" ".join(warning_parts),
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
        banner = "Emergency stop requested. Refresh or Start Queue after verification."
    elif selected_instance_id:
        banner = f"Manual controls target {selected_instance_label or selected_instance_id}."
    else:
        banner = "Select an instance to enable queue and interaction controls."
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
        queue_status = ",".join(statuses) if statuses else "idle"
        return (
            last_queue_result.message
            or (
                f"start_queue completed for {last_queue_result.instance_id}: "
                f"{len(last_queue_result.runs)} run(s), remaining={last_queue_result.remaining_queue_depth}"
            ),
            queue_status,
        )
    if last_command_result is not None and (
        not selected_instance_id
        or not last_command_result.instance_ids
        or selected_instance_id in last_command_result.instance_ids
    ):
        return (
            last_command_result.message or f"{last_command_result.command_type.value} completed",
            last_command_result.status.value,
        )
    return ("No operator command dispatched yet.", "idle")


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
    if global_emergency_stop_active:
        status_message = "Global emergency stop is active."
    elif selected_snapshot is not None and selected_snapshot.context is not None and selected_snapshot.context.stop_requested:
        status_message = f"{selected_instance.label if selected_instance is not None else selected_instance_id} is stopped."
    elif selected_instance is not None:
        status_message = f"{selected_instance.label} is {selected_instance.status}."
    else:
        status_message = "Select an instance to inspect runtime state."

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
    rows: list[InstanceListEntryView] = []
    for instance in snapshot.instances:
        runtime_item = runtime_by_id.get(instance.instance_id)
        context = runtime_item.context if runtime_item is not None else None
        health_summary = "health unknown"
        if runtime_item is not None:
            if runtime_item.health_check_ok is True:
                health_summary = "healthy"
            elif runtime_item.health_check_ok is False:
                health_summary = "health check failed"
        profile_summary = context.profile_binding.display_name if context is not None and context.profile_binding is not None else ""
        preview_summary = runtime_item.preview_frame.image_path if runtime_item is not None and runtime_item.preview_frame is not None else ""
        warning = ""
        if context is not None and context.stop_requested:
            warning = "stop requested"
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


def build_operator_console_state(
    snapshot: ConsoleSnapshot,
    runtime_snapshot: LiveRuntimeSnapshot,
    vision_state: VisionToolingState,
    *,
    selected_instance_id: str = "",
    global_emergency_stop_active: bool = False,
) -> OperatorConsoleState:
    resolved_instance_id = selected_instance_id
    if not resolved_instance_id and runtime_snapshot.instance_snapshots:
        resolved_instance_id = runtime_snapshot.instance_snapshots[0].instance_id
    if not resolved_instance_id and snapshot.instances:
        resolved_instance_id = snapshot.instances[0].instance_id

    selected_snapshot = runtime_snapshot.get_instance_snapshot(resolved_instance_id) if resolved_instance_id else None
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
    return OperatorConsoleState(
        snapshot=snapshot,
        runtime_snapshot=runtime_snapshot,
        selected_instance_snapshot=selected_snapshot,
        summary=summary,
        instance_rows=instance_rows,
        selected_instance_id=resolved_instance_id,
        detail=detail,
        queue=queue,
        logs=logs,
        manual_controls=manual_controls,
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
