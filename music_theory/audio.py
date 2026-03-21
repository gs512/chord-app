"""
Web Audio API playback component for chord voicings.
Generates HTML/JS snippets that can be embedded in Streamlit via st.components.v1.html().
"""

from typing import List
import json

# Shared JS function — each iframe is isolated so no naming conflicts.
_PLAY_JS = """
function playNotes(notes, strum) {
    var AC = window.AudioContext || window.webkitAudioContext;
    var ctx = new AC();
    ctx.resume().then(function() {
        var g = 0.25 / Math.max(notes.length, 1);
        var sd = strum ? 0.04 : 0;
        notes.forEach(function(midi, i) {
            var freq = 440 * Math.pow(2, (midi - 69) / 12);
            var t = ctx.currentTime + i * sd;
            var o1 = ctx.createOscillator();
            var o2 = ctx.createOscillator();
            var gn = ctx.createGain();
            o1.type = 'triangle';
            o2.type = 'sine';
            o1.frequency.value = freq;
            o2.frequency.value = freq * 2;
            o1.connect(gn);
            o2.connect(gn);
            gn.connect(ctx.destination);
            gn.gain.setValueAtTime(0, t);
            gn.gain.linearRampToValueAtTime(g, t + 0.02);
            gn.gain.linearRampToValueAtTime(g * 0.7, t + 0.15);
            gn.gain.setValueAtTime(g * 0.7, t + 0.8);
            gn.gain.linearRampToValueAtTime(0, t + 1.8);
            var gn2 = ctx.createGain();
            o2.disconnect();
            o2.connect(gn2);
            gn2.connect(ctx.destination);
            gn2.gain.setValueAtTime(0, t);
            gn2.gain.linearRampToValueAtTime(g * 0.15, t + 0.02);
            gn2.gain.linearRampToValueAtTime(0, t + 1.2);
            o1.start(t); o2.start(t);
            o1.stop(t + 2.0); o2.stop(t + 1.5);
        });
    });
}
"""


def render_play_button_html(midi_notes: List[int], key_id: str,
                            show_strum: bool = False) -> str:
    """
    Generate HTML with Play/Strum buttons using Web Audio API.
    Each iframe gets the same generic playNotes function (no namespace conflicts).
    """
    if not midi_notes:
        return ""

    notes_json = json.dumps(sorted(midi_notes))

    strum_btn = ""
    if show_strum:
        strum_btn = (
            '<button onclick="playNotes(N,true)" style="'
            'background:#2C3E50;color:#fff;border:none;border-radius:6px;'
            'padding:6px 14px;cursor:pointer;font-size:13px;margin-left:6px'
            '">Strum</button>'
        )

    return f"""<div style="display:flex;align-items:center;gap:4px;padding:2px 0">
<button onclick="playNotes(N,false)" style="background:#4A90D9;color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:13px">Play</button>
{strum_btn}
</div>
<script>
var N={notes_json};
{_PLAY_JS}
</script>"""
