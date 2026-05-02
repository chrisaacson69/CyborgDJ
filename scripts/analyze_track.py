"""Run full Camelot analysis pipeline on a single track and save in AnalysisStore format.

This produces the same analysis_cache.json + analysis_cache.npz that the
Camelot UI generates, so rekordbox_export.py can consume it.

Run with the camelot venv:
    env1/Scripts/python.exe scripts/analyze_track.py <audio_path> <project_dir>
"""

import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add camelot project to path
CAMELOT_DIR = Path(r"C:\Users\Chris.Isaacson\source\repos\camelot_from_youtube")
sys.path.insert(0, str(CAMELOT_DIR))

import numpy as np


def main():
    if len(sys.argv) < 3:
        print("Usage: analyze_track.py <audio_path> <project_dir>")
        sys.exit(1)

    audio_path = Path(sys.argv[1])
    project_dir = Path(sys.argv[2])
    project_dir.mkdir(parents=True, exist_ok=True)

    if not audio_path.exists():
        print(f"Error: Audio not found: {audio_path}")
        sys.exit(1)

    from bpm_detect import (detect_beats, compute_span_bpm,
                            group_beats_into_measures, find_bpm_segments)
    from key_detect import (compute_measure_chroma, compute_phrase_chroma,
                            find_key_segments,
                            compute_summary as key_compute_summary)
    from event_detect import (compute_bar_features, compute_phrase_features,
                              detect_feature_events,
                              compute_summary as event_compute_summary)

    sr = 44100
    phrase_bars = 4

    # --- 1. BPM Detection ---
    print(f"[1/4] BPM detection: {audio_path.name}")
    bpm_data = detect_beats(str(audio_path), sr=sr, hop_length=512)
    beat_times = bpm_data["beat_times"]
    tempo = bpm_data["tempo"]
    phase = bpm_data["downbeat_phase"]
    bars_trimmed = bpm_data.get("bars_trimmed", 0)
    y = bpm_data["y"]
    duration = len(y) / sr

    measures = group_beats_into_measures(beat_times, 4, phase=phase)
    span_data = compute_span_bpm(beat_times, 8)
    segments = find_bpm_segments(measures, tolerance=2.0, min_segment_bars=4)

    print(f"  {len(beat_times)} beats, ~{tempo:.1f} BPM, phase={phase}, {len(measures)} bars")

    # Loudness
    rms = float(np.sqrt(np.mean(y ** 2)))
    peak = float(np.max(np.abs(y)))
    loudness_dbfs = round(20 * np.log10(rms), 1) if rms > 0 else -120.0
    peak_dbfs = round(20 * np.log10(peak), 1) if peak > 0 else -120.0
    safe_volume = 1.0
    if peak_dbfs > -0.1:
        safe_volume = round(min(1.0, 10 ** (-(peak_dbfs + 0.5) / 20)), 2)
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        lufs = round(float(meter.integrated_loudness(y)), 1)
    except Exception:
        lufs = None

    print(f"  Duration: {duration:.1f}s | {loudness_dbfs} dBFS | Peak: {peak_dbfs} dBFS")

    # --- 2. Key Detection ---
    print(f"[2/4] Key timeline analysis...")
    mk = compute_measure_chroma(y, sr, measures, use_harmonic=True)
    ph = compute_phrase_chroma(y, sr, measures, phrase_bars=phrase_bars,
                               use_harmonic=True)
    key_seg = find_key_segments(ph, min_segment_phrases=2)
    key_summary = key_compute_summary(key_seg, ph, duration)

    dominant = key_summary.get("dominant", {})
    print(f"  Dominant: {dominant.get('camelot', '?')} ({dominant.get('coverage_pct', 0):.0f}%)")

    # --- 3. Event Detection (feature-based) ---
    print(f"[3/4] Event detection...")
    bf = compute_bar_features(y, sr, measures)
    ev_phrases = compute_phrase_features(bf, phrase_bars=phrase_bars)
    events = detect_feature_events(ev_phrases, context=2, min_score=0.15,
                                    min_features=2, min_gap_phrases=2,
                                    bar_features=bf)
    ev_summary = event_compute_summary(events, ev_phrases, duration, mode="features")
    print(f"  {len(events)} events detected")

    # --- 4. Spectral Analysis ---
    print(f"[4/4] Spectral analysis...")
    from spectral_analysis import compute_bar_spectra, compute_spectral_summary
    spec_result = compute_bar_spectra(y, sr, measures)
    spec_summary = compute_spectral_summary(spec_result)
    dom_hz = spec_summary["dominant_band_hz"]
    bw = spec_summary["bandwidth_hz"]
    print(f"  Dominant: {dom_hz:.0f} Hz, active {bw[0]:.0f}-{bw[1]:.0f} Hz")

    # --- Save ---
    def _to_list(v):
        if isinstance(v, np.ndarray):
            return v.tolist()
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        return v

    span_save = {k: _to_list(v) for k, v in span_data.items()}

    data = {
        "sr": sr,
        "tempo": _to_list(tempo),
        "duration": duration,
        "downbeat_phase": phase,
        "bars_trimmed": bars_trimmed,
        "loudness_dbfs": loudness_dbfs,
        "peak_dbfs": peak_dbfs,
        "safe_volume": safe_volume,
        "lufs": lufs,
        "measures": measures,
        "segments": segments,
        "span_data": span_save,
        "key": {
            "measure_keys": mk,
            "phrases": ph,
            "key_segments": key_seg,
            "key_summary": key_summary,
        },
        "events_block": {
            "events": events,
            "event_phrases": ev_phrases,
            "event_mode": "features",
            "event_summary": ev_summary,
        },
        "spectrum": {
            "spectral_summary": spec_summary,
        },
        "_audio_name": audio_path.name,
    }

    with open(project_dir / "analysis_cache.json", "w") as f:
        json.dump(data, f, indent=2, default=_to_list)

    # NPZ arrays
    arrays = {"y": y, "beat_times": np.asarray(beat_times)}
    factor = max(1, len(y) // 4000)
    arrays["y_ds"] = y[::factor]
    arrays["t_ds"] = np.arange(len(arrays["y_ds"])) * (factor / sr)
    arrays["bar_spectra"] = spec_result["bar_spectra"]
    arrays["band_centers"] = spec_result["band_centers"]
    arrays["band_edges"] = spec_result["band_edges"]
    np.savez_compressed(str(project_dir / "analysis_cache.npz"), **arrays)

    print(f"\nDone! Saved to {project_dir}/")


if __name__ == "__main__":
    main()
