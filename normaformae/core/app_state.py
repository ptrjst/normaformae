"""
core/app_state.py

Lightweight application state persistence.
Saves last-used discipline, role, and window state to state.json
at the project root. Restored on next launch.

No database — plain JSON file, written on app close.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_STATE_FILENAME = "state.json"


def _state_path() -> Path:
    """Locate state.json at the project root (next to pyproject.toml)."""
    here = Path(__file__).resolve().parent.parent.parent
    return here / _STATE_FILENAME


def load_state() -> dict[str, Any]:
    """
    Load persisted application state.
    Returns empty dict if no state file exists yet.
    """
    path = _state_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    """
    Persist application state to state.json.
    Silent on failure — state loss is acceptable, crash is not.
    """
    path = _state_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def update_state(**kwargs: Any) -> None:
    """Merge kwargs into existing state and save."""
    state = load_state()
    state.update(kwargs)
    save_state(state)
