"""CyborgDJ command-line interface."""

import argparse
import sys

from .engine import load_spec, render_mix, render_transition


def analyze_tracks(spec, tracks_dir=None):
    """Load all tracks and report first-downbeat detection results."""
    from .engine.loader import load_track, detect_first_downbeat, compute_bar_frames
    import os
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    if tracks_dir is None:
        tracks_dir = spec.get("tracks_dir", ".")
    sr = spec.get("sample_rate", 44100)

    print("Track Analysis — First Downbeat Detection")
    print("=" * 70)
    for track in spec["tracks"]:
        file_path = os.path.join(tracks_dir, track["file"])
        print(f"\n[{track['id']}] {track['name']}")
        print(f"    File: {track['file']}")

        audio, _ = load_track(file_path, sr)
        bpm = track["original_bpm"]
        first_beat_override = track.get("first_beat_sample")
        first_beat_detected = detect_first_downbeat(audio, sr)
        first_beat = first_beat_override if first_beat_override is not None else first_beat_detected
        source = "spec" if first_beat_override is not None else "detected"
        bar_frames = compute_bar_frames(bpm, sr, len(audio), first_beat)

        duration = len(audio) / sr
        first_beat_sec = first_beat / sr
        samples_per_bar = (60.0 / bpm) * 4 * sr
        bar_0_offset = bar_frames[0] / sr if len(bar_frames) > 0 else 0
        kick_bar = round((first_beat - bar_frames[0]) / samples_per_bar) if len(bar_frames) > 0 else 0

        print(f"    Duration: {duration:.1f}s  |  BPM: {bpm}")
        print(f"    First beat: sample {first_beat} ({first_beat_sec:.3f}s) = bar ~{kick_bar} [{source}]")
        if first_beat_override is not None:
            det_sec = first_beat_detected / sr
            print(f"    (detector would have said: {det_sec:.3f}s — delta: {abs(first_beat_sec - det_sec):.3f}s)")
        print(f"    Phase offset (bar 0): {bar_0_offset:.3f}s")
        print(f"    Bar grid: {len(bar_frames)} bars, {samples_per_bar:.0f} samples/bar")
        print(f"    Cue range: bar {track.get('cue_in_bar', 0)} to {track.get('cue_out_bar', '?')}")

        cue_in = track.get("cue_in_bar", 0)
        cue_out = track.get("cue_out_bar", len(bar_frames))
        if cue_in < len(bar_frames):
            cue_in_sec = bar_frames[cue_in] / sr
            print(f"    Cue-in time: {cue_in_sec:.3f}s (bar {cue_in})")
        if cue_out < len(bar_frames):
            cue_out_sec = bar_frames[cue_out] / sr
            print(f"    Cue-out time: {cue_out_sec:.3f}s (bar {cue_out})")
        else:
            print(f"    Cue-out: bar {cue_out} (beyond detected grid, will use end of audio)")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="CyborgDJ — Human writes the score, machine executes the mix.",
    )
    parser.add_argument(
        "spec",
        help="Path to mix spec JSON file",
    )
    parser.add_argument(
        "--tracks-dir",
        help="Override tracks directory (default: from spec file)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Override output file path (default: from spec file)",
    )
    parser.add_argument(
        "--transition", "-t",
        type=int,
        help="Render only this transition (0-indexed). Omit for full mix.",
    )
    parser.add_argument(
        "--list-transitions",
        action="store_true",
        help="List all transitions in the spec and exit.",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze all tracks (first downbeat, bar grid) and exit.",
    )

    args = parser.parse_args()

    spec = load_spec(args.spec)

    if args.list_transitions:
        print("Transitions:")
        tracks_by_id = {t["id"]: t for t in spec["tracks"]}
        for i, trans in enumerate(spec.get("transitions", [])):
            from_name = tracks_by_id[trans["from_track"]]["name"]
            to_name = tracks_by_id[trans["to_track"]]["name"]
            t_type = trans.get("type", "crossfade")
            overlap = trans.get("overlap_bars", 0)
            print(f"  [{i}] {from_name} -> {to_name} ({t_type}, {overlap} bars)")
        sys.exit(0)

    if args.analyze:
        analyze_tracks(spec, tracks_dir=args.tracks_dir)
        sys.exit(0)

    if args.transition is not None:
        render_transition(
            spec,
            args.transition,
            tracks_dir=args.tracks_dir,
            output_path=args.output,
        )
    else:
        render_mix(
            spec,
            tracks_dir=args.tracks_dir,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
