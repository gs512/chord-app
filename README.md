## Project Overview

Streamlit web app for chord voicing visualization and interval analysis. Accepts chord symbols (e.g., `Cmaj7`, `Dm7b5`) and progressions (e.g., `Dm7 | G7 | Cmaj7`), displays guitar fretboard diagrams, piano keyboard diagrams, tablature, musical score notation (VexFlow), and interval/progression analysis.

## Commands

```bash
# Install dependencies
pip install .

# Run the app
uvicorn app_fastapi:app --host 0.0.0.0 --port 8886 --reload
```

## Architecture

- **`app.py`** — Streamlit UI entry point. Two modes: single chord and chord progression. Uses tabs to organize guitar, keyboard, score, and interval views.
- **`music_theory/chords.py`** — Core engine. Parses chord symbols via regex into root/quality/intervals. `CHORD_FORMULAS` dict maps quality names to semitone interval lists. All note math is semitone-based (0-11).
- **`music_theory/guitar.py`** — Guitar voicing generation. Has a `VOICING_DB` for common open/barre shapes; falls back to algorithmic barre chord generation. Renders fretboard diagrams with matplotlib.
- **`music_theory/keyboard.py`** — Keyboard voicing in root position. Renders 2-octave piano diagram with matplotlib, highlighting pressed keys.
- **`music_theory/intervals.py`** — Interval analysis. Chord-level (intervals from root) and progression-level (Roman numeral analysis, root movement, pattern detection via `COMMON_PATTERNS` dict). Key detection uses heuristic scoring against major/minor scales.
- **`music_theory/vexflow_render.py`** — Generates HTML+JS using VexFlow 4.x CDN for treble clef and guitar tab notation. Embedded in Streamlit via `st.components.v1.html()`.

## Key Design Decisions

- No external music theory library — all chord/interval math is self-contained in `music_theory/`.
- VexFlow loaded from CDN (`cdn.jsdelivr.net/npm/vexflow@4.2.6`) — no npm build step needed.
- Guitar voicings use a pre-built database with algorithmic fallback; keyboard voicings are always root position.
- Chord symbols are parsed with a longest-match-first strategy against `CHORD_FORMULAS` keys.
