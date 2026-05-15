"""
core/discipline_loader.py

Loads a Domain and Discipline configuration from the domains/ folder tree.
Returns plain dicts — no ORM, no magic. Validates required fields are present.

Slice 1: load + validate JSON. No keypoint or video logic yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DisciplineLoadError(Exception):
    """Raised when a domain or discipline config cannot be loaded or is invalid."""


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def find_domains_root() -> Path:
    here = Path(__file__).resolve().parent          # motion_analysis/core/
    project_root = here.parent.parent               # normaformae/
    domains_root = project_root / "domains"
    if not domains_root.exists():
        raise DisciplineLoadError(f"domains/ folder not found at: {domains_root}")
    return domains_root


def list_domains() -> list[dict[str, Any]]:
    root = find_domains_root()
    domains = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and not path.name.startswith("_"):
            cfg_path = path / "domain.json"
            if cfg_path.exists():
                cfg = _load_json(cfg_path)
                domains.append(cfg)
    return domains


def list_disciplines(domain_id: str) -> list[dict[str, Any]]:
    root = find_domains_root()
    domain_path = root / domain_id
    if not domain_path.exists():
        raise DisciplineLoadError(f"Domain not found: {domain_id}")
    disciplines = []
    for path in sorted(domain_path.iterdir()):
        if path.is_dir() and not path.name.startswith("_"):
            cfg_path = path / "discipline.json"
            if cfg_path.exists():
                cfg = _load_json(cfg_path)
                cfg["path"] = str(path)
                disciplines.append(cfg)
    return disciplines


def load_discipline(discipline_path: str | Path) -> dict[str, Any]:
    path = Path(discipline_path)
    cfg_path = path / "discipline.json"
    if not cfg_path.exists():
        raise DisciplineLoadError(f"discipline.json not found at: {cfg_path}")
    cfg = _load_json(cfg_path)
    _validate_discipline(cfg, cfg_path)
    cfg["path"] = str(path)
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
            data = _load_json(f)
            stance_id = data.get("stance_id", f.stem)
            stances[stance_id] = data
    return stances


def load_all_sequences(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    seq_path = Path(discipline_path) / "library" / "sequences"
    sequences: dict[str, dict] = {}
    if seq_path.exists():
        for f in sorted(seq_path.glob("*.json")):
            data = _load_json(f)
            seq_id = data.get("sequence_id", f.stem)
            sequences[seq_id] = data
    return sequences


def load_all_flows(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    flows_path = Path(discipline_path) / "library" / "flows"
    flows: dict[str, dict] = {}
    if flows_path.exists():
        for f in sorted(flows_path.glob("*.json")):
            data = _load_json(f)
            flow_id = data.get("flow_id", f.stem)
            flows[flow_id] = data
    return flows


def load_published_flows(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    all_flows = load_all_flows(discipline_path)
    return {k: v for k, v in all_flows.items() if v.get("status") == "published"}


def load_all_support_techniques(discipline_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load all supportive technique JSON files from the discipline's support library."""
    support_path = Path(discipline_path) / "library" / "support"
    techniques: dict[str, dict] = {}
    if support_path.exists():
        for f in sorted(support_path.glob("*.json")):
            data = _load_json(f)
            technique_id = data.get("technique_id", f.stem)
            techniques[technique_id] = data
    return techniques


def get_vocabulary(discipline_cfg: dict[str, Any]) -> dict[str, dict[str, str]]:
    """
    Return the vocabulary block from a loaded discipline config.
    Falls back to generic German labels if vocabulary is missing
    (backwards compatibility with disciplines that predate this field).

    Returns dict with keys: static, transition, flow, support
    Each value is a dict with keys: singular, plural
    """
    defaults = {
        "static":     {"singular": "Position",     "plural": "Positionen"},
        "transition": {"singular": "Übergang",     "plural": "Übergänge"},
        "flow":       {"singular": "Ablauf",       "plural": "Abläufe"},
        "support":    {"singular": "Grundtechnik", "plural": "Grundtechniken"},
    }
    vocab = discipline_cfg.get("vocabulary", {})
    result = {}
    for key, default in defaults.items():
        result[key] = vocab.get(key, default)
    return result


# ---------------------------------------------------------------------------
# Save helpers (Author tool writes back to library)
# ---------------------------------------------------------------------------

def save_stance(discipline_path: str | Path, stance_data: dict[str, Any]) -> Path:
    stance_id = stance_data["stance_id"]
    out = Path(discipline_path) / "library" / "stances" / f"{stance_id}.json"
    _write_json(out, stance_data)
    return out


def save_sequence(discipline_path: str | Path, sequence_data: dict[str, Any]) -> Path:
    seq_id = sequence_data["sequence_id"]
    out = Path(discipline_path) / "library" / "sequences" / f"{seq_id}.json"
    _write_json(out, sequence_data)
    return out


def save_flow(discipline_path: str | Path, flow_data: dict[str, Any]) -> Path:
    flow_id = flow_data["flow_id"]
    out = Path(discipline_path) / "library" / "flows" / f"{flow_id}.json"
    _write_json(out, flow_data)
    return out


def save_support_technique(discipline_path: str | Path, technique_data: dict[str, Any]) -> Path:
    technique_id = technique_data["technique_id"]
    out = Path(discipline_path) / "library" / "support" / f"{technique_id}.json"
    _write_json(out, technique_data)
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
    required = ["discipline_id", "domain_id", "display_name", "practitioner_levels",
                "scoring_criteria", "library_paths", "output"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise DisciplineLoadError(
            f"discipline.json at {path} is missing required fields: {missing}"
        )
