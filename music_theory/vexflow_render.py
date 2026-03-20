"""
Generate VexFlow HTML/JS for rendering musical score notation.
Embeds in Streamlit via st.components.v1.html().
"""

from typing import List
from .chords import parse_chord, semitone_to_note

# Map note names to VexFlow key notation
# VexFlow uses: "c/4", "d#/4", "bb/4" etc.
NOTE_TO_VEXFLOW = {
    'C': 'c', 'C#': 'c#', 'Db': 'db',
    'D': 'd', 'D#': 'd#', 'Eb': 'eb',
    'E': 'e', 'F': 'f',
    'F#': 'f#', 'Gb': 'gb',
    'G': 'g', 'G#': 'g#', 'Ab': 'ab',
    'A': 'a', 'A#': 'a#', 'Bb': 'bb',
    'B': 'b',
}


def chord_to_vexflow_keys(chord: dict, base_octave: int = 4) -> List[str]:
    """Convert chord notes to VexFlow key strings like 'c/4', 'e/4', 'g/4'."""
    root_semitone = chord['root_semitone']
    use_flats = chord['use_flats']
    keys = []

    for iv in chord['intervals_semitones']:
        absolute = root_semitone + iv
        octave = base_octave + (absolute // 12)
        note_sem = absolute % 12
        note_name = semitone_to_note(note_sem, use_flats)
        vex_note = NOTE_TO_VEXFLOW.get(note_name, note_name.lower())
        keys.append(f"{vex_note}/{octave}")

    return keys


def chord_to_guitar_tab_positions(chord: dict, voicing: List[int]) -> List[str]:
    """Convert guitar voicing to VexFlow TabNote positions."""
    positions = []
    for string_idx in range(6):
        fret = voicing[string_idx]
        if fret >= 0:
            # VexFlow tab strings are 1-indexed, 1=high E, 6=low E
            vex_string = 6 - string_idx
            positions.append(f"{{str: {vex_string}, fret: {fret}}}")
    return positions


def render_single_chord_html(chord: dict, width: int = 400, height: int = 250) -> str:
    """Generate HTML with VexFlow rendering a single chord on treble clef."""
    keys = chord_to_vexflow_keys(chord)
    keys_js = ', '.join(f'"{k}"' for k in keys)

    html = f"""
    <div id="vf-single" style="margin: 0 auto;"></div>
    <script src="https://cdn.jsdelivr.net/npm/vexflow@4.2.2/build/cjs/vexflow.js"></script>
    <script>
    (function() {{
        const VF = Vex.Flow;
        const div = document.getElementById('vf-single');
        const renderer = new VF.Renderer(div, VF.Renderer.Backends.SVG);
        renderer.resize({width}, {height});
        const context = renderer.getContext();
        context.setFont('Arial', 10);

        const stave = new VF.Stave(10, 40, {width - 30});
        stave.addClef('treble');
        stave.setContext(context).draw();

        const keys = [{keys_js}];
        const note = new VF.StaveNote({{
            keys: keys,
            duration: 'w',
            clef: 'treble'
        }});

        // Add accidentals
        keys.forEach((key, i) => {{
            const notePart = key.split('/')[0];
            if (notePart.includes('#')) {{
                note.addModifier(new VF.Accidental('#'), i);
            }} else if (notePart.includes('b')) {{
                note.addModifier(new VF.Accidental('b'), i);
            }}
        }});

        const voice = new VF.Voice({{ num_beats: 4, beat_value: 4 }});
        voice.addTickables([note]);

        new VF.Formatter().joinVoices([voice]).format([voice], {width - 80});
        voice.draw(context, stave);

        // Add chord symbol text
        context.setFont('Arial', 14, 'bold');
        context.fillText('{chord["symbol"]}', 15, 35);
    }})();
    </script>
    """
    return html


def render_progression_html(chords: List[dict], width: int = 800, height: int = 250) -> str:
    """Generate HTML with VexFlow rendering a chord progression on treble clef."""
    if not chords:
        return "<p>No chords to display</p>"

    # Build notes array in JS
    notes_js_parts = []
    for chord in chords:
        keys = chord_to_vexflow_keys(chord)
        keys_js = ', '.join(f'"{k}"' for k in keys)

        # Build accidentals
        accidentals = []
        for i, k in enumerate(keys):
            note_part = k.split('/')[0]
            if '#' in note_part:
                accidentals.append(f"{{index: {i}, type: '#'}}")
            elif 'b' in note_part:
                accidentals.append(f"{{index: {i}, type: 'b'}}")

        acc_js = '[' + ', '.join(accidentals) + ']'
        notes_js_parts.append(f"{{keys: [{keys_js}], accidentals: {acc_js}, symbol: '{chord['symbol']}'}}")

    notes_js = ',\n            '.join(notes_js_parts)
    stave_width = max(width - 40, len(chords) * 120)

    html = f"""
    <div id="vf-progression" style="margin: 0 auto; overflow-x: auto;"></div>
    <script src="https://cdn.jsdelivr.net/npm/vexflow@4.2.2/build/cjs/vexflow.js"></script>
    <script>
    (function() {{
        const VF = Vex.Flow;
        const div = document.getElementById('vf-progression');
        const renderer = new VF.Renderer(div, VF.Renderer.Backends.SVG);
        renderer.resize({stave_width + 40}, {height});
        const context = renderer.getContext();
        context.setFont('Arial', 10);

        const stave = new VF.Stave(10, 40, {stave_width});
        stave.addClef('treble');
        stave.addTimeSignature('{len(chords)}/4');
        stave.setContext(context).draw();

        const chordData = [
            {notes_js}
        ];

        const notes = chordData.map(cd => {{
            const note = new VF.StaveNote({{
                keys: cd.keys,
                duration: 'q',
                clef: 'treble'
            }});
            cd.accidentals.forEach(acc => {{
                note.addModifier(new VF.Accidental(acc.type), acc.index);
            }});
            return note;
        }});

        const voice = new VF.Voice({{ num_beats: {len(chords)}, beat_value: 4 }});
        voice.addTickables(notes);

        new VF.Formatter().joinVoices([voice]).format([voice], {stave_width - 80});
        voice.draw(context, stave);

        // Add chord symbols above
        chordData.forEach((cd, i) => {{
            const note = notes[i];
            const bb = note.getBoundingBox();
            if (bb) {{
                context.setFont('Arial', 11, 'bold');
                context.fillText(cd.symbol, bb.getX(), 35);
            }}
        }});
    }})();
    </script>
    """
    return html


def render_guitar_tab_html(chords: List[dict], voicings: List[List[int]],
                           width: int = 800, height: int = 250) -> str:
    """Generate HTML with VexFlow rendering guitar tablature."""
    if not chords or not voicings:
        return "<p>No tab to display</p>"

    tab_notes_js = []
    for chord, voicing in zip(chords, voicings):
        positions = []
        for string_idx in range(6):
            fret = voicing[string_idx]
            if fret >= 0:
                vex_string = 6 - string_idx
                positions.append(f"{{str: {vex_string}, fret: {fret}}}")
        pos_js = ', '.join(positions)
        tab_notes_js.append(f"{{positions: [{pos_js}], symbol: '{chord['symbol']}'}}")

    notes_js = ',\n            '.join(tab_notes_js)
    stave_width = max(width - 40, len(chords) * 120)

    html = f"""
    <div id="vf-tab" style="margin: 0 auto; overflow-x: auto;"></div>
    <script src="https://cdn.jsdelivr.net/npm/vexflow@4.2.2/build/cjs/vexflow.js"></script>
    <script>
    (function() {{
        const VF = Vex.Flow;
        const div = document.getElementById('vf-tab');
        const renderer = new VF.Renderer(div, VF.Renderer.Backends.SVG);
        renderer.resize({stave_width + 40}, {height});
        const context = renderer.getContext();

        const stave = new VF.TabStave(10, 40, {stave_width});
        stave.addClef('tab');
        stave.setContext(context).draw();

        const tabData = [
            {notes_js}
        ];

        const notes = tabData.map(td => {{
            return new VF.TabNote({{
                positions: td.positions,
                duration: 'q'
            }});
        }});

        const voice = new VF.Voice({{ num_beats: {len(chords)}, beat_value: 4 }});
        voice.addTickables(notes);

        new VF.Formatter().joinVoices([voice]).format([voice], {stave_width - 80});
        voice.draw(context, stave);

        // Add chord symbols
        tabData.forEach((td, i) => {{
            const note = notes[i];
            const bb = note.getBoundingBox();
            if (bb) {{
                context.setFont('Arial', 11, 'bold');
                context.fillText(td.symbol, bb.getX(), 35);
            }}
        }});
    }})();
    </script>
    """
    return html
