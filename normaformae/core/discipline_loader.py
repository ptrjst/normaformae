"""
core/discipline_loader.py

Loads a Domain and Discipline configuration from the domains/ folder tree.
Returns plain dicts — no ORM, no magic. Validates required fields are present.

Path resolution works both from source (python -m normaformae.app) and
after pip install (normaformae CLI) by using the package location as anchor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from normaformae.core.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DisciplineLoadError(Exception):
    """Raised when a domain or discipline config cannot be loaded or is invalid."""


# ---------------------------------------------------------------------------
# Path resolution — robust for source and installed package
# ---------------------------------------------------------------------------

def find_domains_root() -> Path:
    """
    Locate the domains/ folder.

    Strategy (tried in order):
    1. Relative to this file: works when running from source tree.
    2. Relative to current working directory: works when normaformae is
       installed and user runs from the project folder.
    3. Raises DisciplineLoadError with a helpful message if neither works.
    """
    # Strategy 1: relative to package file location
    here         = Path(__file__).resolve().parent   # normaformae/core/
    package_root = here.parent.parent                # project root
    candidate    = package_root / "domains"
    if candidate.exists():
        return candidate

    # Strategy 2: relative to current working directory
    cwd_candidate = Path.cwd() / "domains"
    if cwd_candidate.exists():
        return cwd_candidate

    raise DisciplineLoadError(
        f"domains/ folder not found.\n"
        f"  Tried: {candidate}\n"
        f"  Tried: {cwd_candidate}\n"
        f"  Run normaformae from the project root directory, or pass --discipline with a full path."
    )


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def list_domains() -> list[dict[str, Any]]:
    root    = find_domains_root()
    domains = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and not path.name.startswith("_"):
            cfg_path = path / "domain.json"
            if cfg_path.exists():
                domains.append(_load_json(cfg_path))
    return domains


def list_disciplines(domain_id: str) -> list[dict[str, Any]]:
    root        = find_domains_root()
    domain_path = root / domain_id
    if not domain_path.exists():
        raise DisciplineLoadError(f"Domain not found: {domain_id}")
    disciplines = []
    for path in sorted(domain_path.iterdir()):
        if path.is_dir() and not path.name.startswith("_"):
            cfg_path = path / "discipline.json"
            if cfg_path.exists():
                cfg         = _load_json(cfg_path)
                cfg["path"] = str(path)
                disciplines.append(cfg)
    return disciplines


def load_discipline(discipline_path: str | Path) -> dict[str, Any]:
    path     = Path(discipline_path)
    cfg_path = path / "discipline.json"
    if not cfg_path.exists():
        raise DisciplineLoadError(f"discipline.json not found at: {cfg_path}")
    cfg         = _load_json(cfg_path)
    _validate_discipline(cfg, cfg_path)
    cfg["path"] = str(path)
    log.info("Disziplin geladen: %s (v%s)", cfg.get("display_name"), cfg.get("version"))
    return cfg


def load_stance(discipline_path: str | Path, stance_id: str) -> dict[str, Any]:
    path = Path(discipline_path) / "library" / "stances" / f"{stance_id}.json"
    if not path.exists():
        raise DisciplineLoadError(f"Stance not found: {stance_id} at {path}")
    return _load_json(path)


def load_all_stances(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    stances_path = Path(discipline_path) / "library" / "stances"
    stances: dict[str, dict] = {}
    if stances_path.exists():
        for f in sorted(stances_path.glob("*.json")):
            data                          = _load_json(f)
            stances[data.get("stance_id", f.stem)] = data
    return stances


def load_all_sequences(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    seq_path  = Path(discipline_path) / "library" / "sequences"
    sequences: dict[str, dict] = {}
    if seq_path.exists():
        for f in sorted(seq_path.glob("*.json")):
            data                               = _load_json(f)
            sequences[data.get("sequence_id", f.stem)] = data
    return sequences


def load_all_flows(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    flows_path = Path(discipline_path) / "library" / "flows"
    flows: dict[str, dict] = {}
    if flows_path.exists():
        for f in sorted(flows_path.glob("*.json")):
            data                          = _load_json(f)
            flows[data.get("flow_id", f.stem)] = data
    return flows


def load_published_flows(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    return {k: v for k, v in load_all_flows(discipline_path).items()
            if v.get("status") == "published"}


def load_all_support_techniques(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    support_path = Path(discipline_path) / "library" / "support"
    techniques: dict[str, dict] = {}
    if support_path.exists():
        for f in sorted(support_path.glob("*.json")):
            data                                    = _load_json(f)
            techniques[data.get("technique_id", f.stem)] = data
    return techniques


def get_vocabulary(discipline_cfg: dict[str, Any]) -> dict[str, dict[str, str]]:
    """
    Return vocabulary block from a loaded discipline config.
    Falls back to generic German labels if vocabulary is missing.
    """
    defaults = {
        "static":     {"singular": "Position",     "plural": "Positionen"},
        "transition": {"singular": "Übergang",     "plural": "Übergänge"},
        "flow":       {"singular": "Ablauf",       "plural": "Abläufe"},
        "support":    {"singular": "Grundtechnik", "plural": "Grundtechniken"},
    }
    vocab  = discipline_cfg.get("vocabulary", {})
    return {key: vocab.get(key, default) for key, default in defaults.items()}


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def save_stance(discipline_path: str | Path, stance_data: dict[str, Any]) -> Path:
    out = Path(discipline_path) / "library" / "stances" / f"{stance_data['stance_id']}.json"
    _write_json(out, stance_data)
    log.debug("Hut gespeichert: %s", out)
    return out


def save_sequence(discipline_path: str | Path, sequence_data: dict[str, Any]) -> Path:
    out = Path(discipline_path) / "library" / "sequences" / f"{sequence_data['sequence_id']}.json"
    _write_json(out, sequence_data)
    log.debug("Sequenz gespeichert: %s", out)
    return out


def save_flow(discipline_path: str | Path, flow_data: dict[str, Any]) -> Path:
    out = Path(discipline_path) / "library" / "flows" / f"{flow_data['flow_id']}.json"
    _write_json(out, flow_data)
    log.debug("Fluss gespeichert: %s", out)
    return out


def save_support_technique(discipline_path: str | Path,
                           technique_data: dict[str, Any]) -> Path:
    out = Path(discipline_path) / "library" / "support" / f"{technique_data['technique_id']}.json"
    _write_json(out, technique_data)
    log.debug("Grundtechnik gespeichert: %s", out)
    return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise DisciplineLoadError(f"Invalid JSON in {path}: {e}") from e


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _validate_discipline(cfg: dict[str, Any], path: Path) -> None:
    required = ["discipline_id", "domain_id", "display_name",
                "practitioner_levels", "scoring_criteria", "library_paths", "output"]
    missing  = [k for k in required if k not in cfg]
    if missing:
        log.error("discipline.json fehlende Felder: %s  Pfad: %s", missing, path)
        raise DisciplineLoadError(
            f"discipline.json at {path} is missing required fields: {missing}"
        )
