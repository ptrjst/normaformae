"""
core/normalizer.py

Pure-numpy keypoint normalisation.
No MediaPipe dependency — works on any (N, 4) keypoint array
where columns are [x, y, z, visibility].

Normalisation steps:
1. Translate: subtract hip midpoint so body centre is at origin.
2. Scale: divide by torso length (hip-midpoint → neck midpoint distance).
3. Filter: zero out keypoints below the visibility threshold.

MediaPipe landmark indices used:
    11 = left shoulder,  12 = right shoulder
    23 = left hip,       24 = right hip
"""

from __future__ import annotations

import numpy as np


# MediaPipe landmark indices for anchor points
_LEFT_SHOULDER  = 11
_RIGHT_SHOULDER = 12
_LEFT_HIP       = 23
_RIGHT_HIP      = 24


def normalize_keypoints(
    keypoints: np.ndarray,
    visibility_threshold: float = 0.5,
) -> np.ndarray:
    """
    Normalise a (33, 4) MediaPipe keypoint array.

    Args:
        keypoints:            np.ndarray of shape (33, 4) — [x, y, z, visibility]
        visibility_threshold: keypoints below this are zeroed out

    Returns:
        Normalised (33, 4) array. Invisible keypoints have x=y=z=0, visibility unchanged.
        Returns the input unchanged if anchor points are not visible enough to normalise.
    """
    if keypoints.shape != (33, 4):
        raise ValueError(f"Expected shape (33, 4), got {keypoints.shape}")

    kp = keypoints.copy().astype(np.float32)

    # --- compute anchor points ---
    left_hip   = kp[_LEFT_HIP,  :3]
    right_hip  = kp[_RIGHT_HIP, :3]
    left_sho   = kp[_LEFT_SHOULDER,  :3]
    right_sho  = kp[_RIGHT_SHOULDER, :3]

    hip_mid  = (left_hip  + right_hip) / 2.0
    neck_mid = (left_sho  + right_sho) / 2.0

    torso_length = float(np.linalg.norm(neck_mid - hip_mid))

    if torso_length < 1e-6:
        # Body not sufficiently visible to normalise — return as-is
        return kp

    # --- translate to hip centre ---
    kp[:, :3] -= hip_mid

    # --- scale by torso length ---
    kp[:, :3] /= torso_length

    # --- zero out low-visibility keypoints ---
    low_vis = kp[:, 3] < visibility_threshold
    kp[low_vis, :3] = 0.0

    return kp


def average_keypoints(frames_keypoints: list[np.ndarray]) -> np.ndarray:
    """
    Average normalised keypoints across multiple frames.
    Weights each frame by the mean visibility of its keypoints,
    so high-confidence frames contribute more.

    Args:
        frames_keypoints: list of (33, 4) arrays, already normalised

    Returns:
        Single (33, 4) averaged array.
    """
    if not frames_keypoints:
        raise ValueError("frames_keypoints must not be empty")

    if len(frames_keypoints) == 1:
        return frames_keypoints[0].copy()

    # Weight each frame by mean visibility
    weights = np.array([kp[:, 3].mean() for kp in frames_keypoints], dtype=np.float32)
    total   = weights.sum()
    if total < 1e-6:
        weights = np.ones(len(frames_keypoints), dtype=np.float32)
        total   = float(len(frames_keypoints))

    averaged = np.zeros((33, 4), dtype=np.float32)
    for w, kp in zip(weights, frames_keypoints):
        averaged += (w / total) * kp

    return averaged


def keypoints_to_list(kp: np.ndarray) -> list[list[float]]:
    """Convert (33, 4) array to JSON-serialisable list of [x, y, z, visibility]."""
    return kp.tolist()


def keypoints_from_list(data: list[list[float]]) -> np.ndarray:
    """Restore (33, 4) array from JSON list."""
    arr = np.array(data, dtype=np.float32)
    if arr.shape != (33, 4):
        raise ValueError(f"Expected 33×4 list, got shape {arr.shape}")
    return arr
