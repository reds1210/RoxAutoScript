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
        "idle": "\u5f85\u547d",
        "queued": "\u5df2\u6392\u5165",
        "running": "\u57f7\u884c\u4e2d",
        "succeeded": "\u5b8c\u6210",
        "failed": "\u5931\u6557",
        "aborted": "\u4e2d\u6b62",
        "ready": "\u5c31\u7dd2",
        "busy": "\u5de5\u4f5c\u4e2d",
        "paused": "\u5df2\u66ab\u505c",
        "error": "\u7570\u5e38",
        "disconnected": "\u96e2\u7dda",
        "connecting": "\u9023\u7dda\u4e2d",
    }
    return labels.get(value.lower(), value)


def _zh_task(task_id: str) -> str:
    return "\u6bcf\u65e5\u9818\u734e" if task_id == "daily_ui.claim_rewards" else task_id


def _zh_health(value: str) -> str:
    replacements = {
        "healthy": "\u5065\u5eb7",
        "health unknown": "\u5c1a\u672a\u6aa2\u67e5",
        "health check failed": "\u5065\u5eb7\u6aa2\u67e5\u5931\u6557",
        "runtime error": "\u57f7\u884c\u968e\u6bb5\u7570\u5e38",
        "stop requested": "\u5df2\u8981\u6c42\u505c\u6b62",
    }
    translated = value
    for source, target in replacements.items():
        translated = translated.replace(source, target)
    return translated


def _zh_match_status(value: str) -> str:
    labels = {
        "matched": "\u5df2\u547d\u4e2d",
        "missed": "\u672a\u547d\u4e2d",
        "ambiguous": "\u7d50\u679c\u4e0d\u660e",
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
            self.setWindowTitle("ROX \u6bcf\u65e5\u9818\u734e\u63a7\u5236\u53f0")
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
            root = QVBoxLayout()
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(16)
            central.setLayout(root)
            self.setCentralWidget(central)

            hero = QGroupBox("MVP Console")
            hero.setObjectName("heroPanel")
            hero_layout = QVBoxLayout()
            hero.setLayout(hero_layout)
            title = QLabel("ROX \u6bcf\u65e5\u9818\u734e\u63a7\u5236\u53f0")
            title.setObjectName("heroTitle")
            subtitle = QLabel("\u4ee5\u300c\u6bcf\u65e5\u9818\u734e\u300d\u70ba\u4e3b\u7684\u55ae\u4efb\u52d9\u63a7\u5236\u53f0\uff0c\u512a\u5148\u986f\u793a\u76ee\u524d\u6b65\u9a5f\u3001\u5931\u6557\u539f\u56e0\u8207\u4e0b\u4e00\u6b65\u3002")
            subtitle.setObjectName("heroSubtitle")
            hero_layout.addWidget(title)
            hero_layout.addWidget(subtitle)
            self.banner_label = QLabel("")
            self.banner_label.setObjectName("statusBanner")
            self.banner_label.setWordWrap(True)
            hero_layout.addWidget(self.banner_label)
            metrics = QGridLayout()
            self.metric_total = self._metric_card(metrics, 0, 0, "\u6a21\u64ec\u5668")
            self.metric_ready = self._metric_card(metrics, 0, 1, "\u5df2\u9023\u7dda")
            self.metric_queue = self._metric_card(metrics, 0, 2, "\u4f47\u5217")
            self.metric_failure = self._metric_card(metrics, 0, 3, "\u5931\u6557")
            hero_layout.addLayout(metrics)
            self.hero_meta = QLabel("")
            self.hero_meta.setObjectName("secondaryText")
            self.hero_meta.setWordWrap(True)
            hero_layout.addWidget(self.hero_meta)
            root.addWidget(hero)

            body = QSplitter()
            body.setChildrenCollapsible(False)
            root.addWidget(body)

            left = QGroupBox("\u6a21\u64ec\u5668")
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

            device_box = QGroupBox("\u57f7\u884c\u5c0d\u8c61")
            device_box.setObjectName("panelCard")
            device_layout = QVBoxLayout()
            device_box.setLayout(device_layout)
            self.instance_title = QLabel("\u5c1a\u672a\u9078\u53d6\u6a21\u64ec\u5668")
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
            self.refresh_button = QPushButton("\u91cd\u65b0\u540c\u6b65")
            self.refresh_button.setObjectName("secondaryButton")
            self.refresh_button.clicked.connect(self._schedule_refresh)
            self.start_button = QPushButton("\u555f\u52d5\u4f47\u5217")
            self.start_button.setObjectName("primaryButton")
            self.start_button.clicked.connect(lambda: self._schedule_command("start_queue"))
            self.stop_button = QPushButton("\u505c\u6b62\u4efb\u52d9")
            self.stop_button.setObjectName("secondaryButton")
            self.stop_button.clicked.connect(lambda: self._schedule_command("stop"))
            self.emergency_button = QPushButton("\u5168\u57df\u505c\u6b62")
            self.emergency_button.setObjectName("dangerButton")
            self.emergency_button.clicked.connect(self._schedule_emergency_stop)
            for button in (self.refresh_button, self.start_button, self.stop_button, self.emergency_button):
                action_row.addWidget(button)
            action_row.addStretch(1)
            device_layout.addLayout(action_row)
            right_layout.addWidget(device_box)

            claim_box = QGroupBox("\u6bcf\u65e5\u9818\u734e")
            claim_box.setObjectName("panelCard")
            claim_layout = QVBoxLayout()
            claim_box.setLayout(claim_layout)
            self.claim_header = QLabel("")
            self.claim_header.setObjectName("sectionTitle")
            self.claim_header.setWordWrap(True)
            self.claim_overview = QLabel("")
            self.claim_overview.setObjectName("secondaryText")
            self.claim_overview.setWordWrap(True)
            self.claim_progress = QProgressBar()
            self.claim_progress.setMinimumHeight(28)
            self.claim_progress.setTextVisible(True)
            self.claim_status = QPlainTextEdit()
            self.claim_status.setReadOnly(True)
            self.claim_status.setMaximumHeight(140)
            claim_actions = QHBoxLayout()
            self.claim_queue_button = QPushButton("\u52a0\u5165\u4f47\u5217")
            self.claim_queue_button.setObjectName("secondaryButton")
            self.claim_queue_button.clicked.connect(self._schedule_claim_queue)
            self.claim_run_button = QPushButton("\u7acb\u5373\u57f7\u884c")
            self.claim_run_button.setObjectName("primaryButton")
            self.claim_run_button.clicked.connect(self._schedule_claim_run)
            claim_actions.addWidget(self.claim_queue_button)
            claim_actions.addWidget(self.claim_run_button)
            claim_actions.addStretch(1)
            self.claim_steps = QListWidget()
            self.claim_steps.setObjectName("stepList")
            claim_layout.addWidget(self.claim_header)
            claim_layout.addWidget(self.claim_overview)
            claim_layout.addWidget(self.claim_progress)
            claim_layout.addWidget(self.claim_status)
            claim_layout.addLayout(claim_actions)
            claim_layout.addWidget(self.claim_steps)
            right_layout.addWidget(claim_box, 1)

            tabs = QTabWidget()
            right_layout.addWidget(tabs, 1)

            preview_tab = QWidget()
            preview_layout = QVBoxLayout()
            preview_tab.setLayout(preview_layout)
            self.preview_summary = QLabel("")
            self.preview_summary.setObjectName("secondaryText")
            self.preview_summary.setWordWrap(True)
            self.preview_image = QLabel("\u5c1a\u7121\u9810\u89bd")
            self.preview_image.setObjectName("previewFrame")
            self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview_image.setMinimumHeight(260)
            self.preview_image.setWordWrap(True)
            self.preview_box = QPlainTextEdit()
            self.preview_box.setReadOnly(True)
            preview_layout.addWidget(self.preview_summary)
            preview_layout.addWidget(self.preview_image)
            preview_layout.addWidget(self.preview_box)
            tabs.addTab(preview_tab, "\u76ee\u524d\u756b\u9762")

            failure_tab = QWidget()
            failure_layout = QVBoxLayout()
            failure_tab.setLayout(failure_layout)
            self.failure_summary = QLabel("")
            self.failure_summary.setObjectName("secondaryText")
            self.failure_summary.setWordWrap(True)
            self.failure_box = QPlainTextEdit()
            self.failure_box.setReadOnly(True)
            failure_layout.addWidget(self.failure_summary)
            failure_layout.addWidget(self.failure_box)
            tabs.addTab(failure_tab, "\u5361\u95dc\u8a3a\u65b7")

            readiness_tab = QWidget()
            readiness_layout = QVBoxLayout()
            readiness_tab.setLayout(readiness_layout)
            self.readiness_summary = QLabel("")
            self.readiness_summary.setObjectName("secondaryText")
            self.readiness_summary.setWordWrap(True)
            self.readiness_box = QPlainTextEdit()
            self.readiness_box.setReadOnly(True)
            readiness_layout.addWidget(self.readiness_summary)
            readiness_layout.addWidget(self.readiness_box)
            tabs.addTab(readiness_tab, "\u57f7\u884c\u689d\u4ef6")

            calibration_tab = QWidget()
            calibration_layout = QVBoxLayout()
            calibration_tab.setLayout(calibration_layout)
            self.editor_summary = QLabel("\u9019\u88e1\u53ea\u7528\u4f86\u91cd\u65b0\u64f7\u53d6\u6a23\u672c\u6216\u8abf\u6574\u6821\u6e96\uff0c\u4e0d\u6703\u6539\u8b8a runtime \u5df2\u5b9a\u7fa9\u7684\u6bcf\u65e5\u9818\u734e\u6d41\u7a0b\u3002")
            self.editor_summary.setObjectName("secondaryText")
            self.editor_summary.setWordWrap(True)
            calibration_layout.addWidget(self.editor_summary)
            form = QFormLayout()
            self.mode_combo = QComboBox()
            self.mode_combo.addItem("\u53ef\u76f4\u63a5\u9818\u53d6", "claimable")
            self.mode_combo.addItem("\u5df2\u9818\u53d6", "already_claimed")
            self.mode_combo.addItem("\u72c0\u614b\u6a21\u7cca", "ambiguous")
            self.mode_combo.addItem("\u9762\u677f\u672a\u958b\u555f", "panel_missing")
            self.crop_input = QLineEdit()
            self.match_input = QLineEdit()
            self.threshold_input = QLineEdit()
            self.scale_input = QLineEdit()
            self.offset_input = QLineEdit()
            form.addRow("\u6aa2\u8996\u6a21\u5f0f\uff08\u50c5\u8a3a\u65b7\uff09", self.mode_combo)
            form.addRow("\u88c1\u5207\u5340\u57df", self.crop_input)
            form.addRow("\u6bd4\u5c0d\u5340\u57df", self.match_input)
            form.addRow("\u4fe1\u5fc3\u9580\u6abb", self.threshold_input)
            form.addRow("\u64f7\u53d6\u7e2e\u653e", self.scale_input)
            form.addRow("\u64f7\u53d6\u504f\u79fb", self.offset_input)
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
            self.capture_preview_button = QPushButton("\u64f7\u53d6\u76ee\u524d\u756b\u9762")
            self.capture_preview_button.setObjectName("secondaryButton")
            self.capture_preview_button.clicked.connect(lambda: self._schedule_claim_capture("preview"))
            self.capture_failure_button = QPushButton("\u64f7\u53d6\u5931\u6557\u756b\u9762")
            self.capture_failure_button.setObjectName("secondaryButton")
            self.capture_failure_button.clicked.connect(lambda: self._schedule_claim_capture("failure"))
            self.apply_button = QPushButton("\u5957\u7528\u6821\u6e96\u8349\u7a3f")
            self.apply_button.setObjectName("primaryButton")
            self.apply_button.clicked.connect(self._apply_editor)
            self.save_button = QPushButton("\u5132\u5b58\u5230\u8a2d\u5b9a\u6a94")
            self.save_button.setObjectName("secondaryButton")
            self.save_button.clicked.connect(self._save_editor)
            self.reset_button = QPushButton("\u6e05\u9664\u672c\u6b21\u8349\u7a3f")
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
            self.calibration_box.setReadOnly(True)
            calibration_layout.addWidget(self.calibration_box)
            tabs.addTab(calibration_tab, "\u6821\u6e96\u5de5\u5177")

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
                f"last_sync: {'ok' if state.runtime_snapshot.last_sync_ok else 'failed'} | "
                f"queue_result: {state.queue.last_queue_status or 'idle'}"
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
                f"{len(state.instance_rows)} \u53f0\u6a21\u64ec\u5668\u3002 "
                "\u5361\u7247\u986f\u793a\u9023\u7dda\u3001\u4efb\u52d9\u8207\u5065\u5eb7\u72c0\u614b\u3002"
            )
            wanted_ids = [row.instance_id for row in state.instance_rows]
            current_ids = [self.instance_list.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.instance_list.count())]
            if current_ids != wanted_ids:
                self._list_syncing = True
                self.instance_list.clear()
                for row in state.instance_rows:
                    warning = f"\nwarning: {_zh_health(row.warning)}" if row.warning else ""
                    active_task = _zh_task(row.active_task_id) if row.active_task_id else "-"
                    item = QListWidgetItem(
                        f"{row.label}\n"
                        f"{_zh_status(row.status)} | {_zh_health(row.health_summary)}\n"
                        f"queue {row.queue_depth} | {active_task}\n"
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
                self.instance_title.setText("\u5c1a\u672a\u9078\u53d6\u6a21\u64ec\u5668")
                self.connection_label.setText("\u8acb\u5148\u5f9e\u5de6\u5074\u9078\u53d6\u4e00\u53f0\u6a21\u64ec\u5668\u3002")
                self.profile_label.setText("")
                self.runtime_label.setText("")
                self.warning_label.setText("")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                return
            active_task = snapshot.context.active_task_id if snapshot.context is not None else ""
            profile = snapshot.profile_binding.display_name if snapshot.profile_binding is not None else "-"
            self.instance_title.setText(snapshot.instance.label)
            self.connection_label.setText(f"\u9023\u7dda\u72c0\u614b: {_zh_status(state.detail.status)} | {state.detail.adb_serial}")
            self.profile_label.setText(f"\u8a2d\u5b9a\u6a94: {profile}")
            self.runtime_label.setText(
                f"\u57f7\u884c\u72c0\u614b: {_zh_task(active_task) if active_task else '-'} | "
                f"queue={state.detail.queue_depth} | {_zh_health(state.detail.inspection_summary)}"
            )
            self.warning_label.setText(state.detail.warning)
            controls = {item.action_key: item for item in state.manual_controls.available_actions}
            self.start_button.setEnabled(controls.get("start_queue").enabled if "start_queue" in controls else False)
            self.stop_button.setEnabled(controls.get("stop").enabled if "stop" in controls else False)

        def _render_claim_rewards(self, state: OperatorConsoleState) -> None:
            claim = state.claim_rewards
            self.claim_header.setText(f"{claim.task_label} | {_zh_status(claim.workflow_status)}")
            overview_lines = [claim.active_step_summary or "-", f"\u4e0b\u4e00\u6b65\uff1a{claim.next_action_summary or '-'}", claim.workflow_banner or "-"]
            self.claim_overview.setText("\n".join(overview_lines))
            total_steps = max(1, claim.progress_total_count or len(claim.step_rows) or 1)
            self.claim_progress.setMaximum(total_steps)
            self.claim_progress.setValue(min(claim.progress_completed_count, total_steps))
            self.claim_progress.setFormat(f"{claim.progress_completed_count}/{claim.progress_total_count or len(claim.step_rows)}")
            self.claim_status.setPlainText(
                "\n".join(
                    [
                        f"目前步驟：{claim.current_step_title or '-'}",
                        f"視覺檢查：{claim.failure_check_summary or '目前沒有需要人工確認的視覺檢查。'}",
                        f"診斷焦點：{claim.selected_anchor_summary or '-'}",
                        f"下一步建議：{claim.next_action_summary or '-'}",
                        f"執行條件：{claim.runtime_gate_summary or '-'}",
                        f"最近執行：{claim.last_run_summary or '-'}",
                        f"失敗原因：{claim.failure_reason or claim.failure_summary or '-'}",
                        f"套用範圍：{claim.selected_scope_summary or '-'}",
                        f"預設配置：{claim.preset_summary or '-'}",
                    ]
                )
            )
            self.claim_steps.clear()
            status_labels = {
                "pending": "\u5f85\u57f7\u884c",
                "running": "\u57f7\u884c\u4e2d",
                "succeeded": "\u5b8c\u6210",
                "failed": "\u5931\u6557",
                "skipped": "\u7565\u904e",
            }
            for row in claim.step_rows:
                prefix = row.status_text or status_labels.get(row.status, row.status)
                summary = row.summary or row.success_condition or row.failure_condition
                self.claim_steps.addItem(QListWidgetItem(f"{prefix} | {row.title}\n{summary}"))
            self.claim_queue_button.setEnabled(claim.can_queue)
            self.claim_run_button.setEnabled(claim.can_run_now)

        def _render_preview(self, state: OperatorConsoleState) -> None:
            preview = state.vision.preview
            image_path = preview.image_path if preview is not None else ""
            overlay = preview.selected_overlay_summary if preview is not None else ""
            self.preview_summary.setText(f"畫面來源：{image_path or '-'} | 疊圖焦點：{overlay or '-'}")
            lines = [f"目前畫面：{state.claim_rewards.preview_summary or '-'}", f"套用範圍：{state.claim_rewards.selected_scope_summary or '-'}"]
            if preview is not None:
                for key, value in sorted(preview.metadata.items()):
                    lines.append(f"{key}: {value}")
            self.preview_box.setPlainText("\n".join(lines))
            if image_path and Path(image_path).exists():
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.preview_image.setPixmap(pixmap.scaled(self.preview_image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    self.preview_image.setText("")
                    return
            self.preview_image.setPixmap(QPixmap())
            self.preview_image.setText("\u5c1a\u7121\u9810\u89bd")

        def _render_failure(self, state: OperatorConsoleState) -> None:
            claim_failure = state.vision.failure.claim_rewards
            self.failure_summary.setText(f"摘要：{state.claim_rewards.failure_summary or '-'} | 卡住步驟：{state.claim_rewards.current_step_title or state.claim_rewards.failure_step_id or '-'}")
            if claim_failure is None:
                self.failure_box.setPlainText("目前沒有失敗快照。")
                return
            selected = claim_failure.selected_check
            lines = [
                f"視覺檢查：{state.claim_rewards.failure_check_summary or '-'}",
                f"診斷焦點：{state.claim_rewards.selected_anchor_summary or '-'}",
                f"下一步：{state.claim_rewards.next_action_summary or '-'}",
                f"診斷摘要：{state.claim_rewards.failure_check_summary or state.claim_rewards.failure_summary or '-'}",
                f"檢查進度：已命中 {claim_failure.matched_check_count} / 缺失 {claim_failure.missing_check_count}",
                "說明：下列模板、參考圖、門檻與區域是 viewer-first 診斷資訊，不代表 app 另外發明了 runtime signal。",
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
                        f"錨點：{selected.anchor_label or selected.label or '-'} | {selected.anchor_id}",
                        f"階段：{state.claim_rewards.current_step_title or selected.stage or '-'}",
                        f"狀態：{_zh_match_status(selected.status.value)}",
                        f"門檻：{threshold:.2f}",
                        f"比對區域：{region}",
                        f"模板：{selected.selected_template_path or '-'}",
                        f"參考圖：{selected.selected_reference_image_path or '-'}",
                        f"最佳候選：{selected.best_candidate_summary or '-'}",
                        f"命中候選：{selected.matched_candidate_summary or '-'}",
                        f"疊圖：{selected.inspection.selected_overlay_summary if selected.inspection is not None else '-'}",
                    ]
                )
            self.failure_box.setPlainText("\n".join(lines))

        def _render_readiness(self, state: OperatorConsoleState) -> None:
            row = _claim_readiness_row(state)
            self.readiness_summary.setText(
                f"建構就緒：{state.task_readiness.builder_ready_count}/{state.task_readiness.total_tasks} | "
                f"執行就緒：{state.task_readiness.implementation_ready_count}/{state.task_readiness.total_tasks}"
            )
            if row is None:
                self.readiness_box.setPlainText("缺少每日領獎的就緒資料。")
                return
            self.readiness_box.setPlainText(
                "\n".join(
                    [
                        f"任務定義：{row.manifest_path}",
                        f"建構狀態：{row.builder_state}",
                        f"執行狀態：{row.implementation_state}",
                        f"目前可直接執行：{'是' if row.implementation_state == 'ready' else '否'}",
                        f"範圍原因：{', '.join(row.scope_reasons) or '-'}",
                        f"必要錨點：{', '.join(row.required_anchors) or '-'}",
                        f"樣板設定：{', '.join(row.fixture_profile_paths) or '-'}",
                        f"Runtime 需求：{', '.join(row.runtime_requirement_ids) or '-'}",
                        f"警告：{'; '.join(row.warnings) or '-'}",
                        f"阻擋項：{'; '.join(row.implementation_blockers) or '-'}",
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
                f"選取來源：{state.claim_rewards.editor.selected_source_kind}",
                f"選取圖片：{state.claim_rewards.editor.selected_source_image or '-'}",
                f"擷取數量：{state.claim_rewards.editor.artifact_count}",
                f"已套用：{state.claim_rewards.editor.last_applied_summary or '-'}",
                f"已保存：{state.claim_rewards.editor.persistence_summary or '-'}",
                f"目前診斷用錨點：{state.claim_rewards.selected_anchor_summary or '-'}",
                f"目前擷取：{capture.selected_artifact_summary or '-'}",
                f"校正縮放：{calibration.scale_summary or '-'}",
                f"校正偏移：{calibration.offset_summary or '-'}",
                f"校正裁切：{calibration.crop_summary or '-'}",
            ]
            if calibration.selected_resolution is not None:
                lines.extend(
                    [
                        f"選取錨點：{calibration.selected_resolution.anchor_id}",
                        f"實際門檻：{calibration.selected_resolution.effective_confidence_threshold:.2f}",
                        f"實際比對區域：{calibration.selected_resolution.effective_match_region}",
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
                QMessageBox.warning(self, "\u9700\u8981\u6a21\u64ec\u5668", "\u8acb\u5148\u5f9e\u5de6\u5074\u9078\u53d6\u4e00\u53f0\u6a21\u64ec\u5668\u3002")
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
                QMessageBox.warning(self, "\u7de8\u8f2f\u683c\u5f0f\u932f\u8aa4", str(exc))

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
