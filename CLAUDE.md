# Normaformae — project context for Claude Code

## What this project is
Normaformae is a domain-aware movement analysis system.
A user submits a video; the system identifies known Stances (Huten) and
Transitions (Übergänge) from a discipline-specific catalog and produces
a Normaformae output — either a structured document or an annotated video file.

The name: Latin plural genitive — "of the standard forms." The system
produces and maintains a corpus of standard forms against which movement
is measured.

## Language rule
**Code in English. All content shown to users in German.**
- Variable names, function names, class names, file names: English
- UI labels, button text, descriptions, error messages: German
- String keys in JSON/Python: English
- String values (labels, descriptions): German

## Architecture

### Role hierarchy
- **Author** — hidden role, curates the discipline catalog (Stances, Sequences, Flows)
- **User** — submits video, receives Normaformae output (document or video file)
- **Trainer** — optional (Slice 5), assigns MovementFlows to Users by level

### Domain hierarchy (runtime)
```
Domain (grouping only, e.g. hema)
  └── Discipline (runtime context, e.g. liechtenauer_longsword)
        ├── Stance (Hut)         — static body position, requires extracted_frame
        ├── Transition (Übergang)— named motion between two Stances
        ├── MovementSequence     — Stance → Transition → Stance (inferred from annotation)
        └── MovementFlow         — ordered series of Sequences · status: draft | published
```

### Key data concepts
- `Stance` requires `extracted_frame` + `keypoints` to be valid for analysis.
  `reference_image` is optional.
- `MovementFlow` has `draft` / `published` states. User tool loads published only.
- `RecognitionResult` — output of analysis engine: free-form detection of Stances
  and Sequences from user video against discipline catalog. NOT a score vs a flow.
- `MovementFlowOutput` — rendered deliverable: HTML/PDF document (Slice 4)
  or annotated video file (Slice 5). Files written to `output/` folder only.
  Naming: `discipline_flow_YYYYMMDD_HHMMSS.ext`

### Author annotation workflow
1. Author loads a reference video (file only, no camera)
2. Video is sampled at native FPS — each frame has a timestamp (frame × 1/fps)
3. Author selects a frame range and assigns one of three labels:
   - **Hut** — static stance, picks from catalog or creates new
   - **Übergang** — transition, picks from catalog or creates new
   - **Ignorieren** — excludes frames from reference
4. System auto-calculates timestamps from frame selection
5. Author saves to discipline library, publishes when ready

## Current state: Slice 1 complete

### Built and tested
- `pyproject.toml` — project definition, `pip install -e .`, entry point `normaformae`
- `motion_analysis/glossary.py` — all German UI strings + HEMA Liechtenauer vocabulary
- `motion_analysis/core/discipline_loader.py` — load/validate/save domain+discipline JSON
- `motion_analysis/core/mock_engine.py` — mock RecognitionResult from real catalog data
- `motion_analysis/startup.py` — PyQt6 startup dialog (domain → discipline → role)
- `motion_analysis/author/window.py` — Author tool stub (full layout, no logic yet)
- `motion_analysis/user/window.py` — User tool stub (mock analysis runs, result displayed)
- `domains/hema/domain.json` + `liechtenauer_longsword/discipline.json`
- 6 Huten, 1 Sequenz, 1 Bewegungsfluss (all draft — no extracted_frame yet)

### To run
```powershell
pip install -e .
python -m motion_analysis.app
# or after install:
normaformae
```

## Slice plan

### Slice 2 — Author video annotation (NEXT)
- Load video file into Author tool (QLabel + QPixmap frame display)
- Frame scrubber (QSlider) with timestamp display
- Frame range selection → label assignment (Hut / Übergang / Ignorieren)
- MediaPipe keypoint extraction on selected frame(s)
- Save Stance with extracted_frame, keypoints, timestamps to library JSON
- Visual: ○ draft → ✓ complete in catalog list

### Slice 3 — Real analysis engine + URL input
- MediaPipe on user-submitted video
- Compare detected keypoints against catalog Stances (cosine similarity)
- Produce real RecognitionResult (replace mock_engine)
- URL input via yt-dlp (download → temp file → analyse)

### Slice 4 — Document renderer
- Jinja2 HTML template for MovementFlowOutput document
- Per-sequence sections: extracted_frame + reference_image + description + Häufige Fehler
- WeasyPrint HTML → PDF export
- Output file written to output/ with timestamp filename

### Slice 5 — Augmented video + Trainer UI + Session log
- cv2.VideoWriter annotated output video (skeleton overlay + stance labels)
- Trainer PyQt6 window: browse users, assign flows, filter by PractitionerLevel
- SQLite session log: persist Sessions per user across launches

## Repo structure
```
normaformae/                        ← project root
  pyproject.toml
  CLAUDE.md                         ← this file
  output/                           ← all output files land here (gitignore large files)
  domains/
    _template/
      domain.json
      _discipline_template/
        discipline.json
        library/stances/ sequences/ flows/
    hema/
      domain.json
      liechtenauer_longsword/
        discipline.json
        library/stances/ sequences/ flows/
  motion_analysis/                  ← Python package
    app.py                          ← entry point
    startup.py                      ← startup dialog
    glossary.py                     ← all German content constants
    core/
      discipline_loader.py          ← load/validate/save discipline data
      mock_engine.py                ← Slice 1 stub — replaced in Slice 3
      engine.py                     ← Slice 3 — real MediaPipe analysis
      normalizer.py                 ← Slice 2 — keypoint normalization
    author/
      window.py                     ← Author tool main window
      annotation.py                 ← Slice 2 — frame scrubber + labeling
    user/
      window.py                     ← User tool main window
    trainer/
      window.py                     ← Slice 5
    output/
      document_renderer.py          ← Slice 4 — HTML/PDF
      video_renderer.py             ← Slice 5 — annotated mp4
  tests/

## Known issues (already fixed — do not reintroduce)
- `no_reference_image` must be in the top-level `UI` dict in `glossary.py`,
  not only in `HEMA_LIECHTENAUER["output_headers"]`. author/window.py reads from `UI`.
- After any `pyproject.toml` change, always run `pip install -e .` to update dist-info.
- Always run with the `.venv` Python, not system Python.
  In VS Code: set interpreter to `.venv`. In terminal: activate first.

## Stack
Python 3.11+, PyQt6, mediapipe, opencv-python, numpy,
scikit-learn, joblib, torch (CPU wheel), yt-dlp, jinja2, weasyprint

## Discipline: HEMA Liechtenauer Longsword
First and reference discipline. German terminology throughout.
- Huten: Vom Tag, Ochs, Pflug, Alber, Zornhut, Schrankhut (+ Nebenhut planned)
- Übergänge: Zornhau, Krumphau, Zwerchhau, Schielhau, Scheitelhau,
             Oberhau, Unterhau, Mittelhau, Stich, Absetzen, Winden
- PractitionerLevels: Schüler, Geselle, Freifechter, Meister
- ScoringCriteria: Struktur, Mensur, Linie, Timing, Krafteinsatz
- Wiktenauer search: https://wiktenauer.com/wiki/Special:Search?search={term}
```
