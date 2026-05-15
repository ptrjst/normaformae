"""
core/engine_config.py

Engine configuration dataclass.
Parameters are read from discipline.json and passed to the analysis engine.
Defaults are tuned for a single-person HEMA video at 30–60fps.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EngineConfig:
    """
    Analysis engine parameters.

    All fields have sensible defaults — discipline.json only needs to
    override what differs from the default.
    """

    # Sample every Nth frame. At 57fps, 5 = ~11fps effective analysis rate.
    # Increase for faster (less accurate) analysis, decrease for slower (more accurate).
    frame_sample_rate: int = 5

    # Minimum cosine similarity to accept a Stance detection as a positive match.
    stance_match_threshold: float = 0.85

    # Minimum number of consecutive sampled frames that must match the same Stance
    # before it is recorded as a confirmed detection (reduces false positives from
    # transitional frames).
    min_consecutive_matches: int = 2

    # Maximum gap in seconds between two detections of the same Stance to merge
    # them into a single detection event (avoids duplicate entries from brief
    # pose variations mid-hold).
    max_merge_gap_seconds: float = 0.5

    # Keypoint visibility threshold — passed to KeypointExtractor.
    # Falls back to discipline-level keypoint_visibility_threshold if not set.
    visibility_threshold: float = 0.5

    # Model variant for PoseLandmarker: "lite" | "full" | "heavy"
    model_variant: str = "full"

    @classmethod
    def from_discipline(cls, discipline_cfg: dict) -> "EngineConfig":
        """
        Build an EngineConfig from a loaded discipline.json dict.
        Only overrides fields that are explicitly present in the config.
        """
        defaults = cls()
        return cls(
            frame_sample_rate=discipline_cfg.get(
                "analysis_frame_sample_rate", defaults.frame_sample_rate
            ),
            stance_match_threshold=discipline_cfg.get(
                "stance_match_threshold", defaults.stance_match_threshold
            ),
            min_consecutive_matches=discipline_cfg.get(
                "min_consecutive_matches", defaults.min_consecutive_matches
            ),
            max_merge_gap_seconds=discipline_cfg.get(
                "max_merge_gap_seconds", defaults.max_merge_gap_seconds
            ),
            visibility_threshold=discipline_cfg.get(
                "keypoint_visibility_threshold", defaults.visibility_threshold
            ),
            model_variant=discipline_cfg.get(
                "analysis_model_variant", defaults.model_variant
            ),
        )
