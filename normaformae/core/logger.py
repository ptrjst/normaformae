"""
core/logger.py

Central logging configuration for Normaformae.

Usage
-----
At application startup (app.py):
    from normaformae.core.logger import setup_logging
    setup_logging(debug=True)   # CLI --debug flag
    setup_logging(debug=False)  # normal mode

In any module:
    from normaformae.core.logger import get_logger
    log = get_logger(__name__)
    log.info("Video geladen: %s", path)
    log.debug("Frame %d: %d/33 Punkte sichtbar", idx, count)
    log.warning("Torsolänge zu klein: %.4f", length)
    log.error("MediaPipe Fehler: %s", str(e))

Activation
----------
CLI:  normaformae <video> --debug
GUI:  set environment variable NORMAFORMAE_DEBUG=1 before launching

Log output
----------
- File: logs/normaformae.log (rotating, 1 MB max, 3 backups)
  Level: DEBUG always — full trace regardless of mode
- Console: WARNING+ in normal mode, DEBUG+ when --debug is active

Log format
----------
2026-05-14 14:32:01.423  DEBUG  normaformae.core.keypoint_extractor  Frame 42: 28/33 sichtbar
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path


_LOGGER_NAME  = "normaformae"
_LOG_FORMAT   = "%(asctime)s.%(msecs)03d  %(levelname)-8s  %(name)s  %(message)s"
_DATE_FORMAT  = "%Y-%m-%d %H:%M:%S"
_LOG_FILENAME = "normaformae.log"
_MAX_BYTES    = 1_000_000   # 1 MB per file
_BACKUP_COUNT = 3

_configured = False


def setup_logging(debug: bool = False) -> None:
    """
    Configure the Normaformae logging system.
    Call once at application startup.

    Args:
        debug: if True, stream DEBUG-level output to console in addition to file.
               If False, console shows WARNING+ only.
    """
    global _configured

    root_logger = logging.getLogger(_LOGGER_NAME)
    root_logger.setLevel(logging.DEBUG)  # capture everything; handlers filter

    if _configured:
        # Re-configure console level if called again (e.g. --debug toggled)
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.handlers.RotatingFileHandler
            ):
                handler.setLevel(logging.DEBUG if debug else logging.WARNING)
        return

    # --- File handler: always DEBUG, rotating ---
    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / _LOG_FILENAME

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # --- Console handler: WARNING+ normally, DEBUG+ in debug mode ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    console_handler.setFormatter(logging.Formatter(
        "%(levelname)-8s  %(name)s  %(message)s"
    ))
    root_logger.addHandler(console_handler)

    _configured = True

    root_logger.info(
        "Normaformae logging gestartet — Datei: %s  debug=%s", log_path, debug
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger for the given module name.
    Strips the top-level 'normaformae.' prefix for cleaner output.

    Usage:
        log = get_logger(__name__)
    """
    # Ensure base logger exists even if setup_logging not called yet
    # (e.g. during testing or import-time use)
    if not _configured:
        _bootstrap()
    return logging.getLogger(name)


def _bootstrap() -> None:
    """
    Minimal setup when get_logger() is called before setup_logging().
    Adds a NullHandler so no 'No handlers' warnings appear.
    Only runs once.
    """
    global _configured
    root = logging.getLogger(_LOGGER_NAME)
    if not root.handlers:
        root.addHandler(logging.NullHandler())
        root.setLevel(logging.DEBUG)
    _configured = True


def _resolve_log_dir() -> Path:
    """
    Resolve logs/ directory at project root.
    Same two-strategy approach as discipline_loader and output_writer.
    """
    # Strategy 1: relative to this file's location in the package
    here         = Path(__file__).resolve().parent   # normaformae/core/
    project_root = here.parent.parent               # project root
    candidate    = project_root / "logs"
    if (project_root / "pyproject.toml").exists():
        return candidate

    # Strategy 2: relative to current working directory
    return Path.cwd() / "logs"
