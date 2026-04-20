from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from roxauto.app.viewmodels import (
    ConsoleSnapshot,
    build_console_snapshot,
    build_manual_control_command,
    build_operator_console_state,
    build_vision_workspace_snapshot,
)
from roxauto.core.commands import CommandRouter, InstanceCommandType
from roxauto.core.events import AppEvent
from roxauto.core.models import (
    StopCondition,
    StopConditionKind,
    TaskManifest,
    TaskSpec,
    VisionMatch,
)
from roxauto.core.queue import QueuedTask
from roxauto.core.runtime import TaskStep, step_success
from roxauto.core.serde import to_primitive
from roxauto.core.time import utc_now
from roxauto.doctor import build_doctor_report
from roxauto.vision import (
    AnchorRepository,
    CalibrationProfile,
    RecordingAction,
    RecordingActionType,
    ReplayScript,
    TemplateMatchResult,
    build_match_result,
)

if TYPE_CHECKING:
    from typing import Any


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sample_repository() -> AnchorRepository | None:
    common_root = _workspace_root() / "assets" / "templates" / "common"
    if (common_root / "manifest.json").exists():
        return AnchorRepository.load(common_root)
    discovered = AnchorRepository.discover(_workspace_root() / "assets" / "templates")
    return discovered[0] if discovered else None


def _sample_calibration_profile() -> CalibrationProfile:
    return CalibrationProfile(
        profile_id="sample.default",
        instance_id="mumu-0",
        emulator_name="mumu",
        scale_x=1.0,
        scale_y=1.0,
        offset_x=0,
        offset_y=0,
        crop_region=(0, 0, 1920, 1080),
        anchor_overrides={"common.close_button": {"confidence_threshold": 0.90}},
    )


def _sample_replay_script() -> ReplayScript:
    return ReplayScript(
        script_id="sample.recording",
        name="Sample Calibration Walkthrough",
        version="0.1.0",
        actions=[
            RecordingAction(
                action_id="action-1",
                action_type=RecordingActionType.CAPTURE,
                target="preview",
                payload={"note": "capture current preview"},
            ),
            RecordingAction(
                action_id="action-2",
                action_type=RecordingActionType.ANNOTATE,
                target="common.close_button",
                payload={"label": "close button anchor"},
            ),
        ],
    )


def _sample_match_result(repository: AnchorRepository | None) -> TemplateMatchResult | None:
    if repository is None:
        return None
    anchors = repository.list_anchors()
    if not anchors:
        return None
    anchor = anchors[0]
    return build_match_result(
        source_image="preview://sample",
        candidates=[
            VisionMatch(
                anchor_id=anchor.anchor_id,
                confidence=0.94,
                bbox=(30, 24, 160, 56),
                source_image="preview://sample",
            )
        ],
        expected_anchor=anchor,
        threshold=anchor.confidence_threshold,
        message="Sample anchor detected",
    )


def _sample_queue_items(snapshot: ConsoleSnapshot) -> list[QueuedTask]:
    if not snapshot.instances:
        return []
    queued: list[QueuedTask] = []
    for index, instance in enumerate(snapshot.instances[:2]):
        manifest = TaskManifest(
            task_id=f"sample.task.{index}",
            name=f"Sample Task {index + 1}",
            version="0.1.0",
            requires=["preview", "health_check"],
            recovery_policy="abort",
            stop_conditions=[
                StopCondition(
                    condition_id=f"manual-stop-{index}",
                    kind=StopConditionKind.MANUAL,
                    message="Operator stop requested",
                )
            ],
        )
        spec = TaskSpec(
            task_id=manifest.task_id,
            name=manifest.name,
            version=manifest.version,
            entry_state="ready",
            manifest=manifest,
            steps=[
                TaskStep(
                    step_id="capture-preview",
                    description="Capture one preview frame",
                    handler=lambda context: step_success(
                        "capture-preview",
                        f"Preview captured for {context.instance.instance_id}",
                    ),
                )
            ],
        )
        queued.append(
            QueuedTask(
                instance_id=instance.instance_id,
                spec=spec,
                priority=100 - index,
                metadata={"source": "gui.sample"},
            )
        )
    return queued


def _sample_log_events(snapshot: ConsoleSnapshot) -> list[AppEvent]:
    if not snapshot.instances:
        return []
    first = snapshot.instances[0]
    return [
        AppEvent(
            name="instance.updated",
            payload={
                "instance_id": first.instance_id,
                "message": "Instance discovered from doctor report",
                "status": first.status,
            },
        ),
        AppEvent(
            name="preview.captured",
            payload={
                "instance_id": first.instance_id,
                "message": "Preview frame captured",
                "task_id": "sample.task.0",
            },
        ),
        AppEvent(
            name="task.failure_snapshot",
            payload={
                "instance_id": first.instance_id,
                "message": "Failure snapshot ready for inspection",
                "task_id": "sample.task.0",
                "snapshot_id": "sample-snapshot-1",
                "status": "failed",
            },
        ),
    ]


def _load_stylesheet() -> str:
    stylesheet = _workspace_root() / "assets" / "ui" / "operator_console.qss"
    return stylesheet.read_text(encoding="utf-8") if stylesheet.exists() else ""


def _parse_point(value: str) -> tuple[int, int]:
    x_text, y_text = value.split(",", maxsplit=1)
    return int(x_text.strip()), int(y_text.strip())


def launch_placeholder_gui() -> int:
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QFormLayout,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QPushButton,
            QSplitter,
            QTabWidget,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PySide6 is not installed. Run scripts/bootstrap-dev.ps1 -InstallFullStack first.")
        return 1

    report = build_console_snapshot(to_primitive(build_doctor_report()))
    repository = _sample_repository()
    vision_snapshot = build_vision_workspace_snapshot(
        repository=repository,
        calibration_profile=_sample_calibration_profile(),
        replay_script=_sample_replay_script(),
        match_result=_sample_match_result(repository),
        source_image="preview://sample",
    )
    app = QApplication([])
    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    class MainWindow(QMainWindow):
        def __init__(self, snapshot: ConsoleSnapshot) -> None:
            super().__init__()
            self.setWindowTitle("RoxAutoScript Operator Console")
            self.resize(1520, 920)
            self._router = CommandRouter()
            self._snapshot = snapshot
            self._vision_snapshot = vision_snapshot
            self._queue_items = _sample_queue_items(snapshot)
            self._events = _sample_log_events(snapshot)
            self._global_emergency_stop_active = False
            self._state = build_operator_console_state(
                self._snapshot,
                self._vision_snapshot,
                queue_items=self._queue_items,
                events=self._events,
                global_emergency_stop_active=self._global_emergency_stop_active,
            )

            central = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(self._build_header())

            splitter = QSplitter()
            splitter.addWidget(self._build_left_panel())
            splitter.addWidget(self._build_right_panel())
            splitter.setSizes([340, 1180])
            layout.addWidget(splitter)

            central.setLayout(layout)
            self.setCentralWidget(central)
            self._render_state()

        def _build_header(self) -> QWidget:
            container = QWidget()
            layout = QGridLayout()
            container.setLayout(layout)

            title = QLabel("ROX operator console")
            title.setObjectName("titleLabel")
            layout.addWidget(title, 0, 0, 1, 2)

            self.summary_label = QLabel()
            layout.addWidget(self.summary_label, 1, 0)

            self.features_label = QLabel()
            layout.addWidget(self.features_label, 1, 1)

            self.emergency_label = QLabel()
            self.emergency_label.setObjectName("emergencyLabel")
            layout.addWidget(self.emergency_label, 2, 0)

            self.template_summary_label = QLabel()
            layout.addWidget(self.template_summary_label, 2, 1)

            header_actions = QHBoxLayout()
            self.refresh_button = QPushButton("Refresh")
            self.refresh_button.clicked.connect(self._refresh_snapshot)
            header_actions.addWidget(self.refresh_button)

            self.global_emergency_button = QPushButton("Emergency Stop")
            self.global_emergency_button.clicked.connect(self._request_global_emergency_stop)
            header_actions.addWidget(self.global_emergency_button)
            header_actions.addStretch(1)
            layout.addLayout(header_actions, 3, 0, 1, 2)
            return container

        def _build_left_panel(self) -> QWidget:
            group = QGroupBox("Instances")
            layout = QVBoxLayout()
            self.instance_list = QListWidget()
            self.instance_list.currentRowChanged.connect(self._on_instance_selected)
            layout.addWidget(self.instance_list)
            group.setLayout(layout)
            return group

        def _build_right_panel(self) -> QWidget:
            container = QWidget()
            layout = QVBoxLayout()

            details = QGroupBox("Instance Detail")
            details_layout = QVBoxLayout()
            self.instance_title = QLabel("No instance selected")
            self.instance_title.setObjectName("sectionTitle")
            self.instance_meta = QLabel("Select one emulator instance to inspect.")
            self.instance_meta.setWordWrap(True)
            details_layout.addWidget(self.instance_title)
            details_layout.addWidget(self.instance_meta)
            details.setLayout(details_layout)
            layout.addWidget(details)

            middle_splitter = QSplitter()
            middle_splitter.addWidget(self._build_operations_panel())
            middle_splitter.addWidget(self._build_observability_panel())
            middle_splitter.setSizes([580, 600])
            layout.addWidget(middle_splitter)

            logs = QGroupBox("Log Pane")
            logs_layout = QVBoxLayout()
            self.log_summary_label = QLabel()
            logs_layout.addWidget(self.log_summary_label)
            self.log_output = QPlainTextEdit()
            self.log_output.setReadOnly(True)
            logs_layout.addWidget(self.log_output)
            logs.setLayout(logs_layout)
            layout.addWidget(logs)

            container.setLayout(layout)
            return container

        def _build_operations_panel(self) -> QWidget:
            container = QWidget()
            layout = QVBoxLayout()

            controls = QGroupBox("Manual Controls")
            controls_layout = QVBoxLayout()
            self.manual_banner_label = QLabel()
            self.manual_banner_label.setWordWrap(True)
            controls_layout.addWidget(self.manual_banner_label)

            button_row = QHBoxLayout()
            self.start_queue_button = QPushButton("Start Queue")
            self.start_queue_button.clicked.connect(lambda: self._dispatch_manual_action("start_queue"))
            button_row.addWidget(self.start_queue_button)

            self.pause_button = QPushButton("Pause")
            self.pause_button.clicked.connect(lambda: self._dispatch_manual_action("pause"))
            button_row.addWidget(self.pause_button)

            self.stop_button = QPushButton("Stop")
            self.stop_button.clicked.connect(lambda: self._dispatch_manual_action("stop"))
            button_row.addWidget(self.stop_button)
            controls_layout.addLayout(button_row)

            tap_form = QFormLayout()
            self.tap_x_input = QLineEdit("640")
            self.tap_y_input = QLineEdit("360")
            self.tap_button = QPushButton("Send Tap")
            self.tap_button.clicked.connect(self._dispatch_tap)
            tap_form.addRow("Tap X", self.tap_x_input)
            tap_form.addRow("Tap Y", self.tap_y_input)
            tap_form.addRow(self.tap_button)
            controls_layout.addLayout(tap_form)

            swipe_form = QFormLayout()
            self.swipe_start_input = QLineEdit("500,700")
            self.swipe_end_input = QLineEdit("500,300")
            self.swipe_duration_input = QLineEdit("300")
            self.swipe_button = QPushButton("Send Swipe")
            self.swipe_button.clicked.connect(self._dispatch_swipe)
            swipe_form.addRow("Swipe Start", self.swipe_start_input)
            swipe_form.addRow("Swipe End", self.swipe_end_input)
            swipe_form.addRow("Duration ms", self.swipe_duration_input)
            swipe_form.addRow(self.swipe_button)
            controls_layout.addLayout(swipe_form)

            text_form = QFormLayout()
            self.text_input = QLineEdit()
            self.text_button = QPushButton("Send Text")
            self.text_button.clicked.connect(self._dispatch_text)
            text_form.addRow("Input Text", self.text_input)
            text_form.addRow(self.text_button)
            controls_layout.addLayout(text_form)

            controls.setLayout(controls_layout)
            layout.addWidget(controls)

            queue_box = QGroupBox("Queue Pane")
            queue_layout = QVBoxLayout()
            self.queue_summary_label = QLabel()
            queue_layout.addWidget(self.queue_summary_label)
            self.queue_output = QPlainTextEdit()
            self.queue_output.setReadOnly(True)
            queue_layout.addWidget(self.queue_output)
            queue_box.setLayout(queue_layout)
            layout.addWidget(queue_box)

            container.setLayout(layout)
            return container

        def _build_observability_panel(self) -> QWidget:
            tabs = QTabWidget()
            tabs.addTab(self._build_preview_tab(), "Preview")
            tabs.addTab(self._build_calibration_tab(), "Calibration")
            tabs.addTab(self._build_recording_tab(), "Recording")
            tabs.addTab(self._build_anchor_tab(), "Anchors")
            tabs.addTab(self._build_failure_tab(), "Failures")
            return tabs

        def _build_preview_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            self.preview_header = QLabel()
            self.preview_header.setWordWrap(True)
            self.preview_box = QPlainTextEdit()
            self.preview_box.setReadOnly(True)
            layout.addWidget(self.preview_header)
            layout.addWidget(self.preview_box)
            tab.setLayout(layout)
            return tab

        def _build_calibration_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            self.calibration_header = QLabel()
            self.calibration_header.setWordWrap(True)
            self.calibration_box = QPlainTextEdit()
            self.calibration_box.setReadOnly(True)
            layout.addWidget(self.calibration_header)
            layout.addWidget(self.calibration_box)
            tab.setLayout(layout)
            return tab

        def _build_recording_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            self.recording_header = QLabel()
            self.recording_header.setWordWrap(True)
            self.recording_box = QPlainTextEdit()
            self.recording_box.setReadOnly(True)
            layout.addWidget(self.recording_header)
            layout.addWidget(self.recording_box)
            tab.setLayout(layout)
            return tab

        def _build_anchor_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            self.anchor_header = QLabel()
            self.anchor_header.setWordWrap(True)
            self.anchor_box = QPlainTextEdit()
            self.anchor_box.setReadOnly(True)
            layout.addWidget(self.anchor_header)
            layout.addWidget(self.anchor_box)
            tab.setLayout(layout)
            return tab

        def _build_failure_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            self.failure_header = QLabel()
            self.failure_header.setWordWrap(True)
            self.failure_box = QPlainTextEdit()
            self.failure_box.setReadOnly(True)
            layout.addWidget(self.failure_header)
            layout.addWidget(self.failure_box)
            tab.setLayout(layout)
            return tab

        def _on_instance_selected(self, row: int) -> None:
            if row < 0 or row >= len(self._snapshot.instances):
                self._rebuild_state(selected_instance_id="")
                return
            self._rebuild_state(selected_instance_id=self._snapshot.instances[row].instance_id)

        def _refresh_snapshot(self) -> None:
            self._snapshot = build_console_snapshot(to_primitive(build_doctor_report()))
            self._queue_items = _sample_queue_items(self._snapshot)
            self._append_event(
                "operator.refresh",
                {
                    "instance_id": self._state.selected_instance_id,
                    "message": "Environment refreshed from doctor report.",
                    "command_type": InstanceCommandType.REFRESH.value,
                },
            )
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _request_global_emergency_stop(self) -> None:
            confirmed = QMessageBox.question(
                self,
                "Emergency Stop",
                "Request a global emergency stop for every instance?",
            )
            if confirmed != QMessageBox.StandardButton.Yes:
                return
            command = build_manual_control_command("emergency_stop")
            route = self._router.route(command)
            self._global_emergency_stop_active = True
            self._append_event(
                "operator.emergency_stop_requested",
                {
                    "message": route.message,
                    "command_type": route.command_type.value,
                    "status": "aborted",
                },
            )
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _dispatch_manual_action(self, action_key: str) -> None:
            instance_id = self._state.selected_instance_id or None
            command = build_manual_control_command(action_key, instance_id=instance_id)
            route = self._router.route(command)
            self._append_event(
                "operator.command_requested",
                {
                    "instance_id": instance_id,
                    "message": route.message,
                    "command_type": route.command_type.value,
                },
            )
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _dispatch_tap(self) -> None:
            payload = {"x": int(self.tap_x_input.text()), "y": int(self.tap_y_input.text())}
            self._dispatch_interaction("tap", payload)

        def _dispatch_swipe(self) -> None:
            payload = {
                "start": _parse_point(self.swipe_start_input.text()),
                "end": _parse_point(self.swipe_end_input.text()),
                "duration_ms": int(self.swipe_duration_input.text()),
            }
            self._dispatch_interaction("swipe", payload)

        def _dispatch_text(self) -> None:
            self._dispatch_interaction("input_text", {"text": self.text_input.text()})

        def _dispatch_interaction(self, action_key: str, payload: dict[str, Any]) -> None:
            instance_id = self._state.selected_instance_id or None
            command = build_manual_control_command(action_key, instance_id=instance_id, payload=payload)
            route = self._router.route(command)
            self._append_event(
                "operator.command_requested",
                {
                    "instance_id": instance_id,
                    "message": route.message,
                    "command_type": route.command_type.value,
                    "status": "routed",
                },
            )
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _append_event(self, name: str, payload: dict[str, Any]) -> None:
            self._events.append(AppEvent(name=name, payload=payload, emitted_at=utc_now()))

        def _rebuild_state(self, *, selected_instance_id: str) -> None:
            self._state = build_operator_console_state(
                self._snapshot,
                self._vision_snapshot,
                queue_items=self._queue_items,
                events=self._events,
                selected_instance_id=selected_instance_id,
                global_emergency_stop_active=self._global_emergency_stop_active,
            )
            self._render_state()

        def _render_state(self) -> None:
            enabled = self._state.snapshot.available_runtime_features
            feature_text = ", ".join(enabled) if enabled else "none"
            self.summary_label.setText(
                f"ADB: {self._state.snapshot.adb_path} | Instances: {self._state.snapshot.instance_count}"
            )
            self.features_label.setText(f"Detected optional packages: {feature_text}")
            self.emergency_label.setText(
                "Global stop: ACTIVE" if self._state.global_emergency_stop_active else "Global stop: idle"
            )
            self.template_summary_label.setText(
                f"Template repository: {self._state.vision.anchors.display_name} "
                f"({self._state.vision.anchors.repository_id or 'untracked'})"
            )

            self._render_instance_list()
            self._render_detail()
            self._render_queue()
            self._render_logs()
            self._render_manual_controls()
            self._render_vision_snapshot()

        def _render_instance_list(self) -> None:
            selected_instance_id = self._state.selected_instance_id
            self.instance_list.blockSignals(True)
            self.instance_list.clear()
            selected_row = -1
            for row, instance in enumerate(self._state.snapshot.instances):
                item = QListWidgetItem(f"{instance.label} [{instance.status}]")
                item.setData(1, instance.instance_id)
                self.instance_list.addItem(item)
                if instance.instance_id == selected_instance_id:
                    selected_row = row
            self.instance_list.blockSignals(False)
            if selected_row >= 0:
                self.instance_list.setCurrentRow(selected_row)

        def _render_detail(self) -> None:
            detail = self._state.detail
            self.instance_title.setText(detail.label)
            lines = [
                f"Instance ID: {detail.instance_id or 'n/a'}",
                f"Status: {detail.status}",
                f"ADB Serial: {detail.adb_serial or 'n/a'}",
                f"Last Seen: {detail.last_seen_at or 'n/a'}",
                f"Queue Depth: {detail.queue_depth}",
            ]
            if detail.warning:
                lines.append(f"Warning: {detail.warning}")
            if detail.metadata_lines:
                lines.append("Metadata:")
                lines.extend(f"  {line}" for line in detail.metadata_lines)
            self.instance_meta.setText("\n".join(lines))

        def _render_queue(self) -> None:
            queue = self._state.queue
            self.queue_summary_label.setText(
                f"Queued items for {self._state.detail.label}: {queue.total_count}"
            )
            if not queue.items:
                self.queue_output.setPlainText(queue.empty_message)
                return
            self.queue_output.setPlainText(
                "\n".join(
                    [
                        f"{item.task_name} [{item.task_id}] | priority={item.priority} | "
                        f"recovery={item.recovery_policy} | requires={item.requirements_summary or 'none'} | "
                        f"queued_at={item.enqueued_at}"
                        for item in queue.items
                    ]
                )
            )

        def _render_logs(self) -> None:
            logs = self._state.logs
            self.log_summary_label.setText(
                f"Log entries: {logs.filtered_count}/{logs.total_count} | failures: {logs.failure_count}"
            )
            if not logs.entries:
                self.log_output.setPlainText(logs.empty_message)
                return
            self.log_output.setPlainText(
                "\n".join(
                    [
                        f"[{entry.level}] {entry.emitted_at} | {entry.instance_id or 'global'} | {entry.summary}"
                        for entry in logs.entries
                    ]
                )
            )

        def _render_manual_controls(self) -> None:
            controls = self._state.manual_controls
            self.manual_banner_label.setText(controls.banner)
            enabled_map = {button.action_key: button.enabled for button in controls.available_actions}
            self.start_queue_button.setEnabled(enabled_map.get("start_queue", False))
            self.pause_button.setEnabled(enabled_map.get("pause", False))
            self.stop_button.setEnabled(enabled_map.get("stop", False))
            self.tap_button.setEnabled(enabled_map.get("tap", False))
            self.swipe_button.setEnabled(enabled_map.get("swipe", False))
            self.text_button.setEnabled(enabled_map.get("input_text", False))
            self.refresh_button.setEnabled(enabled_map.get("refresh", True))
            self.global_emergency_button.setEnabled(enabled_map.get("emergency_stop", True))

        def _render_vision_snapshot(self) -> None:
            preview = self._state.vision.preview
            self.preview_header.setText(
                f"Status: {preview.match_status} | Confidence: {preview.confidence:.3f} | "
                f"Selected anchor: {preview.selected_anchor_id or 'none'}"
            )
            self.preview_box.setPlainText(
                "\n".join(
                    [
                        f"Repository: {preview.repository_id or 'none'}",
                        f"Source image: {preview.source_image or 'n/a'}",
                        f"Message: {preview.message}",
                        "Candidates:",
                        *(preview.candidate_summaries if preview.candidate_summaries else ["  none"]),
                    ]
                )
            )

            calibration = self._state.vision.calibration
            self.calibration_header.setText(
                f"Profile: {calibration.profile_id} | Instance: {calibration.instance_id or 'n/a'} | "
                f"Scale: {calibration.scale_summary}"
            )
            self.calibration_box.setPlainText(
                "\n".join(
                    [
                        f"Emulator: {calibration.emulator_name}",
                        f"Offset: {calibration.offset_summary}",
                        f"Crop: {calibration.crop_region}",
                        "Anchors:",
                        *(
                            [
                                f"  {row.anchor_id} | threshold={row.confidence_threshold:.2f} | "
                                f"region={row.match_region} | override={row.override_summary or 'none'}"
                                for row in calibration.anchor_rows
                            ]
                            if calibration.anchor_rows
                            else ["  none"]
                        ),
                    ]
                )
            )

            recording = self._state.vision.recording
            self.recording_header.setText(
                f"Script: {recording.script_id} | Actions: {recording.action_count} | Version: {recording.version}"
            )
            self.recording_box.setPlainText(
                "\n".join(
                    [
                        f"Name: {recording.name}",
                        "Actions:",
                        *(
                            [
                                f"  {row.action_id} | {row.action_type} | target={row.target or 'n/a'} | "
                                f"payload={row.payload_summary} | at={row.occurred_at}"
                                for row in recording.action_rows
                            ]
                            if recording.action_rows
                            else ["  none"]
                        ),
                    ]
                )
            )

            anchors = self._state.vision.anchors
            self.anchor_header.setText(
                f"Repository: {anchors.display_name} | Version: {anchors.version} | "
                f"Selected: {anchors.selected_anchor_id or 'none'}"
            )
            self.anchor_box.setPlainText(
                "\n".join(
                    [
                        f"Selected summary: {anchors.selected_anchor_summary or 'n/a'}",
                        "Anchors:",
                        *(
                            [
                                f"  {row.anchor_id} | {row.label} | template={row.template_path} | "
                                f"threshold={row.confidence_threshold:.2f} | region={row.match_region}"
                                for row in anchors.anchor_rows
                            ]
                            if anchors.anchor_rows
                            else ["  none"]
                        ),
                    ]
                )
            )

            failure = self._state.vision.failure
            self.failure_header.setText(
                f"Status: {failure.status} | Source: {failure.source_image or 'n/a'}"
            )
            self.failure_box.setPlainText(
                "\n".join(
                    [
                        f"Message: {failure.message}",
                        f"Best candidate: {failure.best_candidate_summary}",
                        "Candidates:",
                        *(failure.candidate_summaries if failure.candidate_summaries else ["  none"]),
                    ]
                )
            )

    window = MainWindow(report)
    window.show()
    return app.exec()
