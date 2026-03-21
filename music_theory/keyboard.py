"""
Keyboard voicing generation and piano diagram rendering.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Tuple
from .chords import parse_chord, semitone_to_note, note_to_semitone

# Piano key layout: which semitones are black keys
BLACK_KEY_SEMITONES = {1, 3, 6, 8, 10}  # C#, D#, F#, G#, A#


def generate_keyboard_voicing(chord: dict, base_octave: int = 4) -> List[Tuple[str, int, int]]:
    """
    Generate a keyboard voicing for the chord.
    Returns list of (note_name, octave, midi_note) tuples.
    Root position starting at base_octave.
    """
    root_semitone = chord['root_semitone']
    use_flats = chord['use_flats']
    result = []

    for iv in chord['intervals_semitones']:
        absolute = root_semitone + iv
        octave = base_octave + (absolute // 12)
        midi = absolute + (base_octave * 12) + 12  # approximate MIDI
        note = semitone_to_note(absolute % 12, use_flats)
        result.append((note, octave, midi))

    return result


def generate_shell_keyboard_voicing(chord: dict, base_octave: int = 3) -> List[Tuple[str, int, int]]:
    """
    Generate a shell voicing for keyboard: root in LH (octave 3), 3rd + 7th in RH (octave 4).
    Returns list of (note_name, octave, midi_note) tuples.
    """
    root_sem = chord['root_semitone']
    use_flats = chord['use_flats']
    intervals = chord['intervals_semitones']

    third_iv = None
    seventh_iv = None
    for iv in intervals:
        iv_mod = iv % 12
        if iv_mod in (3, 4) and third_iv is None:
            third_iv = iv
        elif iv_mod in (10, 11) and seventh_iv is None:
            seventh_iv = iv

    # Fallbacks
    if third_iv is None:
        for iv in intervals:
            if iv % 12 in (5, 2):
                third_iv = iv
                break
    if seventh_iv is None:
        for iv in intervals:
            if iv % 12 == 7:
                seventh_iv = iv
                break

    result = []
    # Root in LH
    root_midi = root_sem + (base_octave * 12) + 12
    root_note = semitone_to_note(root_sem, use_flats)
    result.append((root_note, base_octave, root_midi))

    # 3rd and 7th in RH (octave 4), voiced close together
    rh_octave = base_octave + 1
    if third_iv is not None:
        sem3 = (root_sem + third_iv) % 12
        midi3 = sem3 + (rh_octave * 12) + 12
        if midi3 <= root_midi:
            midi3 += 12
        note3 = semitone_to_note(sem3, use_flats)
        result.append((note3, midi3 // 12 - 1, midi3))

    if seventh_iv is not None:
        sem7 = (root_sem + seventh_iv) % 12
        midi7 = sem7 + (rh_octave * 12) + 12
        if midi7 <= root_midi:
            midi7 += 12
        # Keep 7th close to 3rd (within an octave above the 3rd)
        if third_iv is not None and midi7 < midi3:
            midi7 += 12
        note7 = semitone_to_note(sem7, use_flats)
        result.append((note7, midi7 // 12 - 1, midi7))

    return result


def generate_keyboard_inversions(chord: dict, base_octave: int = 4) -> List[List[Tuple[str, int, int]]]:
    """
    Generate all inversions of the keyboard voicing.
    Returns list of voicings: root position, 1st inversion, 2nd inversion, etc.
    """
    root_voicing = generate_keyboard_voicing(chord, base_octave)
    if len(root_voicing) <= 1:
        return [root_voicing]

    inversions = [root_voicing]
    current = list(root_voicing)

    for _ in range(len(root_voicing) - 1):
        # Move the bottom note up an octave
        bottom = current[0]
        note_name, octave, midi = bottom
        new_note = (note_name, octave + 1, midi + 12)
        current = current[1:] + [new_note]
        inversions.append(list(current))

    return inversions


def generate_shell_keyboard_inversions(chord: dict, base_octave: int = 3) -> List[List[Tuple[str, int, int]]]:
    """
    Generate all inversions of the shell keyboard voicing (root + 3rd + 7th).
    """
    root_voicing = generate_shell_keyboard_voicing(chord, base_octave)
    if len(root_voicing) <= 1:
        return [root_voicing]

    inversions = [root_voicing]
    current = list(root_voicing)

    for _ in range(len(root_voicing) - 1):
        bottom = current[0]
        note_name, octave, midi = bottom
        new_note = (note_name, octave + 1, midi + 12)
        current = current[1:] + [new_note]
        inversions.append(list(current))

    return inversions


def voicing_to_text(chord: dict) -> str:
    """Generate text representation of keyboard voicing."""
    voicing = generate_keyboard_voicing(chord)
    notes_str = ', '.join(f"{n}{o}" for n, o, _ in voicing)
    return f"{chord['symbol']}: {notes_str}"


def render_piano(chord: dict, figsize=(6, 2.5), voicing=None) -> plt.Figure:
    """
    Render a piano keyboard diagram highlighting the chord notes.
    Returns a matplotlib Figure.
    If voicing is provided, use it instead of generating a default one.
    """
    if voicing is None:
        voicing = generate_keyboard_voicing(chord)
    use_flats = chord['use_flats']

    # Determine range: cover all notes with padding, minimum 2 octaves
    midi_notes = [m for _, _, m in voicing]
    min_note = min(midi_notes)
    max_note = max(midi_notes)

    # Start at C below the lowest note, end at C above the highest
    start_midi = min_note - (min_note % 12)
    end_midi = max_note - (max_note % 12) + 12

    # Ensure at least 2 octaves for visual clarity
    if end_midi - start_midi < 24:
        center = (min_note + max_note) // 2
        start_midi = center - 12
        start_midi = start_midi - (start_midi % 12)
        end_midi = start_midi + 24

    start_midi = max(36, start_midi)
    num_octaves = (end_midi - start_midi) // 12

    # Pressed keys by absolute MIDI value (not mod 12, to avoid highlighting all octaves)
    pressed_midi = set(m for _, _, m in voicing)
    pressed_labels = {}
    for note, octave, midi in voicing:
        pressed_labels[midi] = note

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # White key dimensions
    white_w = 1.0
    white_h = 4.0
    black_w = 0.6
    black_h = 2.5

    # Map semitone to white key index
    white_key_semitones = [0, 2, 4, 5, 7, 9, 11]  # C D E F G A B
    black_key_positions = {1: 0.7, 3: 1.7, 6: 3.7, 8: 4.7, 10: 5.7}  # relative to octave start

    white_key_idx = 0

    # Draw white keys first
    for octave_offset in range(num_octaves + 1):
        for sem in white_key_semitones:
            absolute_midi = start_midi + octave_offset * 12 + sem
            if absolute_midi >= end_midi + 1:
                break

            x = white_key_idx * white_w
            is_pressed = absolute_midi in pressed_midi

            color = '#4A90D9' if is_pressed else 'white'
            edge_color = '#2C3E50'

            rect = patches.FancyBboxPatch(
                (x, 0), white_w - 0.05, white_h,
                boxstyle="round,pad=0.02",
                facecolor=color, edgecolor=edge_color, linewidth=1
            )
            ax.add_patch(rect)

            if is_pressed:
                label = pressed_labels.get(absolute_midi, semitone_to_note(absolute_midi % 12, use_flats))
                ax.text(x + white_w / 2, 0.6, label,
                        fontsize=8, ha='center', va='center',
                        fontweight='bold', color='white')

            white_key_idx += 1

    total_white = white_key_idx

    # Draw black keys on top
    for octave_offset in range(num_octaves + 1):
        for sem, rel_pos in black_key_positions.items():
            absolute_midi = start_midi + octave_offset * 12 + sem
            if absolute_midi >= end_midi:
                break

            # Calculate x position relative to octave's first white key
            octave_white_start = octave_offset * 7
            x = octave_white_start * white_w + rel_pos

            is_pressed = absolute_midi in pressed_midi
            color = '#4A90D9' if is_pressed else '#2C3E50'

            rect = patches.FancyBboxPatch(
                (x, white_h - black_h), black_w, black_h,
                boxstyle="round,pad=0.02",
                facecolor=color, edgecolor='black', linewidth=1,
                zorder=2
            )
            ax.add_patch(rect)

            if is_pressed:
                label = pressed_labels.get(absolute_midi, semitone_to_note(absolute_midi % 12, use_flats))
                ax.text(x + black_w / 2, white_h - black_h + 0.5, label,
                        fontsize=7, ha='center', va='center',
                        fontweight='bold', color='white', zorder=3)

    ax.set_xlim(-0.2, total_white * white_w + 0.2)
    ax.set_ylim(-0.5, white_h + 0.5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(chord['symbol'], fontsize=14, fontweight='bold', pad=10)
    fig.tight_layout()

    return fig


def render_scale_piano(scale_name: str, root_note: str, scale_semitones: list,
                       use_flats: bool = False, figsize=(6, 2.5)) -> 'plt.Figure':
    """
    Render a 2-octave piano highlighting scale notes.
    Root notes highlighted in red, other scale notes in blue.
    """
    root_sem = note_to_semitone(root_note)
    scale_notes = set((root_sem + s) % 12 for s in scale_semitones)

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    white_w = 1.0
    white_h = 4.0
    black_w = 0.6
    black_h = 2.5

    white_key_semitones = [0, 2, 4, 5, 7, 9, 11]
    black_key_positions = {1: 0.7, 3: 1.7, 6: 3.7, 8: 4.7, 10: 5.7}

    start_midi = (root_sem // 12) * 12 + 60  # Start at C nearest middle C
    start_midi = start_midi - (start_midi % 12)  # Align to C
    num_octaves = 2
    end_midi = start_midi + num_octaves * 12

    white_key_idx = 0

    # White keys
    for octave_offset in range(num_octaves + 1):
        for sem in white_key_semitones:
            absolute_midi = start_midi + octave_offset * 12 + sem
            if absolute_midi >= end_midi + 1:
                break
            note_sem = absolute_midi % 12

            x = white_key_idx * white_w
            in_scale = note_sem in scale_notes
            is_root = note_sem == root_sem

            if is_root:
                color = '#E74C3C'
            elif in_scale:
                color = '#3498DB'
            else:
                color = 'white'

            rect = patches.FancyBboxPatch(
                (x, 0), white_w - 0.05, white_h,
                boxstyle="round,pad=0.02",
                facecolor=color, edgecolor='#2C3E50', linewidth=1
            )
            ax.add_patch(rect)

            if in_scale or is_root:
                label = semitone_to_note(note_sem, use_flats)
                text_color = 'white' if (is_root or in_scale) else 'black'
                ax.text(x + white_w / 2, 0.6, label,
                        fontsize=8, ha='center', va='center',
                        fontweight='bold', color=text_color)

            white_key_idx += 1

    total_white = white_key_idx

    # Black keys
    for octave_offset in range(num_octaves + 1):
        for sem, rel_pos in black_key_positions.items():
            absolute_midi = start_midi + octave_offset * 12 + sem
            if absolute_midi >= end_midi:
                break
            note_sem = absolute_midi % 12

            octave_white_start = octave_offset * 7
            x = octave_white_start * white_w + rel_pos

            in_scale = note_sem in scale_notes
            is_root = note_sem == root_sem

            if is_root:
                color = '#E74C3C'
            elif in_scale:
                color = '#3498DB'
            else:
                color = '#2C3E50'

            rect = patches.FancyBboxPatch(
                (x, white_h - black_h), black_w, black_h,
                boxstyle="round,pad=0.02",
                facecolor=color, edgecolor='black', linewidth=1,
                zorder=2
            )
            ax.add_patch(rect)

            if in_scale or is_root:
                label = semitone_to_note(note_sem, use_flats)
                ax.text(x + black_w / 2, white_h - black_h + 0.5, label,
                        fontsize=7, ha='center', va='center',
                        fontweight='bold', color='white', zorder=3)

    ax.set_xlim(-0.2, total_white * white_w + 0.2)
    ax.set_ylim(-0.5, white_h + 0.5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f'{root_note} {scale_name}', fontsize=12, fontweight='bold', pad=10)
    fig.tight_layout()

    return fig
