"""
core/engine.py

Real analysis engine for Normaformae.

Takes a video path and a discipline path. Samples frames at a configurable
rate, runs MediaPipe PoseLandmarker on each sampled frame, compares
normalised keypoints against all valid catalog Stances using cosine
similarity, infers MovementSequences from adjacent Stance detections,
and returns a RecognitionResult.

No PyQt6 dependency — safe for CLI and QThread use.

RecognitionResult schema (identical to mock_engine output):
{
    "discipline_id":   str,
    "video_path":      str,
    "detected_stances": [
        {
            "stance_id":       str,
            "label":           str,
            "timestamp_start": float,
            "timestamp_end":   float,
            "confidence":      float,   # cosine similarity score
            "deviation_notes": list[str],
        }, ...
    ],
    "detected_sequences": [
        {
            "sequence_id": str | None,
            "label":       str,
        }, ...
    ],
    "matched_flows": [str, ...],
    "unrecognised_segments": [
        {"start": float, "end": float}, ...
    ],
    "engine":  "real" | "mock",
    "config":  dict,    # EngineConfig as dict for logging/display
}
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from normaformae.core.logger import get_logger

log = get_logger(__name__)


def analyse(
    video_path: str,
    discipline_path: str,
    progress_callback=None,
) -> dict[str, Any]:
    """
    Run the full analysis pipeline on a video file.

    Args:
        video_path:         path to the input video file
        discipline_path:    path to the discipline folder
        progress_callback:  optional callable(current_frame, total_frames)
                            called after each sampled frame is processed.
                            Use for progress bar updates in QThread.

    Returns:
        RecognitionResult dict.
    """
    from normaformae.core.discipline_loader import (
        load_discipline, load_all_stances, load_all_sequences,
        load_all_flows, get_vocabulary,
    )
    from normaformae.core.engine_config import EngineConfig
    from normaformae.core.video_loader import VideoLoader
    from normaformae.core.keypoint_extractor import KeypointExtractor
    from normaformae.core.similarity import best_stance_match, compute_deviation_notes

    # --- load discipline ---
    disc       = load_discipline(discipline_path)
    config     = EngineConfig.from_discipline(disc)
    stances    = load_all_stances(discipline_path)
    sequences  = load_all_sequences(discipline_path)
    flows      = load_all_flows(discipline_path)
    vocab      = get_vocabulary(disc)
    criteria   = disc.get("scoring_criteria", [])
    disc_id    = disc["discipline_id"]

    # Filter to stances with real keypoints (not drafts)
    valid_stances = {
        sid: s for sid, s in stances.items()
        if s.get("keypoints") is not None
    }

    log.info(
        "Analyse gestartet: Video=%s  Disziplin=%s  "
        "Huten=%d/%d gültig  Abtastrate=jedes %d. Bild  Schwellenwert=%.2f",
        Path(video_path).name,
        disc_id,
        len(valid_stances), len(stances),
        config.frame_sample_rate,
        config.stance_match_threshold,
    )

    if not valid_stances:
        log.warning("Keine gültigen Huten im Katalog — leeres Ergebnis.")
        return _empty_result(disc_id, video_path, config)

    # --- frame-level detection pass ---
    frame_detections = []  # list of (frame_idx, timestamp, stance_id, score, deviations)

    with VideoLoader(video_path) as vl:
        info       = vl.info
        total      = info.frame_count
        sample_indices = list(range(0, total, config.frame_sample_rate))

        log.info(
            "Video: %d Bilder gesamt  →  %d Bilder werden analysiert",
            total, len(sample_indices),
        )

        with KeypointExtractor(
            visibility_threshold=config.visibility_threshold,
            model_variant=config.model_variant,
        ) as extractor:

            for i, frame_idx in enumerate(sample_indices):
                frame = vl.read_frame(frame_idx)
                result = extractor.extract(frame)

                if progress_callback:
                    progress_callback(i + 1, len(sample_indices))

                if not result.success or result.keypoints_norm is None:
                    log.debug("Bild %d: keine Pose erkannt", frame_idx)
                    continue

                stance_id, score = best_stance_match(
                    result.keypoints_norm,
                    valid_stances,
                    threshold=config.stance_match_threshold,
                )

                ts = info.timestamp(frame_idx)

                if stance_id:
                    ref_kp = _get_ref_kp(valid_stances[stance_id])
                    deviations = compute_deviation_notes(
                        result.keypoints_norm, ref_kp, criteria
                    )
                    frame_detections.append((frame_idx, ts, stance_id, score, deviations))
                    log.debug(
                        "Bild %d (%.3fs): '%s'  Score=%.4f",
                        frame_idx, ts, stance_id, score,
                    )

    log.info(
        "Erkennungspass abgeschlossen: %d/%d Bilder mit Treffer",
        len(frame_detections), len(sample_indices),
    )

    # --- consolidate frame detections into stance events ---
    detected_stances = _consolidate_detections(
        frame_detections,
        valid_stances,
        config,
    )

    # --- infer sequences from adjacent stance events ---
    detected_sequences = _infer_sequences(detected_stances, sequences)

    # --- match flows ---
    matched_flows = _match_flows(detected_sequences, flows)

    # --- compute unrecognised segments ---
    unrecognised = _compute_unrecognised(
        detected_stances,
        info.duration,
    )

    log.info(
        "Ergebnis: %d Huten  %d Sequenzen  %d Flüsse  %d unerkannte Abschnitte",
        len(detected_stances),
        len(detected_sequences),
        len(matched_flows),
        len(unrecognised),
    )

    return {
        "discipline_id":         disc_id,
        "video_path":            video_path,
        "detected_stances":      detected_stances,
        "detected_sequences":    detected_sequences,
        "matched_flows":         matched_flows,
        "unrecognised_segments": unrecognised,
        "engine":                "real",
        "config":                asdict(config),
    }


# ---------------------------------------------------------------------------
# Consolidation helpers
# ---------------------------------------------------------------------------

def _get_ref_kp(stance: dict):
    """Load reference keypoints from a stance dict."""
    from normaformae.core.normalizer import keypoints_from_list
    return keypoints_from_list(stance["keypoints"])


def _consolidate_detections(
    frame_detections: list,
    valid_stances: dict,
    config,
) -> list[dict]:
    """
    Merge consecutive frame-level detections of the same Stance into
    single events with start/end timestamps and averaged confidence.

    Applies min_consecutive_matches and max_merge_gap_seconds filters.
    """
    if not frame_detections:
        return []

    events = []
    current_stance_id  = None
    current_start_ts   = 0.0
    current_end_ts     = 0.0
    current_scores     = []
    current_deviations = []
    consecutive_count  = 0

    def _flush():
        if (current_stance_id
                and consecutive_count >= config.min_consecutive_matches):
            stance = valid_stances[current_stance_id]
            avg_score = sum(current_scores) / len(current_scores)
            # Pick most common deviation notes
            flat_devs = [d for ds in current_deviations for d in ds]
            unique_devs = list(dict.fromkeys(flat_devs))  # preserve order, deduplicate
            events.append({
                "stance_id":       current_stance_id,
                "label":           stance.get("label", current_stance_id),
                "timestamp_start": round(current_start_ts, 3),
                "timestamp_end":   round(current_end_ts,   3),
                "confidence":      round(avg_score, 4),
                "deviation_notes": unique_devs,
            })
            log.debug(
                "Hut-Ereignis: '%s'  %.3fs–%.3fs  Score=%.4f  Abweichungen=%s",
                current_stance_id, current_start_ts, current_end_ts,
                avg_score, unique_devs or "keine",
            )

    for frame_idx, ts, stance_id, score, deviations in frame_detections:
        gap = ts - current_end_ts if current_end_ts > 0 else 0.0

        if (stance_id == current_stance_id
                and gap <= config.max_merge_gap_seconds):
            # Continue current event
            current_end_ts = ts
            current_scores.append(score)
            current_deviations.append(deviations)
            consecutive_count += 1
        else:
            # New event — flush previous
            _flush()
            current_stance_id  = stance_id
            current_start_ts   = ts
            current_end_ts     = ts
            current_scores     = [score]
            current_deviations = [deviations]
            consecutive_count  = 1

    _flush()  # flush last event
    return events


def _infer_sequences(
    detected_stances: list[dict],
    catalog_sequences: dict,
) -> list[dict]:
    """
    Infer MovementSequences from pairs of adjacent detected Stances.
    Matches against the catalog; returns all pairs regardless of catalog match.
    """
    if len(detected_stances) < 2:
        return []

    inferred = []
    for i in range(len(detected_stances) - 1):
        a = detected_stances[i]
        b = detected_stances[i + 1]

        # Look for a matching sequence in the catalog
        matched_seq_id    = None
        matched_seq_label = f"{a['label']} → {b['label']}"

        for seq_id, seq in catalog_sequences.items():
            if (seq.get("from_stance_id") == a["stance_id"]
                    and seq.get("to_stance_id")   == b["stance_id"]):
                matched_seq_id    = seq_id
                matched_seq_label = seq.get("label", matched_seq_label)
                break

        inferred.append({
            "sequence_id": matched_seq_id,
            "label":       matched_seq_label,
        })
        log.debug(
            "Sequenz erkannt: %s  (Katalog-ID: %s)",
            matched_seq_label, matched_seq_id or "—",
        )

    return inferred


def _match_flows(
    detected_sequences: list[dict],
    catalog_flows: dict,
) -> list[str]:
    """
    Check whether any published MovementFlow's sequence list is fully
    contained in the detected sequences (order-preserving subsequence match).
    Returns list of matched flow labels.
    """
    if not detected_sequences:
        return []

    detected_ids = [s["sequence_id"] for s in detected_sequences if s["sequence_id"]]
    matched = []

    for flow_id, flow in catalog_flows.items():
        if flow.get("status") != "published":
            continue
        flow_seq_ids = flow.get("sequence_ids", [])
        if not flow_seq_ids:
            continue
        if _is_subsequence(flow_seq_ids, detected_ids):
            matched.append(flow.get("label", flow_id))
            log.info("Fluss erkannt: '%s'", flow.get("label", flow_id))

    return matched


def _is_subsequence(needle: list, haystack: list) -> bool:
    """Return True if needle appears as an order-preserving subsequence of haystack."""
    it = iter(haystack)
    return all(item in it for item in needle)


def _compute_unrecognised(
    detected_stances: list[dict],
    total_duration: float,
) -> list[dict]:
    """
    Compute time segments where no Stance was detected.
    Gaps larger than 1 second between detections are flagged.
    """
    if not detected_stances:
        if total_duration > 0:
            return [{"start": 0.0, "end": round(total_duration, 3)}]
        return []

    gaps = []
    MIN_GAP = 1.0  # seconds — smaller gaps are noise between detections

    # Gap before first detection
    first_start = detected_stances[0]["timestamp_start"]
    if first_start > MIN_GAP:
        gaps.append({"start": 0.0, "end": round(first_start, 3)})

    # Gaps between detections
    for i in range(len(detected_stances) - 1):
        end_prev   = detected_stances[i]["timestamp_end"]
        start_next = detected_stances[i + 1]["timestamp_start"]
        gap        = start_next - end_prev
        if gap > MIN_GAP:
            gaps.append({
                "start": round(end_prev, 3),
                "end":   round(start_next, 3),
            })

    # Gap after last detection
    last_end = detected_stances[-1]["timestamp_end"]
    if total_duration - last_end > MIN_GAP:
        gaps.append({"start": round(last_end, 3), "end": round(total_duration, 3)})

    return gaps


def _empty_result(disc_id: str, video_path: str, config) -> dict:
    return {
        "discipline_id":         disc_id,
        "video_path":            video_path,
        "detected_stances":      [],
        "detected_sequences":    [],
        "matched_flows":         [],
        "unrecognised_segments": [],
        "engine":                "real",
        "config":                asdict(config),
    }
