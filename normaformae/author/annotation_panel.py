"""
author/annotation_panel.py

AnnotationPanel — PyQt6 widget for frame range labelling and keypoint extraction.

Responsibilities:
- Let the Author mark a START and END frame for a selection
- Assign a label (Hut / Hieb / Ignorieren) to the selection
- Trigger MediaPipe extraction on the selected frames
- Save the resulting Stance JSON (with keypoints + PNG frame) to the library
- Emit stance_saved(stance_id) when a Stance is successfully written

The panel is connected to VideoPanel via signals/slots — it reads the current
frame index from VideoPanel but does not own the VideoLoader.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QProgressBar, QMessageBox,
    QGroupBox,
)

from normaformae.glossary import UI


class AnnotationPanel(QWidget):
    """
    Frame annotation and extraction panel.

    Signals:
        stance_saved(str): emitted with stance_id after a Stance is written.
        sequence_saved(str): emitted with sequence_id after a Transition is saved.
    """

    stance_saved   = pyqtSignal(str)
    sequence_saved = pyqtSignal(str)

    def __init__(
        self,
        discipline_cfg: dict,
        discipline_path: str,
        vocab: dict,
        stances: dict,
        sequences: dict,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._discipline_cfg  = discipline_cfg
        self._discipline_path = discipline_path
        self._vocab           = vocab
        self._stances         = stances    # live reference — updated on save
        self._sequences       = sequences  # live reference

        self._start_frame: int | None = None
        self._end_frame:   int | None = None
        self._current_frame: int      = 0
        self._source_video: str       = ""
        self._fps: float              = 25.0

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("Annotation")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)
        layout.addWidget(_divider())

        # --- Frame range selection ---
        range_box = QGroupBox("Bildbereich")
        range_layout = QVBoxLayout(range_box)

        start_row = QHBoxLayout()
        self._btn_set_start = QPushButton("◀ Start setzen")
        self._btn_set_start.setEnabled(False)
        self._btn_set_start.clicked.connect(self._on_set_start)
        start_row.addWidget(self._btn_set_start)
        self._start_label = QLabel("—")
        self._start_label.setStyleSheet("font-size: 11px; color: gray;")
        start_row.addWidget(self._start_label)
        range_layout.addLayout(start_row)

        end_row = QHBoxLayout()
        self._btn_set_end = QPushButton("Ende setzen ▶")
        self._btn_set_end.setEnabled(False)
        self._btn_set_end.clicked.connect(self._on_set_end)
        end_row.addWidget(self._btn_set_end)
        self._end_label = QLabel("—")
        self._end_label.setStyleSheet("font-size: 11px; color: gray;")
        end_row.addWidget(self._end_label)
        range_layout.addLayout(end_row)

        self._range_summary = QLabel("Kein Bereich gewählt")
        self._range_summary.setStyleSheet("font-size: 11px; color: gray;")
        self._range_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        range_layout.addWidget(self._range_summary)

        layout.addWidget(range_box)

        # --- Label assignment ---
        label_box = QGroupBox("Bezeichnung")
        label_layout = QVBoxLayout(label_box)

        # Label type buttons
        type_row = QHBoxLayout()
        static_label   = self._vocab.get("static",     {}).get("singular", "Position")
        trans_label    = self._vocab.get("transition",  {}).get("singular", "Übergang")
        ignore_label   = self._discipline_cfg.get("annotation_labels", {}).get("ignore", "Ignorieren")

        self._btn_type_stance     = QPushButton(static_label)
        self._btn_type_transition = QPushButton(trans_label)
        self._btn_type_ignore     = QPushButton(ignore_label)

        for btn in (self._btn_type_stance, self._btn_type_transition, self._btn_type_ignore):
            btn.setCheckable(True)
            btn.setMinimumHeight(32)
            btn.setEnabled(False)

        self._btn_type_stance.clicked.connect(lambda: self._select_type("stance"))
        self._btn_type_transition.clicked.connect(lambda: self._select_type("transition"))
        self._btn_type_ignore.clicked.connect(lambda: self._select_type("ignore"))

        type_row.addWidget(self._btn_type_stance)
        type_row.addWidget(self._btn_type_transition)
        type_row.addWidget(self._btn_type_ignore)
        label_layout.addLayout(type_row)

        # Catalog selector (for Hut or Übergang)
        self._catalog_label = QLabel("Aus Katalog wählen oder neu eingeben:")
        self._catalog_label.setStyleSheet("font-size: 11px;")
        label_layout.addWidget(self._catalog_label)

        self._catalog_combo = QComboBox()
        self._catalog_combo.setEditable(True)
        self._catalog_combo.setEnabled(False)
        self._catalog_combo.setPlaceholderText("Bezeichnung eingeben oder auswählen…")
        label_layout.addWidget(self._catalog_combo)

        layout.addWidget(label_box)

        # --- Extraction & Save ---
        layout.addWidget(_divider())

        self._btn_extract = QPushButton("Extrahieren & Speichern")
        self._btn_extract.setMinimumHeight(40)
        self._btn_extract.setEnabled(False)
        self._btn_extract.clicked.connect(self._on_extract_and_save)
        layout.addWidget(self._btn_extract)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Result label
        self._result_label = QLabel("")
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setWordWrap(True)
        self._result_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._result_label)

        layout.addStretch()

        self._selected_type: str = ""

    # ------------------------------------------------------------------
    # Public API — called by AuthorWindow
    # ------------------------------------------------------------------

    def set_video_context(self, source_video: str, fps: float) -> None:
        """Called when a video is loaded in the Author tool."""
        self._source_video = source_video
        self._fps          = fps
        self._start_frame  = None
        self._end_frame    = None
        self._reset_range_display()
        for btn in (self._btn_set_start, self._btn_set_end,
                    self._btn_type_stance, self._btn_type_transition,
                    self._btn_type_ignore):
            btn.setEnabled(True)

    def on_frame_changed(self, frame_index: int) -> None:
        """Slot connected to VideoPanel.frame_changed signal."""
        self._current_frame = frame_index

    def refresh_catalogs(self) -> None:
        """Reload catalog combo options after a save."""
        self._populate_combo()

    # ------------------------------------------------------------------
    # Frame range
    # ------------------------------------------------------------------

    def _on_set_start(self) -> None:
        self._start_frame = self._current_frame
        ts = self._frame_to_ts(self._start_frame)
        self._start_label.setText(f"Bild {self._start_frame}  ({ts:.3f} s)")
        self._start_label.setStyleSheet("font-size: 11px; color: #4caf50;")
        self._update_range_summary()
        self._update_extract_button()

    def _on_set_end(self) -> None:
        if self._start_frame is None:
            self._end_frame = self._current_frame
        else:
            self._end_frame = max(self._current_frame, self._start_frame)
        ts = self._frame_to_ts(self._end_frame)
        self._end_label.setText(f"Bild {self._end_frame}  ({ts:.3f} s)")
        self._end_label.setStyleSheet("font-size: 11px; color: #4caf50;")
        self._update_range_summary()
        self._update_extract_button()

    def _reset_range_display(self) -> None:
        self._start_label.setText("—")
        self._start_label.setStyleSheet("font-size: 11px; color: gray;")
        self._end_label.setText("—")
        self._end_label.setStyleSheet("font-size: 11px; color: gray;")
        self._range_summary.setText("Kein Bereich gewählt")

    def _update_range_summary(self) -> None:
        if self._start_frame is None or self._end_frame is None:
            return
        n = self._end_frame - self._start_frame + 1
        ts_s = self._frame_to_ts(self._start_frame)
        ts_e = self._frame_to_ts(self._end_frame)
        dur  = ts_e - ts_s
        self._range_summary.setText(
            f"{n} Bild{'er' if n != 1 else ''}  ·  {ts_s:.3f}s – {ts_e:.3f}s  ·  Dauer: {dur:.3f}s"
        )

    # ------------------------------------------------------------------
    # Label type selection
    # ------------------------------------------------------------------

    def _select_type(self, type_: str) -> None:
        self._selected_type = type_
        self._btn_type_stance.setChecked(type_ == "stance")
        self._btn_type_transition.setChecked(type_ == "transition")
        self._btn_type_ignore.setChecked(type_ == "ignore")

        show_catalog = type_ in ("stance", "transition")
        self._catalog_label.setVisible(show_catalog)
        self._catalog_combo.setVisible(show_catalog)
        self._catalog_combo.setEnabled(show_catalog)

        if show_catalog:
            self._populate_combo(type_)

        self._update_extract_button()

    def _populate_combo(self, type_: str = "") -> None:
        self._catalog_combo.clear()
        if not type_:
            type_ = self._selected_type

        if type_ == "stance":
            for sid, s in self._stances.items():
                self._catalog_combo.addItem(s.get("label", sid), userData=sid)
        elif type_ == "transition":
            for seq_id, seq in self._sequences.items():
                self._catalog_combo.addItem(seq.get("label", seq_id), userData=seq_id)

    def _update_extract_button(self) -> None:
        ready = (
            self._start_frame is not None
            and self._end_frame is not None
            and self._selected_type in ("stance", "transition", "ignore")
            and self._source_video != ""
        )
        self._btn_extract.setEnabled(ready)

    # ------------------------------------------------------------------
    # Extraction and save
    # ------------------------------------------------------------------

    def _on_extract_and_save(self) -> None:
        if self._selected_type == "ignore":
            self._result_label.setText(
                f"Bilder {self._start_frame}–{self._end_frame} als 'Ignorieren' markiert."
            )
            self._result_label.setStyleSheet("font-size: 11px; color: gray;")
            self._reset_for_next()
            return

        label = self._catalog_combo.currentText().strip()
        if not label:
            QMessageBox.warning(self, "Bezeichnung fehlt",
                                "Bitte eine Bezeichnung eingeben oder aus dem Katalog wählen.")
            return

        self._progress.setVisible(True)
        self._btn_extract.setEnabled(False)
        self._result_label.setText("Extraktion läuft…")

        try:
            if self._selected_type == "stance":
                self._extract_stance(label)
            elif self._selected_type == "transition":
                self._save_transition(label)
        except Exception as e:
            self._progress.setVisible(False)
            self._btn_extract.setEnabled(True)
            self._result_label.setText(f"Fehler: {e}")
            self._result_label.setStyleSheet("font-size: 11px; color: #f44336;")
            QMessageBox.critical(self, "Extraktionsfehler", str(e))

    def _extract_stance(self, label: str) -> None:
        from normaformae.core.video_loader import VideoLoader, save_frame_png
        from normaformae.core.keypoint_extractor import KeypointExtractor
        from normaformae.core.normalizer import keypoints_to_list
        from normaformae.core.discipline_loader import save_stance
        import datetime

        threshold = self._discipline_cfg.get("keypoint_visibility_threshold", 0.5)
        stance_id = _label_to_id(label)

        # Read selected frames
        with VideoLoader(self._source_video) as vl:
            frames = vl.read_frames(self._start_frame, self._end_frame)

        if not frames:
            raise ValueError("Keine Bilder im gewählten Bereich.")

        # Extract keypoints
        with KeypointExtractor(visibility_threshold=threshold) as extractor:
            result = extractor.extract_averaged(frames)

        if not result.success:
            raise ValueError(f"Erkennung fehlgeschlagen: {result.error}")

        # Save annotated frame as PNG
        frames_dir = Path(self._discipline_path) / "library" / "stances" / "frames"
        frame_path = frames_dir / f"{stance_id}.png"
        save_frame_png(result.annotated_frame, frame_path)

        # Build Stance dict
        ts_start = self._frame_to_ts(self._start_frame)
        ts_end   = self._frame_to_ts(self._end_frame)

        # Preserve existing fields if this Stance already exists
        existing = self._stances.get(stance_id, {})
        stance_data = {
            "_schema_version": "1.0.0",
            "_schema_type":    "stance",
            "stance_id":       stance_id,
            "discipline_id":   self._discipline_cfg["discipline_id"],
            "label":           label,
            "status":          existing.get("status", "draft"),
            "extracted_frame": str(frame_path),
            "keypoints":       keypoints_to_list(result.keypoints_norm),
            "reference_image": existing.get("reference_image"),
            "timestamp_start": ts_start,
            "timestamp_end":   ts_end,
            "source_video":    self._source_video,
            "description":     existing.get("description", ""),
            "common_errors":   existing.get("common_errors", []),
            "notes":           existing.get("notes", ""),
        }

        save_stance(self._discipline_path, stance_data)
        self._stances[stance_id] = stance_data

        self._progress.setVisible(False)
        vis_pct = result.visible_count / 33 * 100
        self._result_label.setText(
            f"✓ '{label}' gespeichert  ·  "
            f"{result.visible_count}/33 Punkte sichtbar ({vis_pct:.0f}%)  ·  "
            f"Schwellenwert: {result.threshold_used:.2f}"
        )
        self._result_label.setStyleSheet("font-size: 11px; color: #4caf50;")
        self._reset_for_next()
        self.stance_saved.emit(stance_id)

    def _save_transition(self, label: str) -> None:
        """
        Save timing data for a Transition (Übergang).
        Keypoint comparison for transitions is Slice 3.
        """
        from normaformae.core.discipline_loader import save_sequence
        import datetime

        ts_start = self._frame_to_ts(self._start_frame)
        ts_end   = self._frame_to_ts(self._end_frame)
        duration = round(ts_end - ts_start, 4)
        seq_id   = _label_to_id(label)

        existing = self._sequences.get(seq_id, {})
        seq_data = {
            "_schema_version":  "1.0.0",
            "_schema_type":     "sequence",
            "sequence_id":      seq_id,
            "discipline_id":    self._discipline_cfg["discipline_id"],
            "label":            label,
            "status":           existing.get("status", "draft"),
            "from_stance_id":   existing.get("from_stance_id"),
            "transition_id":    existing.get("transition_id"),
            "to_stance_id":     existing.get("to_stance_id"),
            "duration_seconds": duration,
            "source_video":     self._source_video,
            "timestamp_start":  ts_start,
            "timestamp_end":    ts_end,
            "description":      existing.get("description", ""),
            "motion_cues":      existing.get("motion_cues", []),
            "common_errors":    existing.get("common_errors", []),
        }

        save_sequence(self._discipline_path, seq_data)
        self._sequences[seq_id] = seq_data

        self._progress.setVisible(False)
        self._result_label.setText(
            f"✓ Übergang '{label}' gespeichert  ·  Dauer: {duration:.3f}s"
        )
        self._result_label.setStyleSheet("font-size: 11px; color: #4caf50;")
        self._reset_for_next()
        self.sequence_saved.emit(seq_id)

    def _reset_for_next(self) -> None:
        """Clear selection after a successful save, ready for next annotation."""
        self._start_frame = None
        self._end_frame   = None
        self._reset_range_display()
        self._btn_extract.setEnabled(False)
        self._selected_type = ""
        for btn in (self._btn_type_stance, self._btn_type_transition, self._btn_type_ignore):
            btn.setChecked(False)
        self._catalog_combo.setEnabled(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _frame_to_ts(self, frame_index: int) -> float:
        return round(frame_index / self._fps, 4) if self._fps > 0 else 0.0


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _label_to_id(label: str) -> str:
    """Convert a German label to a snake_case ID, e.g. 'Vom Tag' → 'vom_tag'."""
    import unicodedata
    # Normalise umlauts
    replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}
    result = label
    for char, sub in replacements.items():
        result = result.replace(char, sub)
    # Remove remaining non-ASCII
    result = unicodedata.normalize("NFKD", result)
    result = "".join(c for c in result if c.isascii())
    # snake_case
    return "_".join(result.lower().split())


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line
