from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from roxauto.app.runtime_bridge import OperatorConsoleRuntimeBridge
from roxauto.app.viewmodels import ConsoleSnapshot, build_operator_console_state, build_vision_workspace_snapshot
from roxauto.core.models import VisionMatch
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


def _sample_calibration_profile(instance_id: str = "mumu-0") -> CalibrationProfile:
    return CalibrationProfile(
        profile_id="sample.default",
        instance_id=instance_id,
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


def _sample_match_result(
    repository: AnchorRepository | None,
    *,
    source_image: str = "preview://sample",
) -> TemplateMatchResult | None:
    if repository is None:
        return None
    anchors = repository.list_anchors()
    if not anchors:
        return None
    anchor = anchors[0]
    return build_match_result(
        source_image=source_image,
        candidates=[
            VisionMatch(
                anchor_id=anchor.anchor_id,
                confidence=0.94,
                bbox=(30, 24, 160, 56),
                source_image=source_image,
            )
        ],
        expected_anchor=anchor,
        threshold=anchor.confidence_threshold,
        message="Sample anchor detected",
    )


def _load_stylesheet() -> str:
    stylesheet = _workspace_root() / "assets" / "ui" / "operator_console.qss"
    return stylesheet.read_text(encoding="utf-8") if stylesheet.exists() else ""


def _parse_point(value: str) -> tuple[int, int]:
    x_text, y_text = value.split(",", maxsplit=1)
    return int(x_text.strip()), int(y_text.strip())


def launch_placeholder_gui() -> int:
    try:
        from PySide6.QtCore import Qt
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

    bridge = OperatorConsoleRuntimeBridge(workspace_root=_workspace_root())
    bridge.refresh()
    repository = _sample_repository()
    app = QApplication([])
    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    class MainWindow(QMainWindow):
        def __init__(self, runtime_bridge: OperatorConsoleRuntimeBridge) -> None:
            super().__init__()
            self.setWindowTitle("RoxAutoScript Operator Console")
            self.resize(1560, 940)
            self._bridge = runtime_bridge
            self._repository = repository
            self._state = build_operator_console_state(
                ConsoleSnapshot(adb_path="not found", instance_count=0, packages={}, instances=[]),
                build_vision_workspace_snapshot(source_image="preview://sample"),
            )

            central = QWidget()
            root = QVBoxLayout()
            central.setLayout(root)
            self.setCentralWidget(central)

            root.addWidget(self._build_header())
            splitter = QSplitter()
            splitter.addWidget(self._build_left_panel())
            splitter.addWidget(self._build_right_panel())
            splitter.setSizes([390, 1170])
            root.addWidget(splitter)
            self._rebuild_state(selected_instance_id="")

        def _build_header(self) -> QWidget:
            box = QGroupBox("Overview")
            layout = QVBoxLayout()
            box.setLayout(layout)

            top = QHBoxLayout()
            title_col = QVBoxLayout()
            title = QLabel("ROX operator console")
            title.setObjectName("titleLabel")
            subtitle = QLabel("Runtime-backed multi-instance operator tooling.")
            subtitle.setObjectName("subtitleLabel")
            title_col.addWidget(title)
            title_col.addWidget(subtitle)
            top.addLayout(title_col)
            top.addStretch(1)

            self.refresh_button = QPushButton("Refresh Runtime")
            self.refresh_button.clicked.connect(self._refresh_snapshot)
            top.addWidget(self.refresh_button)

            self.global_emergency_button = QPushButton("Emergency Stop")
            self.global_emergency_button.setObjectName("emergencyButton")
            self.global_emergency_button.clicked.connect(self._request_global_emergency_stop)
            top.addWidget(self.global_emergency_button)
            layout.addLayout(top)

            self.summary_label = QLabel()
            self.summary_label.setObjectName("statusBanner")
            layout.addWidget(self.summary_label)

            info_row = QHBoxLayout()
            self.features_label = QLabel()
            self.template_summary_label = QLabel()
            info_row.addWidget(self.features_label)
            info_row.addWidget(self.template_summary_label)
            layout.addLayout(info_row)

            metrics = QGridLayout()
            self.metric_total = self._metric_card(metrics, 0, 0, "Instances", Qt)
            self.metric_ready = self._metric_card(metrics, 0, 1, "Ready", Qt)
            self.metric_busy = self._metric_card(metrics, 0, 2, "Busy", Qt)
            self.metric_paused = self._metric_card(metrics, 0, 3, "Paused", Qt)
            self.metric_errors = self._metric_card(metrics, 1, 0, "Errors", Qt)
            self.metric_offline = self._metric_card(metrics, 1, 1, "Offline", Qt)
            self.metric_queue = self._metric_card(metrics, 1, 2, "Sel Queue", Qt)
            self.metric_failures = self._metric_card(metrics, 1, 3, "Failures", Qt)
            layout.addLayout(metrics)
            return box

        def _metric_card(self, layout, row: int, column: int, title: str, qt) -> QLabel:
            card = QGroupBox(title)
            card.setObjectName("summaryCard")
            card_layout = QVBoxLayout()
            value = QLabel("0")
            value.setObjectName("metricValue")
            value.setAlignment(qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(value)
            card.setLayout(card_layout)
            layout.addWidget(card, row, column)
            return value

        def _build_left_panel(self) -> QWidget:
            box = QGroupBox("Instances")
            layout = QVBoxLayout()
            box.setLayout(layout)
            self.instance_list_summary = QLabel()
            self.instance_list_summary.setWordWrap(True)
            layout.addWidget(self.instance_list_summary)
            self.instance_list = QListWidget()
            self.instance_list.currentRowChanged.connect(self._on_instance_selected)
            layout.addWidget(self.instance_list)
            return box

        def _build_right_panel(self) -> QWidget:
            container = QWidget()
            layout = QVBoxLayout()
            container.setLayout(layout)

            detail = QGroupBox("Instance Detail")
            detail_layout = QVBoxLayout()
            detail.setLayout(detail_layout)
            self.instance_title = QLabel("No instance selected")
            self.instance_title.setObjectName("sectionTitle")
            self.instance_warning = QLabel()
            self.instance_warning.setObjectName("warningLabel")
            self.instance_warning.setWordWrap(True)
            detail_layout.addWidget(self.instance_title)
            detail_layout.addWidget(self.instance_warning)

            form = QGridLayout()
            self.detail_id = self._detail_field(form, 0, 0, "Instance ID", QLabel)
            self.detail_status = self._detail_field(form, 0, 2, "Status", QLabel)
            self.detail_queue = self._detail_field(form, 1, 0, "Queue Depth", QLabel)
            self.detail_seen = self._detail_field(form, 1, 2, "Last Seen", QLabel)
            self.detail_adb = self._detail_field(form, 2, 0, "ADB Serial", QLabel)
            self.detail_profile = self._detail_field(form, 2, 2, "Profile", QLabel)
            detail_layout.addLayout(form)
            self.instance_meta = QPlainTextEdit()
            self.instance_meta.setReadOnly(True)
            detail_layout.addWidget(self.instance_meta)
            layout.addWidget(detail)

            mid = QSplitter()
            mid.addWidget(self._build_operations_panel())
            mid.addWidget(self._build_observability_panel())
            mid.setSizes([560, 610])
            layout.addWidget(mid)

            logs = QGroupBox("Logs")
            logs_layout = QVBoxLayout()
            logs.setLayout(logs_layout)
            self.log_summary_label = QLabel()
            self.log_latest_label = QLabel()
            self.log_latest_label.setObjectName("subtleLabel")
            self.log_latest_label.setWordWrap(True)
            self.log_output = QPlainTextEdit()
            self.log_output.setReadOnly(True)
            logs_layout.addWidget(self.log_summary_label)
            logs_layout.addWidget(self.log_latest_label)
            logs_layout.addWidget(self.log_output)
            layout.addWidget(logs)
            return container

        def _detail_field(self, layout, row: int, column: int, label_text: str, label_class):
            label = label_class(label_text)
            label.setObjectName("fieldLabel")
            value = label_class("n/a")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            layout.addWidget(label, row, column)
            layout.addWidget(value, row, column + 1)
            return value

        def _build_operations_panel(self) -> QWidget:
            container = QWidget()
            layout = QVBoxLayout()
            container.setLayout(layout)

            manual = QGroupBox("Manual Controls")
            manual_layout = QVBoxLayout()
            manual.setLayout(manual_layout)
            self.manual_banner_label = QLabel()
            self.manual_banner_label.setWordWrap(True)
            self.manual_last_command_label = QLabel()
            self.manual_last_command_label.setObjectName("subtleLabel")
            self.manual_last_command_label.setWordWrap(True)
            manual_layout.addWidget(self.manual_banner_label)
            manual_layout.addWidget(self.manual_last_command_label)

            actions = QHBoxLayout()
            self.start_queue_button = QPushButton("Start Queue")
            self.start_queue_button.clicked.connect(lambda: self._dispatch_manual_action("start_queue"))
            self.pause_button = QPushButton("Pause")
            self.pause_button.clicked.connect(lambda: self._dispatch_manual_action("pause"))
            self.stop_button = QPushButton("Stop")
            self.stop_button.clicked.connect(lambda: self._dispatch_manual_action("stop"))
            actions.addWidget(self.start_queue_button)
            actions.addWidget(self.pause_button)
            actions.addWidget(self.stop_button)
            manual_layout.addLayout(actions)

            tap = QFormLayout()
            self.tap_x_input = QLineEdit("640")
            self.tap_y_input = QLineEdit("360")
            self.tap_button = QPushButton("Send Tap")
            self.tap_button.clicked.connect(self._dispatch_tap)
            tap.addRow("Tap X", self.tap_x_input)
            tap.addRow("Tap Y", self.tap_y_input)
            tap.addRow("", self.tap_button)
            manual_layout.addLayout(tap)

            swipe = QFormLayout()
            self.swipe_start_input = QLineEdit("500,700")
            self.swipe_end_input = QLineEdit("500,300")
            self.swipe_duration_input = QLineEdit("300")
            self.swipe_button = QPushButton("Send Swipe")
            self.swipe_button.clicked.connect(self._dispatch_swipe)
            swipe.addRow("Swipe Start", self.swipe_start_input)
            swipe.addRow("Swipe End", self.swipe_end_input)
            swipe.addRow("Duration ms", self.swipe_duration_input)
            swipe.addRow("", self.swipe_button)
            manual_layout.addLayout(swipe)

            text = QFormLayout()
            self.text_input = QLineEdit()
            self.text_button = QPushButton("Send Text")
            self.text_button.clicked.connect(self._dispatch_text)
            text.addRow("Input Text", self.text_input)
            text.addRow("", self.text_button)
            manual_layout.addLayout(text)
            layout.addWidget(manual)

            queue = QGroupBox("Queue")
            queue_layout = QVBoxLayout()
            queue.setLayout(queue_layout)
            self.queue_summary_label = QLabel()
            self.queue_summary_label.setWordWrap(True)
            self.queue_output = QPlainTextEdit()
            self.queue_output.setReadOnly(True)
            queue_layout.addWidget(self.queue_summary_label)
            queue_layout.addWidget(self.queue_output)
            layout.addWidget(queue)
            return container

        def _build_observability_panel(self) -> QWidget:
            tabs = QTabWidget()
            tabs.addTab(self._build_preview_tab(Qt), "Preview")
            tabs.addTab(self._text_tab("calibration_header", "calibration_box"), "Calibration")
            tabs.addTab(self._text_tab("recording_header", "recording_box"), "Recording")
            tabs.addTab(self._text_tab("anchor_header", "anchor_box"), "Anchors")
            tabs.addTab(self._text_tab("failure_header", "failure_box"), "Failures")
            return tabs

        def _build_preview_tab(self, qt) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            tab.setLayout(layout)
            self.preview_header = QLabel()
            self.preview_header.setWordWrap(True)
            self.preview_visual = QLabel("Preview source unavailable.")
            self.preview_visual.setObjectName("previewFrame")
            self.preview_visual.setAlignment(qt.AlignmentFlag.AlignCenter)
            self.preview_visual.setWordWrap(True)
            self.preview_visual.setMinimumHeight(150)
            self.preview_context_box = QPlainTextEdit()
            self.preview_context_box.setReadOnly(True)
            self.preview_context_box.setMaximumHeight(110)
            self.preview_box = QPlainTextEdit()
            self.preview_box.setReadOnly(True)
            layout.addWidget(self.preview_header)
            layout.addWidget(self.preview_visual)
            layout.addWidget(self.preview_context_box)
            layout.addWidget(self.preview_box)
            return tab

        def _text_tab(self, header_name: str, box_name: str) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            tab.setLayout(layout)
            header = QLabel()
            header.setWordWrap(True)
            box = QPlainTextEdit()
            box.setReadOnly(True)
            setattr(self, header_name, header)
            setattr(self, box_name, box)
            layout.addWidget(header)
            layout.addWidget(box)
            return tab

        def _on_instance_selected(self, row: int) -> None:
            if row < 0 or row >= len(self._state.instance_rows):
                self._rebuild_state(selected_instance_id="")
                return
            self._rebuild_state(selected_instance_id=self._state.instance_rows[row].instance_id)

        def _refresh_snapshot(self) -> None:
            self._bridge.refresh()
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _request_global_emergency_stop(self) -> None:
            confirmed = QMessageBox.question(self, "Emergency Stop", "Request a global emergency stop for every instance?")
            if confirmed != QMessageBox.StandardButton.Yes:
                return
            self._bridge.dispatch_manual_action("emergency_stop")
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _dispatch_manual_action(self, action_key: str) -> None:
            try:
                self._bridge.dispatch_manual_action(action_key, instance_id=self._state.selected_instance_id or None)
            except ValueError as exc:
                QMessageBox.warning(self, "Command Error", str(exc))
                return
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _dispatch_tap(self) -> None:
            try:
                payload = {"x": int(self.tap_x_input.text()), "y": int(self.tap_y_input.text())}
            except ValueError as exc:
                QMessageBox.warning(self, "Input Error", str(exc))
                return
            self._dispatch_interaction("tap", payload)

        def _dispatch_swipe(self) -> None:
            try:
                payload = {
                    "start": _parse_point(self.swipe_start_input.text()),
                    "end": _parse_point(self.swipe_end_input.text()),
                    "duration_ms": int(self.swipe_duration_input.text()),
                }
            except ValueError as exc:
                QMessageBox.warning(self, "Input Error", str(exc))
                return
            self._dispatch_interaction("swipe", payload)

        def _dispatch_text(self) -> None:
            self._dispatch_interaction("input_text", {"text": self.text_input.text()})

        def _dispatch_interaction(self, action_key: str, payload: dict[str, Any]) -> None:
            try:
                self._bridge.dispatch_manual_action(
                    action_key,
                    instance_id=self._state.selected_instance_id or None,
                    payload=payload,
                )
            except ValueError as exc:
                QMessageBox.warning(self, "Command Error", str(exc))
                return
            self._rebuild_state(selected_instance_id=self._state.selected_instance_id)

        def _resolve_selected_instance_id(self, selected_instance_id: str) -> str:
            ids = {instance.instance_id for instance in self._snapshot.instances}
            if selected_instance_id and selected_instance_id in ids:
                return selected_instance_id
            return self._snapshot.instances[0].instance_id if self._snapshot.instances else ""

        def _preview_context_lines(self, selected_instance_id: str) -> list[str]:
            context = self._bridge.get_runtime_context(selected_instance_id) if selected_instance_id else None
            if context is None:
                return ["Runtime context unavailable."]
            lines = [
                f"Instance: {context.instance_id}",
                f"Queue depth: {context.queue_depth}",
                f"Stop requested: {context.stop_requested}",
                f"Health check: {context.health_check_ok}",
            ]
            if context.profile_binding is not None:
                lines.append(f"Profile: {context.profile_binding.display_name}")
            if context.active_task_id:
                lines.append(f"Active task: {context.active_task_id}")
            if context.preview_frame is not None:
                lines.append(f"Preview frame: {context.preview_frame.image_path}")
            if context.failure_snapshot is not None:
                lines.append(f"Failure snapshot: {context.failure_snapshot.snapshot_id}")
            return lines

        def _build_vision_snapshot(self, selected_instance_id: str):
            context = self._bridge.get_runtime_context(selected_instance_id) if selected_instance_id else None
            source_image = "preview://sample"
            failure_message = ""
            if context is not None:
                if context.preview_frame is not None:
                    source_image = context.preview_frame.image_path
                if context.failure_snapshot is not None:
                    source_image = context.failure_snapshot.screenshot_path or source_image
                    failure_message = str(context.failure_snapshot.metadata.get("message") or context.failure_snapshot.reason.value)
            return build_vision_workspace_snapshot(
                repository=self._repository,
                calibration_profile=_sample_calibration_profile(selected_instance_id or "mumu-0"),
                replay_script=_sample_replay_script(),
                match_result=_sample_match_result(self._repository, source_image=source_image),
                source_image=source_image,
                failure_message=failure_message,
                preview_context_lines=self._preview_context_lines(selected_instance_id),
            )

        def _rebuild_state(self, *, selected_instance_id: str) -> None:
            self._snapshot = self._bridge.snapshot()
            resolved = self._resolve_selected_instance_id(selected_instance_id)
            self._vision_snapshot = self._build_vision_snapshot(resolved)
            self._state = build_operator_console_state(
                self._snapshot,
                self._vision_snapshot,
                queue_items=self._bridge.queue_items(),
                events=self._bridge.events(),
                selected_instance_id=resolved,
                runtime_contexts=self._bridge.runtime_contexts(),
                global_emergency_stop_active=self._bridge.global_emergency_stop_active(),
            )
            self._render_state()

        def _render_state(self) -> None:
            summary = self._state.summary
            features = ", ".join(self._state.snapshot.available_runtime_features) or "none"
            self.summary_label.setText(summary.global_status_message)
            self.features_label.setText(f"ADB: {self._state.snapshot.adb_path} | Optional packages: {features}")
            self.template_summary_label.setText(
                f"Template repository: {self._state.vision.anchors.display_name} ({self._state.vision.anchors.repository_id or 'untracked'})"
            )
            self.metric_total.setText(str(summary.total_instances))
            self.metric_ready.setText(str(summary.ready_count))
            self.metric_busy.setText(str(summary.busy_count))
            self.metric_paused.setText(str(summary.paused_count))
            self.metric_errors.setText(str(summary.error_count))
            self.metric_offline.setText(str(summary.disconnected_count))
            self.metric_queue.setText(str(summary.selected_queue_depth))
            self.metric_failures.setText(str(summary.failure_count))
            self.instance_list_summary.setText(
                f"Selected: {summary.selected_instance_label} [{summary.selected_instance_status}]"
                if summary.selected_instance_label
                else "Select an instance to inspect runtime status, queue, logs, and preview."
            )
            self._render_instance_list()
            self._render_detail()
            self._render_queue()
            self._render_logs()
            self._render_controls()
            self._render_vision()

        def _render_instance_list(self) -> None:
            self.instance_list.blockSignals(True)
            self.instance_list.clear()
            selected_row = -1
            for index, row in enumerate(self._state.instance_rows):
                lines = [f"{row.label} [{row.status}]", f"ADB {row.subtitle}", f"Queue {row.queue_depth} | {row.health_summary}"]
                if row.profile_summary:
                    lines.append(f"Profile {row.profile_summary}")
                if row.active_task_id:
                    lines.append(f"Active {row.active_task_id}")
                if row.warning:
                    lines.append(f"Warning {row.warning}")
                item = QListWidgetItem("\n".join(lines))
                item.setData(1, row.instance_id)
                self.instance_list.addItem(item)
                if row.instance_id == self._state.selected_instance_id:
                    selected_row = index
            self.instance_list.blockSignals(False)
            if selected_row >= 0:
                self.instance_list.setCurrentRow(selected_row)

        def _render_detail(self) -> None:
            detail = self._state.detail
            self.instance_title.setText(detail.label)
            self.instance_warning.setVisible(bool(detail.warning))
            self.instance_warning.setText(detail.warning)
            self.detail_id.setText(detail.instance_id or "n/a")
            self.detail_status.setText(detail.status or "unknown")
            self.detail_queue.setText(str(detail.queue_depth))
            self.detail_seen.setText(detail.last_seen_at or "n/a")
            self.detail_adb.setText(detail.adb_serial or "n/a")
            profile_line = next((line.split(": ", maxsplit=1)[1] for line in detail.metadata_lines if line.startswith("profile_binding: ")), "n/a")
            self.detail_profile.setText(profile_line)
            self.instance_meta.setPlainText("\n".join(detail.metadata_lines) if detail.metadata_lines else "No runtime metadata available.")

        def _render_queue(self) -> None:
            queue = self._state.queue
            self.queue_summary_label.setText(f"Queued items for {self._state.detail.label}: {queue.total_count}")
            if not queue.items:
                self.queue_output.setPlainText(queue.empty_message)
                return
            self.queue_output.setPlainText(
                "\n\n".join(
                    [
                        "\n".join(
                            [
                                f"{item.task_name} [{item.task_id}]",
                                f"priority={item.priority} | recovery={item.recovery_policy}",
                                f"requires={item.requirements_summary or 'none'}",
                                f"queued_at={item.enqueued_at}",
                                f"queue_id={item.queue_id}",
                            ]
                        )
                        for item in queue.items
                    ]
                )
            )

        def _render_logs(self) -> None:
            logs = self._state.logs
            self.log_summary_label.setText(f"Log entries: {logs.filtered_count}/{logs.total_count} | failures: {logs.failure_count}")
            self.log_latest_label.setText(f"Latest: {logs.latest_summary}")
            if not logs.entries:
                self.log_output.setPlainText(logs.empty_message)
                return
            self.log_output.setPlainText(
                "\n\n".join(
                    [
                        "\n".join(
                            [
                                f"[{entry.level}] {entry.event_name}",
                                f"time={entry.emitted_at}",
                                f"instance={entry.instance_id or 'global'}",
                                entry.summary,
                            ]
                        )
                        for entry in logs.entries
                    ]
                )
            )

        def _render_controls(self) -> None:
            controls = self._state.manual_controls
            self.manual_banner_label.setText(controls.banner)
            self.manual_last_command_label.setText(f"Last command [{controls.last_command_status}]: {controls.last_command_summary}")
            enabled = {button.action_key: button.enabled for button in controls.available_actions}
            self.start_queue_button.setEnabled(enabled.get("start_queue", False))
            self.pause_button.setEnabled(enabled.get("pause", False))
            self.stop_button.setEnabled(enabled.get("stop", False))
            self.tap_button.setEnabled(enabled.get("tap", False))
            self.swipe_button.setEnabled(enabled.get("swipe", False))
            self.text_button.setEnabled(enabled.get("input_text", False))
            self.refresh_button.setEnabled(enabled.get("refresh", True))
            self.global_emergency_button.setEnabled(enabled.get("emergency_stop", True))

        def _render_vision(self) -> None:
            preview = self._state.vision.preview
            self.preview_header.setText(
                f"Status: {preview.match_status} | Confidence: {preview.confidence:.3f} | Selected anchor: {preview.selected_anchor_id or 'none'}"
            )
            preview_path = preview.source_image or "n/a"
            path = Path(preview_path) if "://" not in preview_path else None
            available = path is not None and path.exists()
            self.preview_visual.setText(f"{'Preview source available' if available else 'Preview source not materialized yet'}\n{preview_path}")
            self.preview_context_box.setPlainText("\n".join(preview.context_lines) if preview.context_lines else "No runtime preview context.")
            self.preview_box.setPlainText(
                "\n".join([f"Repository: {preview.repository_id or 'none'}", f"Message: {preview.message}", "Candidates:", *(preview.candidate_summaries or ["  none"])])
            )

            calibration = self._state.vision.calibration
            self.calibration_header.setText(f"Profile: {calibration.profile_id} | Instance: {calibration.instance_id or 'n/a'} | Scale: {calibration.scale_summary}")
            self.calibration_box.setPlainText(
                "\n".join([f"Emulator: {calibration.emulator_name}", f"Offset: {calibration.offset_summary}", f"Crop: {calibration.crop_region}", "Anchors:", *([f"  {row.anchor_id} | threshold={row.confidence_threshold:.2f} | region={row.match_region} | override={row.override_summary or 'none'}" for row in calibration.anchor_rows] or ["  none"])])
            )

            recording = self._state.vision.recording
            self.recording_header.setText(f"Script: {recording.script_id} | Actions: {recording.action_count} | Version: {recording.version}")
            self.recording_box.setPlainText(
                "\n".join([f"Name: {recording.name}", "Actions:", *([f"  {row.action_id} | {row.action_type} | target={row.target or 'n/a'} | payload={row.payload_summary} | at={row.occurred_at}" for row in recording.action_rows] or ["  none"])])
            )

            anchors = self._state.vision.anchors
            self.anchor_header.setText(f"Repository: {anchors.display_name} | Version: {anchors.version} | Selected: {anchors.selected_anchor_id or 'none'}")
            self.anchor_box.setPlainText(
                "\n".join([f"Selected summary: {anchors.selected_anchor_summary or 'n/a'}", "Anchors:", *([f"  {row.anchor_id} | {row.label} | template={row.template_path} | threshold={row.confidence_threshold:.2f} | region={row.match_region}" for row in anchors.anchor_rows] or ["  none"])])
            )

            failure = self._state.vision.failure
            self.failure_header.setText(f"Status: {failure.status} | Source: {failure.source_image or 'n/a'}")
            self.failure_box.setPlainText(
                "\n".join([f"Message: {failure.message}", f"Best candidate: {failure.best_candidate_summary}", "Candidates:", *(failure.candidate_summaries or ["  none"])])
            )

    window = MainWindow(bridge)
    window.show()
    return app.exec()
