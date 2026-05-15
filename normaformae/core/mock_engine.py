"""
core/mock_engine.py

Mock analysis engine for Slice 1.

Reads real catalog data (stances, sequences) from the discipline and returns
a plausible-looking RecognitionResult dict — without running MediaPipe.

The returned structure is identical to what the real engine (Slice 3) will
produce, so all downstream display code written in Slice 1 remains valid.

Replaced by core/engine.py in Slice 3.
"""

from __future__ import annotations

import random
from pathlib import Path

from normaformae.core.discipline_loader import (
    load_all_stances, load_all_sequences, load_all_flows,
)
from normaformae.glossary import HEMA_LIECHTENAUER


def build_mock_recognition_result(
    discipline_path: str,
    video_path: str,
) -> dict:
    """
    Build a mock RecognitionResult using real stance/sequence labels from
    the discipline catalog.

    Returns a dict matching the RecognitionResult schema:
    {
        "discipline_id": str,
        "video_path":    str,
        "detected_stances": [
            {
                "stance_id":       str,
                "label":           str,
                "timestamp_start": float,
                "timestamp_end":   float,
                "confidence":      float,   # 0.0 – 1.0
                "deviation_notes": str,     # "" = no deviation
            },
            ...
        ],
        "detected_sequences": [
            {
                "sequence_id": str,
                "label":       str,
            },
            ...
        ],
        "matched_flows": [str, ...],        # flow labels
        "unrecognised_segments": [
            {"start": float, "end": float},
            ...
        ],
    }
    """

    stances   = load_all_stances(discipline_path)
    sequences = load_all_sequences(discipline_path)
    flows     = load_all_flows(discipline_path)

    stance_list  = list(stances.values())
    seq_list     = list(sequences.values())
    flow_list    = list(flows.values())

    # Scoring criteria labels for deviation messages
    criteria = [c["label"] for c in HEMA_LIECHTENAUER["scoring_criteria"]]

    # --- build fake detected stances (2–4 of the available ones) ---
    random.seed(42)                         # deterministic for now
    sample_size = min(len(stance_list), random.randint(2, 4))
    sampled = random.sample(stance_list, sample_size)

    detected_stances = []
    t = 1.2  # start timestamp in seconds
    for stance in sampled:
        duration   = round(random.uniform(0.6, 2.0), 2)
        confidence = round(random.uniform(0.65, 0.98), 2)

        # Randomly add a deviation note for lower-confidence detections
        if confidence < 0.80:
            criterion = random.choice(criteria)
            deviation = f"{criterion} unzureichend"
        else:
            deviation = ""

        detected_stances.append({
            "stance_id":       stance.get("stance_id", ""),
            "label":           stance.get("label", ""),
            "timestamp_start": round(t, 2),
            "timestamp_end":   round(t + duration, 2),
            "confidence":      confidence,
            "deviation_notes": deviation,
        })
        t += duration + round(random.uniform(0.3, 1.0), 2)

    # --- build fake detected sequences (0–all available) ---
    detected_sequences = []
    if seq_list:
        for seq in seq_list:
            detected_sequences.append({
                "sequence_id": seq.get("sequence_id", ""),
                "label":       seq.get("label", ""),
            })

    # --- matched flows (only published ones) ---
    matched_flows = [
        f["label"] for f in flow_list if f.get("status") == "published"
    ]

    # --- unrecognised segment ---
    unrecognised = []
    if t < 8.0:
        unrecognised.append({"start": round(t + 0.5, 2), "end": round(t + 1.8, 2)})

    return {
        "discipline_id":        Path(discipline_path).name,
        "video_path":           video_path,
        "detected_stances":     detected_stances,
        "detected_sequences":   detected_sequences,
        "matched_flows":        matched_flows,
        "unrecognised_segments": unrecognised,
    }
