"""
user/window.py

User tool — main window.

Slice 1: full stub layout. All panels present, no real logic.
         Loads published flows from discipline, shows mock RecognitionResult.

Slice 2: URL input field enabled (yt-dlp).
Slice 3: real analysis engine connected.
Slice 4: document and video export.
Slice 5: session history panel.
"""

from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFrame,
    QTabWidget, QTextEdit, QToolBar, QStatusBar, QMessageBox,
    QFileDialog, QLineEdit, QGroupBox, QProgressBar,
)

from normaformae.core.discipline_loader import (
    load_discipline, load_published_flows, DisciplineLoadError,
)
from normaformae.glossary import UI, resolve_ui
from normaformae.core.mock_engine import build_mock_recognition_result


class UserWindow(QMainWindow):
    """
    Main window for the User persona.

    Layout (left → right):
        [Input + flow selection panel]  |  [Result panel — tabs]
    """

    def __init__(self, discipline_path: str) -> None:
        super().__init__()
        self._discipline_path = discipline_path
        self._discipline: dict = {}
        self._published_flows: dict = {}
        self._vocab: dict = {}
        self._rui: dict = UI.copy()
        self._current_video_path: str = ""

        self.setWindowTitle(UI["user_window_title"])
        self.setMinimumSize(960, 640)

        self._load_data()
        self._build_toolbar()
        self._build_ui()
        self._build_statusbar()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        try:
            self._discipline = load_discipline(self._discipline_path)
            self._published_flows = load_published_flows(self._discipline_path)
            from normaformae.core.discipline_loader import get_vocabulary
            self._vocab = get_vocabulary(self._discipline)
            self._rui   = resolve_ui(self._vocab)
        except DisciplineLoadError as e:
            QMessageBox.critical(self, "Fehler", str(e))

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Hauptwerkzeugleiste")
        tb.setMovable(False)
        self.addToolBar(tb)

        disc_name = self._discipline.get("display_name", self._discipline_path)
        tb.addWidget(QLabel(f"  {disc_name}  "))
        tb.addSeparator()

        n_flows = len(self._published_flows)
        flow_vocab = self._vocab.get("flow", {})
        flow_term = flow_vocab.get("singular", "Ablauf") if n_flows == 1 else flow_vocab.get("plural", "Abläufe")
        flow_info = f"{n_flows} {flow_term}"
        self._flow_count_label = QLabel(flow_info + " verfügbar  ")
        tb.addWidget(self._flow_count_label)

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        splitter.addWidget(self._build_input_panel())
        splitter.addWidget(self._build_result_panel())
        splitter.setSizes([320, 640])

    # ------------------------------------------------------------------
    # Left: Input panel
    # ------------------------------------------------------------------

    def _build_input_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(280)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Section: video input
        video_box = QGroupBox("Video")
        video_layout = QVBoxLayout(video_box)

        # File upload
        upload_row = QHBoxLayout()
        self._video_path_label = QLabel(UI["error_no_video"])
        self._video_path_label.setStyleSheet("font-size: 11px; color: gray;")
        self._video_path_label.setWordWrap(True)
        upload_row.addWidget(self._video_path_label)
        self._btn_upload = QPushButton(UI["upload_video"])
        self._btn_upload.setFixedWidth(110)
        self._btn_upload.clicked.connect(self._on_upload_video)
        upload_row.addWidget(self._btn_upload)
        video_layout.addLayout(upload_row)

        # URL input (disabled until Slice 3)
        video_layout.addWidget(QLabel(UI["video_url"]))
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText(UI["url_disabled"])
        self._url_input.setEnabled(False)
        self._url_input.setToolTip("URL-Eingabe wird in Slice 3 freigeschaltet (yt-dlp).")
        video_layout.addWidget(self._url_input)

        layout.addWidget(video_box)

        # Section: flow selection
        flow_box = QGroupBox(self._vocab.get("flow", {}).get("plural", "Abläufe"))
        flow_layout = QVBoxLayout(flow_box)

        if self._published_flows:
            for fid, flow in self._published_flows.items():
                item = QListWidgetItem(flow.get("label", fid))
                item.setData(Qt.ItemDataRole.UserRole, fid)
        else:
            no_flows = QLabel(f"Keine veröffentlichten {self._vocab.get('flow',{}).get('plural','Abläufe')} vorhanden.\nDer Autor muss zuerst Inhalte veröffentlichen.")
            no_flows.setStyleSheet("color: gray; font-size: 11px;")
            no_flows.setWordWrap(True)
            flow_layout.addWidget(no_flows)

        self._flow_list = QListWidget()
        self._flow_list.setMinimumHeight(120)
        self._flow_list.itemClicked.connect(self._on_flow_selected)
        self._populate_flow_list()
        flow_layout.addWidget(self._flow_list)

        layout.addWidget(flow_box)

        # Analyse button + progress
        self._btn_analyse = QPushButton(UI["start_analysis"])
        self._btn_analyse.setMinimumHeight(44)
        self._btn_analyse.setEnabled(False)
        self._btn_analyse.clicked.connect(self._on_start_analysis)
        layout.addWidget(self._btn_analyse)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)   # indeterminate
        layout.addWidget(self._progress)

        layout.addStretch()

        # Export buttons (enabled after analysis)
        layout.addWidget(_divider())
        self._btn_export_doc = QPushButton(UI["export_document"])
        self._btn_export_doc.setEnabled(False)
        self._btn_export_doc.clicked.connect(self._on_export_document)
        layout.addWidget(self._btn_export_doc)

        self._btn_export_video = QPushButton(UI["export_video"])
        self._btn_export_video.setEnabled(False)
        self._btn_export_video.setToolTip("Augmentiertes Video — verfügbar in Slice 5")
        self._btn_export_video.clicked.connect(self._on_export_video)
        layout.addWidget(self._btn_export_video)

        return panel

    # ------------------------------------------------------------------
    # Right: Result panel (tabs)
    # ------------------------------------------------------------------

    def _build_result_panel(self) -> QWidget:
        self._result_tabs = QTabWidget()

        self._result_tabs.addTab(self._build_overview_tab(),  "Übersicht")
        self._result_tabs.addTab(self._build_stances_tab(),   "Erkannte Huten")
        self._result_tabs.addTab(self._build_sequences_tab(), "Erkannte Sequenzen")
        self._result_tabs.addTab(self._build_history_tab(),   "Verlauf (Slice 5)")

        return self._result_tabs

    def _build_overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._overview_placeholder = QLabel(
            "Kein Analyseergebnis vorhanden.\n\n"
            "1. Video hochladen\n"
            "2. Analyse starten"
        )
        self._overview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overview_placeholder.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(self._overview_placeholder)

        # Result summary (hidden until analysis runs)
        self._overview_result = QTextEdit()
        self._overview_result.setReadOnly(True)
        self._overview_result.setVisible(False)
        layout.addWidget(self._overview_result)

        return tab

    def _build_stances_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self._stances_result_list = QListWidget()
        self._stances_result_list.addItem("— noch keine Analyse —")
        layout.addWidget(self._stances_result_list)

        return tab

    def _build_sequences_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self._sequences_result_list = QListWidget()
        self._sequences_result_list.addItem("— noch keine Analyse —")
        layout.addWidget(self._sequences_result_list)

        return tab

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)

        info = QLabel(
            "Sitzungsverlauf (Slice 5)\n\n"
            "Hier werden vergangene Analysen und Fortschritte angezeigt."
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(info)
        return tab

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        disc_name = self._discipline.get("display_name", "")
        sb.showMessage(f"{disc_name}  ·  Bereit")

    # ------------------------------------------------------------------
    # Populate helpers
    # ------------------------------------------------------------------

    def _populate_flow_list(self) -> None:
        self._flow_list.clear()
        if not self._published_flows:
            return
        for fid, flow in self._published_flows.items():
            level = flow.get("practitioner_level", "")
            label = flow.get("label", fid)
            item = QListWidgetItem(f"▶ {label}  [{level}]")
            item.setData(Qt.ItemDataRole.UserRole, fid)
            self._flow_list.addItem(item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_upload_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, UI["upload_video"], "",
            "Videodateien (*.mp4 *.mov *.avi *.mkv);;Alle Dateien (*)"
        )
        if path:
            self._current_video_path = path
            name = Path(path).name
            self._video_path_label.setText(name)
            self._video_path_label.setStyleSheet("font-size: 11px; color: green;")
            self._update_analyse_button_state()
            self.statusBar().showMessage(f"Video geladen: {name}")

    def _on_flow_selected(self, item: QListWidgetItem) -> None:
        self._update_analyse_button_state()

    def _update_analyse_button_state(self) -> None:
        has_video = bool(self._current_video_path)
        # In Slice 1: allow analysis even without a published flow selected
        # (mock engine doesn't need a real flow)
        self._btn_analyse.setEnabled(has_video)

    def _on_start_analysis(self) -> None:
        """
        Slice 1: runs the mock engine and populates result panels.
        Slice 3: replaced with real MediaPipe engine.
        """
        self._progress.setVisible(True)
        self._btn_analyse.setEnabled(False)
        self.statusBar().showMessage(UI["analysis_running"])

        # Run mock engine (synchronous in Slice 1 — no threading yet)
        result = build_mock_recognition_result(
            discipline_path=self._discipline_path,
            video_path=self._current_video_path,
        )

        self._progress.setVisible(False)
        self._btn_analyse.setEnabled(True)
        self.statusBar().showMessage(UI["analysis_complete"])

        self._display_result(result)

    def _display_result(self, result: dict) -> None:
        """Populate all result tabs from a RecognitionResult dict."""

        # Overview tab
        self._overview_placeholder.setVisible(False)
        self._overview_result.setVisible(True)

        lines = [
            f"=== {UI['result_detected_stances']} ===",
        ]
        for ds in result.get("detected_stances", []):
            lines.append(
                f"  {ds['label']:20}  "
                f"@{ds['timestamp_start']:.2f}s  "
                f"{UI['result_confidence']}: {ds['confidence']:.0%}  "
                f"{'⚠ ' + ds['deviation_notes'] if ds.get('deviation_notes') else '✓'}"
            )

        lines.append(f"\n=== {UI['result_detected_sequences']} ===")
        for seq in result.get("detected_sequences", []):
            lines.append(f"  {seq['label']}")

        lines.append(f"\n=== {self._rui['result_matched_flows']} ===")
        matched = result.get("matched_flows", [])
        if matched:
            for mf in matched:
                lines.append(f"  ▶ {mf}")
        else:
            lines.append("  — keine Übereinstimmung —")

        unrecognised = result.get("unrecognised_segments", [])
        if unrecognised:
            lines.append(f"\n=== {UI['result_unrecognised']} ===")
            for seg in unrecognised:
                lines.append(f"  {seg['start']:.2f}s – {seg['end']:.2f}s")

        self._overview_result.setPlainText("\n".join(lines))

        # Stances tab
        self._stances_result_list.clear()
        for ds in result.get("detected_stances", []):
            conf_pct = f"{ds['confidence']:.0%}"
            dev = f"  ⚠ {ds['deviation_notes']}" if ds.get("deviation_notes") else "  ✓"
            text = f"{ds['label']}  ·  @{ds['timestamp_start']:.2f}s  ·  {conf_pct}{dev}"
            self._stances_result_list.addItem(text)

        # Sequences tab
        self._sequences_result_list.clear()
        for seq in result.get("detected_sequences", []):
            self._sequences_result_list.addItem(f"▶ {seq['label']}")
        if not result.get("detected_sequences"):
            self._sequences_result_list.addItem("— keine Sequenzen erkannt —")

        # Enable exports
        self._btn_export_doc.setEnabled(True)

    def _on_export_document(self) -> None:
        _stub_message(self, UI["export_document"])

    def _on_export_video(self) -> None:
        _stub_message(self, UI["export_video"])


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _stub_message(parent: QWidget, action: str) -> None:
    QMessageBox.information(
        parent, action,
        f"'{action}' wird in einem späteren Entwicklungsschritt implementiert."
    )


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line
