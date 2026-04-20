from __future__ import annotations

from typing import TYPE_CHECKING

from roxauto.core.serde import to_primitive
from roxauto.doctor import build_doctor_report

if TYPE_CHECKING:
    from typing import Any


def launch_placeholder_gui() -> int:
    try:
        from PySide6.QtWidgets import (
            QApplication,
            QLabel,
            QListWidget,
            QMainWindow,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PySide6 is not installed. Run scripts/bootstrap-dev.ps1 -InstallFullStack first.")
        return 1

    report = to_primitive(build_doctor_report())
    app = QApplication([])

    class MainWindow(QMainWindow):
        def __init__(self, doctor_report: dict[str, Any]) -> None:
            super().__init__()
            self.setWindowTitle("RoxAutoScript Foundation")
            self.resize(720, 480)

            central = QWidget()
            layout = QVBoxLayout()

            layout.addWidget(QLabel("ROX control center foundation is ready for track work."))
            layout.addWidget(QLabel(f"ADB path: {doctor_report['adb']['path'] or 'not found'}"))
            layout.addWidget(
                QLabel(
                    f"Discovered instances: {doctor_report['adb']['instances_found']}"
                )
            )

            self.instance_list = QListWidget()
            for instance in doctor_report["instances"]:
                label = f"{instance['label']} | {instance['adb_serial']} | {instance['status']}"
                self.instance_list.addItem(label)
            layout.addWidget(self.instance_list)

            close_button = QPushButton("Close")
            close_button.clicked.connect(self.close)
            layout.addWidget(close_button)

            central.setLayout(layout)
            self.setCentralWidget(central)

    window = MainWindow(report)
    window.show()
    return app.exec()
