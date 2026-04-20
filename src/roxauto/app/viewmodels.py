from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from roxauto.core.commands import InstanceCommand, InstanceCommandType
from roxauto.core.events import (
    AppEvent,
    EVENT_INSTANCE_ERROR,
    EVENT_TASK_FAILURE_SNAPSHOT_RECORDED,
)
from roxauto.core.models import InstanceRuntimeContext, InstanceState, VisionMatch
from roxauto.core.queue import QueuedTask
from roxauto.vision import (
    AnchorRepository,
    CalibrationProfile,
    MatchStatus,
    ReplayScript,
    TemplateMatchResult,
)


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
class TemplateAnchorView:
    anchor_id: str
    label: str
    template_path: str
    confidence_threshold: float
    match_region: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    override_summary: str = ""


@dataclass(slots=True)
class PreviewPaneView:
    repository_id: str
    source_image: str
    selected_anchor_id: str
    match_status: str
    confidence: float
    message: str
    context_lines: list[str] = field(default_factory=list)
    candidate_summaries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CalibrationPaneView:
    profile_id: str
    instance_id: str
    emulator_name: str
    scale_summary: str
    offset_summary: str
    crop_region: str
    anchor_rows: list[TemplateAnchorView] = field(default_factory=list)


@dataclass(slots=True)
class RecordingActionView:
    action_id: str
    action_type: str
    target: str
    payload_summary: str
    occurred_at: str


@dataclass(slots=True)
class RecordingPaneView:
    script_id: str
    name: str
    version: str
    action_count: int
    action_rows: list[RecordingActionView] = field(default_factory=list)


@dataclass(slots=True)
class AnchorInspectionView:
    repository_id: str
    display_name: str
    version: str
    anchor_rows: list[TemplateAnchorView] = field(default_factory=list)
    selected_anchor_id: str = ""
    selected_anchor_summary: str = ""


@dataclass(slots=True)
class FailureInspectionView:
    source_image: str
    status: str
    message: str
    best_candidate_summary: str
    candidate_summaries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VisionWorkspaceSnapshot:
    repository_root: str
    preview: PreviewPaneView
    calibration: CalibrationPaneView
    recording: RecordingPaneView
    anchors: AnchorInspectionView
    failure: FailureInspectionView


@dataclass(slots=True)
class OperatorConsoleState:
    snapshot: ConsoleSnapshot
    summary: ConsoleSummaryView
    instance_rows: list[InstanceListEntryView]
    selected_instance_id: str
    detail: InstanceDetailView
    queue: QueuePaneView
    logs: LogPaneView
    manual_controls: ManualControlsView
    vision: VisionWorkspaceSnapshot
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


def _format_region(region: tuple[int, int, int, int] | None) -> str:
    if not region:
        return "n/a"
    return f"{region[0]},{region[1]},{region[2]},{region[3]}"


def _format_payload_summary(payload: dict[str, Any]) -> str:
    if not payload:
        return "{}"
    return ", ".join(f"{key}={value!r}" for key, value in sorted(payload.items()))


def _format_match(match: VisionMatch) -> str:
    return (
        f"{match.anchor_id} | confidence={match.confidence:.3f} | "
        f"bbox={match.bbox} | source={match.source_image}"
    )


def _anchor_view(
    repository: AnchorRepository | None,
    anchor_id: str,
    override_summary: str = "",
) -> TemplateAnchorView:
    if repository is None or not anchor_id:
        return TemplateAnchorView(
            anchor_id=anchor_id,
            label="",
            template_path="",
            confidence_threshold=0.0,
            match_region="n/a",
            override_summary=override_summary,
        )
    anchor = repository.get_anchor(anchor_id)
    return TemplateAnchorView(
        anchor_id=anchor.anchor_id,
        label=anchor.label,
        template_path=anchor.template_path,
        confidence_threshold=anchor.confidence_threshold,
        match_region=_format_region(anchor.match_region),
        tags=list(anchor.tags),
        description=anchor.description,
        override_summary=override_summary,
    )


def _default_selected_anchor_id(
    repository: AnchorRepository | None,
    match_result: TemplateMatchResult | None,
) -> str:
    if match_result and match_result.expected_anchor_id:
        return match_result.expected_anchor_id
    if repository is not None:
        anchors = repository.list_anchors()
        if anchors:
            return anchors[0].anchor_id
    return ""


def _instance_lookup(snapshot: ConsoleSnapshot) -> dict[str, InstanceCardView]:
    return {instance.instance_id: instance for instance in snapshot.instances}


def _runtime_context_lookup(
    runtime_contexts: dict[str, InstanceRuntimeContext | None] | None,
) -> dict[str, InstanceRuntimeContext]:
    if not runtime_contexts:
        return {}
    return {
        instance_id: context
        for instance_id, context in runtime_contexts.items()
        if context is not None
    }


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
    instances: Iterable[InstanceState],
    *,
    adb_path: str,
    packages: dict[str, bool] | None = None,
    runtime_contexts: dict[str, InstanceRuntimeContext | None] | None = None,
) -> ConsoleSnapshot:
    contexts = runtime_contexts or {}
    cards: list[InstanceCardView] = []
    for instance in instances:
        metadata = dict(instance.metadata)
        context = contexts.get(instance.instance_id)
        if context is not None:
            metadata["queue_depth"] = context.queue_depth
            metadata["stop_requested"] = context.stop_requested
            if context.health_check_ok is not None:
                metadata["health_check_ok"] = context.health_check_ok
            if context.profile_binding is not None:
                metadata["profile_id"] = context.profile_binding.profile_id
            if context.preview_frame is not None:
                metadata["preview_frame"] = context.preview_frame.image_path
            if context.failure_snapshot is not None:
                metadata["failure_snapshot"] = context.failure_snapshot.snapshot_id
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
    queue_items: Iterable[QueuedTask],
    *,
    selected_instance_id: str = "",
) -> QueuePaneView:
    filtered = [
        item
        for item in queue_items
        if not selected_instance_id or item.instance_id == selected_instance_id
    ]
    items = [
        QueueItemView(
            queue_id=item.queue_id,
            task_id=item.task_id,
            task_name=item.spec.name,
            priority=item.priority,
            recovery_policy=(
                item.spec.manifest.recovery_policy
                if item.spec.manifest is not None
                else "default"
            ),
            enqueued_at=str(item.enqueued_at),
            requirements_summary=", ".join(item.spec.manifest.requires)
            if item.spec.manifest is not None and item.spec.manifest.requires
            else "",
        )
        for item in filtered
    ]
    empty_message = "No queued work for the selected instance."
    if not selected_instance_id:
        empty_message = "No queued work available."
    return QueuePaneView(
        selected_instance_id=selected_instance_id,
        total_count=len(items),
        items=items,
        empty_message=empty_message,
    )


def build_log_pane(
    events: Iterable[AppEvent],
    *,
    selected_instance_id: str = "",
) -> LogPaneView:
    event_list = list(events)
    filtered_events = [
        event
        for event in event_list
        if not selected_instance_id or str(event.payload.get("instance_id", "")) == selected_instance_id
    ]
    entries = [_build_log_entry(event) for event in reversed(filtered_events)]
    failure_count = sum(1 for entry in entries if entry.level == "error")
    empty_message = "No operator activity for the selected instance."
    if not selected_instance_id:
        empty_message = "No operator activity yet."
    return LogPaneView(
        total_count=len(event_list),
        filtered_count=len(filtered_events),
        failure_count=failure_count,
        entries=entries,
        empty_message=empty_message,
        latest_summary=entries[0].summary if entries else empty_message,
    )


def _build_log_entry(event: AppEvent) -> LogEntryView:
    payload = event.payload
    instance_id = str(payload.get("instance_id", ""))
    level = "info"
    if event.name in {EVENT_TASK_FAILURE_SNAPSHOT_RECORDED, EVENT_INSTANCE_ERROR}:
        level = "error"
    elif str(payload.get("status", "")).lower() in {"failed", "aborted"}:
        level = "error"

    summary_parts = [event.name]
    for key in ("message", "task_id", "status", "command_type", "snapshot_id"):
        value = payload.get(key)
        if value:
            summary_parts.append(f"{key}={value}")

    return LogEntryView(
        event_name=event.name,
        emitted_at=str(event.emitted_at),
        level=level,
        instance_id=instance_id,
        summary=" | ".join(summary_parts),
    )


def build_instance_detail(
    snapshot: ConsoleSnapshot,
    *,
    selected_instance_id: str = "",
    queue: QueuePaneView | None = None,
    runtime_context: InstanceRuntimeContext | None = None,
    global_emergency_stop_active: bool = False,
) -> InstanceDetailView:
    instance = _instance_lookup(snapshot).get(selected_instance_id)
    if instance is None:
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

    metadata_lines = [f"{key}: {value}" for key, value in sorted(instance.metadata.items())]
    if runtime_context is not None:
        metadata_lines.extend(
            [
                f"stop_requested: {runtime_context.stop_requested}",
                f"health_check_ok: {runtime_context.health_check_ok}",
            ]
        )
        if runtime_context.active_task_id:
            metadata_lines.append(f"active_task_id: {runtime_context.active_task_id}")
        if runtime_context.active_run_id:
            metadata_lines.append(f"active_run_id: {runtime_context.active_run_id}")
        if runtime_context.profile_binding is not None:
            metadata_lines.append(
                f"profile_binding: {runtime_context.profile_binding.display_name} [{runtime_context.profile_binding.profile_id}]"
            )
        if runtime_context.preview_frame is not None:
            metadata_lines.append(f"preview_frame: {runtime_context.preview_frame.image_path}")
        if runtime_context.failure_snapshot is not None:
            metadata_lines.append(
                "failure_snapshot: "
                f"{runtime_context.failure_snapshot.snapshot_id} "
                f"({runtime_context.failure_snapshot.reason.value})"
            )
    warning_parts: list[str] = []
    if global_emergency_stop_active:
        warning_parts.append("Emergency stop requested. Waiting for runtime acknowledgement.")
    elif runtime_context is not None and runtime_context.stop_requested:
        warning_parts.append("Stop requested for this instance.")
    if runtime_context is not None and runtime_context.health_check_ok is False:
        warning_parts.append("Latest health check failed.")
    warning = " ".join(warning_parts)
    return InstanceDetailView(
        instance_id=instance.instance_id,
        label=instance.label,
        status=instance.status,
        adb_serial=instance.adb_serial,
        last_seen_at=instance.last_seen_at,
        queue_depth=runtime_context.queue_depth if runtime_context is not None else (queue.total_count if queue is not None else 0),
        metadata_lines=metadata_lines,
        warning=warning,
    )


def build_manual_controls(
    *,
    selected_instance_id: str = "",
    selected_instance_label: str = "",
    events: Iterable[AppEvent] = (),
    global_emergency_stop_active: bool = False,
) -> ManualControlsView:
    last_command_summary, last_command_status = _latest_command_feedback(
        events,
        selected_instance_id=selected_instance_id,
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
    events: Iterable[AppEvent],
    *,
    selected_instance_id: str = "",
) -> tuple[str, str]:
    for event in reversed(list(events)):
        payload_instance_id = str(event.payload.get("instance_id", ""))
        if selected_instance_id and payload_instance_id not in {"", selected_instance_id}:
            continue
        if event.name == "operator.command.dispatched":
            return (
                str(event.payload.get("message", "Command dispatched.")),
                str(event.payload.get("status", "completed")),
            )
        if event.name == "operator.refresh.completed":
            return (
                str(event.payload.get("message", "Runtime refresh completed.")),
                "completed",
            )
        if event.name == "command.executed":
            command_type = str(event.payload.get("command_type", "command"))
            status = str(event.payload.get("status", "completed"))
            return (f"{command_type} {status}", status)
    return ("No operator command dispatched yet.", "idle")


def build_console_summary(
    snapshot: ConsoleSnapshot,
    *,
    selected_instance_id: str = "",
    queue: QueuePaneView | None = None,
    logs: LogPaneView | None = None,
    runtime_contexts: dict[str, InstanceRuntimeContext | None] | None = None,
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

    contexts = _runtime_context_lookup(runtime_contexts)
    selected_instance = _instance_lookup(snapshot).get(selected_instance_id)
    selected_context = contexts.get(selected_instance_id)
    if global_emergency_stop_active:
        status_message = "Global emergency stop is active."
    elif selected_context is not None and selected_context.stop_requested:
        status_message = f"{selected_instance.label if selected_instance else selected_instance_id} is stopped."
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
        queued_count=queue.total_count if queue is not None else 0,
        failure_count=logs.failure_count if logs is not None else 0,
        selected_instance_label=selected_instance.label if selected_instance is not None else "",
        selected_instance_status=selected_instance.status if selected_instance is not None else "",
        selected_queue_depth=selected_context.queue_depth if selected_context is not None else (queue.total_count if queue is not None else 0),
        global_status_message=status_message,
    )


def build_instance_list_rows(
    snapshot: ConsoleSnapshot,
    *,
    runtime_contexts: dict[str, InstanceRuntimeContext | None] | None = None,
) -> list[InstanceListEntryView]:
    contexts = _runtime_context_lookup(runtime_contexts)
    rows: list[InstanceListEntryView] = []
    for instance in snapshot.instances:
        context = contexts.get(instance.instance_id)
        health_summary = "health unknown"
        if context is not None:
            if context.health_check_ok is True:
                health_summary = "healthy"
            elif context.health_check_ok is False:
                health_summary = "health check failed"
        profile_summary = ""
        if context is not None and context.profile_binding is not None:
            profile_summary = context.profile_binding.display_name
        preview_summary = ""
        if context is not None and context.preview_frame is not None:
            preview_summary = context.preview_frame.image_path
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
                queue_depth=context.queue_depth if context is not None else int(instance.metadata.get("queue_depth", 0) or 0),
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
    vision_snapshot: VisionWorkspaceSnapshot,
    *,
    queue_items: Iterable[QueuedTask] = (),
    events: Iterable[AppEvent] = (),
    selected_instance_id: str = "",
    runtime_contexts: dict[str, InstanceRuntimeContext | None] | None = None,
    global_emergency_stop_active: bool = False,
) -> OperatorConsoleState:
    resolved_instance_id = selected_instance_id
    if not resolved_instance_id and snapshot.instances:
        resolved_instance_id = snapshot.instances[0].instance_id

    contexts = runtime_contexts or {}
    queue = build_queue_pane(queue_items, selected_instance_id=resolved_instance_id)
    logs = build_log_pane(events, selected_instance_id=resolved_instance_id)
    instance = _instance_lookup(snapshot).get(resolved_instance_id)
    runtime_context = contexts.get(resolved_instance_id)
    manual_controls = build_manual_controls(
        selected_instance_id=resolved_instance_id,
        selected_instance_label=instance.label if instance is not None else "",
        events=events,
        global_emergency_stop_active=global_emergency_stop_active,
    )
    detail = build_instance_detail(
        snapshot,
        selected_instance_id=resolved_instance_id,
        queue=queue,
        runtime_context=runtime_context,
        global_emergency_stop_active=global_emergency_stop_active,
    )
    summary = build_console_summary(
        snapshot,
        selected_instance_id=resolved_instance_id,
        queue=queue,
        logs=logs,
        runtime_contexts=contexts,
        global_emergency_stop_active=global_emergency_stop_active,
    )
    instance_rows = build_instance_list_rows(snapshot, runtime_contexts=contexts)
    return OperatorConsoleState(
        snapshot=snapshot,
        summary=summary,
        instance_rows=instance_rows,
        selected_instance_id=resolved_instance_id,
        detail=detail,
        queue=queue,
        logs=logs,
        manual_controls=manual_controls,
        vision=vision_snapshot,
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


def build_vision_workspace_snapshot(
    *,
    repository: AnchorRepository | None = None,
    calibration_profile: CalibrationProfile | None = None,
    replay_script: ReplayScript | None = None,
    match_result: TemplateMatchResult | None = None,
    source_image: str = "",
    failure_message: str = "",
    preview_context_lines: Iterable[str] = (),
) -> VisionWorkspaceSnapshot:
    repository_root = str(repository.root) if repository is not None else ""
    anchors = repository.list_anchors() if repository is not None else []
    selected_anchor_id = _default_selected_anchor_id(repository, match_result)

    anchor_rows = [
        _anchor_view(
            repository,
            anchor.anchor_id,
            override_summary=(
                _format_payload_summary(calibration_profile.anchor_overrides.get(anchor.anchor_id, {}))
                if calibration_profile is not None
                else ""
            ),
        )
        for anchor in anchors
    ]

    if match_result is not None:
        best_candidate = match_result.best_candidate()
        candidate_summaries = [_format_match(candidate) for candidate in match_result.candidates]
        preview = PreviewPaneView(
            repository_id=repository.repository_id if repository is not None else "",
            source_image=match_result.source_image or source_image,
            selected_anchor_id=selected_anchor_id,
            match_status=match_result.status.value,
            confidence=best_candidate.confidence if best_candidate is not None else 0.0,
            message=match_result.message,
            context_lines=list(preview_context_lines),
            candidate_summaries=candidate_summaries,
        )
        failure = FailureInspectionView(
            source_image=match_result.source_image or source_image,
            status=match_result.status.value,
            message=match_result.message or failure_message,
            best_candidate_summary=_format_match(best_candidate) if best_candidate is not None else "no candidate",
            candidate_summaries=candidate_summaries,
        )
    else:
        preview = PreviewPaneView(
            repository_id=repository.repository_id if repository is not None else "",
            source_image=source_image,
            selected_anchor_id=selected_anchor_id,
            match_status=MatchStatus.MISSED.value,
            confidence=0.0,
            message=failure_message or "Preview pipeline not connected yet.",
            context_lines=list(preview_context_lines),
            candidate_summaries=[],
        )
        failure = FailureInspectionView(
            source_image=source_image,
            status=MatchStatus.MISSED.value,
            message=failure_message or "No failure snapshot available.",
            best_candidate_summary="no candidate",
            candidate_summaries=[],
        )

    calibration = CalibrationPaneView(
        profile_id=calibration_profile.profile_id if calibration_profile is not None else "default",
        instance_id=calibration_profile.instance_id if calibration_profile is not None else "",
        emulator_name=calibration_profile.emulator_name if calibration_profile is not None else "mumu",
        scale_summary=(
            f"{calibration_profile.scale_x:.2f} x {calibration_profile.scale_y:.2f}"
            if calibration_profile is not None
            else "1.00 x 1.00"
        ),
        offset_summary=(
            f"{calibration_profile.offset_x}, {calibration_profile.offset_y}"
            if calibration_profile is not None
            else "0, 0"
        ),
        crop_region=_format_region(calibration_profile.crop_region) if calibration_profile is not None else "n/a",
        anchor_rows=anchor_rows,
    )

    recording_actions: list[RecordingActionView] = []
    if replay_script is not None:
        recording_actions = [
            RecordingActionView(
                action_id=action.action_id,
                action_type=action.action_type.value,
                target=action.target,
                payload_summary=_format_payload_summary(action.payload),
                occurred_at=action.occurred_at.isoformat(),
            )
            for action in replay_script.actions
        ]
    recording = RecordingPaneView(
        script_id=replay_script.script_id if replay_script is not None else "sample.script",
        name=replay_script.name if replay_script is not None else "Sample recording",
        version=replay_script.version if replay_script is not None else "0.1.0",
        action_count=len(recording_actions),
        action_rows=recording_actions,
    )

    selected_anchor_summary = ""
    if repository is not None and selected_anchor_id:
        try:
            selected_anchor = repository.get_anchor(selected_anchor_id)
            override_summary = (
                _format_payload_summary(calibration_profile.anchor_overrides.get(selected_anchor.anchor_id, {}))
                if calibration_profile is not None
                else ""
            )
            selected_anchor_summary = (
                f"{selected_anchor.label} | template={selected_anchor.template_path} | "
                f"threshold={selected_anchor.confidence_threshold:.2f} | "
                f"region={_format_region(selected_anchor.match_region)} | "
                f"override={override_summary or 'none'}"
            )
        except KeyError:
            selected_anchor_summary = "selected anchor not found"

    anchors_view = AnchorInspectionView(
        repository_id=repository.repository_id if repository is not None else "",
        display_name=repository.display_name if repository is not None else "No template repository loaded",
        version=repository.manifest.version if repository is not None else "0.0.0",
        anchor_rows=anchor_rows,
        selected_anchor_id=selected_anchor_id,
        selected_anchor_summary=selected_anchor_summary,
    )

    return VisionWorkspaceSnapshot(
        repository_root=repository_root,
        preview=preview,
        calibration=calibration,
        recording=recording,
        anchors=anchors_view,
        failure=failure,
    )
