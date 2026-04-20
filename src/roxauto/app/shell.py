from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from roxauto.app.viewmodels import (
    ConsoleSnapshot,
    InstanceCardView,
    build_console_snapshot,
    build_vision_workspace_snapshot,
)
from roxauto.core.models import VisionMatch
from roxauto.core.serde import to_primitive
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
        anchor_overrides={
            "common.close_button": {"confidence_threshold": 0.90},
        },
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
            QPushButton,
            QSplitter,
            QTabWidget,
            QVBoxLayout,
            QWidget,
            QMainWindow,
        )
    except ImportError:
        print("PySide6 is not installed. Run scripts/bootstrap-dev.ps1 -InstallFullStack first.")
        return 1

    report = build_console_snapshot(to_primitive(build_doctor_report()))
    repository = _sample_repository()
    calibration_profile = _sample_calibration_profile()
    replay_script = _sample_replay_script()
    match_result = _sample_match_result(repository)
    vision_snapshot = build_vision_workspace_snapshot(
        repository=repository,
        calibration_profile=calibration_profile,
        replay_script=replay_script,
        match_result=match_result,
        source_image="preview://sample",
    )
    app = QApplication([])

    class MainWindow(QMainWindow):
        def __init__(self, snapshot: ConsoleSnapshot) -> None:
            super().__init__()
            self.setWindowTitle("RoxAutoScript Control Center")
            self.resize(1400, 860)
            self._snapshot = snapshot
            self._vision_snapshot = vision_snapshot

            central = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(self._build_header())

            splitter = QSplitter()
            splitter.addWidget(self._build_left_panel())
            splitter.addWidget(self._build_right_panel())
            splitter.setSizes([380, 1020])
            layout.addWidget(splitter)

            footer = QHBoxLayout()
            refresh_button = QPushButton("Refresh Environment")
            refresh_button.clicked.connect(self._refresh_snapshot)
            footer.addWidget(refresh_button)

            template_button = QPushButton("Reload Templates")
            template_button.clicked.connect(lambda: self._log_action("Reload Templates"))
            footer.addWidget(template_button)

            record_button = QPushButton("Record Sample")
            record_button.clicked.connect(lambda: self._log_action("Record Sample"))
            footer.addWidget(record_button)

            emergency_button = QPushButton("Emergency Stop")
            emergency_button.clicked.connect(lambda: self._log_action("Emergency Stop"))
            footer.addWidget(emergency_button)

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

            self.template_summary_label = QLabel()
            layout.addWidget(self.template_summary_label, 2, 0, 1, 2)
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

            tabs = QTabWidget()
            tabs.addTab(self._build_preview_tab(), "Preview")
            tabs.addTab(self._build_calibration_tab(), "Calibration")
            tabs.addTab(self._build_recording_tab(), "Recording")
            tabs.addTab(self._build_anchor_tab(), "Anchors")
            tabs.addTab(self._build_failure_tab(), "Failures")
            self.tabs = tabs
            layout.addWidget(tabs)

            logs = QGroupBox("Operator Log")
            logs_layout = QVBoxLayout()
            self.log_output = QPlainTextEdit()
            self.log_output.setReadOnly(True)
            logs_layout.addWidget(self.log_output)
            logs.setLayout(logs_layout)
            layout.addWidget(logs)

            container.setLayout(layout)
            return container

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

        def _render_snapshot(self) -> None:
            enabled = self._snapshot.available_runtime_features
            feature_text = ", ".join(enabled) if enabled else "none"
            self.summary_label.setText(
                f"ADB: {self._snapshot.adb_path} | Instances: {self._snapshot.instance_count}"
            )
            self.features_label.setText(f"Detected optional packages: {feature_text}")
            if self._vision_snapshot.repository_root:
                self.template_summary_label.setText(
                    f"Template repository: {self._vision_snapshot.anchors.display_name} "
                    f"({self._vision_snapshot.anchors.repository_id or 'untracked'})"
                )
            else:
                self.template_summary_label.setText("Template repository: not loaded")

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

            self._render_vision_snapshot()

        def _render_vision_snapshot(self) -> None:
            preview = self._vision_snapshot.preview
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
                        *(
                            preview.candidate_summaries
                            if preview.candidate_summaries
                            else ["  none"]
                        ),
                    ]
                )
            )

            calibration = self._vision_snapshot.calibration
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

            recording = self._vision_snapshot.recording
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

            anchors = self._vision_snapshot.anchors
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

            failure = self._vision_snapshot.failure
            self.failure_header.setText(
                f"Status: {failure.status} | Source: {failure.source_image or 'n/a'}"
            )
            self.failure_box.setPlainText(
                "\n".join(
                    [
                        f"Message: {failure.message}",
                        f"Best candidate: {failure.best_candidate_summary}",
                        "Candidates:",
                        *(
                            failure.candidate_summaries if failure.candidate_summaries else ["  none"]
                        ),
                    ]
                )
            )

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

        def _refresh_snapshot(self) -> None:
            repository = _sample_repository()
            self._snapshot = build_console_snapshot(to_primitive(build_doctor_report()))
            self._vision_snapshot = build_vision_workspace_snapshot(
                repository=repository,
                calibration_profile=_sample_calibration_profile(),
                replay_script=_sample_replay_script(),
                match_result=_sample_match_result(repository),
                source_image="preview://sample",
            )
            self._append_log("Environment refreshed from doctor report and template repository.")
            self._render_snapshot()

        def _log_action(self, action_name: str) -> None:
            instance = self._current_instance()
            target = instance.label if instance else "global"
            self._append_log(f"{action_name} requested for {target}")

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
