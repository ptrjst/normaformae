"""
startup.py

Startup dialog — first thing the user sees.
Step 1: select Domain
Step 2: select Discipline (filtered by domain)
Step 3: select Role (Autor / Benutzer — Trainer deferred to Slice 5)

Uses real data from discipline_loader. No mock here.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QSizePolicy, QSpacerItem,
)

from normaformae.core.discipline_loader import list_domains, list_disciplines
from normaformae.glossary import UI


class StartupDialog(QDialog):
    """
    Modal startup dialog.
    After exec() returns QDialog.DialogCode.Accepted:
        self.selected_role            → "author" | "user"
        self.selected_discipline_path → str path to discipline folder
        self.selected_discipline_cfg  → dict of the discipline.json
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(UI["app_title"])
        self.setMinimumWidth(440)
        self.setModal(True)

        # State populated as user makes selections
        self.selected_role: str = ""
        self.selected_discipline_path: str = ""
        self.selected_discipline_cfg: dict = {}

        # Internal data
        self._domains: list[dict] = []
        self._disciplines: list[dict] = []

        self._build_ui()
        self._load_domains()

    # ------------------------------------------------------------------
    # UI construction
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

        # Domain selector
        root.addWidget(_label(UI["select_domain"]))
        self._domain_combo = QComboBox()
        self._domain_combo.currentIndexChanged.connect(self._on_domain_changed)
        root.addWidget(self._domain_combo)

        # Discipline selector
        root.addWidget(_label(UI["select_discipline"]))
        self._discipline_combo = QComboBox()
        self._discipline_combo.currentIndexChanged.connect(self._on_discipline_changed)
        root.addWidget(self._discipline_combo)

        root.addWidget(_divider())

        # Role selector
        root.addWidget(_label(UI["select_role"]))
        role_row = QHBoxLayout()
        role_row.setSpacing(12)

        self._btn_author = QPushButton(UI["role_author"])
        self._btn_author.setCheckable(True)
        self._btn_author.setMinimumHeight(40)
        self._btn_author.clicked.connect(lambda: self._select_role("author"))

        self._btn_user = QPushButton(UI["role_user"])
        self._btn_user.setCheckable(True)
        self._btn_user.setMinimumHeight(40)
        self._btn_user.clicked.connect(lambda: self._select_role("user"))

        # Trainer button — visible but disabled until Slice 5
        self._btn_trainer = QPushButton(f"{UI['role_trainer']} (Slice 5)")
        self._btn_trainer.setEnabled(False)
        self._btn_trainer.setMinimumHeight(40)
        self._btn_trainer.setToolTip("Trainerfunktion wird in einem späteren Schritt freigeschaltet.")

        role_row.addWidget(self._btn_author)
        role_row.addWidget(self._btn_user)
        role_row.addWidget(self._btn_trainer)
        root.addLayout(role_row)

        root.addItem(QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Confirm button
        self._btn_confirm = QPushButton(UI["confirm"])
        self._btn_confirm.setMinimumHeight(44)
        self._btn_confirm.setEnabled(False)
        self._btn_confirm.clicked.connect(self._on_confirm)
        root.addWidget(self._btn_confirm)

        # Status line
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
        self.selected_discipline_cfg = self._disciplines[index]
        self.selected_discipline_path = self._disciplines[index].get("path", "")
        self._update_confirm_state()

    # ------------------------------------------------------------------
    # Role selection
    # ------------------------------------------------------------------

    def _select_role(self, role: str) -> None:
        self.selected_role = role
        self._btn_author.setChecked(role == "author")
        self._btn_user.setChecked(role == "user")
        self._update_confirm_state()

    def _update_confirm_state(self) -> None:
        ready = bool(self.selected_role and self.selected_discipline_path)
        self._btn_confirm.setEnabled(ready)
        if ready:
            disc_name = self.selected_discipline_cfg.get("display_name", "")
            role_label = UI["role_author"] if self.selected_role == "author" else UI["role_user"]
            self._status_label.setText(f"{disc_name}  ·  {role_label}")
        else:
            self._status_label.setText("")

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
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
