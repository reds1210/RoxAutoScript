from __future__ import annotations

from pathlib import Path

from roxauto.app.runtime_bridge import OperatorConsoleRuntimeBridge
from roxauto.app.viewmodels import OperatorConsoleState, TaskReadinessRowView


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_stylesheet() -> str:
    stylesheet = _workspace_root() / "assets" / "ui" / "operator_console.qss"
    return stylesheet.read_text(encoding="utf-8") if stylesheet.exists() else ""


def _parse_point(value: str) -> tuple[int, int]:
    x_text, y_text = value.split(",", maxsplit=1)
    return int(x_text.strip()), int(y_text.strip())


def _parse_optional_point(value: str) -> tuple[int, int] | None:
    text = value.strip()
    if not text:
        return None
    return _parse_point(text)


def _parse_optional_region(value: str) -> tuple[int, int, int, int] | None:
    text = value.strip()
    if not text:
        return None
    left, top, width, height = [int(part.strip()) for part in text.split(",", maxsplit=3)]
    return left, top, width, height


def _parse_optional_float(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    return float(text)


def _zh_status(value: str) -> str:
    labels = {
        "idle": "Idle",
        "queued": "Queued",
        "running": "Running",
        "succeeded": "Succeeded",
        "failed": "Failed",
        "aborted": "Aborted",
        "ready": "Ready",
        "busy": "Busy",
        "paused": "Paused",
        "error": "Error",
        "disconnected": "Disconnected",
        "connecting": "Connecting",
    }
    return labels.get(value.lower(), value)


def _zh_task(task_id: str) -> str:
    return "Daily Claim" if task_id == "daily_ui.claim_rewards" else task_id


def _zh_health(value: str) -> str:
    replacements = {
        "healthy": "Healthy",
        "health unknown": "Health unknown",
        "health check failed": "Health check failed",
        "runtime error": "Runtime error",
        "stop requested": "Stop requested",
    }
    translated = value
    for source, target in replacements.items():
        translated = translated.replace(source, target)
    return translated


def _zh_match_status(value: str) -> str:
    labels = {
        "matched": "Matched",
        "missed": "Missed",
        "ambiguous": "Ambiguous",
    }
    return labels.get(value.lower(), value)


def _claim_readiness_row(state: OperatorConsoleState) -> TaskReadinessRowView | None:
    for row in state.task_readiness.rows:
        if row.task_id == "daily_ui.claim_rewards":
            return row
    return None


def launch_placeholder_gui() -> int:
    try:
        from PySide6.QtCore import QTimer, Qt
        from PySide6.QtGui import QCloseEvent, QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QComboBox,
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
            QProgressBar,
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
    bridge.start_live_updates(poll_interval_sec=2.0, bootstrap=True)

    app = QApplication([])
    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    class MainWindow(QMainWindow):
        def __init__(self, runtime_bridge: OperatorConsoleRuntimeBridge) -> None:
            super().__init__()
            self.setWindowTitle("ROX Command Deck")
            self.resize(1480, 960)
            self._bridge = runtime_bridge
            self._list_syncing = False
            self._selected_instance_id = ""
            self._build_ui()
            self._poll_live_state()
            self._timer = QTimer(self)
            self._timer.setInterval(750)
            self._timer.timeout.connect(self._poll_live_state)
            self._timer.start()

        def closeEvent(self, event: QCloseEvent) -> None:
            self._timer.stop()
            self._bridge.stop_live_updates()
            super().closeEvent(event)

        def _build_ui(self) -> None:
            central = QWidget()
            central.setObjectName("centralCanvas")
            root = QVBoxLayout()
            root.setContentsMargins(24, 24, 24, 24)
            root.setSpacing(18)
            central.setLayout(root)
            self.setCentralWidget(central)

            hero = QGroupBox("Command Deck")
            hero.setObjectName("heroPanel")
            hero_layout = QVBoxLayout()
            hero_layout.setSpacing(12)
            hero.setLayout(hero_layout)
            title = QLabel("ROX Daily Claim Command Deck")
            title.setObjectName("heroTitle")
            subtitle = QLabel(
                "Single-task operator cockpit for daily claim runs across the fleet. "
                "The first screen stays focused on live queue state, current step, failure cause, and the next move."
            )
            subtitle.setObjectName("heroSubtitle")
            hero_layout.addWidget(title)
            hero_layout.addWidget(subtitle)
            self.banner_label = QLabel("")
            self.banner_label.setObjectName("statusBanner")
            self.banner_label.setWordWrap(True)
            hero_layout.addWidget(self.banner_label)
            metrics = QGridLayout()
            metrics.setHorizontalSpacing(12)
            metrics.setVerticalSpacing(12)
            self.metric_total = self._metric_card(metrics, 0, 0, "Fleet")
            self.metric_ready = self._metric_card(metrics, 0, 1, "Ready")
            self.metric_queue = self._metric_card(metrics, 0, 2, "Queued")
            self.metric_failure = self._metric_card(metrics, 0, 3, "Failures")
            hero_layout.addLayout(metrics)
            self.hero_meta = QLabel("")
            self.hero_meta.setObjectName("secondaryText")
            self.hero_meta.setWordWrap(True)
            hero_layout.addWidget(self.hero_meta)
            root.addWidget(hero)

            body = QSplitter()
            body.setChildrenCollapsible(False)
            body.setHandleWidth(10)
            root.addWidget(body)

            left = QGroupBox("Fleet")
            left.setObjectName("panelCard")
            left_layout = QVBoxLayout()
            left.setLayout(left_layout)
            self.instance_summary = QLabel("")
            self.instance_summary.setObjectName("secondaryText")
            self.instance_summary.setWordWrap(True)
            left_layout.addWidget(self.instance_summary)
            self.instance_list = QListWidget()
            self.instance_list.setObjectName("instanceList")
            self.instance_list.itemSelectionChanged.connect(self._on_instance_selected)
            left_layout.addWidget(self.instance_list)
            body.addWidget(left)

            right = QWidget()
            right_layout = QVBoxLayout()
            right_layout.setSpacing(14)
            right.setLayout(right_layout)
            body.addWidget(right)
            body.setSizes([360, 1120])

            device_box = QGroupBox("Selected Instance")
            device_box.setObjectName("panelCard")
            device_layout = QVBoxLayout()
            device_box.setLayout(device_layout)
            self.instance_title = QLabel("No instance selected")
            self.instance_title.setObjectName("sectionTitle")
            device_layout.addWidget(self.instance_title)
            self.connection_label = QLabel("")
            self.connection_label.setWordWrap(True)
            self.profile_label = QLabel("")
            self.profile_label.setWordWrap(True)
            self.runtime_label = QLabel("")
            self.runtime_label.setWordWrap(True)
            self.warning_label = QLabel("")
            self.warning_label.setObjectName("warningText")
            self.warning_label.setWordWrap(True)
            device_layout.addWidget(self.connection_label)
            device_layout.addWidget(self.profile_label)
            device_layout.addWidget(self.runtime_label)
            device_layout.addWidget(self.warning_label)
            action_row = QHBoxLayout()
            self.refresh_button = QPushButton("Sync Now")
            self.refresh_button.setObjectName("secondaryButton")
            self.refresh_button.clicked.connect(self._schedule_refresh)
            self.start_button = QPushButton("Start Queue")
            self.start_button.setObjectName("primaryButton")
            self.start_button.clicked.connect(lambda: self._schedule_command("start_queue"))
            self.stop_button = QPushButton("Stop Task")
            self.stop_button.setObjectName("secondaryButton")
            self.stop_button.clicked.connect(lambda: self._schedule_command("stop"))
            self.emergency_button = QPushButton("Emergency Stop")
            self.emergency_button.setObjectName("dangerButton")
            self.emergency_button.clicked.connect(self._schedule_emergency_stop)
            for button in (self.refresh_button, self.start_button, self.stop_button, self.emergency_button):
                action_row.addWidget(button)
            action_row.addStretch(1)
            device_layout.addLayout(action_row)
            right_layout.addWidget(device_box)

            claim_box = QGroupBox("Daily Claim Flow")
            claim_box.setObjectName("panelCard")
            claim_layout = QVBoxLayout()
            claim_box.setLayout(claim_layout)
            self.claim_header = QLabel("")
            self.claim_header.setObjectName("sectionTitle")
            self.claim_header.setWordWrap(True)
            self.claim_overview = QLabel("")
            self.claim_overview.setObjectName("secondaryText")
            self.claim_overview.setWordWrap(True)
            claim_focus = QGridLayout()
            claim_focus.setHorizontalSpacing(10)
            claim_focus.setVerticalSpacing(10)
            self.claim_focus_step = self._detail_card(claim_focus, 0, 0, "Current Step")
            self.claim_focus_anchor = self._detail_card(claim_focus, 0, 1, "Primary Anchor")
            self.claim_focus_region = self._detail_card(claim_focus, 1, 0, "Match Region")
            self.claim_focus_threshold = self._detail_card(claim_focus, 1, 1, "Threshold")
            self.claim_progress = QProgressBar()
            self.claim_progress.setMinimumHeight(28)
            self.claim_progress.setTextVisible(True)
            self.claim_status = QPlainTextEdit()
            self.claim_status.setObjectName("workflowConsole")
            self.claim_status.setReadOnly(True)
            self.claim_status.setMaximumHeight(150)
            claim_actions = QHBoxLayout()
            self.claim_queue_button = QPushButton("Queue Claim")
            self.claim_queue_button.setObjectName("secondaryButton")
            self.claim_queue_button.clicked.connect(self._schedule_claim_queue)
            self.claim_run_button = QPushButton("Run Claim Now")
            self.claim_run_button.setObjectName("primaryButton")
            self.claim_run_button.clicked.connect(self._schedule_claim_run)
            claim_actions.addWidget(self.claim_queue_button)
            claim_actions.addWidget(self.claim_run_button)
            claim_actions.addStretch(1)
            self.claim_steps = QListWidget()
            self.claim_steps.setObjectName("stepList")
            claim_layout.addWidget(self.claim_header)
            claim_layout.addWidget(self.claim_overview)
            claim_layout.addLayout(claim_focus)
            claim_layout.addWidget(self.claim_progress)
            claim_layout.addWidget(self.claim_status)
            claim_layout.addLayout(claim_actions)
            claim_layout.addWidget(self.claim_steps)
            right_layout.addWidget(claim_box, 1)

            tabs = QTabWidget()
            tabs.setObjectName("insightTabs")
            tabs.setDocumentMode(True)
            right_layout.addWidget(tabs, 1)

            preview_tab = QWidget()
            preview_layout = QVBoxLayout()
            preview_tab.setLayout(preview_layout)
            self.preview_summary = QLabel("")
            self.preview_summary.setObjectName("secondaryText")
            self.preview_summary.setWordWrap(True)
            self.preview_image = QLabel("No preview frame captured.")
            self.preview_image.setObjectName("previewFrame")
            self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview_image.setMinimumHeight(260)
            self.preview_image.setWordWrap(True)
            self.preview_box = QPlainTextEdit()
            self.preview_box.setObjectName("insightConsole")
            self.preview_box.setReadOnly(True)
            preview_layout.addWidget(self.preview_summary)
            preview_layout.addWidget(self.preview_image)
            preview_layout.addWidget(self.preview_box)
            tabs.addTab(preview_tab, "Preview Feed")

            failure_tab = QWidget()
            failure_layout = QVBoxLayout()
            failure_tab.setLayout(failure_layout)
            self.failure_summary = QLabel("")
            self.failure_summary.setObjectName("secondaryText")
            self.failure_summary.setWordWrap(True)
            self.failure_box = QPlainTextEdit()
            self.failure_box.setObjectName("insightConsole")
            self.failure_box.setReadOnly(True)
            failure_layout.addWidget(self.failure_summary)
            failure_layout.addWidget(self.failure_box)
            tabs.addTab(failure_tab, "Failure Story")

            readiness_tab = QWidget()
            readiness_layout = QVBoxLayout()
            readiness_tab.setLayout(readiness_layout)
            self.readiness_summary = QLabel("")
            self.readiness_summary.setObjectName("secondaryText")
            self.readiness_summary.setWordWrap(True)
            self.readiness_box = QPlainTextEdit()
            self.readiness_box.setObjectName("insightConsole")
            self.readiness_box.setReadOnly(True)
            readiness_layout.addWidget(self.readiness_summary)
            readiness_layout.addWidget(self.readiness_box)
            tabs.addTab(readiness_tab, "Readiness")

            calibration_tab = QWidget()
            calibration_layout = QVBoxLayout()
            calibration_tab.setLayout(calibration_layout)
            self.editor_summary = QLabel(
                "Use this lab to capture fresh evidence or tune calibration. "
                "It does not rewrite the runtime-owned daily-claim workflow."
            )
            self.editor_summary.setObjectName("secondaryText")
            self.editor_summary.setWordWrap(True)
            calibration_layout.addWidget(self.editor_summary)
            form = QFormLayout()
            self.mode_combo = QComboBox()
            self.mode_combo.addItem("Claimable", "claimable")
            self.mode_combo.addItem("Already claimed", "already_claimed")
            self.mode_combo.addItem("Ambiguous", "ambiguous")
            self.mode_combo.addItem("Panel missing", "panel_missing")
            self.crop_input = QLineEdit()
            self.match_input = QLineEdit()
            self.threshold_input = QLineEdit()
            self.scale_input = QLineEdit()
            self.offset_input = QLineEdit()
            form.addRow("Workflow mode (diagnostic only)", self.mode_combo)
            form.addRow("Crop region", self.crop_input)
            form.addRow("Match region", self.match_input)
            form.addRow("Confidence threshold", self.threshold_input)
            form.addRow("Capture scale", self.scale_input)
            form.addRow("Capture offset", self.offset_input)
            calibration_layout.addLayout(form)
            self._editor_widgets = [
                self.mode_combo,
                self.crop_input,
                self.match_input,
                self.threshold_input,
                self.scale_input,
                self.offset_input,
            ]
            editor_actions = QHBoxLayout()
            self.capture_preview_button = QPushButton("Capture Preview")
            self.capture_preview_button.setObjectName("secondaryButton")
            self.capture_preview_button.clicked.connect(lambda: self._schedule_claim_capture("preview"))
            self.capture_failure_button = QPushButton("Capture Failure")
            self.capture_failure_button.setObjectName("secondaryButton")
            self.capture_failure_button.clicked.connect(lambda: self._schedule_claim_capture("failure"))
            self.apply_button = QPushButton("Apply Draft")
            self.apply_button.setObjectName("primaryButton")
            self.apply_button.clicked.connect(self._apply_editor)
            self.save_button = QPushButton("Save Draft")
            self.save_button.setObjectName("secondaryButton")
            self.save_button.clicked.connect(self._save_editor)
            self.reset_button = QPushButton("Reset Draft")
            self.reset_button.setObjectName("secondaryButton")
            self.reset_button.clicked.connect(self._reset_editor)
            for button in (
                self.capture_preview_button,
                self.capture_failure_button,
                self.apply_button,
                self.save_button,
                self.reset_button,
            ):
                editor_actions.addWidget(button)
            editor_actions.addStretch(1)
            calibration_layout.addLayout(editor_actions)
            self.calibration_box = QPlainTextEdit()
            self.calibration_box.setObjectName("insightConsole")
            self.calibration_box.setReadOnly(True)
            calibration_layout.addWidget(self.calibration_box)
            tabs.addTab(calibration_tab, "Calibration Lab")

        def _metric_card(self, layout: QGridLayout, row: int, column: int, title: str) -> QLabel:
            card = QGroupBox(title)
            card.setObjectName("summaryCard")
            card_layout = QVBoxLayout()
            card.setLayout(card_layout)
            value = QLabel("0")
            value.setObjectName("metricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(value)
            layout.addWidget(card, row, column)
            return value

        def _detail_card(self, layout: QGridLayout, row: int, column: int, title: str) -> QLabel:
            card = QGroupBox(title)
            card.setObjectName("summaryCard")
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(8, 10, 8, 8)
            card.setLayout(card_layout)
            value = QLabel("-")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            value.setMinimumHeight(36)
            card_layout.addWidget(value)
            layout.addWidget(card, row, column)
            return value

        def _poll_live_state(self) -> None:
            state = self._bridge.get_live_state(self._selected_instance_id)
            self._selected_instance_id = state.selected_instance_id
            self._render_state(state)

        def _render_state(self, state: OperatorConsoleState) -> None:
            self.banner_label.setText(state.summary.global_status_message)
            self.metric_total.setText(str(state.summary.total_instances))
            self.metric_ready.setText(str(state.summary.ready_count))
            self.metric_queue.setText(str(state.summary.queued_count))
            self.metric_failure.setText(str(state.summary.failure_count))
            self.hero_meta.setText(
                f"ADB: {state.snapshot.adb_path} | "
                f"Last sync: {'healthy' if state.runtime_snapshot.last_sync_ok else 'failed'} | "
                f"Last queue result: {state.queue.last_queue_status or 'idle'}"
            )
            self._render_instance_list(state)
            self._render_selected_instance(state)
            self._render_claim_rewards(state)
            self._render_preview(state)
            self._render_failure(state)
            self._render_readiness(state)
            self._render_calibration(state)

        def _render_instance_list(self, state: OperatorConsoleState) -> None:
            self.instance_summary.setText(
                f"{len(state.instance_rows)} instances in the fleet. "
                "Each card shows connection state, queue depth, active task, and health."
            )
            wanted_ids = [row.instance_id for row in state.instance_rows]
            current_ids = [self.instance_list.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.instance_list.count())]
            if current_ids != wanted_ids:
                self._list_syncing = True
                self.instance_list.clear()
                for row in state.instance_rows:
                    warning = f"\nWarning: {_zh_health(row.warning)}" if row.warning else ""
                    active_task = _zh_task(row.active_task_id) if row.active_task_id else "-"
                    item = QListWidgetItem(
                        f"{row.label}\n"
                        f"{_zh_status(row.status)} | {_zh_health(row.health_summary)}\n"
                        f"Queue {row.queue_depth} | {active_task}\n"
                        f"{row.profile_summary or row.subtitle}{warning}"
                    )
                    item.setData(Qt.ItemDataRole.UserRole, row.instance_id)
                    self.instance_list.addItem(item)
                self._list_syncing = False
            self._list_syncing = True
            for index in range(self.instance_list.count()):
                item = self.instance_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == state.selected_instance_id:
                    self.instance_list.setCurrentItem(item)
                    break
            self._list_syncing = False

        def _render_selected_instance(self, state: OperatorConsoleState) -> None:
            snapshot = state.selected_instance_snapshot
            if snapshot is None:
                self.instance_title.setText("No instance selected")
                self.connection_label.setText("Pick an emulator from the fleet list to unlock the control surface.")
                self.profile_label.setText("")
                self.runtime_label.setText("")
                self.warning_label.setText("")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                return
            active_task = snapshot.context.active_task_id if snapshot.context is not None else ""
            profile = snapshot.profile_binding.display_name if snapshot.profile_binding is not None else "-"
            self.instance_title.setText(snapshot.instance.label)
            self.connection_label.setText(f"Connection: {_zh_status(state.detail.status)} | {state.detail.adb_serial}")
            self.profile_label.setText(f"Profile: {profile}")
            self.runtime_label.setText(
                f"Runtime: {_zh_task(active_task) if active_task else '-'} | "
                f"queue={state.detail.queue_depth} | {_zh_health(state.detail.inspection_summary)}"
            )
            self.warning_label.setText(state.detail.warning)
            controls = {item.action_key: item for item in state.manual_controls.available_actions}
            self.start_button.setEnabled(controls.get("start_queue").enabled if "start_queue" in controls else False)
            self.stop_button.setEnabled(controls.get("stop").enabled if "stop" in controls else False)

        def _render_claim_rewards(self, state: OperatorConsoleState) -> None:
            claim = state.claim_rewards
            claim_task_id = str(getattr(claim, "task_id", "") or "")
            task_label = _zh_task(claim_task_id) if claim_task_id else (claim.task_label or "-")
            self.claim_header.setText(f"{task_label} | {_zh_status(claim.workflow_status)}")
            overview_lines = [
                claim.active_step_summary or "-",
                f"Next action: {claim.next_action_summary or '-'}",
                claim.workflow_banner or "-",
            ]
            self.claim_overview.setText("\n".join(overview_lines))
            self.claim_focus_step.setText(claim.focus_step_summary or "-")
            self.claim_focus_anchor.setText(claim.focus_anchor_summary or "-")
            self.claim_focus_region.setText(claim.focus_region_summary or "-")
            self.claim_focus_threshold.setText(claim.focus_threshold_summary or "-")
            total_steps = max(1, claim.progress_total_count or len(claim.step_rows) or 1)
            self.claim_progress.setMaximum(total_steps)
            self.claim_progress.setValue(min(claim.progress_completed_count, total_steps))
            self.claim_progress.setFormat(f"{claim.progress_completed_count}/{claim.progress_total_count or len(claim.step_rows)}")
            self.claim_status.setPlainText(
                "\n".join(
                    [
                        f"Failure check: {claim.failure_check_summary or 'No failing visual check selected.'}",
                        f"Provenance: {claim.selected_provenance_summary or '-'}",
                        f"Curation: {claim.selected_curation_summary or '-'}",
                        f"Failure explanation: {claim.failure_explanation or '-'}",
                        f"Next action: {claim.next_action_summary or '-'}",
                        f"Runtime gate: {claim.runtime_gate_summary or '-'}",
                        f"Queue state: {claim.queue_summary or '-'}",
                        f"Last run: {claim.last_run_summary or '-'}",
                        f"Failure reason: {claim.failure_reason or claim.failure_summary or '-'}",
                        f"Scope: {claim.selected_scope_summary or '-'}",
                        f"Preset: {claim.preset_summary or '-'}",
                    ]
                )
            )
            self.claim_steps.clear()
            status_labels = {
                "pending": "Pending",
                "running": "Running",
                "succeeded": "Succeeded",
                "failed": "Failed",
                "skipped": "Skipped",
            }
            for row in claim.step_rows:
                prefix = row.status_text or status_labels.get(row.status, row.status)
                summary = row.summary or row.success_condition or row.failure_condition or "-"
                self.claim_steps.addItem(QListWidgetItem(f"{prefix} | {row.title}\n{summary}"))
            self.claim_queue_button.setEnabled(claim.can_queue)
            self.claim_run_button.setEnabled(claim.can_run_now)

        def _render_preview(self, state: OperatorConsoleState) -> None:
            preview = state.vision.preview
            image_path = preview.image_path if preview is not None else ""
            overlay = preview.selected_overlay_summary if preview is not None else ""
            self.preview_summary.setText(f"Source frame: {image_path or '-'} | Overlay focus: {overlay or '-'}")
            lines = [
                f"Preview summary: {state.claim_rewards.preview_summary or '-'}",
                f"Scope: {state.claim_rewards.selected_scope_summary or '-'}",
            ]
            if preview is not None:
                for key, value in sorted(preview.metadata.items()):
                    lines.append(f"{key}: {value}")
            self.preview_box.setPlainText("\n".join(lines))
            if image_path and Path(image_path).exists():
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.preview_image.setPixmap(
                        pixmap.scaled(
                            self.preview_image.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    self.preview_image.setText("")
                    return
            self.preview_image.setPixmap(QPixmap())
            self.preview_image.setText("No preview frame captured.")

        def _render_failure(self, state: OperatorConsoleState) -> None:
            claim_failure = state.vision.failure.claim_rewards
            self.failure_summary.setText(
                f"Failure state: {state.claim_rewards.failure_summary or '-'} | "
                f"Step: {state.claim_rewards.current_step_title or state.claim_rewards.failure_step_id or '-'}"
            )
            if claim_failure is None:
                self.failure_box.setPlainText("No claim-rewards failure snapshot is available.")
                return
            selected = claim_failure.selected_check
            lines = [
                f"Current step: {state.claim_rewards.focus_step_summary or '-'}",
                f"Primary anchor: {state.claim_rewards.focus_anchor_summary or '-'}",
                f"Match region: {state.claim_rewards.focus_region_summary or '-'}",
                f"Threshold: {state.claim_rewards.focus_threshold_summary or '-'}",
                f"Failure check: {state.claim_rewards.failure_check_summary or '-'}",
                f"Selected check: {state.claim_rewards.selected_anchor_summary or '-'}",
                f"Provenance: {state.claim_rewards.selected_provenance_summary or '-'}",
                f"Curation: {state.claim_rewards.selected_curation_summary or '-'}",
                f"Failure explanation: {state.claim_rewards.failure_explanation or '-'}",
                f"Next action: {state.claim_rewards.next_action_summary or '-'}",
                f"Failure detail: {state.claim_rewards.failure_check_summary or state.claim_rewards.failure_summary or '-'}",
                f"Check coverage: matched {claim_failure.matched_check_count} / missing {claim_failure.missing_check_count}",
                "Inspector note: template paths, reference images, and tuning values below are viewer-first diagnostics for calibration and review.",
            ]
            if selected is not None:
                resolution = selected.calibration_resolution
                threshold = (
                    resolution.effective_confidence_threshold
                    if resolution is not None
                    else selected.threshold
                )
                region = (
                    ",".join(str(value) for value in resolution.effective_match_region)
                    if resolution is not None and resolution.effective_match_region is not None
                    else "-"
                )
                lines.extend(
                    [
                        f"Anchor label: {selected.anchor_label or selected.label or '-'} | {selected.anchor_id}",
                        f"Stage: {state.claim_rewards.current_step_title or selected.stage or '-'}",
                        f"Match status: {_zh_match_status(selected.status.value)}",
                        f"Effective threshold: {threshold:.2f}",
                        f"Effective match region: {region}",
                        f"Template path: {selected.selected_template_path or '-'}",
                        f"Reference image: {selected.selected_reference_image_path or '-'}",
                        f"Best candidate: {selected.best_candidate_summary or '-'}",
                        f"Matched candidate: {selected.matched_candidate_summary or '-'}",
                        f"Overlay summary: {selected.inspection.selected_overlay_summary if selected.inspection is not None else '-'}",
                    ]
                )
            self.failure_box.setPlainText("\n".join(lines))

        def _render_readiness(self, state: OperatorConsoleState) -> None:
            row = _claim_readiness_row(state)
            self.readiness_summary.setText(
                f"Builder ready: {state.task_readiness.builder_ready_count}/{state.task_readiness.total_tasks} | "
                f"Implementation ready: {state.task_readiness.implementation_ready_count}/{state.task_readiness.total_tasks}"
            )
            if row is None:
                self.readiness_box.setPlainText("No readiness report is available for daily claim.")
                return
            self.readiness_box.setPlainText(
                "\n".join(
                    [
                        f"Manifest: {row.manifest_path}",
                        f"Builder state: {row.builder_state}",
                        f"Implementation state: {row.implementation_state}",
                        f"Runnable now: {'yes' if row.implementation_state == 'ready' else 'no'}",
                        f"Scope reasons: {', '.join(row.scope_reasons) or '-'}",
                        f"Required anchors: {', '.join(row.required_anchors) or '-'}",
                        f"Fixture profiles: {', '.join(row.fixture_profile_paths) or '-'}",
                        f"Runtime requirements: {', '.join(row.runtime_requirement_ids) or '-'}",
                        f"Warnings: {'; '.join(row.warnings) or '-'}",
                        f"Implementation blockers: {'; '.join(row.implementation_blockers) or '-'}",
                    ]
                )
            )

        def _render_calibration(self, state: OperatorConsoleState) -> None:
            if not any(widget.hasFocus() for widget in self._editor_widgets):
                editor = state.claim_rewards.editor
                index = self.mode_combo.findData(editor.workflow_mode)
                if index >= 0:
                    self.mode_combo.setCurrentIndex(index)
                self.crop_input.setText(editor.crop_region_text)
                self.match_input.setText(editor.match_region_text)
                self.threshold_input.setText(editor.confidence_threshold_text)
                self.scale_input.setText(editor.capture_scale_text)
                self.offset_input.setText(editor.capture_offset_text)
            calibration = state.vision.calibration
            capture = state.vision.capture
            lines = [
                f"Selected source: {state.claim_rewards.editor.selected_source_kind}",
                f"Source image: {state.claim_rewards.editor.selected_source_image or '-'}",
                f"Artifact count: {state.claim_rewards.editor.artifact_count}",
                f"Last applied draft: {state.claim_rewards.editor.last_applied_summary or '-'}",
                f"Persistence: {state.claim_rewards.editor.persistence_summary or '-'}",
                f"Focused anchor: {state.claim_rewards.selected_anchor_summary or '-'}",
                f"Selected artifact: {capture.selected_artifact_summary or '-'}",
                f"Scale summary: {calibration.scale_summary or '-'}",
                f"Offset summary: {calibration.offset_summary or '-'}",
                f"Crop summary: {calibration.crop_summary or '-'}",
            ]
            if calibration.selected_resolution is not None:
                lines.extend(
                    [
                        f"Selected anchor id: {calibration.selected_resolution.anchor_id}",
                        f"Effective threshold: {calibration.selected_resolution.effective_confidence_threshold:.2f}",
                        f"Effective match region: {calibration.selected_resolution.effective_match_region}",
                    ]
                )
            self.calibration_box.setPlainText("\n".join(lines))

        def _on_instance_selected(self) -> None:
            if self._list_syncing:
                return
            item = self.instance_list.currentItem()
            self._selected_instance_id = str(item.data(Qt.ItemDataRole.UserRole)) if item is not None else ""
            self._poll_live_state()

        def _require_instance(self) -> str | None:
            if not self._selected_instance_id:
                QMessageBox.warning(self, "No instance selected", "Pick an emulator from the fleet list first.")
                return None
            return self._selected_instance_id

        def _schedule_refresh(self) -> None:
            self._bridge.schedule_refresh(instance_id=self._selected_instance_id or None, run_health_check=True, capture_preview=True)

        def _schedule_command(self, action_key: str) -> None:
            instance_id = self._require_instance()
            if instance_id is None:
                return
            self._bridge.schedule_command(action_key, instance_id=instance_id)

        def _schedule_emergency_stop(self) -> None:
            self._bridge.schedule_command("emergency_stop")

        def _schedule_claim_queue(self) -> None:
            instance_id = self._require_instance()
            if instance_id is None:
                return
            self._bridge.schedule_claim_rewards_queue(instance_id)

        def _schedule_claim_run(self) -> None:
            instance_id = self._require_instance()
            if instance_id is None:
                return
            self._bridge.schedule_claim_rewards_run(instance_id)

        def _schedule_claim_capture(self, source_kind: str) -> None:
            instance_id = self._require_instance()
            if instance_id is None:
                return
            self._bridge.schedule_claim_rewards_capture_source(instance_id, source_kind=source_kind)

        def _apply_editor(self) -> None:
            instance_id = self._require_instance()
            if instance_id is None:
                return
            try:
                self._bridge.schedule_claim_rewards_editor_update(
                    instance_id,
                    workflow_mode=str(self.mode_combo.currentData() or "claimable"),
                    crop_region=_parse_optional_region(self.crop_input.text()),
                    match_region=_parse_optional_region(self.match_input.text()),
                    confidence_threshold=_parse_optional_float(self.threshold_input.text()),
                    capture_scale=_parse_optional_float(self.scale_input.text()),
                    capture_offset=_parse_optional_point(self.offset_input.text()),
                )
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid draft format", str(exc))

        def _reset_editor(self) -> None:
            instance_id = self._require_instance()
            if instance_id is None:
                return
            self._bridge.schedule_claim_rewards_editor_reset(instance_id)

        def _save_editor(self) -> None:
            instance_id = self._require_instance()
            if instance_id is None:
                return
            self._bridge.schedule_claim_rewards_editor_save(instance_id)

    app.aboutToQuit.connect(bridge.stop_live_updates)
    window = MainWindow(bridge)
    window.show()
    return app.exec()
