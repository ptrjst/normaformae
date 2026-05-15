"""
models/download_models.py

Downloads MediaPipe model files required by Normaformae.
Run once before first use, or call ensure_model() at startup.

Models are stored in the same folder as this script:
    normaformae/models/pose_landmarker_full.task   (default, 6.5 MB)
    normaformae/models/pose_landmarker_lite.task   (4.7 MB, faster)
    normaformae/models/pose_landmarker_heavy.task  (26.4 MB, most accurate)

The .task files are gitignored — they are binary downloads, not source.

Usage:
    python -m normaformae.models.download_models
    python -m normaformae.models.download_models --variant heavy
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path


MODELS = {
    "lite": (
        "pose_landmarker_lite.task",
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        4_700_000,
    ),
    "full": (
        "pose_landmarker_full.task",
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
        6_500_000,
    ),
    "heavy": (
        "pose_landmarker_heavy.task",
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
        26_400_000,
    ),
}

DEFAULT_VARIANT = "full"


def models_dir() -> Path:
    """Return the models/ directory (same folder as this file)."""
    return Path(__file__).resolve().parent


def model_path(variant: str = DEFAULT_VARIANT) -> Path:
    """Return the expected path for a model variant."""
    filename, _, _ = MODELS[variant]
    return models_dir() / filename


def ensure_model(variant: str = DEFAULT_VARIANT) -> Path:
    """
    Return the path to the model file, downloading it if not present.
    Raises RuntimeError if download fails.
    """
    path = model_path(variant)
    if path.exists() and path.stat().st_size > 1_000:
        return path
    download_model(variant)
    return path


def download_model(variant: str = DEFAULT_VARIANT) -> Path:
    """Download a model variant. Shows progress. Returns path."""
    if variant not in MODELS:
        raise ValueError(f"Unknown variant '{variant}'. Choose from: {list(MODELS)}")

    filename, url, approx_size = MODELS[variant]
    out_path = models_dir() / filename

    print(f"[Normaformae] Lade Modell herunter: {filename}")
    print(f"  Von:  {url}")
    print(f"  Nach: {out_path}")
    print(f"  Größe: ca. {approx_size / 1_000_000:.1f} MB")

    try:
        def _progress(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(block_num * block_size / total_size * 100, 100)
                bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
                print(f"\r  [{bar}] {pct:.0f}%", end="", flush=True)

        urllib.request.urlretrieve(url, out_path, reporthook=_progress)
        print()  # newline after progress bar
        print(f"  [OK] Gespeichert: {out_path.stat().st_size / 1_000_000:.1f} MB")
        return out_path

    except Exception as e:
        if out_path.exists():
            out_path.unlink()  # remove partial download
        raise RuntimeError(
            f"Modell-Download fehlgeschlagen: {e}\n"
            f"Bitte manuell herunterladen:\n  {url}\n"
            f"und speichern als:\n  {out_path}"
        ) from e


def list_models() -> None:
    """Print status of all model files."""
    print("Normaformae — Modell-Status:")
    for variant, (filename, url, approx_size) in MODELS.items():
        path = models_dir() / filename
        if path.exists() and path.stat().st_size > 1_000:
            size_mb = path.stat().st_size / 1_000_000
            marker = "[OK]"
            detail = f"{size_mb:.1f} MB"
        else:
            marker = "[  ]"
            detail = f"fehlt  (ca. {approx_size / 1_000_000:.1f} MB)"
        default = " [Standard]" if variant == DEFAULT_VARIANT else ""
        print(f"  {marker} {variant:6} — {filename:40} {detail}{default}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Lade MediaPipe-Modelle für Normaformae herunter."
    )
    parser.add_argument(
        "--variant",
        choices=list(MODELS),
        default=DEFAULT_VARIANT,
        help=f"Modell-Variante (Standard: {DEFAULT_VARIANT})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Zeige Status aller Modelle",
    )
    args = parser.parse_args()

    if args.list:
        list_models()
    else:
        try:
            download_model(args.variant)
        except RuntimeError as e:
            print(f"\n[Fehler] {e}", file=sys.stderr)
            sys.exit(1)
