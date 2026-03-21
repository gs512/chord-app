"""
Voice leading optimization for chord progressions.
Selects voicings across a progression to minimize total movement between chords.
"""

from typing import List, Callable, Any, Tuple


def guitar_voicing_distance(v1: List[int], v2: List[int]) -> int:
    """
    Calculate voice leading distance between two guitar voicings.
    String-by-string fret distance. Muted-to-fretted penalty = 7.
    """
    total = 0
    for s in range(6):
        f1, f2 = v1[s], v2[s]
        if f1 < 0 and f2 < 0:
            continue
        elif f1 < 0 or f2 < 0:
            total += 7
        else:
            total += abs(f1 - f2)
    return total


def keyboard_voicing_distance(v1: List[Tuple], v2: List[Tuple]) -> int:
    """
    Calculate voice leading distance between two keyboard voicings.
    Each voicing is a list of (note_name, octave, midi_note) tuples.
    Pairs voices positionally by pitch, sums MIDI differences.
    """
    midi1 = sorted(m for _, _, m in v1)
    midi2 = sorted(m for _, _, m in v2)

    total = 0
    max_len = max(len(midi1), len(midi2))
    for i in range(max_len):
        if i < len(midi1) and i < len(midi2):
            total += abs(midi1[i] - midi2[i])
        else:
            total += 12  # penalty for unmatched voice
    return total


def optimize_voice_leading(all_voicings: List[List[Any]],
                           distance_fn: Callable[[Any, Any], int]) -> List[int]:
    """
    Find voicing indices that minimize total voice leading distance.
    Viterbi-style DP: O(n * m^2).

    Args:
        all_voicings: all_voicings[i] is the list of possible voicings for chord i.
        distance_fn: function(voicing_a, voicing_b) -> int distance.

    Returns:
        List of ints: optimal voicing index for each chord.
    """
    n = len(all_voicings)
    if n == 0:
        return []
    if n == 1:
        return [0]

    # cost[j] = min total distance to reach current chord using voicing j
    # prev[i][j] = which voicing index of chord i-1 led to this minimum
    prev = []

    # Base case
    m0 = len(all_voicings[0])
    cost = [0] * m0
    prev.append([-1] * m0)

    # Fill forward
    for i in range(1, n):
        mi = len(all_voicings[i])
        new_cost = [0] * mi
        new_prev = [0] * mi

        for j in range(mi):
            best_cost = float('inf')
            best_k = 0
            for k in range(len(all_voicings[i - 1])):
                d = cost[k] + distance_fn(all_voicings[i - 1][k], all_voicings[i][j])
                if d < best_cost:
                    best_cost = d
                    best_k = k
            new_cost[j] = best_cost
            new_prev[j] = best_k

        cost = new_cost
        prev.append(new_prev)

    # Backtrack
    result = [0] * n
    result[n - 1] = min(range(len(cost)), key=lambda j: cost[j])
    for i in range(n - 2, -1, -1):
        result[i] = prev[i + 1][result[i + 1]]

    return result


def optimize_guitar_voice_leading(chords: List[dict]) -> List[int]:
    """
    Given parsed chord dicts, return optimal guitar voicing indices
    for smooth voice leading across the progression.
    """
    from .guitar import generate_all_voicings
    all_v = [generate_all_voicings(c) for c in chords]
    return optimize_voice_leading(all_v, guitar_voicing_distance)


def optimize_keyboard_voice_leading(chords: List[dict]) -> List[int]:
    """
    Given parsed chord dicts, return optimal keyboard inversion indices
    for smooth voice leading across the progression.
    """
    from .keyboard import generate_keyboard_inversions
    all_v = [generate_keyboard_inversions(c) for c in chords]
    return optimize_voice_leading(all_v, keyboard_voicing_distance)
