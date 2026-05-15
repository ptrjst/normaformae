"""
core/video_loader.py

OpenCV-based video loader. No PyQt6 dependency in the core functions —
QPixmap conversion is in a separate helper so the loader stays testable
without a display.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from normaformae.core.logger import get_logger

log = get_logger(__name__)


@dataclass
class VideoInfo:
    path:        str
    fps:         float
    frame_count: int
    width:       int
    height:      int

    def timestamp(self, frame_index: int) -> float:
        return round(frame_index / self.fps, 4) if self.fps > 0 else 0.0

    def frame_index(self, timestamp: float) -> int:
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
            frame = vl.read_frame(42)
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
            log.error("Kann Video nicht öffnen: %s", self._path)
            raise IOError(f"Cannot open video: {self._path}")

        self._info = VideoInfo(
            path        = self._path,
            fps         = self._cap.get(cv2.CAP_PROP_FPS) or 25.0,
            frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            width       = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height      = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        log.info(
            "Video geladen: %s  |  %d Bilder  |  %.2f fps  |  %dx%d  |  %.1fs",
            Path(self._path).name,
            self._info.frame_count,
            self._info.fps,
            self._info.width,
            self._info.height,
            self._info.duration,
        )

    def close(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None
            log.debug("VideoCapture geschlossen: %s", Path(self._path).name)

    @property
    def info(self) -> VideoInfo:
        if self._info is None:
            raise RuntimeError("VideoLoader not opened.")
        return self._info

    def read_frame(self, frame_index: int) -> np.ndarray:
        """Read a single frame by index. Returns numpy RGB (H, W, 3)."""
        if self._cap is None:
            raise RuntimeError("VideoLoader not opened.")
        n = self.info.frame_count
        if not (0 <= frame_index < n):
            log.warning("Frame-Index %d außerhalb [0, %d)", frame_index, n)
            raise IndexError(f"Frame {frame_index} out of range [0, {n})")

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, bgr = self._cap.read()
        if not ok:
            log.error("Konnte Bild %d nicht lesen: %s", frame_index, self._path)
            raise IOError(f"Failed to read frame {frame_index} from {self._path}")

        log.debug("Bild %d gelesen (ts=%.3fs)", frame_index, self.info.timestamp(frame_index))
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def read_frames(self, start: int, end: int) -> list[np.ndarray]:
        """Read [start, end] inclusive. Returns list of RGB arrays."""
        log.debug("Lese Bildbereich %d–%d (%d Bilder)", start, end, end - start + 1)
        return [self.read_frame(i) for i in range(start, end + 1)]


# ---------------------------------------------------------------------------
# PyQt6 conversion helper
# ---------------------------------------------------------------------------

def frame_to_pixmap(frame_rgb: np.ndarray, max_width: int = 0, max_height: int = 0):
    """Convert numpy RGB frame to QPixmap, optionally scaled."""
    from PyQt6.QtGui import QImage, QPixmap
    from PyQt6.QtCore import Qt

    h, w, ch = frame_rgb.shape
    qimg   = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)

    if max_width > 0 and max_height > 0:
        pixmap = pixmap.scaled(
            max_width, max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return pixmap


def save_frame_png(frame_rgb: np.ndarray, out_path: Path) -> None:
    """Save numpy RGB frame as PNG."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr)
    log.debug("Frame-Bild gespeichert: %s", out_path)
