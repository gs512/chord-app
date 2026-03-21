# Chord Voicing & Analysis

Web app for chord voicing visualization and interval analysis. Enter a chord symbol (e.g. `Cmaj7`, `Dm7b5`) or a progression (e.g. `Dm7 | G7 | Cmaj7 | Am7`) and get interactive guitar fretboard diagrams, piano keyboard diagrams, tablature, interval breakdowns, substitution suggestions, and scale recommendations.

Built with FastAPI + HTMX for fast, lightweight delivery — designed to run on a Raspberry Pi and serve mobile devices over a local network.

## Features

### Single Chord Mode
- **Guitar** — Fretboard diagram with full and shell voicings, prev/next navigation, tablature, play/strum audio
- **Keyboard** — Piano diagram with inversions and shell voicings, prev/next navigation, play audio
- **Intervals** — Interval analysis from root (semitones, interval names, scale degrees)
- **Substitutions** — Suggested chord substitutions with guitar and keyboard voicing diagrams
- **Scales** — Scale suggestions for improvisation with fretboard and piano diagrams

### Chord Progression Mode
- **Guitar / Keyboard** — Voicing grid for all chords in the progression with navigation and audio
- **Intervals** — Per-chord intervals, Roman numeral analysis, root movement, common pattern detection
- **Diatonic** — Circle of fifths, diatonic chord table (triads/7th/9th/sus/add9/6th), voicing diagrams, chromatic chord detection
- **Substitutions** — Per-chord substitution suggestions with voicing diagrams
- **Scales** — Per-chord scale suggestions with fretboard and piano diagrams

### Other
- Automatic key detection from chord progressions
- Web Audio API playback (play and strum) — no audio files needed
- PNG disk caching for all chart images (DPI-aware cache keys)
- HTMX partial page updates — no full page reloads
- Responsive CSS grid layout for mobile devices

## Requirements

- Python 3.10+

## Install

```bash
pip install .
```

## Run

```bash
uvicorn app_fastapi:app --host 0.0.0.0 --port 8886 --reload
```

Then open `http://localhost:8886` in a browser.

## Project Structure

```
app_fastapi.py              # FastAPI backend — routes, PNG caching, voicing helpers
templates/
  base.html                 # Main layout — HTMX, mode toggle, view radio groups, audio JS
  partials/
    _voicing_guitar.html    # Reusable guitar voicing card (nav, image, play/strum)
    _voicing_keyboard.html  # Reusable keyboard voicing card (nav, image, play)
    guitar_single.html      # Single chord guitar view (full + shell)
    keyboard_single.html    # Single chord keyboard view (full + shell)
    intervals_single.html   # Single chord interval table
    substitutions.html      # Single chord substitutions with voicings
    scales.html             # Single chord scales with diagrams
    guitar_prog.html        # Progression guitar voicing grid + tablature
    keyboard_prog.html      # Progression keyboard voicing grid
    intervals_prog.html     # Progression intervals + roman numerals + patterns
    diatonic.html           # Circle of fifths + diatonic chord table + voicings
    prog_substitutions.html # Per-chord substitutions
    prog_scales.html        # Per-chord scale suggestions
    mode_form.html          # Mode-switching form (single/progression)
static/
  style.css                 # Responsive CSS — radio pills, chord grid, buttons
music_theory/
  chords.py                 # Chord symbol parser, CHORD_FORMULAS, semitone math
  guitar.py                 # Guitar voicing generation (VOICING_DB + algorithmic), fretboard rendering
  keyboard.py               # Keyboard inversions (root position), piano rendering
  intervals.py              # Interval analysis, key detection, Roman numerals, scales, substitutions
  voice_leading.py          # Voice leading optimization for progressions
  audio.py                  # Web Audio JS generation (legacy Streamlit)
  vexflow_render.py         # VexFlow score rendering (legacy Streamlit)
```

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — async Python web framework
- **[HTMX](https://htmx.org/)** — ~14KB, HTML-over-the-wire partial updates
- **[Jinja2](https://jinja.palletsprojects.com/)** — server-side HTML templates
- **[Matplotlib](https://matplotlib.org/)** — fretboard and piano diagram rendering (Agg backend)
- **Web Audio API** — client-side chord playback with no audio files

## Configuration

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| DPI | `app_fastapi.py` line 9 | `150` | Chart image resolution. Lower = faster rendering, higher = sharper images |
| Cache dir | `app_fastapi.py` line 51 | `.cache/charts/` | PNG disk cache. Delete to regenerate all images |
| LRU cache | `app_fastapi.py` | `maxsize=256` | In-memory voicing cache per chord type |
