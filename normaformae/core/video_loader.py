"""
core/video_loader.py

OpenCV-based video loader. No PyQt6 dependency in the core functions —
QPixmap conversion is in a separate helper so the loader stays testable
without a display.

Responsibilities:
- Open a video file and read metadata (FPS, frame count, resolution)
- Extract a specific frame by index as a numpy RGB array
- Convert a numpy frame to QPixmap for display in the Author UI
- Extract and save a frame as a PNG file
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class VideoInfo:
    path:        str
    fps:         float
    frame_count: int
    width:       int
    height:      int

    def timestamp(self, frame_index: int) -> float:
        """Convert frame index to seconds from video start."""
        return round(frame_index / self.fps, 4) if self.fps > 0 else 0.0

    def frame_index(self, timestamp: float) -> int:
        """Convert seconds to nearest frame index."""
        return int(round(timestamp * self.fps))

    @property
    def duration(self) -> float:
        return self.timestamp(self.frame_count)


class VideoLoader:
    """
    Context-managed video reader.

    Usage:
        with VideoLoader(path) as vl:
            info  = vl.info
            frame = vl.read_frame(42)   # numpy RGB (H, W, 3)
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._cap:  cv2.VideoCapture | None = None
        self._info: VideoInfo | None        = None

    def __enter__(self) -> "VideoLoader":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self._path)
        if not self._cap.isOpened():
            raise IOError(f"Cannot open video: {self._path}")
        self._info = VideoInfo(
            path        = self._path,
            fps         = self._cap.get(cv2.CAP_PROP_FPS) or 25.0,
            frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            width       = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height      = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    def close(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None

    @property
    def info(self) -> VideoInfo:
        if self._info is None:
            raise RuntimeError("VideoLoader not opened.")
        return self._info

    def read_frame(self, frame_index: int) -> np.ndarray:
        """
        Read a single frame by index.
        Returns numpy array of shape (H, W, 3) in RGB colour order.
        Raises IndexError if frame_index is out of range.
        """
        if self._cap is None:
            raise RuntimeError("VideoLoader not opened.")
        n = self.info.frame_count
        if not (0 <= frame_index < n):
            raise IndexError(f"Frame {frame_index} out of range [0, {n})")

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, bgr = self._cap.read()
        if not ok:
            raise IOError(f"Failed to read frame {frame_index} from {self._path}")

        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def read_frames(self, start: int, end: int) -> list[np.ndarray]:
        """
        Read a contiguous range of frames [start, end] inclusive.
        Returns list of RGB numpy arrays.
        """
        return [self.read_frame(i) for i in range(start, end + 1)]


# ---------------------------------------------------------------------------
# PyQt6 conversion helper — import only when UI is available
# ---------------------------------------------------------------------------

def frame_to_pixmap(frame_rgb: np.ndarray, max_width: int = 0, max_height: int = 0):
    """
    Convert a numpy RGB frame to a QPixmap, optionally scaled to fit a bounding box.
    Preserves aspect ratio. Returns QPixmap.

    Import is deferred so this module remains importable in CLI/headless mode.
    """
    from PyQt6.QtGui import QImage, QPixmap
    from PyQt6.QtCore import Qt

    h, w, ch = frame_rgb.shape
    bytes_per_line = ch * w
    qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)

    if max_width > 0 and max_height > 0:
        pixmap = pixmap.scaled(
            max_width, max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    return pixmap


def save_frame_png(frame_rgb: np.ndarray, out_path: Path) -> None:
    """Save a numpy RGB frame as a PNG file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr)
