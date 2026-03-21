"""
Chord Voicing & Analysis — Streamlit App
Displays guitar and keyboard voicings, tablature, musical score,
and interval analysis for chords and progressions.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import matplotlib.pyplot as plt

from music_theory.chords import parse_chord, parse_progression, note_to_semitone
from music_theory.guitar import (
    generate_voicing, generate_all_voicings, render_fretboard, voicing_to_tab,
    voicing_to_notes, voicing_to_midi, get_guitar_tab_for_progression,
    generate_shell_voicing, generate_all_shell_voicings, render_scale_fretboard
)
from music_theory.audio import render_play_button_html
from music_theory.keyboard import (
    generate_keyboard_voicing, generate_keyboard_inversions,
    render_piano, voicing_to_text,
    generate_shell_keyboard_voicing, generate_shell_keyboard_inversions,
    render_scale_piano
)
from music_theory.intervals import (
    analyze_chord_intervals, detect_key, roman_numeral_analysis,
    root_movement_analysis, detect_patterns,
    get_diatonic_chords, suggest_substitutions, suggest_scales, SCALES,
    render_circle_of_fifths
)
from music_theory.vexflow_render import (
    render_single_chord_html, render_progression_html,
    render_guitar_tab_html
)
from music_theory.voice_leading import (
    optimize_guitar_voice_leading, optimize_keyboard_voice_leading
)

st.set_page_config(page_title="Chord Voicing & Analysis", layout="wide")

st.title("Chord Voicing & Analysis")


def _nav_buttons(state_key, count, labels=None, compact=False):
    """Render prev/next navigation buttons. Returns current index."""
    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    idx = min(st.session_state[state_key], count - 1)
    st.session_state[state_key] = idx

    if count <= 1:
        if labels and labels[0]:
            st.caption(labels[0])
        return 0

    if compact:
        c1, c2, c3 = st.columns([1, 2, 1])
    else:
        c1, c2, c3 = st.columns([1, 3, 1])

    with c1:
        if st.button("\u25c0", key=f"{state_key}_prev", disabled=(idx <= 0)):
            st.session_state[state_key] = idx - 1
            st.rerun()
    with c2:
        label = labels[idx] if labels else f"{idx+1}/{count}"
        st.markdown(f"<div style='text-align:center;font-size:{'0.8em' if compact else '1em'};padding-top:6px'>{label}</div>", unsafe_allow_html=True)
    with c3:
        if st.button("\u25b6", key=f"{state_key}_next", disabled=(idx >= count - 1)):
            st.session_state[state_key] = idx + 1
            st.rerun()
    return idx


def render_guitar_nav(chord, key_prefix, compact=False):
    """Render a guitar fretboard with voicing navigation arrows."""
    all_v = generate_all_voicings(chord)
    labels = [f"Voicing {i+1}/{len(all_v)}" for i in range(len(all_v))]
    idx = _nav_buttons(f"gv_{key_prefix}", len(all_v), labels, compact=compact)
    voicing = all_v[idx]
    fig = render_fretboard(chord, voicing)
    st.pyplot(fig, use_container_width=False)
    if not compact:
        tab_text = voicing_to_tab(chord['symbol'], voicing)
        st.code(tab_text, language=None)
    notes = voicing_to_notes(voicing)
    notes_display = [n if n else 'X' for n in notes]
    st.caption(f"Notes: {' '.join(notes_display)}")
    midi_notes = voicing_to_midi(voicing)
    if midi_notes:
        html = render_play_button_html(midi_notes, f"gv_{key_prefix}_{idx}", show_strum=True)
        components.html(html, height=45)
    plt.close('all')
    return voicing


def render_keyboard_nav(chord, key_prefix, compact=False, figsize=(6, 2.5)):
    """Render a piano keyboard with inversion navigation arrows."""
    inversions = generate_keyboard_inversions(chord)
    _suffixes = {1: "st", 2: "nd", 3: "rd"}
    labels = ["Root Position"] + [
        f"{i}{_suffixes.get(i, 'th')} Inv." for i in range(1, len(inversions))
    ]
    idx = _nav_buttons(f"ki_{key_prefix}", len(inversions), labels, compact=compact)
    kb_voicing = inversions[idx]
    fig = render_piano(chord, voicing=kb_voicing, figsize=figsize)
    st.pyplot(fig, use_container_width=not compact)
    notes_str = ', '.join(f"{n}{o}" for n, o, _ in kb_voicing)
    st.caption(f"{notes_str}")
    midi_notes = [m for _, _, m in kb_voicing]
    if midi_notes:
        html = render_play_button_html(midi_notes, f"ki_{key_prefix}_{idx}")
        components.html(html, height=45)
    plt.close('all')
    return kb_voicing


def render_shell_guitar_nav(chord, key_prefix, compact=False):
    """Render a guitar shell voicing fretboard with navigation arrows."""
    all_v = generate_all_shell_voicings(chord)
    labels = [f"Shell {i+1}/{len(all_v)}" for i in range(len(all_v))]
    idx = _nav_buttons(f"sg_{key_prefix}", len(all_v), labels, compact=compact)
    voicing = all_v[idx]
    fig = render_fretboard(chord, voicing)
    st.pyplot(fig, use_container_width=False)
    if not compact:
        tab_text = voicing_to_tab(chord['symbol'] + ' (shell)', voicing)
        st.code(tab_text, language=None)
    notes = voicing_to_notes(voicing)
    notes_display = [n if n else 'X' for n in notes]
    st.caption(f"Notes: {' '.join(notes_display)}")
    midi_notes = voicing_to_midi(voicing)
    if midi_notes:
        html = render_play_button_html(midi_notes, f"sg_{key_prefix}_{idx}", show_strum=True)
        components.html(html, height=45)
    plt.close('all')
    return voicing


def render_shell_keyboard_nav(chord, key_prefix, compact=False, figsize=(6, 2.5)):
    """Render a piano shell voicing with inversion navigation arrows."""
    inversions = generate_shell_keyboard_inversions(chord)
    _suffixes = {1: "st", 2: "nd", 3: "rd"}
    labels = ["Root Position"] + [
        f"{i}{_suffixes.get(i, 'th')} Inv." for i in range(1, len(inversions))
    ]
    idx = _nav_buttons(f"sk_{key_prefix}", len(inversions), labels, compact=compact)
    kb_voicing = inversions[idx]
    fig = render_piano(chord, voicing=kb_voicing, figsize=figsize)
    st.pyplot(fig, use_container_width=not compact)
    notes_str = ', '.join(f"{n}{o}" for n, o, _ in kb_voicing)
    st.caption(f"{notes_str}")
    midi_notes = [m for _, _, m in kb_voicing]
    if midi_notes:
        html = render_play_button_html(midi_notes, f"sk_{key_prefix}_{idx}")
        components.html(html, height=45)
    plt.close('all')
    return kb_voicing

# --- Input Section ---
input_mode = st.radio("Mode", ["Single Chord", "Chord Progression"], horizontal=True)

if input_mode == "Single Chord":
    chord_input = st.text_input(
        "Enter a chord symbol",
        value="Cmaj7",
        placeholder="e.g. Cmaj7, Dm7b5, G7#9, F/A",
        help="Supports: maj, min, 7, maj7, m7, dim, aug, sus2, sus4, 6, 9, 11, 13, add9, m7b5, alt, slash chords"
    )

    if chord_input:
        try:
            chord = parse_chord(chord_input)
        except ValueError as e:
            st.error(f"Could not parse chord: {e}")
            st.stop()

        st.header(f"{chord['symbol']}")

        # Tabs for different views
        tab_guitar, tab_keyboard, tab_score, tab_intervals, tab_subs, tab_scales = st.tabs(
            ["Guitar", "Keyboard", "Score", "Intervals", "Substitutions", "Scales"]
        )

        with tab_guitar:
            st.subheader("Full Voicing")
            voicing = render_guitar_nav(chord, f"single_{chord_input}")

            st.subheader("Shell Voicing (Root + 3rd + 7th)")
            render_shell_guitar_nav(chord, f"single_shell_{chord_input}")

        with tab_keyboard:
            st.subheader("Full Voicing")
            render_keyboard_nav(chord, f"single_{chord_input}")

            st.subheader("Shell Voicing (Root + 3rd + 7th)")
            render_shell_keyboard_nav(chord, f"single_shell_{chord_input}")

        with tab_score:
            st.subheader("Musical Score")
            html = render_single_chord_html(chord)
            components.html(html, height=280, scrolling=False)

        with tab_intervals:
            st.subheader("Interval Analysis")
            intervals = analyze_chord_intervals(chord)
            df = pd.DataFrame(intervals)
            df.columns = ['Note', 'Semitones from Root', 'Interval']
            st.table(df)

            st.caption(f"Root: **{chord['root']}** | Quality: **{chord['quality']}** | "
                       f"Formula: {' '.join(chord['interval_labels'])}")

        with tab_subs:
            st.subheader("Chord Substitutions")
            subs = suggest_substitutions(chord)
            if subs:
                for si, s in enumerate(subs):
                    sub_sym = s['symbol'].split('\u2192')[0].strip().split(' ')[0].strip()
                    with st.expander(f"{s['type']}: {s['symbol']}", expanded=True):
                        st.caption(s['reason'])
                        try:
                            sub_chord = parse_chord(sub_sym)
                            col_g, col_k = st.columns(2)
                            with col_g:
                                render_guitar_nav(sub_chord, f"sub_{chord_input}_{si}", compact=True)
                            with col_k:
                                render_keyboard_nav(sub_chord, f"sub_kb_{chord_input}_{si}", compact=True)
                        except ValueError:
                            pass
            else:
                st.info("No common substitutions for this chord type.")

        with tab_scales:
            st.subheader("Scales for Improvisation")
            scales = suggest_scales(chord)
            if scales:
                for i, s in enumerate(scales):
                    label = "Primary" if s['reason'].startswith('Primary') else "Compatible"
                    with st.expander(f"{s['scale']} ({label})", expanded=(i < 3)):
                        st.code(s['notes'], language=None)
                        st.caption(s['reason'])
                        # Extract scale name and root for diagram
                        parts = s['scale'].split(' ', 1)
                        if len(parts) == 2:
                            s_root, s_name = parts
                            if s_name in SCALES:
                                col_g, col_k = st.columns(2)
                                with col_g:
                                    fig = render_scale_fretboard(s_name, s_root, SCALES[s_name],
                                                                 use_flats=chord['use_flats'])
                                    st.pyplot(fig, use_container_width=True)
                                with col_k:
                                    fig = render_scale_piano(s_name, s_root, SCALES[s_name],
                                                             use_flats=chord['use_flats'])
                                    st.pyplot(fig, use_container_width=True)
                                plt.close('all')
            else:
                st.info("No scale suggestions available.")

else:
    # Chord Progression mode
    prog_input = st.text_input(
        "Enter a chord progression",
        value="Dm7 | G7 | Cmaj7 | Am7",
        placeholder="e.g. Dm7 | G7 | Cmaj7 | Am7",
        help="Separate chords with | , - or spaces"
    )

    key_col, mode_col = st.columns(2)
    with key_col:
        selected_key = st.selectbox(
            "Key (auto-detected if left as Auto)",
            ["Auto"] + [f"{n}" for n in
                        ['C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F',
                         'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B']]
        )
    with mode_col:
        selected_mode = st.selectbox("Mode", ["Auto", "major", "minor"])

    if prog_input:
        try:
            chords = parse_progression(prog_input)
        except ValueError as e:
            st.error(f"Could not parse progression: {e}")
            st.stop()

        if not chords:
            st.warning("No chords found.")
            st.stop()

        # Determine key
        if selected_key == "Auto" or selected_mode == "Auto":
            auto_key, auto_mode = detect_key(chords)
            key = auto_key if selected_key == "Auto" else selected_key
            mode = auto_mode if selected_mode == "Auto" else selected_mode
        else:
            key = selected_key
            mode = selected_mode

        st.header(f"Progression in {key} {mode}")
        st.write(" — ".join(c['symbol'] for c in chords))

        tab_guitar, tab_keyboard, tab_score, tab_intervals, tab_diatonic, tab_subs, tab_scales = st.tabs(
            ["Guitar", "Keyboard", "Score", "Intervals", "Diatonic", "Substitutions", "Scales"]
        )

        with tab_guitar:
            vl_guitar = st.checkbox("Optimize Voice Leading", key="vl_guitar")
            current_prog_g = "|".join(c['symbol'] for c in chords)
            if vl_guitar:
                prev_prog = st.session_state.get("vl_guitar_prog", "")
                if not st.session_state.get("vl_guitar_applied", False) or prev_prog != current_prog_g:
                    optimal_g = optimize_guitar_voice_leading(chords)
                    for i, chord in enumerate(chords):
                        st.session_state[f"gv_prog_g_{i}_{chord['symbol']}"] = optimal_g[i]
                    st.session_state["vl_guitar_applied"] = True
                    st.session_state["vl_guitar_prog"] = current_prog_g
            else:
                st.session_state["vl_guitar_applied"] = False

            cols = st.columns(min(len(chords), 4))
            prog_voicings = []
            for i, chord in enumerate(chords):
                with cols[i % len(cols)]:
                    v = render_guitar_nav(chord, f"prog_g_{i}_{chord['symbol']}", compact=True)
                    prog_voicings.append(v)

            st.subheader("Combined Tablature")
            tab_text = get_guitar_tab_for_progression(chords)
            st.code(tab_text, language=None)

            # VexFlow guitar tab
            st.subheader("Guitar Tab (Notation)")
            tab_html = render_guitar_tab_html(chords, prog_voicings)
            components.html(tab_html, height=280, scrolling=True)

        with tab_keyboard:
            vl_keyboard = st.checkbox("Optimize Voice Leading", key="vl_keyboard")
            current_prog_k = "|".join(c['symbol'] for c in chords)
            if vl_keyboard:
                prev_prog = st.session_state.get("vl_keyboard_prog", "")
                if not st.session_state.get("vl_keyboard_applied", False) or prev_prog != current_prog_k:
                    optimal_k = optimize_keyboard_voice_leading(chords)
                    for i, chord in enumerate(chords):
                        st.session_state[f"ki_prog_k_{i}_{chord['symbol']}"] = optimal_k[i]
                    st.session_state["vl_keyboard_applied"] = True
                    st.session_state["vl_keyboard_prog"] = current_prog_k
            else:
                st.session_state["vl_keyboard_applied"] = False

            cols = st.columns(min(len(chords), 4))
            for i, chord in enumerate(chords):
                with cols[i % len(cols)]:
                    render_keyboard_nav(chord, f"prog_k_{i}_{chord['symbol']}", compact=True, figsize=(4, 1.5))

        with tab_score:
            st.subheader("Musical Score")
            html = render_progression_html(chords)
            components.html(html, height=280, scrolling=True)

        with tab_intervals:
            st.subheader("Chord Interval Analysis")
            for chord in chords:
                intervals = analyze_chord_intervals(chord)
                with st.expander(f"{chord['symbol']}", expanded=True):
                    df = pd.DataFrame(intervals)
                    df.columns = ['Note', 'Semitones', 'Interval']
                    st.table(df)

            st.subheader("Roman Numeral Analysis")
            analysis = roman_numeral_analysis(chords, key, mode)
            roman_df = pd.DataFrame(analysis)
            roman_df = roman_df[['symbol', 'roman', 'degree']]
            roman_df.columns = ['Chord', 'Roman Numeral', 'Scale Degree (semitones)']
            st.table(roman_df)

            st.subheader("Root Movement")
            movements = root_movement_analysis(chords)
            if movements:
                move_df = pd.DataFrame(movements)
                move_df = move_df[['from', 'to', 'description', 'semitones']]
                move_df.columns = ['From', 'To', 'Movement', 'Semitones']
                st.table(move_df)

            st.subheader("Pattern Recognition")
            patterns = detect_patterns(chords, key, mode)
            if patterns:
                for p in patterns:
                    st.success(f"Detected: **{p}**")
            else:
                st.info("No common patterns detected in this progression.")

        with tab_diatonic:
            # Circle of Fifths
            st.subheader("Circle of Fifths")
            cof_col1, cof_col2 = st.columns([1, 1])
            with cof_col1:
                fig = render_circle_of_fifths(key, mode)
                st.pyplot(fig, use_container_width=True)
                plt.close('all')
            with cof_col2:
                st.markdown(f"**Detected key:** {key} {mode}")
                st.markdown("The highlighted segment shows the current key. "
                            "Major keys are on the outer ring, relative minor keys on the inner ring.")

            # Diatonic chords
            st.subheader(f"Diatonic Chords in {key} {mode}")
            chord_type = st.radio("Chord type", ["Triads", "7th Chords"],
                                  horizontal=True, key="dia_chord_type")
            ct = 'triad' if chord_type == "Triads" else '7th'
            diatonic = get_diatonic_chords(key, mode, chord_type=ct)
            dia_df = pd.DataFrame(diatonic)
            dia_df.columns = ['Numeral', 'Root', 'Quality', 'Chord']
            st.table(dia_df)

            # Highlight which progression chords are diatonic vs chromatic
            prog_roots = {c['root_semitone'] for c in chords}
            dia_roots = {note_to_semitone(d['root']) for d in diatonic}
            chromatic = [c['symbol'] for c in chords if c['root_semitone'] not in dia_roots]
            if chromatic:
                st.warning(f"Non-diatonic chords: {', '.join(chromatic)}")
            else:
                st.success("All chords are diatonic to the key.")

            # Show fretboard/keyboard for each diatonic chord
            st.subheader("Diatonic Chord Voicings")
            cols = st.columns(min(len(diatonic), 4))
            for i, d in enumerate(diatonic):
                with cols[i % len(cols)]:
                    try:
                        dc = parse_chord(d['symbol'])
                        st.markdown(f"**{d['numeral']}** — {d['symbol']}")
                        render_guitar_nav(dc, f"dia_g_{ct}_{i}_{d['symbol']}", compact=True)
                        render_keyboard_nav(dc, f"dia_k_{ct}_{i}_{d['symbol']}", compact=True, figsize=(4, 1.5))
                    except ValueError:
                        st.caption(d['symbol'])

        with tab_subs:
            st.subheader("Substitution Suggestions")
            for ci, chord in enumerate(chords):
                subs = suggest_substitutions(chord, key, mode)
                if subs:
                    with st.expander(f"{chord['symbol']}", expanded=True):
                        for si, s in enumerate(subs):
                            sub_sym = s['symbol'].split('\u2192')[0].strip().split(' ')[0].strip()
                            st.markdown(f"**{s['type']}:** `{s['symbol']}`")
                            st.caption(s['reason'])
                            try:
                                sub_chord = parse_chord(sub_sym)
                                col_g, col_k = st.columns(2)
                                with col_g:
                                    render_guitar_nav(sub_chord, f"psub_g_{ci}_{si}_{sub_sym}", compact=True)
                                with col_k:
                                    render_keyboard_nav(sub_chord, f"psub_k_{ci}_{si}_{sub_sym}", compact=True, figsize=(4, 1.5))
                            except ValueError:
                                pass

        with tab_scales:
            st.subheader("Scale Suggestions per Chord")
            for chord in chords:
                scales = suggest_scales(chord)
                if scales:
                    with st.expander(f"{chord['symbol']}", expanded=False):
                        for s in scales[:3]:
                            label = "Primary" if s['reason'].startswith('Primary') else "Compatible"
                            st.markdown(f"**{s['scale']}** ({label})")
                            st.code(s['notes'], language=None)
                            parts = s['scale'].split(' ', 1)
                            if len(parts) == 2:
                                s_root, s_name = parts
                                if s_name in SCALES:
                                    col_g, col_k = st.columns(2)
                                    with col_g:
                                        fig = render_scale_fretboard(s_name, s_root, SCALES[s_name],
                                                                     use_flats=chord['use_flats'])
                                        st.pyplot(fig, use_container_width=True)
                                    with col_k:
                                        fig = render_scale_piano(s_name, s_root, SCALES[s_name],
                                                                 use_flats=chord['use_flats'])
                                        st.pyplot(fig, use_container_width=True)
                                    plt.close('all')
