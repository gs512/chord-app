"""
Chord Voicing & Analysis — FastAPI + HTMX App
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_DPI = 150
plt.rcParams['figure.dpi'] = _DPI
plt.rcParams['savefig.dpi'] = _DPI

import hashlib
import logging
import time
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from music_theory.chords import parse_chord, parse_progression, note_to_semitone, semitone_to_note
from music_theory.guitar import (
    generate_all_voicings, render_fretboard, voicing_to_tab,
    voicing_to_notes, voicing_to_midi, get_guitar_tab_for_progression,
    generate_all_shell_voicings, render_scale_fretboard
)
from music_theory.keyboard import (
    generate_keyboard_inversions, render_piano,
    generate_shell_keyboard_inversions, render_scale_piano
)
from music_theory.intervals import (
    analyze_chord_intervals, detect_key, roman_numeral_analysis,
    root_movement_analysis, detect_patterns,
    get_diatonic_chords, suggest_substitutions, suggest_scales, SCALES,
    render_circle_of_fifths
)

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('chord-app')

# --- App setup ---
app = FastAPI()

CHART_CACHE = Path(__file__).parent / '.cache' / 'charts'
CHART_CACHE.mkdir(parents=True, exist_ok=True)

app.mount("/charts", StaticFiles(directory=str(CHART_CACHE)), name="charts")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

ALL_KEYS = ['C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F',
            'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B']

INV_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}

CT_MAP = {
    "triads": "triad", "7th": "7th", "9th": "9th",
    "sus4": "sus4", "sus2": "sus2", "add9": "add9", "6th": "6th",
}

# --- PNG cache ---

def _chart_key(*parts):
    raw = '|'.join(str(p) for p in parts) + f'|dpi={_DPI}'
    return hashlib.md5(raw.encode()).hexdigest()


def _fig_to_cached_png(cache_key, render_fn):
    path = CHART_CACHE / f"{cache_key}.png"
    if not path.exists():
        t = time.perf_counter()
        fig = render_fn()
        fig.savefig(path, bbox_inches='tight', facecolor='white', pad_inches=0.1)
        plt.close(fig)
        log.info(f'rendered {cache_key[:8]}... in {(time.perf_counter()-t)*1000:.0f}ms')
    return f"/charts/{cache_key}.png"


# --- Cached voicing generation ---

@lru_cache(maxsize=256)
def _cached_all_voicings(symbol):
    return generate_all_voicings(parse_chord(symbol))

@lru_cache(maxsize=256)
def _cached_keyboard_inversions(symbol):
    return generate_keyboard_inversions(parse_chord(symbol))

@lru_cache(maxsize=256)
def _cached_all_shell_voicings(symbol):
    return generate_all_shell_voicings(parse_chord(symbol))

@lru_cache(maxsize=256)
def _cached_shell_keyboard_inversions(symbol):
    return generate_shell_keyboard_inversions(parse_chord(symbol))


# --- Helpers to build voicing data for templates ---

def _safe_id(symbol):
    """Make chord symbol safe for use in HTML IDs and CSS selectors."""
    return symbol.replace('#', 'sharp').replace('/', 'over')


def _guitar_voicing_data(chord, voicing_idx=0, *, shell=False):
    cache_fn = _cached_all_shell_voicings if shell else _cached_all_voicings
    prefix = 'shell' if shell else 'fret'
    label_prefix = 'Shell' if shell else 'Voicing'

    all_v = cache_fn(chord['symbol'])
    idx = min(voicing_idx, len(all_v) - 1)
    v = all_v[idx]
    ck = _chart_key(prefix, chord['symbol'], tuple(v))
    img = _fig_to_cached_png(ck, lambda: render_fretboard(chord, v))
    tab_sym = chord['symbol'] + (' (shell)' if shell else '')
    return {
        'img': img, 'notes': [n or 'X' for n in voicing_to_notes(v)],
        'midi': voicing_to_midi(v), 'tab': voicing_to_tab(tab_sym, v),
        'idx': idx, 'total': len(all_v),
        'label': f"{label_prefix} {idx+1}/{len(all_v)}",
        'symbol': chord['symbol'], 'safe_id': _safe_id(chord['symbol']),
    }


def _keyboard_voicing_data(chord, inversion_idx=0, figsize=(6, 2.5), *, shell=False):
    cache_fn = _cached_shell_keyboard_inversions if shell else _cached_keyboard_inversions
    prefix = 'shellpiano' if shell else 'piano'

    inversions = cache_fn(chord['symbol'])
    idx = min(inversion_idx, len(inversions) - 1)
    kb = inversions[idx]
    ck = _chart_key(prefix, chord['symbol'], tuple(tuple(v) for v in kb), figsize)
    img = _fig_to_cached_png(ck, lambda: render_piano(chord, voicing=kb, figsize=figsize))
    labels = ["Root Position"] + [f"{i}{INV_SUFFIXES.get(i, 'th')} Inv." for i in range(1, len(inversions))]
    return {
        'img': img, 'notes_str': ', '.join(f"{n}{o}" for n, o, _ in kb),
        'midi': [m for _, _, m in kb], 'idx': idx, 'total': len(inversions),
        'label': labels[idx], 'symbol': chord['symbol'], 'safe_id': _safe_id(chord['symbol']),
    }


def _enrich_subs(subs, chord=None):
    """Add guitar/keyboard voicing data to substitution dicts."""
    for s in subs:
        sub_sym = s['symbol'].split('\u2192')[0].strip().split(' ')[0].strip()
        try:
            sub_c = parse_chord(sub_sym)
            s['gv'] = _guitar_voicing_data(sub_c)
            s['kv'] = _keyboard_voicing_data(sub_c, figsize=(4, 1.5))
        except ValueError:
            pass


def _enrich_scales(scales, use_flats):
    """Add fretboard/piano diagram URLs to scale dicts."""
    for s in scales:
        parts = s['scale'].split(' ', 1)
        if len(parts) == 2:
            s_root, s_name = parts
            if s_name in SCALES:
                sk = _chart_key('scalefret', s_name, s_root, use_flats)
                s['fret_img'] = _fig_to_cached_png(sk, lambda s_name=s_name, s_root=s_root, uf=use_flats:
                    render_scale_fretboard(s_name, s_root, SCALES[s_name], use_flats=uf))
                sk = _chart_key('scalepiano', s_name, s_root, use_flats)
                s['piano_img'] = _fig_to_cached_png(sk, lambda s_name=s_name, s_root=s_root, uf=use_flats:
                    render_scale_piano(s_name, s_root, SCALES[s_name], use_flats=uf))


def _parse_prog_params(prog_input, sel_key, sel_mode):
    """Parse progression and detect key. Returns (chords, key, mode) or raises ValueError."""
    chords = parse_progression(prog_input)
    if not chords:
        raise ValueError("No chords found")
    if sel_key == "Auto" or sel_mode == "Auto":
        auto_key, auto_mode = detect_key(chords)
        key = auto_key if sel_key == "Auto" else sel_key
        mode = auto_mode if sel_mode == "Auto" else sel_mode
    else:
        key, mode = sel_key, sel_mode
    return chords, key, mode


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    chord_input = "Cmaj7"
    try:
        chord = parse_chord(chord_input)
        gv = _guitar_voicing_data(chord)
        sgv = _guitar_voicing_data(chord, shell=True)
        content = templates.get_template("partials/guitar_single.html").render(
            chord=chord, gv=gv, sgv=sgv)
    except ValueError:
        content = '<p class="alert alert-warning">Enter a valid chord symbol.</p>'

    return templates.TemplateResponse("base.html", {
        "request": request, "mode": "single",
        "chord_input": chord_input, "single_view": "guitar",
        "prog_input": "Dm7 | G7 | Cmaj7 | Am7",
        "sel_key": "Auto", "sel_mode": "Auto", "prog_view": "guitar",
        "all_keys": ALL_KEYS, "content": content,
    })


@app.get("/partial/mode_form", response_class=HTMLResponse)
async def mode_form(request: Request, app_mode: str = "single"):
    return templates.TemplateResponse("partials/mode_form.html", {
        "request": request, "mode": app_mode,
        "chord_input": "Cmaj7", "single_view": "guitar",
        "prog_input": "Dm7 | G7 | Cmaj7 | Am7",
        "sel_key": "Auto", "sel_mode": "Auto", "prog_view": "guitar",
        "all_keys": ALL_KEYS,
    })


@app.get("/partial/single_content", response_class=HTMLResponse)
async def single_content(request: Request,
                         chord: str = "Cmaj7",
                         single_view: str = "guitar",
                         voicing_idx: int = 0,
                         inversion_idx: int = 0,
                         shell_voicing_idx: int = 0,
                         shell_inversion_idx: int = 0):
    t0 = time.perf_counter()
    try:
        c = parse_chord(chord)
    except ValueError as e:
        return HTMLResponse(f'<p class="alert alert-warning">Cannot parse: {e}</p>')

    ctx = {"request": request, "chord": c}

    if single_view == "guitar":
        ctx['gv'] = _guitar_voicing_data(c, voicing_idx)
        ctx['sgv'] = _guitar_voicing_data(c, shell_voicing_idx, shell=True)
        tpl = "partials/guitar_single.html"
    elif single_view == "keyboard":
        ctx['kv'] = _keyboard_voicing_data(c, inversion_idx)
        ctx['skv'] = _keyboard_voicing_data(c, shell_inversion_idx, shell=True)
        tpl = "partials/keyboard_single.html"
    elif single_view == "intervals":
        ctx['intervals'] = analyze_chord_intervals(c)
        tpl = "partials/intervals_single.html"
    elif single_view == "substitutions":
        subs = suggest_substitutions(c)
        _enrich_subs(subs)
        ctx['subs'] = subs
        tpl = "partials/substitutions.html"
    elif single_view == "scales":
        scales = suggest_scales(c)
        _enrich_scales(scales, c['use_flats'])
        ctx['scales'] = scales
        tpl = "partials/scales.html"
    else:
        return HTMLResponse('<p class="alert alert-warning">Unknown view.</p>')

    log.info(f'single/{single_view} [{chord}]: {(time.perf_counter()-t0)*1000:.0f}ms')
    return templates.TemplateResponse(tpl, ctx)


@app.get("/partial/prog_content", response_class=HTMLResponse)
async def prog_content(request: Request,
                       prog_input: str = "Dm7 | G7 | Cmaj7 | Am7",
                       sel_key: str = "Auto",
                       sel_mode: str = "Auto",
                       prog_view: str = "guitar",
                       chord_type: str = "7th"):
    t0 = time.perf_counter()
    try:
        chords, key, mode = _parse_prog_params(prog_input, sel_key, sel_mode)
    except ValueError as e:
        return HTMLResponse(f'<p class="alert alert-warning">{e}</p>')

    ctx = {"request": request, "chords": chords, "key": key, "mode": mode,
           "prog_input": prog_input, "sel_key": sel_key, "sel_mode": sel_mode}

    if prog_view == "guitar":
        ctx['voicings'] = [_guitar_voicing_data(c) for c in chords]
        ctx['tab_text'] = get_guitar_tab_for_progression(chords)
        tpl = "partials/guitar_prog.html"
    elif prog_view == "keyboard":
        ctx['voicings'] = [_keyboard_voicing_data(c, figsize=(4, 1.5)) for c in chords]
        tpl = "partials/keyboard_prog.html"
    elif prog_view == "intervals":
        ctx['chord_intervals'] = [(c, analyze_chord_intervals(c)) for c in chords]
        ctx['roman'] = roman_numeral_analysis(chords, key, mode)
        ctx['movements'] = root_movement_analysis(chords)
        ctx['patterns'] = detect_patterns(chords, key, mode)
        tpl = "partials/intervals_prog.html"
    elif prog_view == "diatonic":
        ct = CT_MAP.get(chord_type, "7th")
        cof_ck = _chart_key('cof', key, mode)
        ctx['cof_img'] = _fig_to_cached_png(cof_ck, lambda: render_circle_of_fifths(key, mode))
        diatonic = get_diatonic_chords(key, mode, chord_type=ct)
        for d in diatonic:
            try:
                dc = parse_chord(d['symbol'])
                notes = [semitone_to_note((dc['root_semitone'] + iv) % 12, dc['use_flats'])
                         for iv in dc['intervals_semitones']]
                d['notes'] = '  '.join(notes)
                d['gv'] = _guitar_voicing_data(dc)
                d['kv'] = _keyboard_voicing_data(dc, figsize=(4, 1.5))
            except ValueError:
                d['notes'] = ''
        ctx['diatonic'] = diatonic
        ctx['chord_type'] = chord_type
        dia_roots = {note_to_semitone(d['root']) for d in diatonic}
        ctx['chromatic'] = [c['symbol'] for c in chords if c['root_semitone'] not in dia_roots]
        tpl = "partials/diatonic.html"
    elif prog_view == "substitutions":
        chord_subs = []
        for c in chords:
            subs = suggest_substitutions(c, key, mode)
            _enrich_subs(subs)
            chord_subs.append((c, subs))
        ctx['chord_subs'] = chord_subs
        tpl = "partials/prog_substitutions.html"
    elif prog_view == "scales":
        chord_scales = []
        for c in chords:
            scales = suggest_scales(c)
            _enrich_scales(scales, c['use_flats'])
            chord_scales.append((c, scales))
        ctx['chord_scales'] = chord_scales
        tpl = "partials/prog_scales.html"
    else:
        return HTMLResponse('<p class="alert alert-warning">Unknown view.</p>')

    log.info(f'prog/{prog_view}: {(time.perf_counter()-t0)*1000:.0f}ms')
    return templates.TemplateResponse(tpl, ctx)


# --- Voicing navigation (prev/next via HTMX) ---

_VOICING_NAV_DISPATCH = {
    "guitar":        (lambda c, idx: _guitar_voicing_data(c, idx),                "partials/_voicing_guitar.html"),
    "shell_guitar":  (lambda c, idx: _guitar_voicing_data(c, idx, shell=True),    "partials/_voicing_guitar.html"),
    "keyboard":      (lambda c, idx: _keyboard_voicing_data(c, idx),              "partials/_voicing_keyboard.html"),
    "shell_keyboard":(lambda c, idx: _keyboard_voicing_data(c, idx, shell=True),  "partials/_voicing_keyboard.html"),
}


@app.get("/partial/voicing_nav", response_class=HTMLResponse)
async def voicing_nav(request: Request,
                      symbol: str = "Cmaj7",
                      vtype: str = "guitar",
                      idx: int = 0):
    try:
        c = parse_chord(symbol)
    except ValueError as e:
        return HTMLResponse(f'<p class="text-muted">{e}</p>')

    entry = _VOICING_NAV_DISPATCH.get(vtype)
    if not entry:
        return HTMLResponse('<p>Unknown type</p>')

    builder, tpl = entry
    return templates.TemplateResponse(tpl, {"request": request, "v": builder(c, idx), "vtype": vtype})
