from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from roxauto.app.runtime_bridge import OperatorConsoleRuntimeBridge
from roxauto.app.viewmodels import ConsoleSnapshot, build_operator_console_state

if TYPE_CHECKING:
    from typing import Any


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_stylesheet() -> str:
    stylesheet = _workspace_root() / "assets" / "ui" / "operator_console.qss"
    return stylesheet.read_text(encoding="utf-8") if stylesheet.exists() else ""


def _parse_point(value: str) -> tuple[int, int]:
    x_text, y_text = value.split(",", maxsplit=1)
    return int(x_text.strip()), int(y_text.strip())


def launch_placeholder_gui() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap
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
    app = QApplication([])
    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    class MainWindow(QMainWindow):
        def __init__(self, runtime_bridge: OperatorConsoleRuntimeBridge) -> None:
            super().__init__()
            self.setWindowTitle("RoxAutoScript Operator Console")
            self.resize(1560, 980)
            self._bridge = runtime_bridge
            self._state = build_operator_console_state(
                ConsoleSnapshot(adb_path="not found", instance_count=0, packages={}, instances=[]),
                self._bridge.snapshot(),
                self._bridge.vision_tooling_state(""),
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
            subtitle = QLabel("Live runtime and vision tooling operator surface.")
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
            tabs.addTab(self._text_tab("readiness_header", "readiness_box"), "Readiness")
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
            self.preview_visual.setMinimumHeight(220)
            self.preview_context_box = QPlainTextEdit()
            self.preview_context_box.setReadOnly(True)
            self.preview_context_box.setMaximumHeight(150)
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
            confirmed = QMessageBox.question(
                self,
                "Emergency Stop",
                "Request a global emergency stop for every instance?",
            )
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
            ids = {instance.instance_id for instance in self._console_snapshot.instances}
            if selected_instance_id and selected_instance_id in ids:
                return selected_instance_id
            return self._console_snapshot.instances[0].instance_id if self._console_snapshot.instances else ""

        def _rebuild_state(self, *, selected_instance_id: str) -> None:
            self._runtime_snapshot = self._bridge.snapshot()
            self._console_snapshot = self._bridge.console_snapshot()
            resolved = self._resolve_selected_instance_id(selected_instance_id)
            self._vision_state = self._bridge.vision_tooling_state(resolved)
            self._state = build_operator_console_state(
                self._console_snapshot,
                self._runtime_snapshot,
                self._vision_state,
                selected_instance_id=resolved,
                global_emergency_stop_active=self._bridge.global_emergency_stop_active(),
            )
            self._render_state()

        def _render_state(self) -> None:
            summary = self._state.summary
            features = ", ".join(self._state.snapshot.available_runtime_features) or "none"
            workspace = self._state.vision.workspace
            readiness = self._state.vision.readiness

            self.summary_label.setText(summary.global_status_message)
            self.features_label.setText(f"ADB: {self._state.snapshot.adb_path} | Optional packages: {features}")
            self.template_summary_label.setText(
                "Templates: "
                f"{workspace.selected_repository_id or 'none'} | "
                f"repos={workspace.repository_count} | "
                f"blocking={readiness.blocking_count if readiness is not None else 0}"
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
                lines = [
                    f"{row.label} [{row.status}]",
                    f"ADB {row.subtitle}",
                    f"Queue {row.queue_depth} | {row.health_summary}",
                ]
                if row.profile_summary:
                    lines.append(f"Profile {row.profile_summary}")
                if row.active_task_id:
                    lines.append(f"Active {row.active_task_id}")
                if row.preview_summary:
                    lines.append(f"Preview {row.preview_summary}")
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
            profile_line = next(
                (
                    line.split(": ", maxsplit=1)[1]
                    for line in detail.metadata_lines
                    if line.startswith("profile_binding: ")
                ),
                "n/a",
            )
            self.detail_profile.setText(profile_line)
            self.instance_meta.setPlainText(
                "\n".join(detail.metadata_lines) if detail.metadata_lines else "No runtime metadata available."
            )

        def _render_queue(self) -> None:
            queue = self._state.queue
            self.queue_summary_label.setText(
                f"Queued items for {self._state.detail.label}: {queue.total_count} "
                f"(runtime total {len(self._state.runtime_snapshot.queue_items)})"
            )
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
            self.log_summary_label.setText(
                f"Log entries: {logs.filtered_count}/{logs.total_count} | failures: {logs.failure_count}"
            )
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
            self.manual_last_command_label.setText(
                f"Last command [{controls.last_command_status}]: {controls.last_command_summary}"
            )
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
            selected = self._state.selected_instance_snapshot
            vision = self._state.vision
            readiness = vision.readiness
            workspace = vision.workspace
            preview_path = self._preview_path()

            self.preview_header.setText(
                f"Match: {vision.match.status.value} | "
                f"Anchor: {vision.anchors.selected_anchor_id or 'none'} | "
                f"Repository: {workspace.selected_repository_id or 'none'}"
            )
            self._render_preview_visual(preview_path, QPixmap, Qt)
            self.preview_context_box.setPlainText(
                "\n".join(self._preview_context_lines()) or "No runtime preview context."
            )
            self.preview_box.setPlainText(
                "\n".join(
                    [
                        f"Source image: {preview_path or 'n/a'}",
                        f"Match message: {vision.match.message or 'n/a'}",
                        f"Failure message: {vision.failure.message or 'n/a'}",
                        f"Matched candidate: {vision.match.matched_candidate_summary or 'no candidate'}",
                        f"Best candidate: {vision.match.best_candidate_summary or 'no candidate'}",
                    ]
                )
            )

            if readiness is None:
                self.readiness_header.setText("Workspace readiness unavailable.")
                self.readiness_box.setPlainText("Asset inventory or template readiness report unavailable.")
            else:
                self.readiness_header.setText(
                    f"Workspace: {workspace.templates_root} | "
                    f"repos={workspace.repository_count} | "
                    f"blocking={readiness.blocking_count}"
                )
                dependency_lines = [
                    (
                        f"{item.asset_id} | pack={item.pack_id} | anchor={item.anchor_id or 'n/a'} | "
                        f"status={item.readiness_status.value} | inventory={item.inventory_status} | "
                        f"mismatch={'yes' if item.inventory_mismatch else 'no'}"
                    )
                    for item in readiness.template_dependencies
                ]
                self.readiness_box.setPlainText(
                    "\n".join(
                        [
                            f"ready={readiness.ready_count}",
                            f"placeholder={readiness.placeholder_count}",
                            f"missing={readiness.missing_count}",
                            f"invalid={readiness.invalid_count}",
                            f"inventory_mismatch={readiness.inventory_mismatch_count}",
                            "Dependencies:",
                            *(dependency_lines or ["none"]),
                        ]
                    )
                )

            calibration = vision.calibration
            self.calibration_header.setText(
                f"Profile: {calibration.profile_id or 'n/a'} | "
                f"Instance: {calibration.instance_id or 'n/a'} | "
                f"Scale: {calibration.scale_summary or '1.00 x 1.00'}"
            )
            self.calibration_box.setPlainText(
                "\n".join(
                    [
                        f"Emulator: {calibration.emulator_name or 'n/a'}",
                        f"Offset: {calibration.offset_summary or '0, 0'}",
                        f"Crop: {calibration.crop_summary or 'n/a'}",
                        f"Override count: {calibration.override_count}",
                        "Anchors:",
                        *(
                            [
                                f"  {row.anchor_id} | threshold={row.effective_confidence_threshold:.2f} | "
                                f"region={row.effective_match_region or row.match_region} | "
                                f"issues={','.join(row.issue_codes) or 'none'}"
                                for row in calibration.anchors
                            ]
                            or ["  none"]
                        ),
                    ]
                )
            )

            replay = vision.replay
            self.recording_header.setText(
                f"Script: {replay.script_id or 'n/a'} | Actions: {replay.total_actions} | Version: {replay.version}"
            )
            self.recording_box.setPlainText(
                "\n".join(
                    [
                        f"Name: {replay.script_name or 'No replay script'}",
                        "Actions:",
                        *(
                            [
                                f"  {row.action_id} | {row.action_type.value} | "
                                f"label={row.label} | payload={row.payload_summary or 'n/a'} | "
                                f"selected={'yes' if row.is_selected else 'no'}"
                                for row in replay.actions
                            ]
                            or ["  none"]
                        ),
                    ]
                )
            )

            anchors = vision.anchors
            self.anchor_header.setText(
                f"Repository: {anchors.display_name or 'none'} | "
                f"Version: {anchors.version or 'n/a'} | "
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
                                f"resolved={row.resolved_template_path} | exists={'yes' if row.asset_exists else 'no'} | "
                                f"threshold={row.effective_confidence_threshold:.2f}"
                                for row in anchors.anchors
                            ]
                            or ["  none"]
                        ),
                    ]
                )
            )

            failure = vision.failure
            self.failure_header.setText(
                f"Failure: {failure.failure_id or 'none'} | "
                f"Status: {failure.status.value} | "
                f"Instance: {failure.instance_id or (selected.instance_id if selected is not None else 'n/a')}"
            )
            self.failure_box.setPlainText(
                "\n".join(
                    [
                        f"Screenshot: {failure.screenshot_path or 'n/a'}",
                        f"Preview image: {failure.preview_image_path or 'n/a'}",
                        f"Message: {failure.message or 'n/a'}",
                        f"Best candidate: {failure.best_candidate_summary or 'no candidate'}",
                        "Candidates:",
                        *(
                            [
                                f"  {candidate.anchor_id} | confidence={candidate.confidence:.3f} | bbox={candidate.bbox}"
                                for candidate in failure.candidates
                            ]
                            or ["  none"]
                        ),
                    ]
                )
            )

        def _preview_path(self) -> str:
            selected = self._state.selected_instance_snapshot
            if selected is not None and selected.preview_frame is not None:
                return selected.preview_frame.image_path
            if self._state.vision.capture.selected_artifact is not None:
                return self._state.vision.capture.selected_artifact.image_path
            if self._state.vision.failure.preview_image_path:
                return self._state.vision.failure.preview_image_path
            if self._state.vision.failure.screenshot_path:
                return self._state.vision.failure.screenshot_path
            return self._state.vision.match.source_image

        def _render_preview_visual(self, preview_path: str, pixmap_class, qt) -> None:
            path = Path(preview_path) if preview_path and "://" not in preview_path else None
            if path is not None and path.exists():
                pixmap = pixmap_class(str(path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.preview_visual.width() or 520,
                        self.preview_visual.height() or 220,
                        qt.AspectRatioMode.KeepAspectRatio,
                        qt.TransformationMode.SmoothTransformation,
                    )
                    self.preview_visual.setPixmap(scaled)
                    self.preview_visual.setText("")
                    return
            self.preview_visual.setPixmap(pixmap_class())
            availability = "Preview source available" if path is not None and path.exists() else "Preview source not materialized yet"
            self.preview_visual.setText(f"{availability}\n{preview_path or 'n/a'}")

        def _preview_context_lines(self) -> list[str]:
            selected = self._state.selected_instance_snapshot
            vision = self._state.vision
            lines: list[str] = []
            if selected is None:
                return ["Runtime context unavailable."]
            context = selected.context
            lines.extend(
                [
                    f"Instance: {selected.instance_id}",
                    f"Runtime status: {selected.instance.status.value}",
                    f"Queue depth: {selected.queue_depth}",
                ]
            )
            if context is not None:
                lines.append(f"Stop requested: {context.stop_requested}")
                lines.append(f"Health check: {context.health_check_ok}")
                if context.active_task_id:
                    lines.append(f"Active task: {context.active_task_id}")
                if context.active_run_id:
                    lines.append(f"Active run: {context.active_run_id}")
                if context.profile_binding is not None:
                    lines.append(
                        f"Profile: {context.profile_binding.display_name} [{context.profile_binding.profile_id}]"
                    )
                if context.preview_frame is not None:
                    lines.append(f"Preview frame: {context.preview_frame.image_path}")
                    lines.append(f"Preview source: {context.preview_frame.source}")
                if context.failure_snapshot is not None:
                    lines.append(f"Failure snapshot: {context.failure_snapshot.snapshot_id}")
                    lines.append(f"Failure reason: {context.failure_snapshot.reason.value}")
            readiness = vision.readiness
            if readiness is not None:
                lines.append(f"Workspace blockers: {readiness.blocking_count}")
            if vision.anchors.selected_anchor_summary:
                lines.append(f"Anchor: {vision.anchors.selected_anchor_summary}")
            return lines

    window = MainWindow(bridge)
    window.show()
    return app.exec()
