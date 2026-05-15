"""
user/window.py

User tool — main window.

Slice 3: real analysis engine (engine.py) via QThread.
         URL input enabled via yt-dlp.
         Real RecognitionResult displayed in tabs.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFrame,
    QTabWidget, QTextEdit, QToolBar, QStatusBar, QMessageBox,
    QFileDialog, QLineEdit, QGroupBox, QProgressBar,
)

from normaformae.core.discipline_loader import (
    load_discipline, load_published_flows, load_all_stances,
    get_vocabulary, DisciplineLoadError,
)
from normaformae.glossary import UI, resolve_ui
from normaformae.core.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Analysis worker thread
# ---------------------------------------------------------------------------

class AnalysisWorker(QThread):
    """
    Runs the analysis engine in a background thread.
    Emits progress updates and a final result.
    """
    progress  = pyqtSignal(int, int)   # (current_frame, total_frames)
    finished  = pyqtSignal(dict)       # RecognitionResult
    error     = pyqtSignal(str)        # error message

    def __init__(self, video_path: str, discipline_path: str) -> None:
        super().__init__()
        self._video_path      = video_path
        self._discipline_path = discipline_path

    def run(self) -> None:
        try:
            from normaformae.core.engine import analyse
            result = analyse(
                video_path=self._video_path,
                discipline_path=self._discipline_path,
                progress_callback=lambda cur, tot: self.progress.emit(cur, tot),
            )
            self.finished.emit(result)
        except Exception as e:
            log.error("Analysefehler im Worker-Thread: %s", e, exc_info=True)
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# URL download worker thread
# ---------------------------------------------------------------------------

class DownloadWorker(QThread):
    """Downloads a video URL to a temp file via yt-dlp."""
    finished = pyqtSignal(str)   # temp file path
    error    = pyqtSignal(str)   # error message

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    def run(self) -> None:
        try:
            import yt_dlp
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.close()
            ydl_opts = {
                "outtmpl": tmp.name,
                "format":  "mp4/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                "quiet":   True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self._url])
            log.info("Video heruntergeladen: %s → %s", self._url, tmp.name)
            self.finished.emit(tmp.name)
        except Exception as e:
            log.error("Download-Fehler: %s", e, exc_info=True)
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class UserWindow(QMainWindow):
    """
    Main window for the User persona.
    Layout: [Input + flow selection panel] | [Result panel — tabs]
    """

    def __init__(self, discipline_path: str) -> None:
        super().__init__()
        self._discipline_path = discipline_path
        self._discipline: dict = {}
        self._published_flows: dict = {}
        self._valid_stances: dict = {}
        self._vocab: dict = {}
        self._rui: dict = UI.copy()
        self._current_video_path: str = ""
        self._temp_video_path: str = ""   # set when URL download used
        self._worker: AnalysisWorker | None = None
        self._dl_worker: DownloadWorker | None = None

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
            self._discipline      = load_discipline(self._discipline_path)
            self._published_flows = load_published_flows(self._discipline_path)
            all_stances           = load_all_stances(self._discipline_path)
            self._valid_stances   = {
                sid: s for sid, s in all_stances.items()
                if s.get("keypoints") is not None
            }
            self._vocab = get_vocabulary(self._discipline)
            self._rui   = resolve_ui(self._vocab)
        except DisciplineLoadError as e:
            QMessageBox.critical(self, "Fehler", str(e))

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        disc_name = self._discipline.get("display_name", "")
        tb.addWidget(QLabel(f"  {disc_name}  "))
        tb.addSeparator()
        n = len(self._valid_stances)
        total = len(load_all_stances(self._discipline_path)) if self._discipline_path else 0
        tb.addWidget(QLabel(
            f"{n}/{total} {self._vocab.get('static',{}).get('plural','Huten')} im Katalog  "
        ))

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
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

        # Video input
        video_box = QGroupBox("Video")
        vl = QVBoxLayout(video_box)

        upload_row = QHBoxLayout()
        self._video_path_label = QLabel(UI["error_no_video"])
        self._video_path_label.setStyleSheet("font-size: 11px; color: gray;")
        self._video_path_label.setWordWrap(True)
        upload_row.addWidget(self._video_path_label)
        self._btn_upload = QPushButton(UI["upload_video"])
        self._btn_upload.setFixedWidth(110)
        self._btn_upload.clicked.connect(self._on_upload_video)
        upload_row.addWidget(self._btn_upload)
        vl.addLayout(upload_row)

        # URL input — now enabled
        vl.addWidget(QLabel(UI["video_url"]))
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://youtube.com/watch?v=…")
        self._url_input.returnPressed.connect(self._on_download_url)
        vl.addWidget(self._url_input)

        self._btn_download = QPushButton("URL herunterladen")
        self._btn_download.clicked.connect(self._on_download_url)
        vl.addWidget(self._btn_download)

        layout.addWidget(video_box)

        # Flow selector
        flow_box = QGroupBox(
            self._vocab.get("flow", {}).get("plural", "Abläufe")
        )
        fl = QVBoxLayout(flow_box)

        if not self._published_flows:
            no_flows = QLabel(
                f"Keine veröffentlichten "
                f"{self._vocab.get('flow',{}).get('plural','Abläufe')} vorhanden."
            )
            no_flows.setStyleSheet("color: gray; font-size: 11px;")
            no_flows.setWordWrap(True)
            fl.addWidget(no_flows)

        self._flow_list = QListWidget()
        self._flow_list.setMinimumHeight(80)
        self._populate_flow_list()
        fl.addWidget(self._flow_list)
        layout.addWidget(flow_box)

        # Analyse button + progress
        self._btn_analyse = QPushButton(UI["start_analysis"])
        self._btn_analyse.setMinimumHeight(44)
        self._btn_analyse.setEnabled(False)
        self._btn_analyse.clicked.connect(self._on_start_analysis)
        layout.addWidget(self._btn_analyse)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet("font-size: 10px; color: gray;")
        layout.addWidget(self._progress_label)

        layout.addStretch()

        layout.addWidget(_divider())
        self._btn_export_doc = QPushButton(UI["export_document"])
        self._btn_export_doc.setEnabled(False)
        self._btn_export_doc.clicked.connect(self._on_export_document)
        layout.addWidget(self._btn_export_doc)

        self._btn_export_video = QPushButton(UI["export_video"])
        self._btn_export_video.setEnabled(False)
        self._btn_export_video.setToolTip("Augmentiertes Video — verfügbar in Slice 5")
        layout.addWidget(self._btn_export_video)

        return panel

    # ------------------------------------------------------------------
    # Right: Result panel
    # ------------------------------------------------------------------

    def _build_result_panel(self) -> QWidget:
        self._result_tabs = QTabWidget()
        self._result_tabs.addTab(self._build_overview_tab(),  "Übersicht")
        self._result_tabs.addTab(self._build_stances_tab(),   self._vocab.get("static",{}).get("plural","Huten"))
        self._result_tabs.addTab(self._build_sequences_tab(), "Sequenzen")
        self._result_tabs.addTab(self._build_history_tab(),   "Verlauf (Slice 5)")
        return self._result_tabs

    def _build_overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)

        self._overview_placeholder = QLabel(
            "Kein Analyseergebnis vorhanden.\n\n"
            "1. Video hochladen oder URL eingeben\n"
            "2. Analyse starten"
        )
        self._overview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overview_placeholder.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(self._overview_placeholder)

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
        info = QLabel("Sitzungsverlauf (Slice 5)\n\nHier werden vergangene Analysen angezeigt.")
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
        n = len(self._valid_stances)
        sb.showMessage(f"{disc_name}  ·  {n} {self._vocab.get('static',{}).get('plural','Huten')} verfügbar  ·  Bereit")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _populate_flow_list(self) -> None:
        self._flow_list.clear()
        for fid, flow in self._published_flows.items():
            level = flow.get("practitioner_level", "")
            item  = QListWidgetItem(f"▶ {flow.get('label', fid)}  [{level}]")
            item.setData(Qt.ItemDataRole.UserRole, fid)
            self._flow_list.addItem(item)

    def _set_video(self, path: str, label: str) -> None:
        self._current_video_path = path
        self._video_path_label.setText(label)
        self._video_path_label.setStyleSheet("font-size: 11px; color: green;")
        self._btn_analyse.setEnabled(bool(self._valid_stances))
        if not self._valid_stances:
            self.statusBar().showMessage(
                "Keine gültigen Huten im Katalog — bitte zuerst Huten annotieren."
            )
        else:
            self.statusBar().showMessage(f"Video bereit: {label}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_upload_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, UI["upload_video"], "",
            "Videodateien (*.mp4 *.mov *.avi *.mkv);;Alle Dateien (*)"
        )
        if path:
            # Clean up any previous temp download
            self._cleanup_temp()
            self._set_video(path, Path(path).name)

    def _on_download_url(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            return
        self._btn_download.setEnabled(False)
        self._btn_upload.setEnabled(False)
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._progress_label.setText("Video wird heruntergeladen…")
        self.statusBar().showMessage(f"Lade herunter: {url}")
        log.info("URL-Download gestartet: %s", url)

        self._dl_worker = DownloadWorker(url)
        self._dl_worker.finished.connect(self._on_download_finished)
        self._dl_worker.error.connect(self._on_download_error)
        self._dl_worker.start()

    def _on_download_finished(self, tmp_path: str) -> None:
        self._cleanup_temp()
        self._temp_video_path = tmp_path
        self._btn_download.setEnabled(True)
        self._btn_upload.setEnabled(True)
        self._progress.setVisible(False)
        self._progress_label.setText("")
        name = Path(tmp_path).name
        self._set_video(tmp_path, f"[URL] {self._url_input.text()[:40]}")

    def _on_download_error(self, msg: str) -> None:
        self._btn_download.setEnabled(True)
        self._btn_upload.setEnabled(True)
        self._progress.setVisible(False)
        self._progress_label.setText("")
        QMessageBox.critical(self, "Download-Fehler", msg)
        self.statusBar().showMessage("Download fehlgeschlagen.")

    def _on_start_analysis(self) -> None:
        if not self._current_video_path:
            QMessageBox.warning(self, "Kein Video", UI["error_no_video"])
            return
        if not self._valid_stances:
            QMessageBox.warning(
                self, "Keine Huten",
                "Keine annotierten Huten im Katalog. "
                "Bitte zuerst Huten im Autorenwerkzeug anlegen."
            )
            return

        self._btn_analyse.setEnabled(False)
        self._progress.setRange(0, 0)  # indeterminate start
        self._progress.setVisible(True)
        self._progress_label.setText("Modell wird geladen…")
        self.statusBar().showMessage(UI["analysis_running"])
        log.info("Analyse gestartet: %s", self._current_video_path)

        self._worker = AnalysisWorker(self._current_video_path, self._discipline_path)
        self._worker.progress.connect(self._on_analysis_progress)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _on_analysis_progress(self, current: int, total: int) -> None:
        if self._progress.maximum() == 0:
            self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._progress_label.setText(f"Bild {current} / {total}")

    def _on_analysis_finished(self, result: dict) -> None:
        self._progress.setVisible(False)
        self._progress_label.setText("")
        self._btn_analyse.setEnabled(True)
        self.statusBar().showMessage(UI["analysis_complete"])
        log.info("Analyse abgeschlossen — Engine: %s", result.get("engine", "?"))
        self._display_result(result)
        self._btn_export_doc.setEnabled(True)

    def _on_analysis_error(self, msg: str) -> None:
        self._progress.setVisible(False)
        self._progress_label.setText("")
        self._btn_analyse.setEnabled(True)
        self.statusBar().showMessage("Analyse fehlgeschlagen.")
        QMessageBox.critical(self, "Analysefehler", msg)

    def _on_export_document(self) -> None:
        QMessageBox.information(
            self, UI["export_document"],
            "Dokument-Export wird in Slice 4 implementiert."
        )

    # ------------------------------------------------------------------
    # Result display
    # ------------------------------------------------------------------

    def _display_result(self, result: dict) -> None:
        engine_label = (
            "Echtzeit-Engine" if result.get("engine") == "real" else "Simulation"
        )
        cfg = result.get("config", {})

        lines = [
            f"Engine: {engine_label}",
            f"Abtastrate: jedes {cfg.get('frame_sample_rate','?')}. Bild  "
            f"·  Schwellenwert: {cfg.get('stance_match_threshold','?')}",
            "",
            f"=== {self._rui['result_detected_stances']} "
            f"({len(result.get('detected_stances', []))}) ===",
        ]
        for ds in result.get("detected_stances", []):
            devs = ", ".join(ds.get("deviation_notes", [])) or "✓ keine Abweichung"
            lines.append(
                f"  {ds['label']:20}  "
                f"@{ds['timestamp_start']:.2f}s–{ds['timestamp_end']:.2f}s  "
                f"{ds['confidence']:.0%}  {devs}"
            )

        seqs = result.get("detected_sequences", [])
        lines += ["", f"=== Sequenzen ({len(seqs)}) ==="]
        for s in seqs:
            lines.append(f"  ▶ {s['label']}")
        if not seqs:
            lines.append("  — keine —")

        matched = result.get("matched_flows", [])
        lines += ["", f"=== {self._rui['result_matched_flows']} ({len(matched)}) ==="]
        for mf in matched:
            lines.append(f"  ▶ {mf}")
        if not matched:
            lines.append("  — keine —")

        unrec = result.get("unrecognised_segments", [])
        if unrec:
            lines += ["", f"=== {UI['result_unrecognised']} ==="]
            for seg in unrec:
                lines.append(f"  {seg['start']:.2f}s – {seg['end']:.2f}s")

        self._overview_placeholder.setVisible(False)
        self._overview_result.setVisible(True)
        self._overview_result.setPlainText("\n".join(lines))

        # Stances tab
        self._stances_result_list.clear()
        for ds in result.get("detected_stances", []):
            devs = ", ".join(ds.get("deviation_notes", [])) or "✓"
            self._stances_result_list.addItem(
                f"{ds['label']}  ·  @{ds['timestamp_start']:.2f}s  "
                f"·  {ds['confidence']:.0%}  ·  {devs}"
            )
        if not result.get("detected_stances"):
            self._stances_result_list.addItem("— keine erkannt —")

        # Sequences tab
        self._sequences_result_list.clear()
        for s in seqs:
            cat = " [Katalog]" if s.get("sequence_id") else " [abgeleitet]"
            self._sequences_result_list.addItem(f"▶ {s['label']}{cat}")
        if not seqs:
            self._sequences_result_list.addItem("— keine erkannt —")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_temp(self) -> None:
        if self._temp_video_path:
            try:
                Path(self._temp_video_path).unlink(missing_ok=True)
                log.debug("Temp-Datei gelöscht: %s", self._temp_video_path)
            except Exception:
                pass
            self._temp_video_path = ""

    def closeEvent(self, event) -> None:
        self._cleanup_temp()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line
