"""
core/keypoint_extractor.py

MediaPipe Pose Landmarker wrapper for keypoint extraction.
Uses the MediaPipe Tasks API (0.10+): mp.tasks.vision.PoseLandmarker.

Accepts a numpy RGB frame (or a list of frames for averaging).
Returns normalised keypoints and an annotated frame image.

Key differences from the legacy 0.9 solutions API:
- Uses PoseLandmarker (tasks API) instead of mp.solutions.pose.Pose
- Requires a downloaded .task model file (see normaformae/models/)
- pose_world_landmarks gives metric 3D coordinates — used for normalisation
- Drawing is done manually with OpenCV (mp.solutions.drawing_utils is gone)

TODO: self-adjusting threshold
    If visible_count < MIN_VISIBLE_KEYPOINTS and threshold > 0.2:
        retry with threshold -= 0.05
    Log which threshold was ultimately used.
    Implement in _extract_with_threshold() — public API unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from normaformae.core.logger import get_logger

log = get_logger(__name__)


# MediaPipe POSE_CONNECTIONS — 35 pairs of landmark indices
# Defined here so we don't need mp.solutions at runtime
POSE_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,7),(0,4),(4,5),(5,6),(6,8),
    (9,10),(11,12),(11,13),(13,15),(15,17),(15,19),(15,21),(17,19),
    (12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
    (11,23),(12,24),(23,24),(23,25),(24,26),(25,27),(26,28),
    (27,29),(28,30),(29,31),(30,32),(27,31),(28,32),
]


@dataclass
class ExtractionResult:
    """Output of a keypoint extraction run. Interface unchanged from Slice 2."""
    success:          bool
    keypoints_raw:    np.ndarray | None   # (33, 4) — [x, y, z, visibility]
    keypoints_norm:   np.ndarray | None   # (33, 4) — normalised
    annotated_frame:  np.ndarray | None   # RGB frame with skeleton drawn
    threshold_used:   float = 0.5
    visible_count:    int   = 0
    error:            str   = ""


class KeypointExtractor:
    """
    Stateful MediaPipe PoseLandmarker extractor (Tasks API 0.10+).
    Create once, call extract() / extract_averaged() per frame set.

    Args:
        visibility_threshold: minimum landmark visibility to include in normalised vector
        model_variant:        "lite" | "full" | "heavy" (default: "full")
    """

    MIN_VISIBLE_KEYPOINTS = 10

    def __init__(
        self,
        visibility_threshold: float = 0.5,
        model_variant: str = "full",
    ) -> None:
        self._threshold     = visibility_threshold
        self._model_variant = model_variant
        self._landmarker    = None   # lazy-initialised on first use

    def _get_landmarker(self):
        """Lazy-initialise PoseLandmarker. Downloads model if needed."""
        if self._landmarker is not None:
            return self._landmarker

        from mediapipe.tasks.python.vision import (
            PoseLandmarker, PoseLandmarkerOptions, RunningMode,
        )
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from normaformae.models.download_models import ensure_model

        model_path = ensure_model(self._model_variant)

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)
        log.info("PoseLandmarker geladen: Variante=%s  Schwellenwert=%.2f",
                 self._model_variant, self._threshold)
        return self._landmarker

    def extract(self, frame_rgb: np.ndarray) -> ExtractionResult:
        """Extract and normalise keypoints from a single RGB frame."""
        return self._extract_with_threshold(frame_rgb, self._threshold)

    def extract_averaged(self, frames_rgb: list[np.ndarray]) -> ExtractionResult:
        """
        Extract keypoints from multiple frames and return a weighted average.
        Frames that fail extraction are skipped.
        Annotated frame is taken from the highest-confidence individual result.
        """
        from normaformae.core.normalizer import average_keypoints

        results = [self.extract(f) for f in frames_rgb]
        good    = [r for r in results if r.success and r.keypoints_norm is not None]

        if not good:
            # Collect all per-frame errors for a useful diagnostic message
            errors = [r.error for r in results if r.error]
            summary = errors[0] if errors else "Unbekannter Fehler"
            return ExtractionResult(
                success=False,
                keypoints_raw=None,
                keypoints_norm=None,
                annotated_frame=None,
                error=f"Kein Bild lieferte verwertbare Schlüsselpunkte. "
                      f"Erster Fehler: {summary}",
            )

        averaged_norm = average_keypoints([r.keypoints_norm for r in good])
        averaged_raw  = average_keypoints([r.keypoints_raw  for r in good])
        best          = max(good, key=lambda r: r.visible_count)
        log.info(
            "Mittelwert aus %d/%d Bildern — beste Sichtbarkeit: %d/33",
            len(good), len(results), best.visible_count,
        )

        return ExtractionResult(
            success=True,
            keypoints_raw=averaged_raw,
            keypoints_norm=averaged_norm,
            annotated_frame=best.annotated_frame,
            threshold_used=self._threshold,
            visible_count=best.visible_count,
        )

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def __enter__(self) -> "KeypointExtractor":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _extract_with_threshold(
        self, frame_rgb: np.ndarray, threshold: float
    ) -> ExtractionResult:
        """
        Run PoseLandmarker on one frame at the given threshold.

        TODO: self-adjusting threshold
            If visible_count < MIN_VISIBLE_KEYPOINTS and threshold > 0.2:
                retry with threshold -= 0.05, up to 3 retries
            Log which threshold was ultimately used in ExtractionResult.threshold_used
        """
        import mediapipe as mp
        from normaformae.core.normalizer import normalize_keypoints

        try:
            landmarker = self._get_landmarker()

            # Wrap numpy array in MediaPipe Image
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame_rgb.astype(np.uint8),
            )
            result = landmarker.detect(mp_image)

        except Exception as e:
            log.error("MediaPipe Fehler: %s", e, exc_info=True)
            return ExtractionResult(
                success=False,
                keypoints_raw=None,
                keypoints_norm=None,
                annotated_frame=frame_rgb.copy() if frame_rgb is not None else None,
                error=f"MediaPipe Fehler: {e}",
            )

        # Check if any pose was detected
        if not result.pose_world_landmarks or not result.pose_landmarks:
            log.debug("Keine Pose im Bild erkannt.")
            return ExtractionResult(
                success=False,
                keypoints_raw=None,
                keypoints_norm=None,
                annotated_frame=frame_rgb.copy(),
                error="Keine Pose im Bild erkannt.",
            )

        # Use first detected person (num_poses=1)
        world_lm = result.pose_world_landmarks[0]   # metric 3D — for normalisation
        norm_lm  = result.pose_landmarks[0]          # normalised 0-1 — for visibility

        # Build (33, 4) array: [x, y, z] from world landmarks, visibility from norm
        raw = np.array(
            [[wl.x, wl.y, wl.z, nl.visibility]
             for wl, nl in zip(world_lm, norm_lm)],
            dtype=np.float32,
        )

        visible_count = int((raw[:, 3] >= threshold).sum())
        log.debug(
            "Extraktion: %d/33 Punkte sichtbar (Schwellenwert=%.2f)",
            visible_count, threshold,
        )
        if visible_count < KeypointExtractor.MIN_VISIBLE_KEYPOINTS:
            log.warning(
                "Wenige sichtbare Punkte: %d/33 (Minimum=%d, Schwellenwert=%.2f)",
                visible_count, KeypointExtractor.MIN_VISIBLE_KEYPOINTS, threshold,
            )
        norm          = normalize_keypoints(raw, visibility_threshold=threshold)

        # Draw skeleton on annotated frame
        annotated = _draw_skeleton(frame_rgb.copy(), result)

        return ExtractionResult(
            success=True,
            keypoints_raw=raw,
            keypoints_norm=norm,
            annotated_frame=annotated,
            threshold_used=threshold,
            visible_count=visible_count,
        )


# ---------------------------------------------------------------------------
# Drawing helper — manual OpenCV drawing (mp.solutions.drawing_utils gone in 0.10+)
# ---------------------------------------------------------------------------

# Landmark colours
_COLOUR_JOINT      = (0, 255, 0)    # green
_COLOUR_CONNECTION = (255, 255, 0)  # yellow
_COLOUR_LOW_VIS    = (128, 128, 128) # grey for low-visibility joints


def _draw_skeleton(frame_rgb: np.ndarray, mp_result) -> np.ndarray:
    """
    Draw pose skeleton on an RGB frame using OpenCV.
    Uses normalised landmarks (0–1 coordinates) for pixel projection.
    """
    import cv2

    if not mp_result.pose_landmarks:
        return frame_rgb

    annotated = frame_rgb.copy()
    h, w      = annotated.shape[:2]
    lms       = mp_result.pose_landmarks[0]

    # Pixel coordinates for all 33 landmarks
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]

    # Draw connections
    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            vis = min(lms[a].visibility, lms[b].visibility)
            colour = _COLOUR_CONNECTION if vis >= 0.5 else _COLOUR_LOW_VIS
            cv2.line(annotated, pts[a], pts[b], colour, 2, cv2.LINE_AA)

    # Draw joints
    for i, (x, y) in enumerate(pts):
        vis    = lms[i].visibility
        colour = _COLOUR_JOINT if vis >= 0.5 else _COLOUR_LOW_VIS
        radius = 4 if vis >= 0.5 else 2
        cv2.circle(annotated, (x, y), radius, colour, -1, cv2.LINE_AA)

    return annotated
