"""Render transition 7->8 with per-band EQ automation for A/B comparison.

Renders two versions:
  1. Original 1b (fader-only automation)
  2. Per-band EQ blend (tutorial slow-blend technique)

Usage: python -m scripts.render_eq_test
"""

import json
import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cyborgdj.engine import load_spec, render_transition

SPEC_PATH = "specs/dj-set-1b.json"
TRANSITION_INDEX = 6  # 7->8 (PQM -> Quivver)

# Per-band EQ automation: tutorial slow-blend technique mapped to the 80-bar overlap.
#
# Musical landmarks (in overlap-bar coordinates, PQM bar = overlap bar + 209):
#   Bar 0:  PQM perc drop just happened (bar 208)
#   Bar 32: PQM decrease (bar 241) -- natural bass swap point
#   Bar 48: PQM increase (bar 257) -- last energy burst
#   Bar 55: PQM perc drop (bar 264) -- outro thinning
#   Bar 64: PQM perc drop (bar 273) -- nearly gone
#   Bar 80: PQM fill (bar 289) -- must be fully out
#
# Tutorial pattern (Video 4, "3 Ways To Mix Techno" slow EQ blend):
#   1. Incoming mids first (harmonic preview)
#   2. Incoming highs next (texture/shimmer)
#   3. Bass swap (outgoing bass drops, incoming bass rises)
#   4. Outgoing highs fade
#   5. Outgoing mids linger (vocal farewell), then fade last
#   6. Fader is cleanup crew
#
# V1: first attempt — too aggressive, Quivver stomps PQM melody at bar 11,
#     bass bleed through mid band (300 Hz crossover too low), PQM lows muddy at bar 49.
EQ_BLEND_V1 = {
    "incoming_mid":    [[0, 0.0], [8, 0.3], [20, 0.7], [36, 1.0]],
    "incoming_high":   [[0, 0.0], [16, 0.0], [28, 0.5], [40, 1.0]],
    "incoming_low":    [[0, 0.0], [30, 0.0], [38, 1.0]],
    "outgoing_low":    [[0, 1.0], [28, 1.0], [34, 0.0]],
    "outgoing_high":   [[0, 1.0], [32, 1.0], [44, 0.0]],
    "outgoing_mid":    [[0, 1.0], [52, 1.0], [64, 0.0]],
    "incoming_fader":  [[0, 1.0]],
    "outgoing_fader":  [[0, 1.0], [68, 1.0], [76, 0.0]],
}

# V2: fixes from listening session feedback.
# Changes:
#   - low_freq 300 -> 450 Hz: captures bass harmonics/warmth that were bleeding into mids
#   - Incoming mids: slower start (0.15 at bar 16, not 0.3 at bar 8) — stop stomping PQM melody
#   - Incoming bass: delayed to bar 42-50, enters AFTER PQM vocal callback at ~bar 41
#   - Outgoing highs: drop by bar 38 (was 44) — stop interfering with Quivver at bar 43
#   - Outgoing lows: drop by bar 38 — clear before Quivver bass arrives
#   - Outgoing mids: start dropping at bar 44 (was 52) — reduce mud from bass harmonics in mid band
EQ_BLEND_V2 = {
    # Crossover: 450 Hz captures kick warmth + bass harmonics in the "low" band
    "low_freq": 450,
    "high_freq": 3000,

    # --- Incoming (Quivver) ---
    # Mids: much gentler start — just a whisper until bar 28, then bloom
    "incoming_mid":    [[0, 0.0], [16, 0.15], [28, 0.5], [40, 1.0]],
    # Highs: hold off until mids are established, then layer in
    "incoming_high":   [[0, 0.0], [20, 0.0], [32, 0.5], [44, 1.0]],
    # Bass: delayed until after PQM vocal callback (~bar 41). Clean entry.
    "incoming_low":    [[0, 0.0], [42, 0.0], [50, 1.0]],

    # --- Outgoing (PQM) ---
    # Bass: clear out before Quivver bass arrives at 42
    "outgoing_low":    [[0, 1.0], [28, 1.0], [38, 0.0]],
    # Highs: drop faster — gone by bar 38, no interference at bar 43
    "outgoing_high":   [[0, 1.0], [28, 1.0], [38, 0.0]],
    # Mids: still linger for vocal farewell, but start dropping sooner to reduce mud
    "outgoing_mid":    [[0, 1.0], [44, 1.0], [56, 0.0]],

    # --- Faders ---
    "incoming_fader":  [[0, 1.0]],
    "outgoing_fader":  [[0, 1.0], [60, 1.0], [72, 0.0]],
}

# V3: listening feedback round 2.
# Early part fixed. Remaining issues:
#   - Quivver bass too late (was bar 42-50) — bring in 6 bars earlier
#   - PQM mids mud at bar ~48 (5:57) — at V2 values, outgoing_mid ≈ 0.67 there.
#     Drop earlier so it's ~0.2 by bar 48.
#   - Mud zone bars 26-40 noted but parked for later iteration.
EQ_BLEND_V3 = {
    "low_freq": 450,
    "high_freq": 3000,

    # --- Incoming (Quivver) ---
    "incoming_mid":    [[0, 0.0], [16, 0.15], [28, 0.5], [40, 1.0]],
    "incoming_high":   [[0, 0.0], [20, 0.0], [32, 0.5], [44, 1.0]],
    # Bass: 6 bars earlier (was 42-50, now 36-44)
    "incoming_low":    [[0, 0.0], [36, 0.0], [44, 1.0]],

    # --- Outgoing (PQM) ---
    "outgoing_low":    [[0, 1.0], [28, 1.0], [38, 0.0]],
    "outgoing_high":   [[0, 1.0], [28, 1.0], [38, 0.0]],
    # Mids: start dropping at bar 40, gone by 50 (was 44-56)
    # At bar 48: ~0.2 remaining instead of ~0.67
    "outgoing_mid":    [[0, 1.0], [40, 1.0], [50, 0.0]],

    # --- Faders ---
    "incoming_fader":  [[0, 1.0]],
    "outgoing_fader":  [[0, 1.0], [54, 1.0], [64, 0.0]],
}

# Active version for rendering
EQ_BLEND_AUTOMATION = EQ_BLEND_V3


def main():
    spec = load_spec(SPEC_PATH)

    # --- Render A: original 1b (fader-only) ---
    print("=" * 60)
    print("RENDER A: Original 1b (fader-only automation)")
    print("=" * 60)
    render_transition(spec, TRANSITION_INDEX,
                      output_path="output/t7-8_A_fader_only.wav")

    # --- Render B: per-band EQ blend ---
    print()
    print("=" * 60)
    print("RENDER B: Per-band EQ automation (tutorial slow-blend)")
    print("=" * 60)
    spec_b = copy.deepcopy(spec)
    trans = spec_b["transitions"][TRANSITION_INDEX]
    trans["automation"] = EQ_BLEND_AUTOMATION
    # Clear legacy EQ fields that would conflict
    trans.pop("eq_outgoing", None)
    trans.pop("eq_incoming", None)
    trans.pop("eq_3band_outgoing", None)
    trans.pop("eq_3band_incoming", None)

    render_transition(spec_b, TRANSITION_INDEX,
                      output_path="output/t7-8_B_eq_blend.wav")

    print()
    print("Done! Compare:")
    print("  A (fader-only): output/t7-8_A_fader_only.wav")
    print("  B (EQ blend):   output/t7-8_B_eq_blend.wav")


if __name__ == "__main__":
    main()
