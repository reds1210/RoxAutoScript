from __future__ import annotations

from typing import TYPE_CHECKING

from roxauto.app.viewmodels import ConsoleSnapshot, InstanceCardView, build_console_snapshot
from roxauto.core.serde import to_primitive
from roxauto.doctor import build_doctor_report

if TYPE_CHECKING:
    from typing import Any


def launch_placeholder_gui() -> int:
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QPlainTextEdit,
            QSizePolicy,
            QMainWindow,
            QPushButton,
            QSplitter,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PySide6 is not installed. Run scripts/bootstrap-dev.ps1 -InstallFullStack first.")
        return 1

    report = build_console_snapshot(to_primitive(build_doctor_report()))
    app = QApplication([])

    class MainWindow(QMainWindow):
        def __init__(self, snapshot: ConsoleSnapshot) -> None:
            super().__init__()
            self.setWindowTitle("RoxAutoScript Control Center")
            self.resize(1200, 760)
            self._snapshot = snapshot

            central = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(self._build_header())

            splitter = QSplitter()
            splitter.addWidget(self._build_left_panel())
            splitter.addWidget(self._build_right_panel())
            splitter.setSizes([380, 760])
            layout.addWidget(splitter)

            footer = QHBoxLayout()
            refresh_button = QPushButton("Refresh Environment")
            refresh_button.clicked.connect(self._refresh_snapshot)
            footer.addWidget(refresh_button)

            close_button = QPushButton("Close")
            close_button.clicked.connect(self.close)
            footer.addWidget(close_button)
            layout.addLayout(footer)

            central.setLayout(layout)
            self.setCentralWidget(central)
            self._render_snapshot()

        def _build_header(self) -> QWidget:
            container = QWidget()
            layout = QGridLayout()
            container.setLayout(layout)

            title = QLabel("ROX operator console foundation")
            title.setStyleSheet("font-size: 20px; font-weight: 600;")
            layout.addWidget(title, 0, 0, 1, 2)

            self.summary_label = QLabel()
            layout.addWidget(self.summary_label, 1, 0)

            self.features_label = QLabel()
            layout.addWidget(self.features_label, 1, 1)
            return container

        def _build_left_panel(self) -> QWidget:
            group = QGroupBox("Instances")
            layout = QVBoxLayout()
            self.instance_list = QListWidget()
            self.instance_list.currentRowChanged.connect(self._sync_instance_detail)
            layout.addWidget(self.instance_list)
            group.setLayout(layout)
            return group

        def _build_right_panel(self) -> QWidget:
            container = QWidget()
            layout = QVBoxLayout()

            details = QGroupBox("Instance Details")
            details_layout = QVBoxLayout()
            self.instance_title = QLabel("No instance selected")
            self.instance_title.setStyleSheet("font-size: 18px; font-weight: 600;")
            self.instance_meta = QLabel("Select one emulator instance to inspect.")
            self.instance_meta.setWordWrap(True)
            details_layout.addWidget(self.instance_title)
            details_layout.addWidget(self.instance_meta)
            details.setLayout(details_layout)
            layout.addWidget(details)

            actions = QGroupBox("Controls")
            actions_layout = QHBoxLayout()
            self.start_button = QPushButton("Start Queue")
            self.pause_button = QPushButton("Pause")
            self.stop_button = QPushButton("Stop")
            self.emergency_button = QPushButton("Emergency Stop")
            self.tap_test_button = QPushButton("Tap Test")
            for button in [
                self.start_button,
                self.pause_button,
                self.stop_button,
                self.emergency_button,
                self.tap_test_button,
            ]:
                button.clicked.connect(lambda _checked=False, name=button.text(): self._log_action(name))
                actions_layout.addWidget(button)
            actions.setLayout(actions_layout)
            layout.addWidget(actions)

            preview = QGroupBox("Preview")
            preview_layout = QVBoxLayout()
            self.preview_label = QLabel("Preview pipeline not wired yet.\nUse this pane for screenshots after runtime integration.")
            self.preview_label.setMinimumHeight(180)
            self.preview_label.setStyleSheet(
                "border: 1px solid #666; padding: 12px; background: #161616; color: #e8e8e8;"
            )
            self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            preview_layout.addWidget(self.preview_label)
            preview.setLayout(preview_layout)
            layout.addWidget(preview)

            logs = QGroupBox("Operator Log")
            logs_layout = QVBoxLayout()
            self.log_output = QPlainTextEdit()
            self.log_output.setReadOnly(True)
            logs_layout.addWidget(self.log_output)
            logs.setLayout(logs_layout)
            layout.addWidget(logs)

            container.setLayout(layout)
            return container

        def _render_snapshot(self) -> None:
            enabled = self._snapshot.available_runtime_features
            feature_text = ", ".join(enabled) if enabled else "none"
            self.summary_label.setText(
                f"ADB: {self._snapshot.adb_path} | Instances: {self._snapshot.instance_count}"
            )
            self.features_label.setText(f"Detected optional packages: {feature_text}")

            self.instance_list.clear()
            for instance in self._snapshot.instances:
                item = QListWidgetItem(f"{instance.label} [{instance.status}]")
                item.setData(1, instance.instance_id)
                self.instance_list.addItem(item)

            if self._snapshot.instances:
                self.instance_list.setCurrentRow(0)
            else:
                self._sync_instance_detail(-1)
                self._append_log("No emulator instances discovered.")

        def _sync_instance_detail(self, row: int) -> None:
            if row < 0 or row >= len(self._snapshot.instances):
                self.instance_title.setText("No instance selected")
                self.instance_meta.setText("Select one emulator instance to inspect.")
                return
            instance = self._snapshot.instances[row]
            self.instance_title.setText(instance.label)
            self.instance_meta.setText(
                "\n".join(
                    [
                        f"Instance ID: {instance.instance_id}",
                        f"ADB Serial: {instance.adb_serial}",
                        f"Status: {instance.status}",
                        f"Last Seen: {instance.last_seen_at or 'n/a'}",
                    ]
                )
            )

        def _log_action(self, action_name: str) -> None:
            instance = self._current_instance()
            target = instance.label if instance else "global"
            self._append_log(f"{action_name} requested for {target}")

        def _refresh_snapshot(self) -> None:
            self._snapshot = build_console_snapshot(to_primitive(build_doctor_report()))
            self._append_log("Environment refreshed from doctor report.")
            self._render_snapshot()

        def _current_instance(self) -> InstanceCardView | None:
            row = self.instance_list.currentRow()
            if row < 0 or row >= len(self._snapshot.instances):
                return None
            return self._snapshot.instances[row]

        def _append_log(self, message: str) -> None:
            self.log_output.appendPlainText(message)

    window = MainWindow(report)
    window.show()
    return app.exec()
