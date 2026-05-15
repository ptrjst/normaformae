"""
author/video_panel.py

VideoPanel — PyQt6 widget for video display and frame navigation.

Responsibilities:
- Show the current frame in a QLabel (scaled, aspect-ratio preserved)
- Provide a QSlider scrubber across all frames
- Previous / Next frame buttons
- Emit frame_changed(frame_index: int) signal when the user navigates

Does NOT handle annotation logic — that lives in annotation_panel.py.
Does NOT import MediaPipe or do any analysis.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QSizePolicy,
)

from normaformae.core.video_loader import VideoLoader, VideoInfo, frame_to_pixmap


class VideoPanel(QWidget):
    """
    Displays a video frame and provides scrubber navigation.

    Signals:
        frame_changed(int): emitted whenever the displayed frame index changes.
    """

    frame_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loader:       VideoLoader | None = None
        self._info:         VideoInfo   | None = None
        self._current_idx:  int                = 0

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Frame display
        self._frame_label = QLabel()
        self._frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame_label.setMinimumHeight(300)
        self._frame_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._frame_label.setStyleSheet(
            "background-color: #111; border: 1px solid #333;"
        )
        self._frame_label.setText("Kein Video geladen")
        self._frame_label.setStyleSheet(
            "background-color: #111; color: #666; font-size: 13px;"
            "border: 1px solid #333;"
        )
        layout.addWidget(self._frame_label)

        # Timestamp label
        self._time_label = QLabel("—")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._time_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self._time_label)

        # Scrubber
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(0)
        self._slider.setEnabled(False)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

        # Navigation buttons
        nav_row = QHBoxLayout()
        nav_row.setSpacing(8)

        self._btn_prev = QPushButton("◀ Vorheriges Bild")
        self._btn_prev.setEnabled(False)
        self._btn_prev.clicked.connect(self._on_prev)
        nav_row.addWidget(self._btn_prev)

        self._frame_counter = QLabel("—")
        self._frame_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame_counter.setStyleSheet("font-size: 11px; color: gray; min-width: 100px;")
        nav_row.addWidget(self._frame_counter)

        self._btn_next = QPushButton("Nächstes Bild ▶")
        self._btn_next.setEnabled(False)
        self._btn_next.clicked.connect(self._on_next)
        nav_row.addWidget(self._btn_next)

        layout.addLayout(nav_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_video(self, path: str) -> None:
        """
        Open a video file and display the first frame.
        Closes any previously loaded video.
        """
        if self._loader:
            self._loader.close()
            self._loader = None

        self._loader = VideoLoader(path)
        self._loader.open()
        self._info       = self._loader.info
        self._current_idx = 0

        self._slider.setMaximum(self._info.frame_count - 1)
        self._slider.setValue(0)
        self._slider.setEnabled(True)
        self._btn_prev.setEnabled(True)
        self._btn_next.setEnabled(True)

        self._show_frame(0)

    def current_frame_index(self) -> int:
        return self._current_idx

    def current_timestamp(self) -> float:
        if self._info is None:
            return 0.0
        return self._info.timestamp(self._current_idx)

    def read_current_frame(self):
        """Return the current frame as a numpy RGB array, or None."""
        if self._loader is None:
            return None
        return self._loader.read_frame(self._current_idx)

    def read_frame_range(self, start: int, end: int) -> list:
        """Return frames [start, end] inclusive as a list of numpy RGB arrays."""
        if self._loader is None:
            return []
        end = min(end, self._info.frame_count - 1)
        return self._loader.read_frames(start, end)

    @property
    def info(self) -> VideoInfo | None:
        return self._info

    def closeEvent(self, event) -> None:
        if self._loader:
            self._loader.close()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Internal navigation
    # ------------------------------------------------------------------

    def _show_frame(self, index: int) -> None:
        if self._loader is None or self._info is None:
            return

        index = max(0, min(index, self._info.frame_count - 1))
        self._current_idx = index

        try:
            frame = self._loader.read_frame(index)
            w     = self._frame_label.width()  or 640
            h     = self._frame_label.height() or 400
            pix   = frame_to_pixmap(frame, max_width=w, max_height=h)
            self._frame_label.setPixmap(pix)
        except Exception as e:
            self._frame_label.setText(f"Fehler: {e}")

        ts = self._info.timestamp(index)
        self._time_label.setText(f"{ts:.3f} s")
        self._frame_counter.setText(f"Bild {index + 1} / {self._info.frame_count}")

        self.frame_changed.emit(index)

    def _on_slider_changed(self, value: int) -> None:
        if value != self._current_idx:
            self._show_frame(value)

    def _on_prev(self) -> None:
        if self._current_idx > 0:
            new_idx = self._current_idx - 1
            self._slider.setValue(new_idx)

    def _on_next(self) -> None:
        if self._info and self._current_idx < self._info.frame_count - 1:
            new_idx = self._current_idx + 1
            self._slider.setValue(new_idx)
