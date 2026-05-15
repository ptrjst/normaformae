# Normaformae — project context for Claude Code

## What this project is
Normaformae is a domain-aware movement analysis system.
A user submits a video; the system identifies known Stances and Transitions
from a discipline-specific catalog and produces a Normaformae output —
either a structured document or an annotated video file.

The name: Latin plural genitive — "of the standard forms."

## Language rule
**Code in English. All content shown to users in German.**
- Variable/function/class/file names: English
- UI labels, button text, descriptions, error messages: German
- JSON keys: English — JSON values: German

## Confirmation rule
**Always ask for confirmation before changing or adding any code.**
Collect multiple pending tasks, present a plan, wait for "yes" before applying.

---

## Architecture

### Role hierarchy
- **Author** — curates the discipline catalog (Stances, Sequences, Flows, Support techniques)
- **User** — submits video, receives Normaformae output (document or video file)
- **Trainer** — optional (Slice 5), assigns MovementFlows to Users by level

### Domain hierarchy (runtime)
```
Domain (grouping only, e.g. hema)
  └── Discipline (runtime context, e.g. liechtenauer_longsword)
        ├── Stance              — static body position; requires extracted_frame
        ├── Transition          — named motion between two Stances
        ├── MovementSequence    — Stance → Transition → Stance (inferred from annotation)
        ├── MovementFlow        — ordered series of Sequences · status: draft | published
        └── SupportiveTechnique — instructional enrichment; linked to Stances/Transitions
```

### Vocabulary — discipline-configurable labels
Every discipline defines its own labels for the four catalog types via `vocabulary`
in `discipline.json`. UI strings with `{flow}` / `{flows}` placeholders are resolved
at runtime via `glossary.resolve_ui(vocab)`. Windows store the resolved copy as
`self._rui` and use it for all flow-related display strings.

| Internal key | HEMA Longsword | Generic fallback |
|---|---|---|
| static | Hut / Huten | Position / Positionen |
| transition | Hieb / Hiebe | Übergang / Übergänge |
| flow | Drill / Drills | Ablauf / Abläufe |
| support | Grundtechnik / Grundtechniken | same |

### Key data concepts
- `Stance` requires `extracted_frame` + `keypoints` to be valid for analysis.
  `reference_image` is optional.
- `MovementFlow` has `draft` / `published` states. User tool loads published only.
- `RecognitionResult` — free-form detection of Stances and Sequences from user
  video against discipline catalog. NOT a score vs a specific flow.
- `MovementFlowOutput` — rendered deliverable written to `output/` folder only.
  Naming: `discipline_videoname_YYYYMMDD_HHMMSS.ext`

### Author annotation workflow
1. Load reference video (file only — no camera ever)
2. Video sampled at native FPS — each frame has timestamp (frame × 1/fps)
3. Author selects frame range → assigns label:
   - **Hut** (static) — picks from catalog or creates new
   - **Übergang** (transition) — picks from catalog or creates new
   - **Ignorieren** — excludes frames
4. System auto-calculates timestamps from frame selection
5. Author saves to library, sets draft/published state

---

## Current state: Slice 1 complete

### Package structure
```
normaformae/                    ← project root
  pyproject.toml                ← entry point: normaformae = "normaformae.app:main"
  CLAUDE.md                     ← this file
  README.md
  .gitignore                    ← excludes state.json, output/, .venv/, __pycache__/
  state.json                    ← auto-created on first run; machine-local; gitignored
  output/                       ← all output files land here; gitignored
  domains/
    _template/
      domain.json
      _discipline_template/
        discipline.json
        library/ stances/ sequences/ flows/ support/
    hema/
      domain.json
      liechtenauer_longsword/
        discipline.json
        library/ stances/ sequences/ flows/ support/
  normaformae/                  ← Python package (previously motion_analysis/)
    app.py                      ← entry point; CLI + GUI modes
    startup.py                  ← startup dialog; role click = immediate launch
    glossary.py                 ← all German UI strings + resolve_ui()
    core/
      discipline_loader.py      ← load/validate/save; two-strategy path resolution
      mock_engine.py            ← Slice 1 stub RecognitionResult
      app_state.py              ← state.json read/write (last discipline, role)
    author/
      window.py                 ← Author tool; uses self._rui for flow labels
    user/
      window.py                 ← User tool; uses self._rui for flow labels
    trainer/                    ← Slice 5
    cli/
      output_writer.py          ← CLI file writer; three-strategy output dir resolution
    output/                     ← Slice 4+ renderers
  tests/
```

### Built and tested
- Startup dialog: pre-selects last discipline+role from state.json; role click = launch
- Author window: vocabulary-driven section headers; multi-select support technique
  checklist; Wiktenauer search; showMaximized()
- User window: video upload; mock analysis; three result tabs
- CLI: `normaformae <video>` writes two stub files to output/; `--help` works
- App state: saved on launch, restored on next open

### Known issues fixed (do not reintroduce)
- `no_reference_image` must be in top-level `UI` dict (author/window.py reads from UI)
- After any pyproject.toml change: run `pip install -e . --no-deps`
- Always run with .venv Python, not system Python
- All flow-related UI strings use `{flow}` placeholders — always resolve via
  `resolve_ui(vocab)` and use `self._rui[key]`, never raw `UI[key]` for those keys
- `UI["confirm"]` was removed — Bestätigen button no longer exists

---

## Slice plan

### Slice 2 — Author video annotation (NEXT)
- Load video file into Author tool (QLabel + QPixmap frame display)
- Frame scrubber (QSlider) with timestamp display (frame × 1/fps)
- Frame range selection → label assignment (Hut / Übergang / Ignorieren)
- MediaPipe keypoint extraction on selected frame(s)
- Save Stance with extracted_frame, keypoints, timestamps to library JSON
- Visual: ○ draft → ✓ complete in catalog list

### Slice 3 — Real analysis engine + URL input
- MediaPipe on user-submitted video
- Compare detected keypoints against catalog Stances (cosine similarity)
- Produce real RecognitionResult (replace mock_engine)
- URL input via yt-dlp

### Slice 4 — Document renderer
- Jinja2 HTML template for MovementFlowOutput
- Per-sequence: extracted_frame + reference_image + description + Häufige Fehler
- WeasyPrint HTML → PDF
- Output file to output/ with timestamp filename

### Slice 5 — Augmented video + Trainer UI + Session log
- cv2.VideoWriter annotated output video
- Trainer PyQt6 window
- SQLite session log

---

## To run
```powershell
# Activate venv first
.venv\Scripts\Activate.ps1

# GUI (default)
normaformae

# CLI
normaformae C:\path\to\video.mp4
normaformae C:\path\to\video.mp4 --discipline liechtenauer_longsword
normaformae C:\path\to\video.mp4 --doc-only
normaformae --help
```

## Stack
Python 3.11+, PyQt6, mediapipe, opencv-python, numpy,
scikit-learn, joblib, torch (CPU), yt-dlp, jinja2, weasyprint

## First discipline: HEMA — Liechtenauer Longsword
- Huten: Vom Tag, Ochs, Pflug, Alber, Zornhut, Schrankhut
- Hiebe: Zornhau, Krumphau, Zwerchhau, Schielhau, Scheitelhau,
         Oberhau, Unterhau, Mittelhau, Stich, Absetzen, Winden
- Grundtechniken: Vor und Nach, Fühlen
- Levels: Schüler, Geselle, Freifechter, Meister
- Criteria: Struktur, Mensur, Linie, Timing, Krafteinsatz
- Wiktenauer: https://wiktenauer.com/wiki/Special:Search?search={term}
