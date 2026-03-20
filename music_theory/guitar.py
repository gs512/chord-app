"""
Guitar voicing generation and fretboard diagram rendering.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import List, Optional, Tuple
from .chords import parse_chord, note_to_semitone, semitone_to_note

# Standard tuning: string 6 (low E) to string 1 (high E)
STANDARD_TUNING = [40, 45, 50, 55, 59, 64]  # MIDI notes: E2 A2 D3 G3 B3 E4
TUNING_NOTES = ['E', 'A', 'D', 'G', 'B', 'E']
TUNING_SEMITONES = [note_to_semitone(n) for n in TUNING_NOTES]  # [4, 9, 2, 7, 11, 4]

# Pre-defined voicing database: chord_key -> list of voicings
# Each voicing is a list of 6 values: fret number per string, -1 = muted, 0 = open
VOICING_DB = {
    # Major open chords
    ('C', 'maj'):   [[(-1, 0, 3, 2, 0, 1, 0)]],
    ('D', 'maj'):   [(-1, -1, 0, 2, 3, 2)],
    ('E', 'maj'):   [(0, 2, 2, 1, 0, 0)],
    ('G', 'maj'):   [(3, 2, 0, 0, 0, 3)],
    ('A', 'maj'):   [(-1, 0, 2, 2, 2, 0)],
    # Minor open chords
    ('A', 'm'):     [(-1, 0, 2, 2, 1, 0)],
    ('D', 'm'):     [(-1, -1, 0, 2, 3, 1)],
    ('E', 'm'):     [(0, 2, 2, 0, 0, 0)],
    # Seventh chords
    ('A', '7'):     [(-1, 0, 2, 0, 2, 0)],
    ('B', '7'):     [(-1, 2, 1, 2, 0, 2)],
    ('C', '7'):     [(-1, 3, 2, 3, 1, 0)],
    ('D', '7'):     [(-1, -1, 0, 2, 1, 2)],
    ('E', '7'):     [(0, 2, 0, 1, 0, 0)],
    ('G', '7'):     [(3, 2, 0, 0, 0, 1)],
    # Major 7
    ('C', 'maj7'):  [(-1, 3, 2, 0, 0, 0)],
    ('D', 'maj7'):  [(-1, -1, 0, 2, 2, 2)],
    ('E', 'maj7'):  [(0, 2, 1, 1, 0, 0)],
    ('G', 'maj7'):  [(3, 2, 0, 0, 0, 2)],
    ('A', 'maj7'):  [(-1, 0, 2, 1, 2, 0)],
    # Minor 7
    ('A', 'm7'):    [(-1, 0, 2, 0, 1, 0)],
    ('D', 'm7'):    [(-1, -1, 0, 2, 1, 1)],
    ('E', 'm7'):    [(0, 2, 0, 0, 0, 0)],
    # Diminished
    ('B', 'dim'):   [(-1, 2, 0, 1, 0, -1)],
    # sus chords
    ('A', 'sus4'):  [(-1, 0, 2, 2, 3, 0)],
    ('D', 'sus4'):  [(-1, -1, 0, 2, 3, 3)],
    ('E', 'sus4'):  [(0, 2, 2, 2, 0, 0)],
    ('A', 'sus2'):  [(-1, 0, 2, 2, 0, 0)],
    ('D', 'sus2'):  [(-1, -1, 0, 2, 3, 0)],
}


def generate_voicing(chord: dict) -> List[int]:
    """
    Generate a guitar voicing for the given chord.
    Returns list of 6 fret numbers (-1 = muted, 0 = open).
    """
    root = chord['root']
    quality = chord['quality']

    # Check voicing database first
    key = (root, quality)
    if key in VOICING_DB:
        voicing = VOICING_DB[key]
        if isinstance(voicing[0], list) or isinstance(voicing[0], tuple):
            v = voicing[0]
            if isinstance(v[0], tuple):
                return list(v[0])
            return list(v)
        return list(voicing)

    # Generate a barre chord voicing algorithmically
    return _generate_barre_voicing(chord)


def _generate_barre_voicing(chord: dict) -> List[int]:
    """Generate a guitar voicing by finding playable positions on the fretboard."""
    root_semitone = chord['root_semitone']
    chord_semitones = set((root_semitone + iv) % 12 for iv in chord['intervals_semitones'])
    bass_semitone = note_to_semitone(chord['bass']) if chord.get('bass') else root_semitone

    # For extended chords (5+ notes), also try dropping the P5 (common practice)
    tone_sets = [chord_semitones]
    if len(chord['intervals_semitones']) >= 5:
        p5 = (root_semitone + 7) % 12
        if p5 in chord_semitones:
            tone_sets.append(chord_semitones - {p5})

    best_voicing = None
    best_score = -1

    for chord_sems in tone_sets:
        for root_string in [0, 1]:
            open_semitone = TUNING_SEMITONES[root_string]
            root_fret = (bass_semitone - open_semitone) % 12

            fret_options = [root_fret]
            if root_fret <= 2:
                fret_options.append(root_fret + 12)

            for base_fret in fret_options:
                if base_fret > 12:
                    continue

                voicing = [-1] * 6
                voicing[root_string] = base_fret

                for s in range(root_string + 1, 6):
                    open_sem = TUNING_SEMITONES[s]
                    best_fret = -1
                    best_dist = 99

                    low = max(0, base_fret - 1)
                    high = base_fret + 4

                    for fret in range(low, high + 1):
                        note_sem = (open_sem + fret) % 12
                        if note_sem in chord_sems:
                            dist = abs(fret - base_fret)
                            if dist < best_dist:
                                best_dist = dist
                                best_fret = fret

                    voicing[s] = best_fret

                # Mute any strings that ended up with non-chord tones
                for s in range(6):
                    if voicing[s] >= 0:
                        note = (TUNING_SEMITONES[s] + voicing[s]) % 12
                        if note not in chord_sems:
                            voicing[s] = -1

                # Calculate score
                fretted = [f for f in voicing if f > 0]
                span = (max(fretted) - min(fretted)) if fretted else 0
                if span > 4:
                    continue

                played_notes = set()
                for s, f in enumerate(voicing):
                    if f >= 0:
                        played_notes.add((TUNING_SEMITONES[s] + f) % 12)

                coverage = len(played_notes & chord_sems)
                strings_played = sum(1 for f in voicing if f >= 0)
                has_root = any(
                    (TUNING_SEMITONES[s] + f) % 12 == root_semitone
                    for s, f in enumerate(voicing) if f >= 0
                )

                # Prefer: more chord tones covered, more strings, lower position,
                # root in bass, fewer frets to span
                score = (coverage * 15
                         + strings_played * 2
                         - span * 2
                         + (8 if has_root else 0)
                         - base_fret)  # prefer lower positions

                if score > best_score:
                    best_score = score
                    best_voicing = list(voicing)

    return best_voicing or [-1, -1, -1, -1, -1, -1]


def generate_shell_voicing(chord: dict) -> List[int]:
    """
    Generate a shell voicing (root + 3rd + 7th only, 3 notes on 3 strings).
    Two forms: root on string 6 or string 5.
    Returns the most compact voicing.
    """
    root_sem = chord['root_semitone']
    intervals = chord['intervals_semitones']

    # Find the 3rd and 7th intervals
    third_sem = None
    seventh_sem = None
    for iv in intervals:
        iv_mod = iv % 12
        if iv_mod in (3, 4) and third_sem is None:  # m3 or M3
            third_sem = (root_sem + iv) % 12
        elif iv_mod in (10, 11) and seventh_sem is None:  # b7 or M7
            seventh_sem = (root_sem + iv) % 12

    # If no 7th (e.g. triad), use 5th; if no 3rd (e.g. sus), use 4th or 2nd
    if third_sem is None:
        for iv in intervals:
            if iv % 12 == 5:  # P4 (sus4)
                third_sem = (root_sem + iv) % 12
                break
            elif iv % 12 == 2:  # M2 (sus2)
                third_sem = (root_sem + iv) % 12
                break
    if seventh_sem is None:
        for iv in intervals:
            if iv % 12 == 7:  # P5
                seventh_sem = (root_sem + iv) % 12
                break

    if third_sem is None or seventh_sem is None:
        # Fallback: use full voicing algorithm
        return generate_voicing(chord)

    shell_tones = {root_sem, third_sem, seventh_sem}

    best_voicing = None
    best_score = -1

    # Shell voicings: root on string 6 (strings 6,5,4) or root on string 5 (strings 5,4,3)
    for root_str, string_set in [(0, [0, 1, 2]), (1, [1, 2, 3])]:
        open_sem = TUNING_SEMITONES[string_set[0]]
        root_fret = (root_sem - open_sem) % 12

        for base_fret in [root_fret, root_fret + 12] if root_fret <= 2 else [root_fret]:
            if base_fret > 12:
                continue

            voicing = [-1] * 6
            voicing[string_set[0]] = base_fret

            # Assign 3rd and 7th to the other two strings
            remaining_tones = [third_sem, seventh_sem]
            remaining_strings = string_set[1:]

            # Try both assignments, pick the more compact one
            for assignment in [(0, 1), (1, 0)]:
                v = list(voicing)
                ok = True
                for idx, tone_idx in enumerate(assignment):
                    s = remaining_strings[idx]
                    target = remaining_tones[tone_idx]
                    open_s = TUNING_SEMITONES[s]
                    fret = -1
                    best_dist = 99
                    for f in range(max(0, base_fret - 2), base_fret + 4):
                        if (open_s + f) % 12 == target:
                            d = abs(f - base_fret)
                            if d < best_dist:
                                best_dist = d
                                fret = f
                    if fret < 0:
                        ok = False
                        break
                    v[s] = fret

                if not ok:
                    continue

                fretted = [f for f in v if f > 0]
                span = (max(fretted) - min(fretted)) if fretted else 0
                if span > 4:
                    continue

                score = -span - base_fret + (10 if base_fret <= 7 else 0)
                if score > best_score:
                    best_score = score
                    best_voicing = v

    return best_voicing or generate_voicing(chord)


def voicing_to_notes(voicing: List[int]) -> List[Optional[str]]:
    """Convert a voicing to note names per string."""
    notes = []
    for s, fret in enumerate(voicing):
        if fret < 0:
            notes.append(None)
        else:
            semitone = (TUNING_SEMITONES[s] + fret) % 12
            notes.append(semitone_to_note(semitone))
    return notes


def voicing_to_tab(chord_symbol: str, voicing: List[int]) -> str:
    """Generate ASCII tablature for a single chord voicing."""
    string_names = ['e', 'B', 'G', 'D', 'A', 'E']
    lines = []
    for i in range(5, -1, -1):  # high E to low E display order reversed for tab
        fret = voicing[5 - i]  # reverse mapping
    # Actually, voicing[0] = string 6 (low E), voicing[5] = string 1 (high E)
    # Tab displays from high e on top to low E on bottom
    lines = []
    for i in range(5, -1, -1):
        fret = voicing[i]
        name = string_names[5 - i]
        if fret < 0:
            fret_str = 'X'
        else:
            fret_str = str(fret)
        lines.append(f"{name}|--{fret_str}--")
    return '\n'.join(lines)


def render_fretboard(chord: dict, voicing: List[int], figsize=(3, 4)) -> plt.Figure:
    """
    Render a guitar fretboard chord diagram using matplotlib.
    Returns a matplotlib Figure.
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    num_frets_shown = 5
    num_strings = 6

    # Determine fret range
    fretted = [f for f in voicing if f > 0]
    if fretted:
        min_fret = min(fretted)
        if min_fret <= 3:
            start_fret = 1
        else:
            start_fret = min_fret
    else:
        start_fret = 1

    end_fret = start_fret + num_frets_shown - 1

    # Drawing dimensions
    string_spacing = 1.0
    fret_spacing = 1.2
    left_margin = 1.5
    top_margin = 1.5

    # Draw frets (horizontal lines)
    for i in range(num_frets_shown + 1):
        y = top_margin - i * fret_spacing
        width = (num_strings - 1) * string_spacing
        lw = 3 if (i == 0 and start_fret == 1) else 1
        ax.plot([left_margin, left_margin + width], [y, y], 'k-', linewidth=lw)

    # Draw strings (vertical lines)
    for i in range(num_strings):
        x = left_margin + i * string_spacing
        y_top = top_margin
        y_bottom = top_margin - num_frets_shown * fret_spacing
        ax.plot([x, x], [y_top, y_bottom], 'k-', linewidth=0.8)

    # Draw fret numbers
    if start_fret > 1:
        ax.text(left_margin - 0.6, top_margin - 0.5 * fret_spacing,
                str(start_fret), fontsize=10, ha='center', va='center')

    # Draw finger positions, open strings, muted strings
    notes = voicing_to_notes(voicing)
    use_flats = chord.get('use_flats', False)

    for s in range(num_strings):
        x = left_margin + s * string_spacing
        fret = voicing[s]

        if fret < 0:
            # Muted string - X above
            ax.text(x, top_margin + 0.4, 'X', fontsize=11, ha='center', va='center',
                    fontweight='bold', color='gray')
        elif fret == 0:
            # Open string - circle above
            circle = plt.Circle((x, top_margin + 0.4), 0.18, fill=False,
                                edgecolor='black', linewidth=1.5)
            ax.add_patch(circle)
        else:
            # Fretted note - filled circle
            fret_pos = fret - start_fret
            y = top_margin - (fret_pos + 0.5) * fret_spacing
            circle = plt.Circle((x, y), 0.3, fill=True,
                                facecolor='#2C3E50', edgecolor='black', linewidth=1)
            ax.add_patch(circle)
            # Note name inside
            note = notes[s] if notes[s] else ''
            ax.text(x, y, note, fontsize=7, ha='center', va='center',
                    color='white', fontweight='bold')

    # String labels at bottom
    for s in range(num_strings):
        x = left_margin + s * string_spacing
        y = top_margin - num_frets_shown * fret_spacing - 0.5
        ax.text(x, y, TUNING_NOTES[s], fontsize=9, ha='center', va='center', color='#666')

    # Title
    ax.set_title(chord['symbol'], fontsize=14, fontweight='bold', pad=15)

    ax.set_xlim(left_margin - 1, left_margin + (num_strings - 1) * string_spacing + 1)
    ax.set_ylim(top_margin - num_frets_shown * fret_spacing - 1, top_margin + 1)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout()

    return fig


def render_scale_fretboard(scale_name: str, root_note: str, scale_semitones: List[int],
                           figsize=(6, 2.5), use_flats: bool = False) -> 'plt.Figure':
    """
    Render a guitar fretboard showing scale positions across all strings.
    scale_semitones: list of semitone intervals from root (e.g. [0,2,4,5,7,9,11] for major).
    """
    root_sem = note_to_semitone(root_note)
    scale_notes = set((root_sem + s) % 12 for s in scale_semitones)

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    num_frets = 12
    num_strings = 6
    fret_spacing = 1.0
    string_spacing = 0.8
    left_margin = 1.0
    top_margin = 0.5

    # Draw frets (vertical lines for horizontal fretboard)
    for f in range(num_frets + 1):
        x = left_margin + f * fret_spacing
        lw = 2.5 if f == 0 else 0.8
        ax.plot([x, x],
                [top_margin, top_margin + (num_strings - 1) * string_spacing],
                'k-', linewidth=lw)

    # Draw strings (horizontal)
    for s in range(num_strings):
        y = top_margin + s * string_spacing
        ax.plot([left_margin, left_margin + num_frets * fret_spacing],
                [y, y], 'k-', linewidth=0.6)

    # Fret markers (dots at 3,5,7,9,12)
    for dot_fret in [3, 5, 7, 9]:
        x = left_margin + (dot_fret - 0.5) * fret_spacing
        y = top_margin + 2.5 * string_spacing
        ax.plot(x, y, 'o', color='#ccc', markersize=6)
    # Double dot at 12
    for dy in [1.5, 3.5]:
        x = left_margin + 11.5 * fret_spacing
        y = top_margin + dy * string_spacing
        ax.plot(x, y, 'o', color='#ccc', markersize=6)

    # Plot scale notes
    for s in range(num_strings):
        open_sem = TUNING_SEMITONES[s]
        y = top_margin + (num_strings - 1 - s) * string_spacing  # low E at bottom

        for fret in range(num_frets + 1):
            note_sem = (open_sem + fret) % 12
            if note_sem in scale_notes:
                x = left_margin + (fret - 0.5) * fret_spacing if fret > 0 else left_margin - 0.3
                is_root = (note_sem == root_sem)
                color = '#E74C3C' if is_root else '#3498DB'
                size = 12 if is_root else 9
                note_name = semitone_to_note(note_sem, use_flats)
                ax.plot(x, y, 'o', color=color, markersize=size, zorder=3)
                ax.text(x, y, note_name, fontsize=5, ha='center', va='center',
                        color='white', fontweight='bold', zorder=4)

    # String labels
    for s in range(num_strings):
        y = top_margin + (num_strings - 1 - s) * string_spacing
        ax.text(left_margin - 0.7, y, TUNING_NOTES[s], fontsize=8, ha='center', va='center')

    ax.set_title(f'{root_note} {scale_name}', fontsize=11, fontweight='bold')
    ax.set_xlim(left_margin - 1.2, left_margin + num_frets * fret_spacing + 0.5)
    ax.set_ylim(top_margin - 0.8, top_margin + (num_strings - 1) * string_spacing + 0.8)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout()
    return fig


def get_guitar_tab_for_progression(chords: List[dict]) -> str:
    """Generate tab for a full chord progression."""
    voicings = [generate_voicing(c) for c in chords]
    string_names = ['e', 'B', 'G', 'D', 'A', 'E']

    # Build tab lines
    lines = {name: f"{name}|" for name in string_names}

    for chord, voicing in zip(chords, voicings):
        for idx, name in enumerate(string_names):
            s = 5 - idx  # map display order to voicing index
            fret = voicing[s]
            fret_str = 'X' if fret < 0 else str(fret)
            lines[name] += f"--{fret_str:>2}--"
        for name in string_names:
            lines[name] += "|"

    # Header with chord names
    header = "    " + "  ".join(f"{c['symbol']:^6}" for c in chords)
    tab_lines = [header] + [lines[name] for name in string_names]
    return '\n'.join(tab_lines)
