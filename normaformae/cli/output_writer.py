"""
cli/output_writer.py

Writes MovementFlowOutput files in CLI mode.

Slice 1: writes stub plain-text files showing the RecognitionResult.
Slice 4: document renderer replaced with real HTML/PDF output.
Slice 5: video renderer replaced with real cv2 annotated video.

No PyQt6 imports. Safe for headless / pipeline use.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def write_cli_outputs(
    result: dict[str, Any],
    discipline_path: str,
    video_path: str,
    write_document: bool = True,
    write_video: bool = True,
) -> dict[str, str]:
    """
    Write output files from a RecognitionResult to the output/ folder.

    Returns a dict mapping output type to absolute file path:
        {"Dokument": "/path/to/output/..._doc.txt",
         "Video":    "/path/to/output/..._video.txt"}
    """
    output_dir = _resolve_output_dir(discipline_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    disc_id     = result.get("discipline_id", "unknown")
    video_name  = Path(video_path).stem

    written: dict[str, str] = {}

    if write_document:
        doc_path = output_dir / f"{disc_id}_{video_name}_{timestamp}_doc.txt"
        _write_document_stub(doc_path, result, video_path)
        written["Dokument"] = str(doc_path)

    if write_video:
        vid_path = output_dir / f"{disc_id}_{video_name}_{timestamp}_video.txt"
        _write_video_stub(vid_path, result, video_path)
        written["Video"] = str(vid_path)

    return written


# ---------------------------------------------------------------------------
# Stub writers — replaced in Slice 4 and Slice 5
# ---------------------------------------------------------------------------

def _write_document_stub(path: Path, result: dict, video_path: str) -> None:
    """
    Slice 1 stub: plain-text summary of RecognitionResult.
    Slice 4: replaced with Jinja2 HTML → PDF renderer.
    """
    lines = [
        "NORMAFORMAE — Dokument-Output (Entwurf, Slice 1)",
        "=" * 60,
        f"Disziplin:   {result.get('discipline_id', '—')}",
        f"Video:       {Path(video_path).name}",
        f"Erstellt:    {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        "",
        "ERKANNTE HUTEN",
        "-" * 40,
    ]
    for ds in result.get("detected_stances", []):
        dev = f"  ⚠ {ds['deviation_notes']}" if ds.get("deviation_notes") else "  ✓"
        lines.append(
            f"  {ds['label']:20}  "
            f"@{ds['timestamp_start']:.2f}s – {ds['timestamp_end']:.2f}s  "
            f"Sicherheit: {ds['confidence']:.0%}{dev}"
        )

    lines += ["", "ERKANNTE SEQUENZEN", "-" * 40]
    seqs = result.get("detected_sequences", [])
    if seqs:
        for s in seqs:
            lines.append(f"  ▶ {s['label']}")
    else:
        lines.append("  — keine Sequenzen erkannt —")

    lines += ["", "ÜBEREINSTIMMENDE FLÜSSE", "-" * 40]
    matched = result.get("matched_flows", [])
    if matched:
        for mf in matched:
            lines.append(f"  ▶ {mf}")
    else:
        lines.append("  — keine Übereinstimmung —")

    unrecognised = result.get("unrecognised_segments", [])
    if unrecognised:
        lines += ["", "NICHT ERKANNTE ABSCHNITTE", "-" * 40]
        for seg in unrecognised:
            lines.append(f"  {seg['start']:.2f}s – {seg['end']:.2f}s")

    lines += [
        "",
        "=" * 60,
        "Hinweis: Dies ist eine Stub-Ausgabe (Slice 1).",
        "Vollständiges HTML/PDF-Dokument wird in Slice 4 implementiert.",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


def _write_video_stub(path: Path, result: dict, video_path: str) -> None:
    """
    Slice 1 stub: JSON manifest of what the augmented video would contain.
    Slice 5: replaced with cv2.VideoWriter annotated mp4.
    """
    manifest = {
        "_note": "Stub-Ausgabe (Slice 1). Augmentiertes Video wird in Slice 5 implementiert.",
        "source_video":   Path(video_path).name,
        "discipline_id":  result.get("discipline_id"),
        "created":        datetime.now().isoformat(),
        "annotations_planned": [
            {
                "stance":       ds["label"],
                "start":        ds["timestamp_start"],
                "end":          ds["timestamp_end"],
                "overlay_text": f"{ds['label']} ({ds['confidence']:.0%})",
            }
            for ds in result.get("detected_stances", [])
        ],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_output_dir(discipline_path: str) -> Path:
    """
    Output always goes to output/ at the project root — fixed, no subfolders.
    """
    disc_path = Path(discipline_path).resolve()
    # Walk up to find the project root (contains pyproject.toml)
    candidate = disc_path
    for _ in range(8):
        if (candidate / "pyproject.toml").exists():
            return candidate / "output"
        candidate = candidate.parent
    # Fallback: output/ next to domains/
    return disc_path.parent.parent.parent / "output"
