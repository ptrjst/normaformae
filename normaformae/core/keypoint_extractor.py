"""
core/keypoint_extractor.py

MediaPipe Pose wrapper for keypoint extraction.

Accepts a numpy RGB frame (or a list of frames for averaging).
Returns normalised keypoints and an annotated frame image.

Configurable visibility threshold per discipline.
TODO: self-adjusting threshold — retry with lower threshold if too few
      keypoints are visible above the current one. See _extract_with_threshold().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class ExtractionResult:
    """Output of a keypoint extraction run."""
    success:          bool
    keypoints_raw:    np.ndarray | None   # (33, 4) — [x, y, z, visibility], world coords
    keypoints_norm:   np.ndarray | None   # (33, 4) — normalised by normalizer.py
    annotated_frame:  np.ndarray | None   # RGB frame with skeleton drawn
    threshold_used:   float = 0.5
    visible_count:    int   = 0           # keypoints above threshold
    error:            str   = ""


class KeypointExtractor:
    """
    Stateful MediaPipe Pose extractor.
    Create once, call extract() for each frame or frame set.

    Args:
        visibility_threshold: minimum landmark visibility to include in normalised vector
        model_complexity:     0 (fastest), 1 (default), 2 (most accurate)
    """

    # Minimum keypoints that must be visible for a result to be considered usable
    MIN_VISIBLE_KEYPOINTS = 10

    def __init__(
        self,
        visibility_threshold: float = 0.5,
        model_complexity: int = 1,
    ) -> None:
        self._threshold       = visibility_threshold
        self._model_complexity = model_complexity
        self._pose            = None   # lazy-initialised on first use

    def _get_pose(self):
        """Lazy-initialise MediaPipe Pose (avoids import cost at module load)."""
        if self._pose is None:
            import mediapipe as mp
            self._pose = mp.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=self._model_complexity,
                enable_segmentation=False,
                min_detection_confidence=0.5,
            )
        return self._pose

    def extract(self, frame_rgb: np.ndarray) -> ExtractionResult:
        """
        Extract and normalise keypoints from a single RGB frame.

        Returns ExtractionResult. On failure, success=False and error is set.
        """
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
            return ExtractionResult(
                success=False,
                keypoints_raw=None,
                keypoints_norm=None,
                annotated_frame=None,
                error="No frames yielded usable keypoints.",
            )

        averaged_norm = average_keypoints([r.keypoints_norm for r in good])
        averaged_raw  = average_keypoints([r.keypoints_raw  for r in good])

        # Use the annotated frame from the result with the most visible keypoints
        best = max(good, key=lambda r: r.visible_count)

        return ExtractionResult(
            success=True,
            keypoints_raw=averaged_raw,
            keypoints_norm=averaged_norm,
            annotated_frame=best.annotated_frame,
            threshold_used=self._threshold,
            visible_count=best.visible_count,
        )

    def close(self) -> None:
        if self._pose is not None:
            self._pose.close()
            self._pose = None

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
        Run MediaPipe on one frame at the given threshold.

        TODO: self-adjusting threshold
            If visible_count < MIN_VISIBLE_KEYPOINTS and threshold > 0.2:
                retry with threshold -= 0.05
            Log which threshold was ultimately used.
            Implement here so the public extract() API is unchanged.
        """
        import mediapipe as mp
        from normaformae.core.normalizer import normalize_keypoints

        try:
            pose    = self._get_pose()
            results = pose.process(frame_rgb)
        except Exception as e:
            return ExtractionResult(
                success=False,
                keypoints_raw=None,
                keypoints_norm=None,
                annotated_frame=None,
                error=f"MediaPipe error: {e}",
            )

        if not results.pose_landmarks:
            return ExtractionResult(
                success=False,
                keypoints_raw=None,
                keypoints_norm=None,
                annotated_frame=frame_rgb.copy(),
                error="No pose detected in frame.",
            )

        # Build (33, 4) array from landmarks
        lm  = results.pose_landmarks.landmark
        raw = np.array(
            [[p.x, p.y, p.z, p.visibility] for p in lm],
            dtype=np.float32,
        )

        visible_count = int((raw[:, 3] >= threshold).sum())
        norm          = normalize_keypoints(raw, visibility_threshold=threshold)

        # Draw skeleton on a copy of the frame
        annotated = _draw_skeleton(frame_rgb.copy(), results)

        return ExtractionResult(
            success=True,
            keypoints_raw=raw,
            keypoints_norm=norm,
            annotated_frame=annotated,
            threshold_used=threshold,
            visible_count=visible_count,
        )


# ---------------------------------------------------------------------------
# Drawing helper
# ---------------------------------------------------------------------------

def _draw_skeleton(frame_rgb: np.ndarray, mp_results) -> np.ndarray:
    """Draw MediaPipe pose skeleton onto a copy of the frame."""
    import mediapipe as mp
    import cv2

    annotated = frame_rgb.copy()
    mp_drawing      = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_pose         = mp.solutions.pose

    # Convert RGB → BGR for OpenCV drawing, then back
    bgr = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
    mp_drawing.draw_landmarks(
        bgr,
        mp_results.pose_landmarks,
        mp_pose.POSE_CONNECTIONS,
        landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style(),
    )
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
