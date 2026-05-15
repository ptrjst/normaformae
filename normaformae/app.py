"""
app.py

Application entry point for Normaformae.

Usage
-----
GUI mode (default — no arguments):
    normaformae
    python -m motion_analysis.app
    python -m motion_analysis.app --gui

CLI mode — no display required:
    normaformae <video_path>
    normaformae <video_path> --discipline liechtenauer_longsword
    normaformae <video_path> --doc-only
    normaformae <video_path> --video-only
    normaformae <video_path> --discipline <id> --doc-only

CLI output: both files written to output/ by default.
            Paths printed to stdout on completion.

PyQt6 is NEVER imported in CLI mode — safe for headless / pipeline use.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="normaformae",
        description="Normaformae — Bewegungsanalyse und Normaformae-Generierung",
    )

    parser.add_argument(
        "video",
        nargs="?",
        default=None,
        help="Pfad zur Videodatei (aktiviert CLI-Modus)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="GUI explizit starten (Standard wenn kein Video angegeben)",
    )
    parser.add_argument(
        "--discipline",
        default=None,
        metavar="DISCIPLINE_ID",
        help=(
            "Disziplin-ID für die Analyse, z.B. 'liechtenauer_longsword'. "
            "Standard: erste verfügbare Disziplin."
        ),
    )
    parser.add_argument(
        "--doc-only",
        action="store_true",
        help="Nur Dokument-Output erzeugen (kein augmentiertes Video)",
    )
    parser.add_argument(
        "--video-only",
        action="store_true",
        help="Nur augmentiertes Video erzeugen (kein Dokument)",
    )

    return parser


# ---------------------------------------------------------------------------
# CLI runner — zero PyQt6
# ---------------------------------------------------------------------------

def run_cli(video_path: str, discipline_id: str | None,
            doc_only: bool, video_only: bool) -> int:
    """
    Run analysis pipeline in CLI mode.
    Returns exit code: 0 = success, 1 = error.
    """
    from normaformae.core.discipline_loader import (
        list_domains, list_disciplines, load_discipline,
        DisciplineLoadError,
    )
    from normaformae.core.mock_engine import build_mock_recognition_result
    from normaformae.cli.output_writer import write_cli_outputs

    # --- resolve video path ---
    video = Path(video_path)
    if not video.exists():
        print(f"[Fehler] Videodatei nicht gefunden: {video}", file=sys.stderr)
        return 1

    # --- resolve discipline ---
    try:
        discipline_path = _resolve_discipline(discipline_id)
    except Exception as e:
        print(f"[Fehler] Disziplin nicht gefunden: {e}", file=sys.stderr)
        return 1

    disc = load_discipline(discipline_path)
    print(f"[Normaformae] Disziplin: {disc['display_name']}")
    print(f"[Normaformae] Video:     {video.name}")

    # --- run analysis (mock in Slice 1, real engine in Slice 3) ---
    print("[Normaformae] Analyse läuft…")
    result = build_mock_recognition_result(
        discipline_path=discipline_path,
        video_path=str(video),
    )

    # --- write outputs ---
    output_paths = write_cli_outputs(
        result=result,
        discipline_path=discipline_path,
        video_path=str(video),
        write_document=not video_only,
        write_video=not doc_only,
    )

    print("[Normaformae] Analyse abgeschlossen.")
    for label, path in output_paths.items():
        print(f"  {label}: {path}")

    return 0


def _resolve_discipline(discipline_id: str | None) -> str:
    """
    Return the filesystem path to the requested discipline folder.
    If discipline_id is None, returns the first available discipline.
    """
    from normaformae.core.discipline_loader import list_domains, list_disciplines

    domains = list_domains()
    if not domains:
        raise RuntimeError("Keine Domains gefunden.")

    for domain in domains:
        disciplines = list_disciplines(domain["domain_id"])
        for disc in disciplines:
            if discipline_id is None or disc["discipline_id"] == discipline_id:
                return disc["path"]

    raise RuntimeError(
        f"Disziplin '{discipline_id}' nicht gefunden. "
        f"Verfügbar: {_list_all_discipline_ids()}"
    )


def _list_all_discipline_ids() -> list[str]:
    from normaformae.core.discipline_loader import list_domains, list_disciplines
    ids = []
    for domain in list_domains():
        for disc in list_disciplines(domain["domain_id"]):
            ids.append(disc["discipline_id"])
    return ids


# ---------------------------------------------------------------------------
# GUI runner
# ---------------------------------------------------------------------------

def run_gui() -> int:
    """Launch the PyQt6 GUI. Returns exit code."""
    from PyQt6.QtWidgets import QApplication
    from normaformae.glossary import UI
    from normaformae.startup import StartupDialog
    from normaformae.author.window import AuthorWindow
    from normaformae.user.window import UserWindow

    app = QApplication(sys.argv)
    app.setApplicationName(UI["app_title"])

    dialog = StartupDialog()
    if dialog.exec():
        role             = dialog.selected_role
        discipline_path  = dialog.selected_discipline_path

        if role == "author":
            window = AuthorWindow(discipline_path=discipline_path)
        else:
            window = UserWindow(discipline_path=discipline_path)

        window.show()
        return app.exec()

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.video and not args.gui:
        # CLI mode
        code = run_cli(
            video_path=args.video,
            discipline_id=args.discipline,
            doc_only=args.doc_only,
            video_only=args.video_only,
        )
        sys.exit(code)
    else:
        # GUI mode (default)
        sys.exit(run_gui())


if __name__ == "__main__":
    main()
