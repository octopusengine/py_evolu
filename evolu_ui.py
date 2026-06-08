from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QWidget):
    action_requested = pyqtSignal(str, object)
    profile_requested = pyqtSignal(int)
    debug_changed = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("py_evolu | Evolu Relay Test")
        self.resize(1180, 720)
        self.setMinimumSize(900, 560)

        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_debug_panel())
        splitter.setSizes([650, 530])
        root.addWidget(splitter, stretch=1)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        title = QLabel("Agama Evolu App")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        profile_box = QGroupBox("Relay profile")
        profile_layout = QVBoxLayout(profile_box)
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.profile_requested.emit)
        profile_layout.addWidget(self.profile_combo)
        self.profile_info = QLabel("")
        self.profile_info.setWordWrap(True)
        profile_layout.addWidget(self.profile_info)
        layout.addWidget(profile_box)

        input_box = QGroupBox("Text input")
        input_layout = QVBoxLayout(input_box)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Text to save into active text file and Evolu")
        input_layout.addWidget(self.text_input)
        layout.addWidget(input_box)

        actions = QGroupBox("Actions")
        actions_layout = QGridLayout(actions)
        actions_layout.setSpacing(6)
        self._add_action(actions_layout, 0, 0, "Load active data", "load")
        self._add_action(actions_layout, 1, 0, "Save text", "save_text")
        self._add_action(actions_layout, 2, 0, "Sync active relay", "sync")
        self._add_action(actions_layout, 3, 0, "Export DB backup", "backup")
        self._add_action(actions_layout, 4, 0, "Write both samples", "sample_both")

        self._add_action(actions_layout, 0, 1, "Restore from EVOLU_KEY", "restore_env")
        self._add_action(actions_layout, 1, 1, "Show owner", "show_owner")
        self._add_action(actions_layout, 2, 1, "Save key to .env", "save_key")

        reset_btn = QPushButton("Reset active DB")
        reset_btn.clicked.connect(self._confirm_reset)
        actions_layout.addWidget(reset_btn, 3, 1)
        actions_layout.setColumnStretch(0, 1)
        actions_layout.setColumnStretch(1, 1)
        layout.addWidget(actions)

        data_box = QGroupBox("Current data")
        data_layout = QVBoxLayout(data_box)
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.text_file_box = QTextBrowser()
        self.text_file_box.setMinimumHeight(70)
        self.text_file_box.setMaximumHeight(120)
        self.data_box = QTextBrowser()
        data_layout.addWidget(self.path_label)
        data_layout.addWidget(QLabel("Text file"))
        data_layout.addWidget(self.text_file_box)
        data_layout.addWidget(QLabel("Evolu rows"))
        data_layout.addWidget(self.data_box, stretch=1)
        layout.addWidget(data_box, stretch=1)

        return panel

    def _build_debug_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("Debug")
        title.setObjectName("Title")
        top.addWidget(title)
        top.addStretch()
        self.debug_checkbox = QCheckBox("Verbose")
        self.debug_checkbox.setChecked(True)
        self.debug_checkbox.toggled.connect(self.debug_changed.emit)
        top.addWidget(self.debug_checkbox)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_debug)
        top.addWidget(save_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_debug)
        top.addWidget(clear_btn)
        layout.addLayout(top)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("Status")
        layout.addWidget(self.status_label)

        self.debug_box = QTextBrowser()
        self.debug_box.setObjectName("VerboseLog")
        layout.addWidget(self.debug_box, stretch=1)

        return panel

    def _add_action(self, layout: QGridLayout, row: int, column: int, label: str, action: str) -> None:
        button = QPushButton(label)
        button.clicked.connect(lambda _checked=False, name=action: self._emit_action(name))
        layout.addWidget(button, row, column)

    def _emit_action(self, action: str) -> None:
        payload: dict[str, Any] = {}
        if action == "save_text":
            payload["text"] = self.text_input.text().strip()
        self.action_requested.emit(action, payload)

    def _confirm_reset(self) -> None:
        result = QMessageBox.question(
            self,
            "Reset local DB",
            "Really reset the active local Evolu database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self.action_requested.emit("reset", {})

    def set_profiles(self, profiles: list[dict[str, str]]) -> None:
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in profiles:
            self.profile_combo.addItem(f"{profile['label']} - {profile['relay']}")
        self.profile_combo.blockSignals(False)

    def set_profile_index(self, index: int) -> None:
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def append_debug(self, text: str) -> None:
        self.debug_box.append(f"<pre>{html.escape(text)}</pre>")
        self.debug_box.verticalScrollBar().setValue(self.debug_box.verticalScrollBar().maximum())

    def clear_debug(self) -> None:
        self.debug_box.clear()

    def save_debug(self) -> None:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        filename = datetime.now().strftime("log_%y%m%d_%H_%M.txt")
        path = data_dir / filename
        path.write_text(self.debug_box.toPlainText(), encoding="utf-8")
        self.append_debug(f"log saved: {path}")

    def update_view(self, state: dict[str, Any]) -> None:
        profile = state.get("profile", {})
        owner = state.get("owner", {})
        self.profile_info.setText(
            "\n".join(
                [
                    f"Active: {profile.get('label', '')}",
                    f"Relay: {profile.get('relay', '')}",
                    f"Owner: {owner.get('ownerId', '<unknown>')}",
                ]
            )
        )

        self.path_label.setText(
            "\n".join(
                [
                    f"DB: {state.get('db_path', '')}",
                    f"TXT: {state.get('text_path', '')}",
                    f"Backup: {state.get('backup_path', '')}",
                ]
            )
        )

        text_content = state.get("text_content")
        self.text_file_box.setPlainText(text_content if text_content else "<missing or empty>")

        rows = state.get("rows")
        if rows is None:
            self.data_box.setPlainText("<no data loaded>")
        else:
            self.data_box.setPlainText(json.dumps(rows, indent=2, ensure_ascii=False, default=str))

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #15171a;
                color: #e8e8e8;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 11pt;
            }
            QLabel#Title {
                font-size: 15pt;
                font-weight: 600;
                color: #ffffff;
            }
            QLabel#AppTitle {
                font-size: 15pt;
                font-weight: 700;
                color: #b56cff;
            }
            QLabel#Status {
                color: #9ad1ff;
                padding: 4px 0;
            }
            QLabel#Muted {
                color: #8b96a3;
            }
            QGroupBox {
                border: 1px solid #333941;
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                background: #26313d;
                border: 1px solid #3d4a57;
                border-radius: 5px;
                padding: 8px 10px;
                text-align: center;
            }
            QPushButton:hover {
                background: #314153;
            }
            QPushButton:pressed {
                background: #1d2732;
            }
            QPushButton:disabled {
                color: #626b75;
                background: #1a1f25;
                border-color: #2c333a;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #58616b;
                background: #1b2026;
            }
            QCheckBox::indicator {
                border-radius: 3px;
            }
            QRadioButton::indicator {
                border-radius: 8px;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                border: 3px solid #58616b;
                background: #39ff14;
            }
            QLineEdit, QComboBox, QTextBrowser {
                background: #0f1114;
                border: 1px solid #333941;
                border-radius: 5px;
                padding: 6px;
                color: #e8e8e8;
            }
            QTextBrowser#VerboseLog {
                background: #070b08;
                border-color: #2f5f3b;
                color: #39ff72;
                font-family: Consolas, Cascadia Mono, monospace;
                font-size: 9pt;
            }
            QSplitter::handle {
                background: #262b31;
            }
            """
        )
