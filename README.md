# Normaformae

Domain-aware movement analysis and standard form generation.

Identifies known Stances (Huten) and Transitions (Übergänge) from a
discipline-specific catalog in a submitted video, and produces a
structured MovementFlowOutput — document or annotated video.

---

## Setup (Windows)

### 1. Create and activate the virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If activation is blocked by execution policy:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then activate again.

You must see `(.venv)` in your prompt before installing or running anything.

### 2. Install dependencies

```powershell
pip install mediapipe opencv-python numpy scikit-learn joblib torch PyQt6 yt-dlp jinja2
pip install -e . --no-deps
```

> WeasyPrint (PDF export) requires GTK on Windows — skip until Slice 4.

### 3. Verify

```powershell
python -c "from normaformae.core.discipline_loader import list_domains; print(list_domains())"
```

Expected: HEMA domain printed to console.

### 4. Run

```powershell
normaformae
```

Or after install:

```powershell
normaformae
```

---

## VS Code setup

1. Open the folder in VS Code: `code .`
2. `Ctrl+Shift+P` → **Python: Select Interpreter** → choose `.venv`
3. Always use the integrated terminal (it activates the venv automatically once the interpreter is set)

---

## Current state — Slice 1

- Startup dialog: Domain → Discipline → Role selection
- Author tool: catalog browser, properties panel, Wiktenauer search (stubs for annotation)
- User tool: video upload, mock analysis engine, result display in three tabs

First discipline: **HEMA — Liechtenauer Langschwert**

---

## Known issues fixed

| Issue | Fix |
|---|---|
| Wrong Python environment | Always activate `.venv` first, or use VS Code with interpreter set to `.venv` |
| Stale entry point after rename | Run `pip install -e .` after any `pyproject.toml` change |
| Missing `no_reference_image` UI key | Added to `UI` dict in `glossary.py` |
