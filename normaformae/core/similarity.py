"""
core/similarity.py

Cosine similarity computation between normalised keypoint arrays.

Design notes:
- Works on (33, 4) arrays where col 3 is visibility.
- Only x, y, z (cols 0-2) contribute to the similarity score.
- Keypoints zeroed by the normalizer (low visibility) are masked out
  from both vectors before the dot product, so missing joints don't
  drag the score down artificially.
- Returns float in [0.0, 1.0]. 1.0 = identical pose.
"""

from __future__ import annotations

import numpy as np

from normaformae.core.logger import get_logger

log = get_logger(__name__)


def cosine_similarity(
    kp_a: np.ndarray,
    kp_b: np.ndarray,
    min_shared_keypoints: int = 10,
) -> float:
    """
    Compute cosine similarity between two normalised (33, 4) keypoint arrays.

    Args:
        kp_a:                   reference keypoints (from catalog Stance)
        kp_b:                   detected keypoints (from analysis frame)
        min_shared_keypoints:   minimum number of jointly-visible keypoints
                                required to return a meaningful score.
                                Returns 0.0 if fewer are available.

    Returns:
        float in [0.0, 1.0]
    """
    if kp_a.shape != (33, 4) or kp_b.shape != (33, 4):
        raise ValueError(
            f"Expected (33, 4) arrays, got {kp_a.shape} and {kp_b.shape}"
        )

    # Mask: both keypoints must be non-zero (i.e. above visibility threshold)
    # A zeroed keypoint has x=y=z=0 after normalisation.
    mag_a  = np.linalg.norm(kp_a[:, :3], axis=1)
    mag_b  = np.linalg.norm(kp_b[:, :3], axis=1)
    shared = (mag_a > 1e-6) & (mag_b > 1e-6)
    n_shared = int(shared.sum())

    if n_shared < min_shared_keypoints:
        log.debug(
            "Cosinus-Ähnlichkeit: zu wenige gemeinsame Punkte (%d < %d) — Score=0.0",
            n_shared, min_shared_keypoints,
        )
        return 0.0

    vec_a = kp_a[shared, :3].flatten()
    vec_b = kp_b[shared, :3].flatten()

    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0

    score = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    # Clamp to [0, 1] — floating point can produce tiny negatives
    score = max(0.0, min(1.0, score))

    log.debug(
        "Cosinus-Ähnlichkeit: %.4f  (gemeinsame Punkte: %d/33)",
        score, n_shared,
    )
    return score


def best_stance_match(
    detected_kp: np.ndarray,
    catalog_stances: dict,
    threshold: float = 0.85,
) -> tuple[str | None, float]:
    """
    Find the best matching Stance from the catalog for a detected keypoint array.

    Args:
        detected_kp:      (33, 4) normalised keypoints from the analysis frame
        catalog_stances:  dict of {stance_id: stance_dict} with 'keypoints' field
        threshold:        minimum cosine similarity to count as a match

    Returns:
        (stance_id, score) of the best match above threshold,
        or (None, 0.0) if no match found.
    """
    from normaformae.core.normalizer import keypoints_from_list

    best_id    = None
    best_score = 0.0

    for stance_id, stance in catalog_stances.items():
        raw_kp = stance.get("keypoints")
        if raw_kp is None:
            continue  # draft stance — skip

        try:
            ref_kp = keypoints_from_list(raw_kp)
        except Exception as e:
            log.warning("Ungültige Schlüsselpunkte für Hut '%s': %s", stance_id, e)
            continue

        score = cosine_similarity(detected_kp, ref_kp)

        if score > best_score:
            best_score = score
            best_id    = stance_id

    if best_id and best_score >= threshold:
        log.debug(
            "Bester Treffer: '%s'  Score=%.4f  (Schwellenwert=%.2f)",
            best_id, best_score, threshold,
        )
        return best_id, best_score

    log.debug(
        "Kein Treffer über Schwellenwert %.2f  (bester Score=%.4f für '%s')",
        threshold, best_score, best_id or "—",
    )
    return None, best_score


def compute_deviation_notes(
    detected_kp: np.ndarray,
    reference_kp: np.ndarray,
    scoring_criteria: list[dict],
    threshold: float = 0.05,
) -> list[str]:
    """
    Compare detected vs reference keypoints per body region and return
    human-readable deviation notes in German.

    Uses landmark index groups mapped loosely to scoring criteria.
    Returns a list of German deviation strings (empty list = no notable deviations).

    Args:
        detected_kp:      (33, 4) normalised detected keypoints
        reference_kp:     (33, 4) normalised reference keypoints
        scoring_criteria: list of {criterion_id, label} dicts from discipline
        threshold:        mean positional error per region to flag as deviation
    """
    # Landmark groups per scoring criterion (approximate)
    # MediaPipe landmark indices:
    # 0=nose, 11-12=shoulders, 13-16=elbows/wrists, 23-26=hips/knees, 27-32=ankles/feet
    REGION_GROUPS = {
        "struktur":     [11, 12, 23, 24],      # shoulders + hips — body alignment
        "linie":        [13, 14, 15, 16],      # elbows + wrists — arm/blade line
        "mensur":       [23, 24, 25, 26, 27, 28],  # hips + knees + ankles — stance width
        "timing":       [],                     # timing cannot be assessed per-frame
        "krafteinsatz": [],                     # force cannot be assessed from keypoints
    }

    criteria_labels = {c["criterion_id"]: c["label"] for c in scoring_criteria}
    deviations = []

    for criterion_id, indices in REGION_GROUPS.items():
        if not indices:
            continue

        label = criteria_labels.get(criterion_id, criterion_id)

        # Only use jointly-visible keypoints in this region
        errors = []
        for i in indices:
            mag_d = np.linalg.norm(detected_kp[i, :3])
            mag_r = np.linalg.norm(reference_kp[i, :3])
            if mag_d > 1e-6 and mag_r > 1e-6:
                error = float(np.linalg.norm(detected_kp[i, :3] - reference_kp[i, :3]))
                errors.append(error)

        if not errors:
            continue

        mean_error = float(np.mean(errors))
        if mean_error > threshold:
            deviations.append(f"{label} unzureichend")
            log.debug(
                "Abweichung '%s': mittlerer Fehler=%.4f (Schwellenwert=%.4f)",
                label, mean_error, threshold,
            )

    return deviations
