"""
startup.py

Startup dialog — domain → discipline selection, then one-click role launch.

No Bestätigen button. Clicking a role button immediately accepts the dialog
and launches the corresponding window. Domain/discipline combos stay for
switching context. State is restored from state.json on open and saved on
role selection.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QSizePolicy, QSpacerItem,
)

from normaformae.core.discipline_loader import list_domains, list_disciplines
from normaformae.core.app_state import load_state, update_state
from normaformae.glossary import UI


class StartupDialog(QDialog):
    """
    Modal startup dialog.

    User flow:
        1. Domain and discipline are pre-selected from last session (state.json).
        2. User adjusts discipline if needed via combo boxes.
        3. User clicks a role button → dialog accepts immediately.

    After exec() returns Accepted:
        self.selected_role            → "author" | "user"
        self.selected_discipline_path → str path to discipline folder
        self.selected_discipline_cfg  → dict of discipline.json
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(UI["app_title"])
        self.setMinimumWidth(440)
        self.setModal(True)

        self.selected_role: str            = ""
        self.selected_discipline_path: str = ""
        self.selected_discipline_cfg: dict = {}

        self._domains:     list[dict] = []
        self._disciplines: list[dict] = []
        self._state = load_state()

        self._build_ui()
        self._load_domains()
        self._restore_state()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel(UI["app_title"])
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        root.addWidget(title)

        root.addWidget(_divider())

        # Domain + discipline selectors
        root.addWidget(_label(UI["select_domain"]))
        self._domain_combo = QComboBox()
        self._domain_combo.currentIndexChanged.connect(self._on_domain_changed)
        root.addWidget(self._domain_combo)

        root.addWidget(_label(UI["select_discipline"]))
        self._discipline_combo = QComboBox()
        self._discipline_combo.currentIndexChanged.connect(self._on_discipline_changed)
        root.addWidget(self._discipline_combo)

        root.addWidget(_divider())

        # Role selection — clicking a button launches immediately
        root.addWidget(_label(UI["select_role"]))

        hint = QLabel("Rolle auswählen, um direkt zu starten")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)

        role_row = QHBoxLayout()
        role_row.setSpacing(12)

        self._btn_author = QPushButton(UI["role_author"])
        self._btn_author.setMinimumHeight(48)
        self._btn_author.clicked.connect(lambda: self._launch_role("author"))

        self._btn_user = QPushButton(UI["role_user"])
        self._btn_user.setMinimumHeight(48)
        self._btn_user.clicked.connect(lambda: self._launch_role("user"))

        self._btn_trainer = QPushButton(f"{UI['role_trainer']} (Slice 5)")
        self._btn_trainer.setMinimumHeight(48)
        self._btn_trainer.setEnabled(False)
        self._btn_trainer.setToolTip(
            "Trainerfunktion wird in einem späteren Schritt freigeschaltet."
        )

        role_row.addWidget(self._btn_author)
        role_row.addWidget(self._btn_user)
        role_row.addWidget(self._btn_trainer)
        root.addLayout(role_row)

        root.addItem(
            QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # Status line — shows selected discipline name
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: gray; font-size: 11px;")
        root.addWidget(self._status_label)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_domains(self) -> None:
        try:
            self._domains = list_domains()
        except Exception as e:
            self._status_label.setText(f"Fehler beim Laden der Bereiche: {e}")
            return

        self._domain_combo.clear()
        for d in self._domains:
            self._domain_combo.addItem(d["display_name"], userData=d["domain_id"])

        if self._domains:
            self._on_domain_changed(0)

    def _on_domain_changed(self, index: int) -> None:
        if index < 0 or not self._domains:
            return
        domain_id = self._domain_combo.currentData()
        try:
            self._disciplines = list_disciplines(domain_id)
        except Exception as e:
            self._status_label.setText(f"Fehler: {e}")
            return

        self._discipline_combo.clear()
        for d in self._disciplines:
            self._discipline_combo.addItem(d["display_name"], userData=d.get("path", ""))

        if self._disciplines:
            self._on_discipline_changed(0)

    def _on_discipline_changed(self, index: int) -> None:
        if index < 0 or not self._disciplines:
            return
        self.selected_discipline_cfg  = self._disciplines[index]
        self.selected_discipline_path = self._disciplines[index].get("path", "")
        self._update_role_buttons()
        disc_name = self.selected_discipline_cfg.get("display_name", "")
        self._status_label.setText(disc_name)

    # ------------------------------------------------------------------
    # State restore
    # ------------------------------------------------------------------

    def _restore_state(self) -> None:
        last_path = self._state.get("last_discipline_path", "")
        if last_path:
            for i in range(self._discipline_combo.count()):
                if self._discipline_combo.itemData(i) == last_path:
                    self._discipline_combo.setCurrentIndex(i)
                    break

    def _update_role_buttons(self) -> None:
        enabled = bool(self.selected_discipline_path)
        self._btn_author.setEnabled(enabled)
        self._btn_user.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Launch — role click = immediate accept
    # ------------------------------------------------------------------

    def _launch_role(self, role: str) -> None:
        if not self.selected_discipline_path:
            self._status_label.setText("Bitte zuerst eine Disziplin auswählen.")
            return
        self.selected_role = role
        update_state(
            last_discipline_path=self.selected_discipline_path,
            last_role=role,
        )
        self.accept()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
    return lbl


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line
