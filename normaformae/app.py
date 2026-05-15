"""
app.py

Entry point for Normaformae.

GUI mode (default):
    normaformae
    normaformae --gui

CLI mode:
    normaformae <video_path>
    normaformae <video_path> --discipline liechtenauer_longsword
    normaformae <video_path> --doc-only
    normaformae <video_path> --video-only

PyQt6 is never imported in CLI mode — safe for headless/pipeline use.
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
        "video", nargs="?", default=None,
        help="Pfad zur Videodatei (aktiviert CLI-Modus)",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="GUI explizit starten (Standard wenn kein Video angegeben)",
    )
    parser.add_argument(
        "--discipline", default=None, metavar="DISCIPLINE_ID",
        help="Disziplin-ID, z.B. 'liechtenauer_longsword'",
    )
    parser.add_argument(
        "--doc-only", action="store_true",
        help="Nur Dokument-Output erzeugen",
    )
    parser.add_argument(
        "--video-only", action="store_true",
        help="Nur augmentiertes Video erzeugen",
    )
    return parser


# ---------------------------------------------------------------------------
# CLI runner — zero PyQt6
# ---------------------------------------------------------------------------

def run_cli(video_path: str, discipline_id: str | None,
            doc_only: bool, video_only: bool) -> int:
    from normaformae.core.discipline_loader import load_discipline, DisciplineLoadError
    from normaformae.core.mock_engine import build_mock_recognition_result
    from normaformae.cli.output_writer import write_cli_outputs

    video = Path(video_path)
    if not video.exists():
        print(f"[Fehler] Videodatei nicht gefunden: {video}", file=sys.stderr)
        return 1

    try:
        discipline_path = _resolve_discipline(discipline_id)
    except Exception as e:
        print(f"[Fehler] Disziplin nicht gefunden: {e}", file=sys.stderr)
        return 1

    disc = load_discipline(discipline_path)
    print(f"[Normaformae] Disziplin: {disc['display_name']}")
    print(f"[Normaformae] Video:     {video.name}")
    print("[Normaformae] Analyse läuft…")

    result = build_mock_recognition_result(
        discipline_path=discipline_path,
        video_path=str(video),
    )

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
    from normaformae.core.discipline_loader import list_domains, list_disciplines
    for domain in list_domains():
        for disc in list_disciplines(domain["domain_id"]):
            if discipline_id is None or disc["discipline_id"] == discipline_id:
                return disc["path"]
    raise RuntimeError(
        f"Disziplin '{discipline_id}' nicht gefunden. "
        f"Verfügbar: {_list_all_discipline_ids()}"
    )


def _list_all_discipline_ids() -> list[str]:
    from normaformae.core.discipline_loader import list_domains, list_disciplines
    return [
        disc["discipline_id"]
        for domain in list_domains()
        for disc in list_disciplines(domain["domain_id"])
    ]


# ---------------------------------------------------------------------------
# GUI runner
# ---------------------------------------------------------------------------

def run_gui() -> int:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from normaformae.glossary import UI
    from normaformae.startup import StartupDialog
    from normaformae.author.window import AuthorWindow
    from normaformae.user.window import UserWindow
    from normaformae.core.app_state import update_state

    app = QApplication(sys.argv)
    app.setApplicationName(UI["app_title"])

    dialog = StartupDialog()
    if not dialog.exec():
        return 0

    role            = dialog.selected_role
    discipline_path = dialog.selected_discipline_path

    if role == "author":
        window = AuthorWindow(discipline_path=discipline_path)
    else:
        window = UserWindow(discipline_path=discipline_path)

    # Launch maximized
    window.showMaximized()

    exit_code = app.exec()

    # Persist window state on close
    update_state(window_maximized=window.isMaximized())

    return exit_code


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    if args.video and not args.gui:
        sys.exit(run_cli(
            video_path=args.video,
            discipline_id=args.discipline,
            doc_only=args.doc_only,
            video_only=args.video_only,
        ))
    else:
        sys.exit(run_gui())


if __name__ == "__main__":
    main()
