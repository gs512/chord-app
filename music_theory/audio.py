"""
Web Audio API playback component for chord voicings.
Generates HTML/JS snippets that can be embedded in Streamlit via st.components.v1.html().
"""

from typing import List
import json


def render_play_button_html(midi_notes: List[int], key_id: str,
                            show_strum: bool = False, height: int = 45) -> str:
    """
    Generate HTML with a Play button (and optional Strum button) that uses
    Web Audio API to play the given MIDI notes as a chord.

    Args:
        midi_notes: List of MIDI note numbers to play.
        key_id: Unique identifier for DOM element IDs.
        show_strum: If True, also show a Strum button (arpeggiated playback).
        height: Height of the HTML component.

    Returns:
        HTML string to embed via st.components.v1.html().
    """
    if not midi_notes:
        return ""

    notes_json = json.dumps(sorted(midi_notes))
    safe_id = key_id.replace(" ", "_").replace("#", "s").replace("/", "_")

    strum_button = ""
    strum_handler = ""
    if show_strum:
        strum_button = f"""
        <button id="strum_{safe_id}" onclick="strumChord_{safe_id}()" style="
            background: #2C3E50; color: white; border: none; border-radius: 6px;
            padding: 6px 14px; cursor: pointer; font-size: 13px; margin-left: 6px;
        ">Strum</button>
        """
        strum_handler = f"""
        function strumChord_{safe_id}() {{
            playNotes_{safe_id}(true);
        }}
        """

    html = f"""
    <div style="display: flex; align-items: center; gap: 4px; padding: 2px 0;">
        <button id="play_{safe_id}" onclick="playChord_{safe_id}()" style="
            background: #4A90D9; color: white; border: none; border-radius: 6px;
            padding: 6px 14px; cursor: pointer; font-size: 13px;
        ">Play</button>
        {strum_button}
    </div>
    <script>
    (function() {{
        const notes_{safe_id} = {notes_json};

        function midiToFreq(midi) {{
            return 440 * Math.pow(2, (midi - 69) / 12);
        }}

        function playNotes_{safe_id}(strum) {{
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            const ctx = new AudioContext();
            const numNotes = notes_{safe_id}.length;
            const gain = 0.25 / Math.max(numNotes, 1);
            const strumDelay = strum ? 0.04 : 0;

            notes_{safe_id}.forEach((midi, i) => {{
                const freq = midiToFreq(midi);
                const startTime = ctx.currentTime + i * strumDelay;

                // Two oscillators for richer sound
                const osc1 = ctx.createOscillator();
                const osc2 = ctx.createOscillator();
                const gainNode = ctx.createGain();

                osc1.type = 'triangle';
                osc2.type = 'sine';
                osc1.frequency.value = freq;
                osc2.frequency.value = freq * 2; // octave harmonic

                osc1.connect(gainNode);
                osc2.connect(gainNode);
                gainNode.connect(ctx.destination);

                // ADSR envelope
                gainNode.gain.setValueAtTime(0, startTime);
                gainNode.gain.linearRampToValueAtTime(gain, startTime + 0.02);       // attack
                gainNode.gain.linearRampToValueAtTime(gain * 0.7, startTime + 0.15); // decay
                gainNode.gain.setValueAtTime(gain * 0.7, startTime + 0.8);           // sustain
                gainNode.gain.linearRampToValueAtTime(0, startTime + 1.8);           // release

                // Harmonic is quieter
                const gainNode2 = ctx.createGain();
                osc2.disconnect();
                osc2.connect(gainNode2);
                gainNode2.connect(ctx.destination);
                gainNode2.gain.setValueAtTime(0, startTime);
                gainNode2.gain.linearRampToValueAtTime(gain * 0.15, startTime + 0.02);
                gainNode2.gain.linearRampToValueAtTime(0, startTime + 1.2);

                osc1.start(startTime);
                osc2.start(startTime);
                osc1.stop(startTime + 2.0);
                osc2.stop(startTime + 1.5);
            }});
        }}

        window.playChord_{safe_id} = function() {{
            playNotes_{safe_id}(false);
        }};

        {strum_handler}

        window.strumChord_{safe_id} = window.strumChord_{safe_id} || function() {{}};
    }})();
    </script>
    """
    return html
