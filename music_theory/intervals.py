"""
Interval analysis for individual chords and chord progressions.
"""

from typing import List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from .chords import (
    parse_chord, note_to_semitone, semitone_to_note,
    SEMITONE_TO_INTERVAL, SEMITONE_TO_ROOT_INTERVAL,
    SHARP_NOTES, FLAT_NOTES, CHORD_FORMULAS, CHORD_INTERVAL_LABELS
)

# Major scale intervals for Roman numeral analysis
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]

# Scale degree names
SCALE_DEGREES = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']

# Common progression patterns
COMMON_PATTERNS = {
    ('ii', 'V', 'I'): 'ii-V-I (Jazz standard cadence)',
    ('ii', 'V', 'i'): 'ii-V-i (Minor ii-V-i)',
    ('I', 'IV', 'V'): 'I-IV-V (Blues/Rock)',
    ('I', 'IV', 'V', 'I'): 'I-IV-V-I (Authentic cadence)',
    ('I', 'V', 'vi', 'IV'): 'I-V-vi-IV (Pop progression)',
    ('I', 'vi', 'IV', 'V'): 'I-vi-IV-V (50s progression)',
    ('I', 'vi', 'ii', 'V'): 'I-vi-ii-V (Rhythm changes turnaround)',
    ('i', 'bVI', 'bVII', 'i'): 'i-bVI-bVII (Aeolian cadence)',
    ('I', 'bVII', 'IV', 'I'): 'I-bVII-IV (Mixolydian vamp)',
    ('i', 'iv', 'v'): 'i-iv-v (Natural minor)',
    ('I', 'IV', 'vi', 'V'): 'I-IV-vi-V (Modern pop)',
    ('vi', 'IV', 'I', 'V'): 'vi-IV-I-V (Axis progression)',
    ('I', 'V', 'vi', 'iii', 'IV', 'I', 'IV', 'V'): 'Pachelbel Canon progression',
}


def analyze_chord_intervals(chord: dict) -> List[dict]:
    """
    Analyze the intervals within a single chord.
    Returns list of dicts with note, semitones_from_root, interval_name.
    """
    result = []
    root_semitone = chord['root_semitone']
    use_flats = chord['use_flats']

    for i, iv in enumerate(chord['intervals_semitones']):
        note_sem = (root_semitone + iv) % 12
        note_name = semitone_to_note(note_sem, use_flats)
        label = chord['interval_labels'][i] if i < len(chord['interval_labels']) else SEMITONE_TO_INTERVAL.get(iv % 12, '?')

        result.append({
            'note': note_name,
            'semitones': iv,
            'interval': label,
        })
    return result


def detect_key(chords: List[dict]) -> Tuple[str, str]:
    """
    Attempt to detect the key of a chord progression.
    Returns (key_note, mode) e.g., ('C', 'major') or ('A', 'minor').
    Uses a simple heuristic: score each possible key by how many chord roots
    fall on its scale degrees.
    """
    if not chords:
        return ('C', 'major')

    best_key = 'C'
    best_mode = 'major'
    best_score = -1

    root_semitones = [c['root_semitone'] for c in chords]

    major_qualities = ('maj', 'maj7', 'M7', '7', '9', 'maj9', 'M9', '6',
                        '13', 'maj13', 'add9', 'sus4', 'sus2', 'sus', 'aug', '5')
    minor_qualities = ('m', 'min', 'min7', 'm7', 'm9', 'min9', 'm11', 'min11',
                        'm13', 'min13', 'm6', 'min6', 'mM7', 'minmaj7', 'madd9')

    for key_root in range(12):
        # Check major
        major_scale_notes = set((key_root + s) % 12 for s in MAJOR_SCALE)
        score = sum(1 for r in root_semitones if r in major_scale_notes)
        # Bonus if first chord is major quality and is the tonic
        if root_semitones[0] == key_root and chords[0]['quality'] in major_qualities:
            score += 3
        # Bonus if last chord resolves to tonic
        if root_semitones[-1] == key_root:
            score += 1
        # Bonus for V-I motion (dominant resolution)
        for i in range(len(chords) - 1):
            if root_semitones[i] == (key_root + 7) % 12 and root_semitones[i + 1] == key_root:
                score += 2
        # Bonus for ii-V pattern pointing to this key
        for i in range(len(chords) - 1):
            if root_semitones[i] == (key_root + 2) % 12 and root_semitones[i + 1] == (key_root + 7) % 12:
                score += 2

        if score > best_score:
            best_score = score
            best_key = semitone_to_note(key_root)
            best_mode = 'major'

        # Check minor
        minor_root = key_root
        minor_scale = set((minor_root + s) % 12 for s in [0, 2, 3, 5, 7, 8, 10])
        # Harmonic minor: also accept raised 7th (dominant V chord)
        harmonic_minor_scale = minor_scale | {(minor_root + 11) % 12}
        score_m = sum(1 for r in root_semitones if r in harmonic_minor_scale)
        # Only give first-chord bonus if it's actually a minor quality chord
        if root_semitones[0] == minor_root and chords[0]['quality'] in minor_qualities:
            score_m += 3
        if root_semitones[-1] == minor_root and chords[-1]['quality'] in minor_qualities:
            score_m += 2
        # Bonus for V-i in minor (dominant chord resolving to minor tonic)
        for i in range(len(chords) - 1):
            if (root_semitones[i] == (minor_root + 7) % 12 and
                chords[i]['quality'] in ('7', 'maj', '9', '13') and
                root_semitones[i + 1] == minor_root):
                score_m += 3

        if score_m > best_score:
            best_score = score_m
            best_key = semitone_to_note(minor_root)
            best_mode = 'minor'

    return (best_key, best_mode)


def roman_numeral_analysis(chords: List[dict], key: Optional[str] = None,
                           mode: Optional[str] = None) -> List[dict]:
    """
    Perform Roman numeral analysis on a chord progression.
    Returns list of dicts with chord symbol, roman numeral, scale degree, etc.
    """
    if not chords:
        return []

    if key is None or mode is None:
        key, mode = detect_key(chords)

    key_semitone = note_to_semitone(key)

    if mode == 'minor':
        scale = [0, 2, 3, 5, 7, 8, 10]
    else:
        scale = MAJOR_SCALE

    result = []
    for chord in chords:
        interval = (chord['root_semitone'] - key_semitone) % 12

        # Find closest scale degree
        degree_idx = None
        for i, s in enumerate(scale):
            if s == interval:
                degree_idx = i
                break

        if degree_idx is not None:
            numeral = SCALE_DEGREES[degree_idx]
        else:
            # Chromatic — find closest and add accidental
            for i, s in enumerate(scale):
                if (s - 1) % 12 == interval:
                    numeral = 'b' + SCALE_DEGREES[i]
                    break
                elif (s + 1) % 12 == interval:
                    numeral = '#' + SCALE_DEGREES[i]
                    break
            else:
                numeral = '?'

        # Adjust case for chord quality
        quality = chord['quality']
        is_minor = quality in ('m', 'min', 'min7', 'm7', 'dim', 'm7b5', 'dim7',
                                'm9', 'min9', 'm11', 'min11', 'm13', 'min13',
                                'm6', 'min6', 'mM7', 'minmaj7', 'madd9')
        if is_minor:
            numeral = numeral.lower()

        # Add quality suffix
        quality_suffix = ''
        if quality in ('7', 'aug7'):
            quality_suffix = '7'
        elif quality in ('maj7', 'M7'):
            quality_suffix = 'maj7'
        elif quality in ('m7', 'min7'):
            quality_suffix = '7'
        elif quality in ('dim', ):
            quality_suffix = '\u00b0'  # degree sign
        elif quality in ('dim7', ):
            quality_suffix = '\u00b07'
        elif quality in ('m7b5', ):
            quality_suffix = '\u00f87'  # ø7
        elif quality in ('aug', ):
            quality_suffix = '+'
        elif quality in ('sus4', 'sus'):
            quality_suffix = 'sus4'
        elif quality in ('sus2', ):
            quality_suffix = 'sus2'
        elif quality in ('9', ):
            quality_suffix = '9'
        elif quality in ('maj9', 'M9'):
            quality_suffix = 'maj9'
        elif quality in ('m9', 'min9'):
            quality_suffix = '9'
        elif quality in ('11', ):
            quality_suffix = '11'
        elif quality in ('13', ):
            quality_suffix = '13'

        result.append({
            'symbol': chord['symbol'],
            'roman': numeral + quality_suffix,
            'degree': interval,
            'key': key,
            'mode': mode,
        })

    return result


def root_movement_analysis(chords: List[dict]) -> List[dict]:
    """
    Analyze the interval movement between successive chord roots.
    Returns list of dicts describing the movement from each chord to the next.
    """
    movements = []
    for i in range(len(chords) - 1):
        from_root = chords[i]['root_semitone']
        to_root = chords[i + 1]['root_semitone']

        ascending = (to_root - from_root) % 12
        descending = (from_root - to_root) % 12

        # Use the smaller interval
        if ascending <= descending:
            semitones = ascending
            direction = 'up'
        else:
            semitones = descending
            direction = 'down'

        interval_name = SEMITONE_TO_ROOT_INTERVAL.get(semitones, '?')

        movements.append({
            'from': chords[i]['symbol'],
            'to': chords[i + 1]['symbol'],
            'direction': direction,
            'semitones': semitones,
            'interval': interval_name,
            'description': f"{direction} {interval_name}",
        })

    return movements


def detect_patterns(chords: List[dict], key: Optional[str] = None,
                    mode: Optional[str] = None) -> List[str]:
    """Detect common chord progression patterns."""
    if not chords:
        return []

    analysis = roman_numeral_analysis(chords, key, mode)
    # Extract simplified roman numerals (without quality suffixes for matching)
    romans = []
    for a in analysis:
        r = a['roman']
        # Strip quality suffixes for pattern matching
        for suffix in ['maj13', 'maj11', 'maj9', 'maj7', 'sus4', 'sus2',
                        '\u00f87', '\u00b07', '13', '11', '9', '7', '+', '\u00b0']:
            if r.endswith(suffix):
                r = r[:-len(suffix)]
                break
        romans.append(r)

    found = []
    romans_tuple = tuple(romans)

    # Check exact match
    if romans_tuple in COMMON_PATTERNS:
        found.append(COMMON_PATTERNS[romans_tuple])

    # Check subsequences (length 3+)
    for length in range(3, len(romans) + 1):
        for start in range(len(romans) - length + 1):
            sub = tuple(romans[start:start + length])
            if sub in COMMON_PATTERNS and COMMON_PATTERNS[sub] not in found:
                found.append(COMMON_PATTERNS[sub])

    return found


# --- Diatonic chords ---

# Diatonic triad qualities for each scale degree
DIATONIC_MAJOR_TRIADS = [
    ('I', 'maj'), ('ii', 'm'), ('iii', 'm'), ('IV', 'maj'),
    ('V', 'maj'), ('vi', 'm'), ('vii\u00b0', 'dim'),
]

DIATONIC_MINOR_TRIADS = [
    ('i', 'm'), ('ii\u00b0', 'dim'), ('III', 'maj'), ('iv', 'm'),
    ('V', 'maj'), ('VI', 'maj'), ('vii\u00b0', 'dim'),
]

# Diatonic 7th chord qualities for each scale degree
DIATONIC_MAJOR_7THS = [
    ('I', 'maj7'), ('ii', 'm7'), ('iii', 'm7'), ('IV', 'maj7'),
    ('V', '7'), ('vi', 'm7'), ('vii\u00f8', 'm7b5'),
]

DIATONIC_MINOR_7THS = [
    ('i', 'mM7'), ('ii\u00f8', 'm7b5'), ('III', 'maj7'), ('iv', 'm7'),
    ('V', '7'), ('VI', 'maj7'), ('vii\u00b0', 'dim7'),
]

# Diatonic 9th chords
DIATONIC_MAJOR_9THS = [
    ('I', 'maj9'), ('ii', 'm9'), ('iii', 'm7'), ('IV', 'maj9'),
    ('V', '9'), ('vi', 'm9'), ('vii\u00f8', 'm7b5'),
]
# iii stays m7 (diatonic 9th is b9, uncommon), vii stays m7b5 (same reason)

DIATONIC_MINOR_9THS = [
    ('i', 'mM7'), ('ii\u00f8', 'm7b5'), ('III', 'maj9'), ('iv', 'm9'),
    ('V', '9'), ('VI', 'maj9'), ('vii\u00b0', 'dim7'),
]
# i stays mM7 (9 works but mM9 not in formulas), ii/vii stay as-is (b9)

# Diatonic sus4 chords
DIATONIC_MAJOR_SUS4 = [
    ('I', 'sus4'), ('II', 'sus4'), ('III', 'sus4'), ('IV', 'sus4'),
    ('V', 'sus4'), ('VI', 'sus4'), ('VII', 'sus4'),
]

DIATONIC_MINOR_SUS4 = [
    ('i', 'sus4'), ('II', 'sus4'), ('III', 'sus4'), ('iv', 'sus4'),
    ('V', 'sus4'), ('VI', 'sus4'), ('VII', 'sus4'),
]

# Diatonic sus2 chords
DIATONIC_MAJOR_SUS2 = [
    ('I', 'sus2'), ('II', 'sus2'), ('III', 'sus2'), ('IV', 'sus2'),
    ('V', 'sus2'), ('VI', 'sus2'), ('VII', 'sus2'),
]

DIATONIC_MINOR_SUS2 = [
    ('i', 'sus2'), ('II', 'sus2'), ('III', 'sus2'), ('iv', 'sus2'),
    ('V', 'sus2'), ('VI', 'sus2'), ('VII', 'sus2'),
]

# Diatonic add9 chords
DIATONIC_MAJOR_ADD9 = [
    ('I', 'add9'), ('ii', 'madd9'), ('iii', 'm'), ('IV', 'add9'),
    ('V', 'add9'), ('vi', 'madd9'), ('vii\u00b0', 'dim'),
]
# iii and vii get b9 diatonically, so fall back to simpler forms

DIATONIC_MINOR_ADD9 = [
    ('i', 'madd9'), ('ii\u00b0', 'dim'), ('III', 'add9'), ('iv', 'madd9'),
    ('V', 'add9'), ('VI', 'add9'), ('vii\u00b0', 'dim'),
]

# Diatonic 6th chords
DIATONIC_MAJOR_6THS = [
    ('I', '6'), ('ii', 'm6'), ('iii', 'm'), ('IV', '6'),
    ('V', '6'), ('vi', 'm6'), ('vii\u00b0', 'dim'),
]
# iii gets b6 diatonically (dim interval), vii same — fall back

DIATONIC_MINOR_6THS = [
    ('i', 'm6'), ('ii\u00b0', 'dim'), ('III', '6'), ('iv', 'm6'),
    ('V', '6'), ('VI', '6'), ('vii\u00b0', 'dim'),
]

# Lookup table for chord_type -> (major_degrees, minor_degrees)
DIATONIC_TABLES = {
    'triad': (DIATONIC_MAJOR_TRIADS, DIATONIC_MINOR_TRIADS),
    '7th':   (DIATONIC_MAJOR_7THS, DIATONIC_MINOR_7THS),
    '9th':   (DIATONIC_MAJOR_9THS, DIATONIC_MINOR_9THS),
    'sus4':  (DIATONIC_MAJOR_SUS4, DIATONIC_MINOR_SUS4),
    'sus2':  (DIATONIC_MAJOR_SUS2, DIATONIC_MINOR_SUS2),
    'add9':  (DIATONIC_MAJOR_ADD9, DIATONIC_MINOR_ADD9),
    '6th':   (DIATONIC_MAJOR_6THS, DIATONIC_MINOR_6THS),
}

# Scale definitions: name -> list of semitone intervals from root
SCALES = {
    'Major (Ionian)':       [0, 2, 4, 5, 7, 9, 11],
    'Dorian':               [0, 2, 3, 5, 7, 9, 10],
    'Phrygian':             [0, 1, 3, 5, 7, 8, 10],
    'Lydian':               [0, 2, 4, 6, 7, 9, 11],
    'Mixolydian':           [0, 2, 4, 5, 7, 9, 10],
    'Natural Minor (Aeolian)': [0, 2, 3, 5, 7, 8, 10],
    'Locrian':              [0, 1, 3, 5, 6, 8, 10],
    'Harmonic Minor':       [0, 2, 3, 5, 7, 8, 11],
    'Melodic Minor':        [0, 2, 3, 5, 7, 9, 11],
    'Blues':                 [0, 3, 5, 6, 7, 10],
    'Minor Pentatonic':     [0, 3, 5, 7, 10],
    'Major Pentatonic':     [0, 2, 4, 7, 9],
    'Whole Tone':           [0, 2, 4, 6, 8, 10],
    'Diminished (H-W)':     [0, 1, 3, 4, 6, 7, 9, 10],
    'Diminished (W-H)':     [0, 2, 3, 5, 6, 8, 9, 11],
    'Altered':              [0, 1, 3, 4, 6, 8, 10],
    'Lydian Dominant':      [0, 2, 4, 6, 7, 9, 10],
    'Phrygian Dominant':    [0, 1, 4, 5, 7, 8, 10],
    'Bebop Dominant':       [0, 2, 4, 5, 7, 9, 10, 11],
}


def get_diatonic_chords(key: str, mode: str = 'major', chord_type: str = '7th') -> List[dict]:
    """
    Return the diatonic chords for a given key.
    chord_type: 'triad', '7th', '9th', 'sus4', 'sus2', 'add9', '6th'.
    Each entry: {numeral, root, quality, symbol}
    """
    key_semitone = note_to_semitone(key)
    use_flats = 'b' in key or key in ('F', 'D', 'G', 'C')

    if mode == 'minor':
        scale = [0, 2, 3, 5, 7, 8, 10]
    else:
        scale = MAJOR_SCALE

    major_table, minor_table = DIATONIC_TABLES.get(chord_type, DIATONIC_TABLES['7th'])
    degrees = minor_table if mode == 'minor' else major_table

    result = []
    for i, (numeral, quality) in enumerate(degrees):
        root_sem = (key_semitone + scale[i % len(scale)]) % 12
        root_note = semitone_to_note(root_sem, use_flats)
        symbol = root_note + (quality if quality != 'maj' else '')
        result.append({
            'numeral': numeral,
            'root': root_note,
            'quality': quality,
            'symbol': symbol,
        })
    return result


# --- Chord substitutions ---

def suggest_substitutions(chord: dict, key: str = None, mode: str = None) -> List[dict]:
    """
    Suggest chord substitutions for a given chord.
    Returns list of {type, symbol, reason}.
    """
    root_sem = chord['root_semitone']
    quality = chord['quality']
    use_flats = chord['use_flats']
    subs = []

    # Tritone substitution (for dominant 7th chords)
    if quality in ('7', '9', '13', '7#9', '7b9', '7#11', '7b13', 'alt'):
        tri_root = (root_sem + 6) % 12
        tri_note = semitone_to_note(tri_root, use_flats)
        subs.append({
            'type': 'Tritone sub',
            'symbol': f'{tri_note}7',
            'reason': f'Same tritone (3rd/7th swap), resolves down by half step',
        })

    # Relative minor/major swap
    if quality in ('maj', 'maj7', 'M7', 'maj9', 'M9', '6', 'add9'):
        rel_minor = (root_sem + 9) % 12
        rel_note = semitone_to_note(rel_minor, use_flats)
        subs.append({
            'type': 'Relative minor',
            'symbol': f'{rel_note}m7',
            'reason': 'Shares 3 of 4 chord tones',
        })
    elif quality in ('m', 'min', 'm7', 'min7', 'm9', 'min9'):
        rel_major = (root_sem + 3) % 12
        rel_note = semitone_to_note(rel_major, use_flats)
        subs.append({
            'type': 'Relative major',
            'symbol': f'{rel_note}maj7',
            'reason': 'Shares 3 of 4 chord tones',
        })

    # Minor ii-V substitution: for dominant chords, suggest ii-V pair
    if quality in ('7', '9', '13'):
        ii_root = (root_sem + 5) % 12  # a 4th below = a 5th above the target
        ii_note = semitone_to_note(ii_root, use_flats)
        subs.append({
            'type': 'ii-V expansion',
            'symbol': f'{ii_note}m7 → {chord["root"]}7',
            'reason': 'Expand dominant into ii-V motion',
        })

    # Diminished passing chord (for dom7)
    if quality in ('7', '9'):
        dim_root = (root_sem + 1) % 12
        dim_note = semitone_to_note(dim_root, use_flats)
        subs.append({
            'type': 'Diminished approach',
            'symbol': f'{dim_note}dim7',
            'reason': 'Chromatic approach from above, shares 3 tones with dominant',
        })

    # Modal interchange: borrow from parallel minor/major
    if quality in ('maj', 'maj7', 'M7') and key:
        key_sem = note_to_semitone(key)
        degree = (root_sem - key_sem) % 12
        if degree == 0:  # tonic
            subs.append({
                'type': 'Modal interchange',
                'symbol': f'{chord["root"]}m',
                'reason': 'Borrowed from parallel minor — adds color',
            })

    # Dominant substitution: any dom7 can be approached by its V/V
    if quality in ('7', '9', '13'):
        secondary_dom = (root_sem + 7) % 12
        sec_note = semitone_to_note(secondary_dom, use_flats)
        subs.append({
            'type': 'Secondary dominant',
            'symbol': f'{sec_note}7 → {chord["root"]}7',
            'reason': 'V/V — dominant of the dominant',
        })

    return subs


# --- Scale suggestions ---

def suggest_scales(chord: dict) -> List[dict]:
    """
    Suggest scales that work over a given chord.
    Returns list of {scale, root, notes, reason}.
    """
    root_sem = chord['root_semitone']
    chord_sems = set((root_sem + iv) % 12 for iv in chord['intervals_semitones'])
    use_flats = chord['use_flats']
    quality = chord['quality']
    root_note = chord['root']

    suggestions = []

    # Quality-based primary suggestions (most idiomatic choices first)
    primary = _primary_scales_for_quality(quality)

    for scale_name in primary:
        if scale_name in SCALES:
            scale_sems = set((root_sem + s) % 12 for s in SCALES[scale_name])
            notes = [semitone_to_note((root_sem + s) % 12, use_flats) for s in SCALES[scale_name]]
            suggestions.append({
                'scale': f'{root_note} {scale_name}',
                'notes': ' '.join(notes),
                'reason': 'Primary choice for this chord quality',
            })

    # Also find all scales where every chord tone is present
    for scale_name, intervals in SCALES.items():
        # Try the scale rooted on the chord root
        scale_sems = set((root_sem + s) % 12 for s in intervals)
        if chord_sems <= scale_sems:
            entry_name = f'{root_note} {scale_name}'
            if not any(s['scale'] == entry_name for s in suggestions):
                notes = [semitone_to_note((root_sem + s) % 12, use_flats) for s in intervals]
                suggestions.append({
                    'scale': entry_name,
                    'notes': ' '.join(notes),
                    'reason': 'Contains all chord tones',
                })

    return suggestions


def _primary_scales_for_quality(quality: str) -> List[str]:
    """Return the most idiomatic scale choices for a chord quality."""
    q = quality.lower() if quality not in ('M7', 'M9') else quality

    if q in ('maj', 'maj7', 'M7', 'maj9', 'M9', '6', 'add9', 'maj13'):
        return ['Major (Ionian)', 'Lydian']
    elif q in ('7', '9', '13'):
        return ['Mixolydian', 'Lydian Dominant', 'Bebop Dominant', 'Blues']
    elif q in ('m', 'min', 'm7', 'min7', 'm9', 'min9', 'm11', 'min11', 'm13', 'min13'):
        return ['Dorian', 'Natural Minor (Aeolian)', 'Minor Pentatonic']
    elif q in ('m7b5',):
        return ['Locrian']
    elif q in ('dim', 'dim7'):
        return ['Diminished (H-W)']
    elif q in ('alt', '7#9', '7b9', '7b13'):
        return ['Altered', 'Phrygian Dominant', 'Diminished (H-W)']
    elif q in ('7#11',):
        return ['Lydian Dominant']
    elif q in ('mm7', 'minmaj7'):
        return ['Melodic Minor', 'Harmonic Minor']
    elif q in ('aug', '7#5', 'aug7'):
        return ['Whole Tone']
    elif q in ('sus4', 'sus', 'sus2'):
        return ['Mixolydian', 'Major (Ionian)']
    elif q in ('5',):
        return ['Major (Ionian)', 'Minor Pentatonic']
    else:
        return ['Major (Ionian)']


# --- Circle of Fifths ---

# Keys in order of fifths (clockwise from top)
CIRCLE_OF_FIFTHS_MAJOR = ['C', 'G', 'D', 'A', 'E', 'B', 'F#/Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F']
CIRCLE_OF_FIFTHS_MINOR = ['Am', 'Em', 'Bm', 'F#m', 'C#m', 'G#m/Abm', 'Ebm', 'Bbm', 'Fm', 'Cm', 'Gm', 'Dm']
CIRCLE_OF_FIFTHS_SHARPS_FLATS = [
    '0', '1\u266f', '2\u266f', '3\u266f', '4\u266f', '5\u266f', '6\u266f/6\u266d',
    '5\u266d', '4\u266d', '3\u266d', '2\u266d', '1\u266d'
]


def render_circle_of_fifths(current_key: str = 'C', current_mode: str = 'major',
                             figsize=(6, 6)) -> 'plt.Figure':
    """
    Render a Circle of Fifths diagram with the current key highlighted.
    Returns a matplotlib Figure.
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize, subplot_kw={'projection': 'polar'})

    n = 12
    angles = [np.pi / 2 - (2 * np.pi * i / n) for i in range(n)]  # start at top, clockwise

    # Normalize current key for matching
    current_key_norm = current_key.replace('#', '\u266f').replace('b', '\u266d') if len(current_key) > 1 else current_key

    # Draw segments
    segment_width = 2 * np.pi / n
    outer_radius = 1.0
    inner_radius = 0.65
    center_radius = 0.4

    for i in range(n):
        angle = angles[i]
        theta_start = angle - segment_width / 2
        theta_range = np.linspace(theta_start, theta_start + segment_width, 30)

        # Check if this is the highlighted key
        major_key = CIRCLE_OF_FIFTHS_MAJOR[i]
        minor_key = CIRCLE_OF_FIFTHS_MINOR[i]

        is_major_match = (current_mode == 'major' and
                          (current_key in major_key.split('/') or current_key_norm in major_key))
        is_minor_match = (current_mode == 'minor' and
                          (current_key + 'm' in minor_key.split('/') or
                           current_key_norm + 'm' in minor_key))

        # Outer segment (major keys)
        if is_major_match:
            ax.fill_between(theta_range, inner_radius, outer_radius,
                            color='#E74C3C', alpha=0.3)
        elif is_minor_match:
            ax.fill_between(theta_range, center_radius, inner_radius,
                            color='#E74C3C', alpha=0.3)

        # Draw segment borders
        ax.plot(theta_range, [outer_radius] * len(theta_range), 'k-', linewidth=0.5)
        ax.plot(theta_range, [inner_radius] * len(theta_range), 'k-', linewidth=0.5)
        ax.plot(theta_range, [center_radius] * len(theta_range), 'k-', linewidth=0.3)
        ax.plot([theta_start, theta_start], [center_radius, outer_radius], 'k-', linewidth=0.5)

        # Major key label (outer ring)
        major_color = '#E74C3C' if is_major_match else '#2C3E50'
        major_weight = 'bold' if is_major_match else 'normal'
        ax.text(angle, (outer_radius + inner_radius) / 2, major_key,
                ha='center', va='center', fontsize=10, fontweight=major_weight,
                color=major_color)

        # Minor key label (inner ring)
        minor_color = '#E74C3C' if is_minor_match else '#666'
        minor_weight = 'bold' if is_minor_match else 'normal'
        ax.text(angle, (inner_radius + center_radius) / 2, minor_key,
                ha='center', va='center', fontsize=7, fontweight=minor_weight,
                color=minor_color)

        # Sharps/flats label (center area)
        ax.text(angle, center_radius * 0.55, CIRCLE_OF_FIFTHS_SHARPS_FLATS[i],
                ha='center', va='center', fontsize=6, color='#999')

    # Close the last segment border
    last_start = angles[0] - segment_width / 2 + 2 * np.pi
    ax.plot([angles[0] + segment_width / 2, angles[0] + segment_width / 2],
            [center_radius, outer_radius], 'k-', linewidth=0.5)

    ax.set_ylim(0, outer_radius + 0.15)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines['polar'].set_visible(False)
    ax.set_title('Circle of Fifths', fontsize=14, fontweight='bold', pad=20)

    fig.tight_layout()
    return fig
