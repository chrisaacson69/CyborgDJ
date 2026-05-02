"""Render transition 1->2 (Deep Style -> Foss) with per-band EQ automation.

Renders two versions:
  A. Original 1b (12-bar overlap, HP 250 + fader automation)
  B. Slow EQ blend (28-bar overlap, per-band automation, tutorial technique)

Usage: python -m scripts.render_eq_1_2
"""

import json
import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cyborgdj.engine import load_spec, render_transition

SPEC_PATH = "specs/dj-set-1b.json"
TRANSITION_INDEX = 0  # 1->2 (Deep Style -> Foss)

# 28-bar slow EQ blend for 1->2.
#
# Spectral analysis findings:
#   - Tonally very similar (all ranges within 3 dB) — ideal for slow EQ blend
#   - Crossover at 447 Hz: DS dominant below (200-400 Hz warmth), Foss dominant above (500-1000 Hz)
#   - DS energy declining (mids 33.7 -> 28.4 dB), Foss building (mids rising to 37.9)
#   - Natural energy crossover at overlap bars 12-15
#   - DS key change at DS bar 200 = overlap bar 21 — must be inaudible by then
#   - Foss bar 0 is quiet (intro pad), kicks in at bar 2
#   - Foss sub-bass hotter (43 vs 40 dB), DS has more air (7 vs -1 dB at 12.5 kHz)
#
# Tutorial pattern (Video 4, slow EQ blend):
#   1. Incoming mids first — harmonic preview
#   2. Incoming highs next — texture/shimmer
#   3. Bass swap — outgoing out, incoming in
#   4. Outgoing highs thin
#   5. Outgoing mids linger (farewell), fade last
#   6. Fader is cleanup crew
#
# Narrative:
#   0-4:   DS solo, Foss mids whisper in (bar 0 is silent anyway)
#   4-12:  Foss mids growing, highs starting to appear
#   12-16: Bass swap (4-bar soft swap at the energy crossover point)
#   16-18: Foss owns bass+mids, DS thinning to mids only
#   18-21: DS mids fade to silence, fader dropping. Key change at 21 is inaudible.
#   21-25: Fader cleanup, Foss highs finish arriving
#   25-28: Buffer — pure Foss

# V1: first attempt — mids too aggressive bars 10-15, Foss kick harmonics
# audible through mid band before bass swap. At bars 10-15, incoming_mid was
# 0.5-0.75 — enough for kick upper harmonics (above 450 Hz) to punch through.
EQ_BLEND_V1 = {
    "low_freq": 450,
    "high_freq": 3000,
    "incoming_mid":    [[0, 0.0], [4, 0.2], [8, 0.4], [14, 0.75], [18, 1.0]],
    "incoming_high":   [[0, 0.0], [8, 0.0], [14, 0.3], [20, 0.7], [24, 1.0]],
    "incoming_low":    [[0, 0.0], [12, 0.0], [16, 1.0]],
    "outgoing_low":    [[0, 1.0], [12, 1.0], [16, 0.0]],
    "outgoing_high":   [[0, 1.0], [10, 1.0], [18, 0.0]],
    "outgoing_mid":    [[0, 1.0], [14, 1.0], [21, 0.0]],
    "incoming_fader":  [[0, 1.0]],
    "outgoing_fader":  [[0, 1.0], [18, 0.6], [21, 0.15], [25, 0.0]],
}

# V2: Fix Foss kick bleed at bars 10-15.
# Keep incoming mids as a whisper (0.1-0.15) until the bass swap completes
# at bar 16, then ramp up together. This way the kick's upper harmonics in
# the mid band stay masked by DS until the bass swap hands off low end.
# Also delay incoming highs slightly — no reason for shimmer before the swap.
EQ_BLEND = {
    "low_freq": 450,    # DS owns 200-400 Hz warmth; above = Foss's sweet spot
    "high_freq": 3000,   # Standard presence/air boundary

    # --- Incoming (Foss) ---
    # Mids: whisper until bass swap completes, then bloom together.
    "incoming_mid":    [[0, 0.0], [4, 0.1], [12, 0.15], [16, 0.5], [20, 1.0]],
    # Highs: hold off until bass swap is underway, then layer in.
    "incoming_high":   [[0, 0.0], [12, 0.0], [18, 0.4], [24, 1.0]],
    # Bass: same 4-bar swap at bars 12-16.
    "incoming_low":    [[0, 0.0], [12, 0.0], [16, 1.0]],

    # --- Outgoing (DS) ---
    # Bass: hold through bar 12, swap out 12-16 (mirrors incoming bass).
    "outgoing_low":    [[0, 1.0], [12, 1.0], [16, 0.0]],
    # Highs: DS has the air — start thinning at bar 12, gone by 20.
    "outgoing_high":   [[0, 1.0], [12, 1.0], [20, 0.0]],
    # Mids: linger longest (farewell). Hold through bass swap, fade before key change.
    "outgoing_mid":    [[0, 1.0], [14, 1.0], [21, 0.0]],

    # --- Faders ---
    "incoming_fader":  [[0, 1.0]],
    # Fader is cleanup: holds through the transition, drops at the key change.
    "outgoing_fader":  [[0, 1.0], [18, 0.6], [21, 0.15], [25, 0.0]],
}


def main():
    spec = load_spec(SPEC_PATH)

    # --- Render A: original 1b ---
    print("=" * 60)
    print("RENDER A: Original 1b (12-bar, HP 250 + fader automation)")
    print("=" * 60)
    render_transition(spec, TRANSITION_INDEX,
                      output_path="output/t1-2_A_original.wav")

    # --- Render B: 28-bar slow EQ blend ---
    print()
    print("=" * 60)
    print("RENDER B: 28-bar slow EQ blend (tutorial technique)")
    print("=" * 60)
    spec_b = copy.deepcopy(spec)
    trans = spec_b["transitions"][TRANSITION_INDEX]

    # Extend overlap from 12 to 28 bars
    trans["overlap_bars"] = 28

    # Replace automation with per-band EQ
    trans["automation"] = EQ_BLEND

    # Clear legacy EQ/fade fields that would conflict
    trans.pop("eq_outgoing", None)
    trans.pop("eq_incoming", None)
    trans.pop("eq_3band_outgoing", None)
    trans.pop("eq_3band_incoming", None)
    trans.pop("fade_type", None)
    trans.pop("fade_power", None)

    render_transition(spec_b, TRANSITION_INDEX,
                      output_path="output/t1-2_B2_eq_blend.wav")

    print()
    print("Done! Compare:")
    print("  A (original 1b): output/t1-2_A_original.wav")
    print("  B2 (EQ blend):   output/t1-2_B2_eq_blend.wav")


if __name__ == "__main__":
    main()
