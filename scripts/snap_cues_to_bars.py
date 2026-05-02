"""Snap all Rekordbox cue points to the nearest bar boundary.

Reads the rekordbox_collection.xml, then for each track:
- Multi-tempo tracks with real tempo changes (e.g. DJ mix rips): kept as-is,
  cues snapped to the bar grid of whichever tempo segment they fall in.
- Multi-tempo tracks with detection noise: collapsed to single TEMPO using
  AverageBpm, cues snapped to the unified grid.
- Single-tempo tracks: cues snapped to bar grid.

Updates @bar labels in cue names. Prints diagnostic report.
"""

import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

XML_PATH = Path(r"C:\Users\Chris.Isaacson\source\repos\camelot_from_youtube\rekordbox_collection.xml")

# Tracks with genuine tempo changes — do NOT collapse these
KEEP_MULTI_TEMPO = {
    "Lady Danger (Mixed)",
}


def get_tempo_segments(track_el):
    """Return list of (inizio, bpm) from TEMPO elements."""
    tempos = track_el.findall("TEMPO")
    if not tempos:
        return None
    return [(float(t.get("Inizio", 0)), float(t.get("Bpm", 120))) for t in tempos]


def collapse_tempo(track_el):
    """Collapse multi-tempo track to single TEMPO using AverageBpm.

    Removes extra TEMPO elements, updates the remaining one.
    Returns (inizio, bpm).
    """
    tempos = track_el.findall("TEMPO")
    avg_bpm = float(track_el.get("AverageBpm", tempos[0].get("Bpm", 120)))
    inizio = float(tempos[0].get("Inizio", 0))

    for t in tempos[1:]:
        track_el.remove(t)
    tempos[0].set("Bpm", str(avg_bpm))

    return inizio, avg_bpm


def snap_to_bar_single(time_sec, inizio, bpm):
    """Snap to nearest bar on a single-tempo grid. Returns (snapped, bar_num)."""
    bar_dur = 4 * 60.0 / bpm
    bars = (time_sec - inizio) / bar_dur
    nearest = round(bars)
    return round(inizio + nearest * bar_dur, 3), nearest


def snap_to_bar_multi(time_sec, segments, total_time):
    """Snap to nearest bar on a multi-tempo grid.

    Each segment has its own bar grid starting at its Inizio.
    We find which segment the cue falls in, snap to that segment's grid,
    and compute a cumulative bar number across all segments.
    """
    # Find which segment this time falls in
    seg_idx = 0
    for i, (seg_start, _) in enumerate(segments):
        if time_sec >= seg_start:
            seg_idx = i

    seg_inizio, seg_bpm = segments[seg_idx]
    bar_dur = 4 * 60.0 / seg_bpm

    # Snap within this segment's grid
    bars_in_seg = (time_sec - seg_inizio) / bar_dur
    nearest_in_seg = round(bars_in_seg)
    snapped = round(seg_inizio + nearest_in_seg * bar_dur, 3)

    # Compute cumulative bar number across all segments
    cumulative_bars = 0
    for i in range(seg_idx):
        s_start, s_bpm = segments[i]
        s_bar_dur = 4 * 60.0 / s_bpm
        next_start = segments[i + 1][0]
        cumulative_bars += int((next_start - s_start) / s_bar_dur)

    bar_num = cumulative_bars + nearest_in_seg
    return snapped, bar_num


def update_bar_in_label(name, bar_num):
    """Update the @N bar reference in a cue label, or add one."""
    if re.search(r'@\d+', name):
        return re.sub(r'@\d+', f'@{bar_num}', name)
    return name


def main():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    collection = root.find("COLLECTION")

    total_snapped = 0
    total_cues = 0
    total_collapsed = 0

    for track in collection.findall("TRACK"):
        name = track.get("Name", "?")
        total_time = float(track.get("TotalTime", 600))
        segments = get_tempo_segments(track)

        if not segments:
            print(f"\n[SKIP] {name} — no TEMPO element")
            continue

        num_tempos = len(segments)
        keep_multi = name in KEEP_MULTI_TEMPO and num_tempos > 1

        if num_tempos > 1 and not keep_multi:
            inizio, bpm = collapse_tempo(track)
            total_collapsed += 1
            mode = "collapsed"
        else:
            inizio, bpm = segments[0]
            mode = "multi" if keep_multi else "single"

        bar_dur = 4 * 60.0 / bpm

        print(f"\n{'='*70}")
        print(f"{name}")
        if mode == "collapsed":
            print(f"  COLLAPSED {num_tempos} tempo segments -> single BPM={bpm}")
        elif mode == "multi":
            print(f"  KEEPING {num_tempos} tempo segments (genuine tempo changes)")
            for i, (s, b) in enumerate(segments):
                print(f"    seg {i}: Inizio={s:.3f}s  BPM={b}")
        print(f"  Primary: Inizio={inizio:.3f}s  BPM={bpm}  bar_dur={bar_dur:.3f}s")
        print(f"  {'Cue Label':<45} {'Original':>9} {'Bar.Beat':>9} {'Snapped':>9} {'Delta':>7}")
        print(f"  {'-'*45} {'-'*9} {'-'*9} {'-'*9} {'-'*7}")

        for mark in track.findall("POSITION_MARK"):
            total_cues += 1
            orig_start = float(mark.get("Start", 0))
            cue_name = mark.get("Name", "")

            if mode == "multi":
                snapped, bar_num = snap_to_bar_multi(orig_start, segments, total_time)
            else:
                snapped, bar_num = snap_to_bar_single(orig_start, inizio, bpm)

            delta = snapped - orig_start

            # Compute fractional bar.beat for display
            bars_frac = (orig_start - inizio) / bar_dur
            bar_int = int(bars_frac)
            beat_frac = (bars_frac - bar_int) * 4 + 1
            bar_beat = f"{bar_int}.{beat_frac:.1f}"

            mark.set("Start", str(snapped))
            new_name = update_bar_in_label(cue_name, bar_num)
            mark.set("Name", new_name)

            if abs(delta) > 0.01:
                total_snapped += 1
                flag = " *"
            else:
                flag = ""

            short_name = cue_name[:43]
            print(f"  {short_name:<45} {orig_start:>8.3f}s {bar_beat:>9} {snapped:>8.3f}s {delta:>+6.3f}s{flag}")

    tree.write(str(XML_PATH), encoding="utf-8", xml_declaration=True)

    print(f"\n{'='*70}")
    print(f"Done. {total_snapped}/{total_cues} cues snapped (moved > 10ms).")
    print(f"Collapsed {total_collapsed} multi-tempo tracks to single BPM.")
    print(f"Saved to: {XML_PATH}")


if __name__ == "__main__":
    main()
