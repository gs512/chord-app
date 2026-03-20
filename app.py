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
    generate_voicing, render_fretboard, voicing_to_tab,
    voicing_to_notes, get_guitar_tab_for_progression,
    generate_shell_voicing, render_scale_fretboard
)
from music_theory.keyboard import (
    generate_keyboard_voicing, render_piano, voicing_to_text,
    generate_shell_keyboard_voicing, render_scale_piano
)
from music_theory.intervals import (
    analyze_chord_intervals, detect_key, roman_numeral_analysis,
    root_movement_analysis, detect_patterns,
    get_diatonic_chords, suggest_substitutions, suggest_scales, SCALES
)
from music_theory.vexflow_render import (
    render_single_chord_html, render_progression_html,
    render_guitar_tab_html
)

st.set_page_config(page_title="Chord Voicing & Analysis", layout="wide")

st.title("Chord Voicing & Analysis")

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
            voicing = generate_voicing(chord)
            shell = generate_shell_voicing(chord)

            st.subheader("Full Voicing")
            col1, col2 = st.columns([1, 2])
            with col1:
                fig = render_fretboard(chord, voicing)
                st.pyplot(fig, use_container_width=False)
            with col2:
                tab_text = voicing_to_tab(chord['symbol'], voicing)
                st.code(tab_text, language=None)
                notes = voicing_to_notes(voicing)
                notes_display = [n if n else 'X' for n in notes]
                st.caption(f"Notes: {' '.join(notes_display)}")

            st.subheader("Shell Voicing (Root + 3rd + 7th)")
            col1, col2 = st.columns([1, 2])
            with col1:
                fig = render_fretboard(chord, shell)
                st.pyplot(fig, use_container_width=False)
            with col2:
                tab_text = voicing_to_tab(chord['symbol'] + ' (shell)', shell)
                st.code(tab_text, language=None)
                shell_notes = voicing_to_notes(shell)
                shell_display = [n if n else 'X' for n in shell_notes]
                st.caption(f"Notes: {' '.join(shell_display)}")

        with tab_keyboard:
            st.subheader("Full Voicing")
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = render_piano(chord)
                st.pyplot(fig, use_container_width=False)
            with col2:
                voicing_text = voicing_to_text(chord)
                st.code(voicing_text, language=None)
                kb_voicing = generate_keyboard_voicing(chord)
                notes_str = ', '.join(f"{n}{o}" for n, o, _ in kb_voicing)
                st.caption(f"Notes: {notes_str}")

            st.subheader("Shell Voicing (Root + 3rd + 7th)")
            shell_kb = generate_shell_keyboard_voicing(chord)
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = render_piano(chord, voicing=shell_kb)
                st.pyplot(fig, use_container_width=False)
            with col2:
                shell_notes_str = ', '.join(f"{n}{o}" for n, o, _ in shell_kb)
                st.code(f"{chord['symbol']} (shell): {shell_notes_str}", language=None)
                st.caption(f"LH: root | RH: 3rd + 7th")

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
                for s in subs:
                    # Extract the first chord symbol (handle "Cm7 → G7" style)
                    sub_sym = s['symbol'].split('→')[0].strip().split(' ')[0].strip()
                    with st.expander(f"{s['type']}: {s['symbol']}", expanded=True):
                        st.caption(s['reason'])
                        try:
                            sub_chord = parse_chord(sub_sym)
                            sub_v = generate_voicing(sub_chord)
                            col_g, col_k = st.columns(2)
                            with col_g:
                                fig = render_fretboard(sub_chord, sub_v)
                                st.pyplot(fig, use_container_width=False)
                            with col_k:
                                fig = render_piano(sub_chord)
                                st.pyplot(fig, use_container_width=False)
                            plt.close('all')
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
            # Fretboard diagrams in columns
            voicings = [generate_voicing(c) for c in chords]
            cols = st.columns(min(len(chords), 4))
            for i, (chord, voicing) in enumerate(zip(chords, voicings)):
                with cols[i % len(cols)]:
                    fig = render_fretboard(chord, voicing)
                    st.pyplot(fig, use_container_width=False)

            st.subheader("Combined Tablature")
            tab_text = get_guitar_tab_for_progression(chords)
            st.code(tab_text, language=None)

            # VexFlow guitar tab
            st.subheader("Guitar Tab (Notation)")
            tab_html = render_guitar_tab_html(chords, voicings)
            components.html(tab_html, height=280, scrolling=True)

        with tab_keyboard:
            cols = st.columns(min(len(chords), 4))
            for i, chord in enumerate(chords):
                with cols[i % len(cols)]:
                    fig = render_piano(chord)
                    st.pyplot(fig, use_container_width=False)
                    st.caption(voicing_to_text(chord))

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
            st.subheader(f"Diatonic Chords in {key} {mode}")
            diatonic = get_diatonic_chords(key, mode)
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
                        dv = generate_voicing(dc)
                        st.markdown(f"**{d['numeral']}** — {d['symbol']}")
                        fig = render_fretboard(dc, dv)
                        st.pyplot(fig, use_container_width=False)
                        fig = render_piano(dc, figsize=(4, 1.5))
                        st.pyplot(fig, use_container_width=True)
                        plt.close('all')
                    except ValueError:
                        st.caption(d['symbol'])

        with tab_subs:
            st.subheader("Substitution Suggestions")
            for chord in chords:
                subs = suggest_substitutions(chord, key, mode)
                if subs:
                    with st.expander(f"{chord['symbol']}", expanded=True):
                        for s in subs:
                            sub_sym = s['symbol'].split('→')[0].strip().split(' ')[0].strip()
                            st.markdown(f"**{s['type']}:** `{s['symbol']}`")
                            st.caption(s['reason'])
                            try:
                                sub_chord = parse_chord(sub_sym)
                                sub_v = generate_voicing(sub_chord)
                                col_g, col_k = st.columns(2)
                                with col_g:
                                    fig = render_fretboard(sub_chord, sub_v)
                                    st.pyplot(fig, use_container_width=False)
                                with col_k:
                                    fig = render_piano(sub_chord, figsize=(4, 1.5))
                                    st.pyplot(fig, use_container_width=True)
                                plt.close('all')
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
