"""
Core chord parsing and music theory engine.
Parses chord symbols into root notes, intervals, and concrete pitches.
"""

import re
from typing import List, Tuple, Optional

# Semitone values for each note name
NOTE_TO_SEMITONE = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
}

# All note names in chromatic order (using sharps)
SHARP_NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

# Keys that conventionally use flats
FLAT_KEYS = {'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb',
             'Dm', 'Gm', 'Cm', 'Fm', 'Bbm', 'Ebm'}

# Interval names and their semitone distances
INTERVAL_SEMITONES = {
    'P1': 0, 'R': 0,
    'm2': 1, 'b9': 1,
    'M2': 2, '9': 2,
    '#9': 3, 'm3': 3,
    'M3': 4,
    'P4': 5, '11': 5,
    '#4': 6, '#11': 6, 'b5': 6, 'TT': 6,
    'P5': 7,
    '#5': 8, 'b6': 8, 'b13': 8,
    'M6': 9, '6': 9, 'dim7': 9, 'bb7': 9,
    'm7': 10, 'b7': 10,
    'M7': 11,
    'b9': 13, '9': 14, '#9': 15,
    '11': 17, '#11': 18,
    'b13': 20, '13': 21,
}

# Map semitone distance to interval name for display
SEMITONE_TO_INTERVAL = {
    0: 'R', 1: 'b2', 2: 'M2', 3: 'm3', 4: 'M3', 5: 'P4',
    6: 'b5', 7: 'P5', 8: '#5', 9: 'M6', 10: 'b7', 11: 'M7'
}

# Interval between two roots (for progression analysis)
SEMITONE_TO_ROOT_INTERVAL = {
    0: 'P1', 1: 'm2', 2: 'M2', 3: 'm3', 4: 'M3', 5: 'P4',
    6: 'TT', 7: 'P5', 8: 'm6', 9: 'M6', 10: 'm7', 11: 'M7'
}

# Chord quality definitions: quality_name -> list of intervals in semitones
CHORD_FORMULAS = {
    # Triads
    'maj':      [0, 4, 7],
    'min':      [0, 3, 7],
    'm':        [0, 3, 7],
    'dim':      [0, 3, 6],
    'aug':      [0, 4, 8],
    'sus2':     [0, 2, 7],
    'sus4':     [0, 5, 7],
    'sus':      [0, 5, 7],
    # Sixths
    '6':        [0, 4, 7, 9],
    'm6':       [0, 3, 7, 9],
    'min6':     [0, 3, 7, 9],
    # Sevenths
    '7':        [0, 4, 7, 10],
    'maj7':     [0, 4, 7, 11],
    'M7':       [0, 4, 7, 11],
    'min7':     [0, 3, 7, 10],
    'm7':       [0, 3, 7, 10],
    'mM7':      [0, 3, 7, 11],
    'minmaj7':  [0, 3, 7, 11],
    'dim7':     [0, 3, 6, 9],
    'm7b5':     [0, 3, 6, 10],
    'aug7':     [0, 4, 8, 10],
    '7#5':      [0, 4, 8, 10],
    '7b5':      [0, 4, 6, 10],
    # Extended
    '9':        [0, 4, 7, 10, 14],
    'maj9':     [0, 4, 7, 11, 14],
    'M9':       [0, 4, 7, 11, 14],
    'min9':     [0, 3, 7, 10, 14],
    'm9':       [0, 3, 7, 10, 14],
    '11':       [0, 4, 7, 10, 14, 17],
    'maj11':    [0, 4, 7, 11, 14, 17],
    'min11':    [0, 3, 7, 10, 14, 17],
    'm11':      [0, 3, 7, 10, 14, 17],
    '13':       [0, 4, 7, 10, 14, 17, 21],
    'maj13':    [0, 4, 7, 11, 14, 17, 21],
    'min13':    [0, 3, 7, 10, 14, 17, 21],
    'm13':      [0, 3, 7, 10, 14, 17, 21],
    # Altered
    '7#9':      [0, 4, 7, 10, 15],
    '7b9':      [0, 4, 7, 10, 13],
    '7#11':     [0, 4, 7, 10, 18],
    '7b13':     [0, 4, 7, 10, 20],
    'alt':      [0, 4, 6, 10, 13, 15],  # 7 b5 b9 #9
    # Add chords
    'add9':     [0, 4, 7, 14],
    'add11':    [0, 4, 7, 17],
    'madd9':    [0, 3, 7, 14],
    # Power chord
    '5':        [0, 7],
}

# Interval labels for each formula position
CHORD_INTERVAL_LABELS = {
    'maj':      ['R', 'M3', 'P5'],
    'min':      ['R', 'm3', 'P5'],
    'm':        ['R', 'm3', 'P5'],
    'dim':      ['R', 'm3', 'b5'],
    'aug':      ['R', 'M3', '#5'],
    'sus2':     ['R', 'M2', 'P5'],
    'sus4':     ['R', 'P4', 'P5'],
    'sus':      ['R', 'P4', 'P5'],
    '6':        ['R', 'M3', 'P5', 'M6'],
    'm6':       ['R', 'm3', 'P5', 'M6'],
    'min6':     ['R', 'm3', 'P5', 'M6'],
    '7':        ['R', 'M3', 'P5', 'b7'],
    'maj7':     ['R', 'M3', 'P5', 'M7'],
    'M7':       ['R', 'M3', 'P5', 'M7'],
    'min7':     ['R', 'm3', 'P5', 'b7'],
    'm7':       ['R', 'm3', 'P5', 'b7'],
    'mM7':      ['R', 'm3', 'P5', 'M7'],
    'minmaj7':  ['R', 'm3', 'P5', 'M7'],
    'dim7':     ['R', 'm3', 'b5', 'bb7'],
    'm7b5':     ['R', 'm3', 'b5', 'b7'],
    'aug7':     ['R', 'M3', '#5', 'b7'],
    '7#5':      ['R', 'M3', '#5', 'b7'],
    '7b5':      ['R', 'M3', 'b5', 'b7'],
    '9':        ['R', 'M3', 'P5', 'b7', '9'],
    'maj9':     ['R', 'M3', 'P5', 'M7', '9'],
    'M9':       ['R', 'M3', 'P5', 'M7', '9'],
    'min9':     ['R', 'm3', 'P5', 'b7', '9'],
    'm9':       ['R', 'm3', 'P5', 'b7', '9'],
    '11':       ['R', 'M3', 'P5', 'b7', '9', '11'],
    'maj11':    ['R', 'M3', 'P5', 'M7', '9', '11'],
    'min11':    ['R', 'm3', 'P5', 'b7', '9', '11'],
    'm11':      ['R', 'm3', 'P5', 'b7', '9', '11'],
    '13':       ['R', 'M3', 'P5', 'b7', '9', '11', '13'],
    'maj13':    ['R', 'M3', 'P5', 'M7', '9', '11', '13'],
    'min13':    ['R', 'm3', 'P5', 'b7', '9', '11', '13'],
    'm13':      ['R', 'm3', 'P5', 'b7', '9', '11', '13'],
    '7#9':      ['R', 'M3', 'P5', 'b7', '#9'],
    '7b9':      ['R', 'M3', 'P5', 'b7', 'b9'],
    '7#11':     ['R', 'M3', 'P5', 'b7', '#11'],
    '7b13':     ['R', 'M3', 'P5', 'b7', 'b13'],
    'alt':      ['R', 'M3', 'b5', 'b7', 'b9', '#9'],
    'add9':     ['R', 'M3', 'P5', '9'],
    'add11':    ['R', 'M3', 'P5', '11'],
    'madd9':    ['R', 'm3', 'P5', '9'],
    '5':        ['R', 'P5'],
}


def note_to_semitone(note: str) -> int:
    """Convert a note name (e.g., 'C#', 'Bb') to semitone value (0-11)."""
    base = note[0].upper()
    semitone = NOTE_TO_SEMITONE[base]
    for accidental in note[1:]:
        if accidental == '#':
            semitone += 1
        elif accidental == 'b':
            semitone -= 1
    return semitone % 12


def semitone_to_note(semitone: int, use_flats: bool = False) -> str:
    """Convert semitone value (0-11) to note name."""
    s = semitone % 12
    if use_flats:
        return FLAT_NOTES[s]
    return SHARP_NOTES[s]


def parse_chord(symbol: str) -> dict:
    """
    Parse a chord symbol into its components.

    Returns dict with:
        - symbol: original symbol
        - root: root note name
        - root_semitone: root as semitone (0-11)
        - quality: chord quality key
        - bass: bass note (for slash chords), or None
        - intervals_semitones: list of semitone intervals
        - interval_labels: list of interval names
        - notes: list of note names
        - use_flats: whether to display with flats
    """
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("Empty chord symbol")

    # Extract slash — could be bass note (C/E) or extension shorthand (Cmaj7/9)
    bass = None
    main_symbol = symbol
    if '/' in symbol:
        parts = symbol.split('/', 1)
        after_slash = parts[1].strip()
        # If it starts with a note letter, it's a bass note slash chord
        # If it's a number/alteration (9, 11, 13, b9, #11), it's an extension
        if re.match(r'^[A-Ga-g]', after_slash):
            main_symbol = parts[0]
            bass = after_slash
        else:
            # Extension shorthand: Cmaj7/9 → treat as Cmaj7 + add the extension
            main_symbol = parts[0] + after_slash

    # Strip parentheses — A7(b13) → A7b13, Cm(maj7) → Cmmaj7
    main_symbol = main_symbol.replace('(', '').replace(')', '')

    # Parse root note
    match = re.match(r'^([A-Ga-g])([#b]*)', main_symbol)
    if not match:
        raise ValueError(f"Cannot parse chord: {symbol}")

    root = match.group(1).upper() + match.group(2)
    remainder = main_symbol[match.end():]

    # Determine quality
    quality = _parse_quality(remainder)
    use_flats = _should_use_flats(root)

    root_semitone = note_to_semitone(root)
    intervals = list(CHORD_FORMULAS[quality])
    labels = list(CHORD_INTERVAL_LABELS[quality])

    # Compute note names
    notes = [semitone_to_note((root_semitone + iv) % 12, use_flats) for iv in intervals]

    return {
        'symbol': symbol,
        'root': root,
        'root_semitone': root_semitone,
        'quality': quality,
        'bass': bass,
        'intervals_semitones': intervals,
        'interval_labels': labels,
        'notes': notes,
        'use_flats': use_flats,
    }


def _parse_quality(remainder: str) -> str:
    """Determine chord quality from the part after the root note."""
    if not remainder or remainder.lower() in ('', 'maj', 'major'):
        if not remainder:
            return 'maj'

    r = remainder

    # Normalize common compound notations before matching
    # e.g. maj79 → maj9, mmaj7 → mM7, min79 → min9
    QUALITY_ALIASES = {
        'maj79': 'maj9', 'maj711': 'maj11', 'maj713': 'maj13',
        'mmaj7': 'mM7', 'mmaj9': 'mM7',  # minor-major
        'min79': 'min9', 'min711': 'min11', 'min713': 'min13',
        'm79': 'm9', 'm711': 'm11', 'm713': 'm13',
        'Maj7': 'maj7', 'Maj9': 'maj9', 'Maj13': 'maj13',
        'Min7': 'm7', 'Min9': 'm9',
        'mi': 'm', 'mi7': 'm7', 'mi9': 'm9',
    }
    if r in QUALITY_ALIASES:
        r = QUALITY_ALIASES[r]

    # Direct matches (try longest first)
    candidates = sorted(CHORD_FORMULAS.keys(), key=len, reverse=True)
    for q in candidates:
        # Case-sensitive check for things like 'M7' vs 'm7'
        if r == q:
            return q
        # Case-insensitive for text forms
        if r.lower() == q.lower() and q not in ('m', 'M7', 'M9'):
            return q

    # Handle '-' as minor
    if r.startswith('-'):
        minor_remainder = r[1:]
        if not minor_remainder:
            return 'm'
        for q in candidates:
            if q.startswith('m') and q[1:] == minor_remainder:
                return q

    # Handle 'min' prefix
    if r.lower().startswith('min'):
        sub = r[3:]
        if not sub:
            return 'min'
        candidate = 'min' + sub
        if candidate in CHORD_FORMULAS:
            return candidate
        candidate = 'm' + sub
        if candidate in CHORD_FORMULAS:
            return candidate

    # Handle 'Maj' / 'Major' prefix for maj7 etc.
    if r.lower().startswith('maj'):
        sub = r[3:]
        if not sub:
            return 'maj'
        candidate = 'maj' + sub
        if candidate in CHORD_FORMULAS:
            return candidate
        candidate = 'M' + sub
        if candidate in CHORD_FORMULAS:
            return candidate

    # Handle triangle (delta) → maj7
    if r.startswith('Δ') or r.startswith('△'):
        sub = r[1:]
        if not sub or sub == '7':
            return 'maj7'

    # Handle 'o' for diminished, 'ø' for half-diminished
    if r == 'o' or r == '°':
        return 'dim'
    if r in ('o7', '°7'):
        return 'dim7'
    if r in ('ø', 'ø7'):
        return 'm7b5'

    raise ValueError(f"Unknown chord quality: '{remainder}'")


def _should_use_flats(root: str) -> bool:
    """Determine if a root note conventionally uses flats."""
    # Roots whose chords are conventionally spelled with flats
    return 'b' in root or root in ('F', 'D', 'G', 'C')


def parse_progression(text: str) -> List[dict]:
    """
    Parse a chord progression string.
    Accepts separators: | , - or whitespace
    Example: "Dm7 | G7 | Cmaj7 | Am7"
    """
    # Split on | , - or whitespace
    symbols = re.split(r'[|,\-\s]+', text.strip())
    symbols = [s.strip() for s in symbols if s.strip()]
    return [parse_chord(s) for s in symbols]


def get_chord_notes_with_octave(chord: dict, base_octave: int = 4) -> List[Tuple[str, int]]:
    """
    Get chord notes with octave numbers suitable for notation.
    Returns list of (note_name, octave) tuples.
    """
    root_semitone = chord['root_semitone']
    use_flats = chord['use_flats']
    result = []
    current_semitone = root_semitone + (base_octave * 12)

    for i, iv in enumerate(chord['intervals_semitones']):
        absolute = root_semitone + iv
        octave = base_octave + (absolute // 12)
        note = semitone_to_note(absolute % 12, use_flats)
        result.append((note, octave))

    return result
