"""
core/normalizer.py

Pure-numpy keypoint normalisation. No MediaPipe dependency.
Works on any (N, 4) array where columns are [x, y, z, visibility].

Normalisation steps:
1. Translate: subtract hip midpoint.
2. Scale: divide by torso length (hip midpoint → neck midpoint).
3. Filter: zero out keypoints below the visibility threshold.
"""

from __future__ import annotations

import numpy as np

from normaformae.core.logger import get_logger

log = get_logger(__name__)

_LEFT_SHOULDER  = 11
_RIGHT_SHOULDER = 12
_LEFT_HIP       = 23
_RIGHT_HIP      = 24


def normalize_keypoints(
    keypoints: np.ndarray,
    visibility_threshold: float = 0.5,
) -> np.ndarray:
    """Normalise a (33, 4) MediaPipe keypoint array."""
    if keypoints.shape != (33, 4):
        raise ValueError(f"Expected shape (33, 4), got {keypoints.shape}")

    kp = keypoints.copy().astype(np.float32)

    left_hip  = kp[_LEFT_HIP,  :3]
    right_hip = kp[_RIGHT_HIP, :3]
    left_sho  = kp[_LEFT_SHOULDER,  :3]
    right_sho = kp[_RIGHT_SHOULDER, :3]

    hip_mid      = (left_hip  + right_hip) / 2.0
    neck_mid     = (left_sho  + right_sho) / 2.0
    torso_length = float(np.linalg.norm(neck_mid - hip_mid))

    if torso_length < 1e-6:
        log.warning(
            "Torsolänge zu klein (%.6f) — Normalisierung übersprungen", torso_length
        )
        return kp

    log.debug(
        "Normalisierung: Torsolänge=%.4f  Hüftmitte=(%.3f, %.3f, %.3f)",
        torso_length, hip_mid[0], hip_mid[1], hip_mid[2],
    )

    kp[:, :3] -= hip_mid
    kp[:, :3] /= torso_length

    low_vis = kp[:, 3] < visibility_threshold
    zeroed  = int(low_vis.sum())
    kp[low_vis, :3] = 0.0

    if zeroed > 0:
        log.debug(
            "Normalisierung: %d/%d Punkte unter Sichtbarkeitsschwelle (%.2f) genullt",
            zeroed, len(kp), visibility_threshold,
        )

    return kp


def average_keypoints(frames_keypoints: list[np.ndarray]) -> np.ndarray:
    """Average normalised keypoints across multiple frames, weighted by visibility."""
    if not frames_keypoints:
        raise ValueError("frames_keypoints must not be empty")

    if len(frames_keypoints) == 1:
        return frames_keypoints[0].copy()

    weights = np.array(
        [kp[:, 3].mean() for kp in frames_keypoints], dtype=np.float32
    )
    total = weights.sum()
    if total < 1e-6:
        weights = np.ones(len(frames_keypoints), dtype=np.float32)
        total   = float(len(frames_keypoints))

    averaged = np.zeros((33, 4), dtype=np.float32)
    for w, kp in zip(weights, frames_keypoints):
        averaged += (w / total) * kp

    return averaged


def keypoints_to_list(kp: np.ndarray) -> list[list[float]]:
    return kp.tolist()


def keypoints_from_list(data: list[list[float]]) -> np.ndarray:
    arr = np.array(data, dtype=np.float32)
    if arr.shape != (33, 4):
        raise ValueError(f"Expected 33×4 list, got shape {arr.shape}")
    return arr
