"""spectral_collision.py - Compare two tracks' spectral overlap and suggest crossovers.

Loads per-bar spectral data from MixLens analysis caches, computes a
collision map over the specified bar ranges, and identifies frequency
bands where one track dominates — suggesting crossover frequencies for
EQ-based transitions.

Usage:
    python -m scripts.spectral_collision \
        --track-a "path/to/Track A project/" --bars-a 200-260 \
        --track-b "path/to/Track B project/" --bars-b 1-61 \
        [--save-plot collision.png] [--min-gap-db 10]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# Add camelot project to path for NOISE_FLOOR_DB
CAMELOT_DIR = Path(r"C:\Users\Chris.Isaacson\source\repos\camelot_from_youtube")
sys.path.insert(0, str(CAMELOT_DIR))

from spectral_analysis import NOISE_FLOOR_DB


# ── Data loading ────────────────────────────────────────────────────────

def load_track_spectra(project_dir):
    """Load spectral data from a track's analysis cache.

    Parameters
    ----------
    project_dir : str or Path
        Path to the track's project directory containing
        analysis_cache.npz and analysis_cache.json.

    Returns
    -------
    dict with keys: bar_spectra, band_centers, band_edges, measures,
                    loudness_dbfs, lufs
    """
    d = Path(project_dir)
    npz_path = d / "analysis_cache.npz"
    json_path = d / "analysis_cache.json"

    if not npz_path.exists():
        raise FileNotFoundError(f"No analysis_cache.npz in {d}")
    if not json_path.exists():
        raise FileNotFoundError(f"No analysis_cache.json in {d}")

    npz = np.load(str(npz_path), allow_pickle=False)

    if "bar_spectra" not in npz:
        raise ValueError(
            f"No spectral data in {npz_path}. "
            "Re-run analysis with spectral analysis enabled.")

    with open(json_path, "r") as f:
        data = json.load(f)

    result = {
        "bar_spectra": npz["bar_spectra"],
        "band_centers": npz["band_centers"],
        "band_edges": npz["band_edges"],
        "measures": data["measures"],
        "loudness_dbfs": data.get("loudness_dbfs"),
        "lufs": data.get("lufs"),
        "name": data.get("_audio_name", d.name),
    }
    npz.close()
    return result


def _parse_bar_range(bar_spec, n_bars):
    """Parse '200-260' into a slice of bar indices (0-based).

    Bar numbers in the spec are 1-based measure_nums.
    """
    parts = bar_spec.split("-")
    if len(parts) != 2:
        raise ValueError(f"Bar range must be 'start-end', got '{bar_spec}'")
    start = int(parts[0]) - 1  # convert to 0-based index
    end = int(parts[1])        # end is exclusive in slice
    if start < 0 or end > n_bars or start >= end:
        raise ValueError(
            f"Bar range {bar_spec} out of bounds (track has {n_bars} bars)")
    return start, end


# ── Loudness normalization ──────────────────────────────────────────────

def _normalize_spectra(spectra, loudness_dbfs, lufs):
    """Normalize spectra to 0 dBFS peak reference.

    Uses LUFS if available, otherwise RMS dBFS.  The offset shifts all
    spectral values so that the loudest track's reference is 0.
    """
    # Use LUFS preferably, otherwise loudness_dbfs
    ref = lufs if lufs is not None else loudness_dbfs
    if ref is None:
        return spectra
    # Shift so that the reference level becomes 0
    offset = -ref
    normalized = spectra + offset
    return np.clip(normalized, NOISE_FLOOR_DB, None)


# ── Collision analysis ──────────────────────────────────────────────────

def compute_collision(spectra_a, spectra_b, bars_a, bars_b,
                      track_a_data=None, track_b_data=None):
    """Compute spectral collision between two track regions.

    Parameters
    ----------
    spectra_a, spectra_b : dict
        Output of load_track_spectra.
    bars_a, bars_b : str
        Bar range specs like '200-260'.
    track_a_data, track_b_data : dict, optional
        If provided, used for loudness normalization.

    Returns
    -------
    dict with keys:
        collision : np.ndarray (n_bars, n_bands) — scores 0–80
        total_per_bar : np.ndarray (n_bars,) — sum across bands
        total_per_band : np.ndarray (n_bands,) — sum across bars
        hotspot_bars : list of bar indices with high collision
        hotspot_bands : list of band indices with high collision
        bar_spectra_a : np.ndarray — normalized spectra for region A
        bar_spectra_b : np.ndarray — normalized spectra for region B
        band_centers : np.ndarray
    """
    sa = spectra_a["bar_spectra"]
    sb = spectra_b["bar_spectra"]

    start_a, end_a = _parse_bar_range(bars_a, sa.shape[0])
    start_b, end_b = _parse_bar_range(bars_b, sb.shape[0])

    region_a = sa[start_a:end_a].copy()
    region_b = sb[start_b:end_b].copy()

    if region_a.shape[0] != region_b.shape[0]:
        raise ValueError(
            f"Bar ranges must be equal length: A has {region_a.shape[0]} bars, "
            f"B has {region_b.shape[0]} bars")

    # Verify band_centers match
    if not np.allclose(spectra_a["band_centers"], spectra_b["band_centers"]):
        raise ValueError("Tracks have different band_centers — "
                         "different sample rates?")

    # Loudness normalization
    if track_a_data is not None:
        region_a = _normalize_spectra(
            region_a, track_a_data.get("loudness_dbfs"),
            track_a_data.get("lufs"))
    if track_b_data is not None:
        region_b = _normalize_spectra(
            region_b, track_b_data.get("loudness_dbfs"),
            track_b_data.get("lufs"))

    # Collision: min(dB_A, dB_B) - NOISE_FLOOR_DB
    # Both loud → high score.  Either silent → near zero.
    collision = np.maximum(
        np.minimum(region_a, region_b) - NOISE_FLOOR_DB, 0.0)

    total_per_bar = collision.sum(axis=1)
    total_per_band = collision.sum(axis=0)

    # Hotspots: bars/bands with collision above 75th percentile
    bar_threshold = np.percentile(total_per_bar, 75) if len(total_per_bar) > 4 else 0
    band_threshold = np.percentile(total_per_band, 75) if len(total_per_band) > 4 else 0

    hotspot_bars = [int(i) for i in np.where(total_per_bar > bar_threshold)[0]]
    hotspot_bands = [int(i) for i in np.where(total_per_band > band_threshold)[0]]

    return {
        "collision": collision,
        "total_per_bar": total_per_bar,
        "total_per_band": total_per_band,
        "hotspot_bars": hotspot_bars,
        "hotspot_bands": hotspot_bands,
        "bar_spectra_a": region_a,
        "bar_spectra_b": region_b,
        "band_centers": spectra_a["band_centers"],
        "band_edges": spectra_a["band_edges"],
    }


# ── Spectral gap / crossover analysis ──────────────────────────────────

def find_spectral_gaps(spectra_a, spectra_b, bars_a, bars_b,
                       track_a_data=None, track_b_data=None,
                       min_gap_db=10.0):
    """Find frequency bands where one track dominates by >= min_gap_db.

    Parameters
    ----------
    spectra_a, spectra_b : dict
        Output of load_track_spectra.
    bars_a, bars_b : str
        Bar range specs.
    track_a_data, track_b_data : dict, optional
        For loudness normalization.
    min_gap_db : float
        Minimum dB difference to consider a gap (default 10).

    Returns
    -------
    dict with keys:
        gaps : list of dicts with frequency_hz, a_dominates, mean_gap_db,
               consistency (fraction of bars where gap holds)
        suggested_crossovers : list of dicts with frequency_hz,
               below_dominant, above_dominant, confidence
    """
    sa = spectra_a["bar_spectra"]
    sb = spectra_b["bar_spectra"]

    start_a, end_a = _parse_bar_range(bars_a, sa.shape[0])
    start_b, end_b = _parse_bar_range(bars_b, sb.shape[0])

    region_a = sa[start_a:end_a].copy()
    region_b = sb[start_b:end_b].copy()

    if region_a.shape[0] != region_b.shape[0]:
        raise ValueError("Bar ranges must be equal length")

    # Loudness normalization
    if track_a_data is not None:
        region_a = _normalize_spectra(
            region_a, track_a_data.get("loudness_dbfs"),
            track_a_data.get("lufs"))
    if track_b_data is not None:
        region_b = _normalize_spectra(
            region_b, track_b_data.get("loudness_dbfs"),
            track_b_data.get("lufs"))

    centers = spectra_a["band_centers"]
    n_bars, n_bands = region_a.shape

    # Per-band analysis
    gaps = []
    for i in range(n_bands):
        diff = region_a[:, i] - region_b[:, i]  # positive = A louder
        mean_diff = float(np.mean(diff))
        abs_gap = abs(mean_diff)

        if abs_gap >= min_gap_db:
            a_dom = mean_diff > 0
            # Consistency: fraction of bars where the dominance holds
            if a_dom:
                consistency = float(np.mean(diff > 0))
            else:
                consistency = float(np.mean(diff < 0))

            gaps.append({
                "frequency_hz": float(centers[i]),
                "band_idx": i,
                "a_dominates": a_dom,
                "mean_gap_db": round(abs_gap, 1),
                "consistency": round(consistency, 2),
            })

    # Find crossover suggestions: boundaries between A-dominant and B-dominant
    suggested_crossovers = []
    for j in range(len(gaps) - 1):
        g1 = gaps[j]
        g2 = gaps[j + 1]
        # Check for dominance flip
        if g1["a_dominates"] != g2["a_dominates"]:
            # Crossover at geometric mean of the two band frequencies
            xover_hz = float(np.sqrt(g1["frequency_hz"] * g2["frequency_hz"]))
            confidence = min(g1["consistency"], g2["consistency"])
            below = "A" if g1["a_dominates"] else "B"
            above = "A" if g2["a_dominates"] else "B"
            suggested_crossovers.append({
                "frequency_hz": round(xover_hz, 0),
                "below_dominant": below,
                "above_dominant": above,
                "confidence": round(confidence, 2),
                "gap_below_db": g1["mean_gap_db"],
                "gap_above_db": g2["mean_gap_db"],
            })

    return {
        "gaps": gaps,
        "suggested_crossovers": suggested_crossovers,
    }


# ── Reporting ───────────────────────────────────────────────────────────

def collision_report(collision_result, gap_result, name_a, name_b):
    """Generate a human-readable collision report.

    Returns
    -------
    str
    """
    lines = []
    lines.append(f"Spectral Collision Report: {name_a} vs {name_b}")
    lines.append("=" * 60)

    col = collision_result
    centers = col["band_centers"]

    # Overall collision
    total = float(col["collision"].sum())
    lines.append(f"\nTotal collision score: {total:.0f}")
    lines.append(f"Hotspot bars (top 25%): {len(col['hotspot_bars'])} of "
                 f"{col['collision'].shape[0]}")

    # Top colliding bands
    band_totals = col["total_per_band"]
    top_band_idx = np.argsort(band_totals)[::-1][:5]
    lines.append("\nTop 5 colliding frequency bands:")
    for idx in top_band_idx:
        lines.append(f"  {centers[idx]:>8.0f} Hz  score={band_totals[idx]:.0f}")

    # Worst bars
    bar_totals = col["total_per_bar"]
    top_bar_idx = np.argsort(bar_totals)[::-1][:5]
    lines.append(f"\nTop 5 colliding bars (0-indexed within region):")
    for idx in top_bar_idx:
        lines.append(f"  Bar {idx:>3d}  score={bar_totals[idx]:.0f}")

    # Gaps
    gaps = gap_result["gaps"]
    lines.append(f"\nSpectral gaps (>= threshold): {len(gaps)} bands")
    for g in gaps:
        dom = name_a if g["a_dominates"] else name_b
        lines.append(
            f"  {g['frequency_hz']:>8.0f} Hz  {dom} dominates by "
            f"{g['mean_gap_db']:.1f} dB ({g['consistency']:.0%} consistent)")

    # Crossover suggestions
    xovers = gap_result["suggested_crossovers"]
    if xovers:
        lines.append(f"\nSuggested crossover frequencies:")
        for x in xovers:
            below_name = name_a if x["below_dominant"] == "A" else name_b
            above_name = name_a if x["above_dominant"] == "A" else name_b
            lines.append(
                f"  {x['frequency_hz']:.0f} Hz  "
                f"(below: {below_name}, above: {above_name}, "
                f"confidence: {x['confidence']:.0%})")
    else:
        lines.append("\nNo clear crossover suggestions found.")

    return "\n".join(lines)


# ── Visualization ───────────────────────────────────────────────────────

def plot_collision(collision_result, gap_result, name_a, name_b,
                   save_path=None):
    """Three-panel collision figure.

    1. Collision heatmap with suggested crossover lines
    2. Per-band total collision (horizontal bar chart)
    3. Per-bar total collision (line plot)
    """
    import matplotlib.pyplot as plt

    col = collision_result
    centers = col["band_centers"]
    edges = col["band_edges"]
    n_bars = col["collision"].shape[0]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10),
                                         gridspec_kw={"height_ratios": [4, 2, 2]})
    fig.subplots_adjust(left=0.08, right=0.92, top=0.94, bottom=0.06,
                        hspace=0.35)

    # Panel 1: Collision heatmap
    t_edges = np.arange(n_bars + 1)
    f_edges = [edges[0, 0]] + [edges[i, 1] for i in range(len(edges))]
    T, F = np.meshgrid(t_edges, f_edges)

    pcm = ax1.pcolormesh(T, F, col["collision"].T, shading="flat",
                         cmap="YlOrRd", vmin=0,
                         vmax=np.percentile(col["collision"], 95))
    ax1.set_yscale("log")
    ax1.set_ylim(20, 20000)
    ax1.set_yticks([50, 100, 200, 500, 1000, 2000, 5000, 10000])
    ax1.set_yticklabels(["50", "100", "200", "500", "1k", "2k", "5k", "10k"])

    # Crossover lines
    for x in gap_result["suggested_crossovers"]:
        ax1.axhline(y=x["frequency_hz"], color="cyan", linewidth=1.5,
                     linestyle="--", alpha=0.8)
        ax1.text(n_bars * 0.02, x["frequency_hz"] * 1.1,
                 f'{x["frequency_hz"]:.0f} Hz',
                 color="cyan", fontsize=8, fontweight="bold")

    cb = fig.colorbar(pcm, ax=ax1, pad=0.02)
    cb.set_label("Collision Score", fontsize=8)
    ax1.set_xlabel("Bar (within overlap region)", fontsize=9)
    ax1.set_ylabel("Frequency (Hz)", fontsize=9)
    ax1.set_title(f"Spectral Collision: {name_a} vs {name_b}", fontsize=10)
    ax1.tick_params(labelsize=8)

    # Panel 2: Per-band total (horizontal bar chart)
    band_labels = [f"{c:.0f}" if c < 1000 else f"{c/1000:.1f}k"
                   for c in centers]
    y_pos = np.arange(len(centers))
    ax2.barh(y_pos, col["total_per_band"], color="#cc6633", alpha=0.8)
    ax2.set_yticks(y_pos[::3])
    ax2.set_yticklabels([band_labels[i] for i in range(0, len(centers), 3)],
                         fontsize=7)
    ax2.set_xlabel("Total Collision", fontsize=9)
    ax2.set_ylabel("Frequency (Hz)", fontsize=9)
    ax2.set_title("Collision by Frequency Band", fontsize=10)
    ax2.tick_params(labelsize=8)

    # Panel 3: Per-bar total (line plot)
    ax3.plot(np.arange(n_bars), col["total_per_bar"],
             color="#336699", linewidth=1.2)
    ax3.fill_between(np.arange(n_bars), col["total_per_bar"],
                     alpha=0.3, color="#336699")
    ax3.set_xlabel("Bar (within overlap region)", fontsize=9)
    ax3.set_ylabel("Total Collision", fontsize=9)
    ax3.set_title("Collision Over Time", fontsize=10)
    ax3.tick_params(labelsize=8)

    if save_path:
        fig.savefig(str(save_path), dpi=150, bbox_inches="tight")
        print(f"Saved plot: {save_path}")

    return fig


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Spectral collision analysis between two tracks")
    parser.add_argument("--track-a", required=True,
                        help="Path to Track A project directory")
    parser.add_argument("--bars-a", required=True,
                        help="Bar range for Track A (e.g. '200-260')")
    parser.add_argument("--track-b", required=True,
                        help="Path to Track B project directory")
    parser.add_argument("--bars-b", required=True,
                        help="Bar range for Track B (e.g. '1-61')")
    parser.add_argument("--save-plot", default=None,
                        help="Save collision plot to PNG")
    parser.add_argument("--min-gap-db", type=float, default=10.0,
                        help="Minimum dB gap to consider a spectral gap")
    args = parser.parse_args()

    print(f"Loading Track A: {args.track_a}")
    data_a = load_track_spectra(args.track_a)
    print(f"  {data_a['name']} — {data_a['bar_spectra'].shape[0]} bars")

    print(f"Loading Track B: {args.track_b}")
    data_b = load_track_spectra(args.track_b)
    print(f"  {data_b['name']} — {data_b['bar_spectra'].shape[0]} bars")

    print(f"\nComputing collision: bars {args.bars_a} vs {args.bars_b}")
    col = compute_collision(data_a, data_b, args.bars_a, args.bars_b,
                            track_a_data=data_a, track_b_data=data_b)

    print("Finding spectral gaps...")
    gaps = find_spectral_gaps(data_a, data_b, args.bars_a, args.bars_b,
                              track_a_data=data_a, track_b_data=data_b,
                              min_gap_db=args.min_gap_db)

    report = collision_report(col, gaps, data_a["name"], data_b["name"])
    print(f"\n{report}")

    # Plot
    import matplotlib.pyplot as plt
    fig = plot_collision(col, gaps, data_a["name"], data_b["name"],
                         save_path=args.save_plot)
    if not args.save_plot:
        plt.show()


if __name__ == "__main__":
    main()
