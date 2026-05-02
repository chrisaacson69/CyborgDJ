"""
Analyze frequency content of bars 0-16 of Below The Belt (Chris Micali Remix)
to find where the "da da da" vocal pattern appears.

Version 2: Better visualization and relative comparisons.
"""

import numpy as np
import librosa

# Track parameters
AUDIO_PATH = r"C:\Users\Chris.Isaacson\source\repos\music\Below The Belt (Chris Micali Remix).mp3"
BPM = 129.2
FIRST_BEAT_SAMPLE = 8688
SR = 44100
FIRST_BEAT_TIME = FIRST_BEAT_SAMPLE / SR  # ~0.197s

# Bar duration: 4 beats per bar
BAR_DURATION = 4 * 60.0 / BPM  # ~1.858s
BEAT_DURATION = 60.0 / BPM     # ~0.464s

# Frequency bands
BANDS = {
    'sub-bass':  (20, 80),
    'bass':      (80, 250),
    'low-mids':  (250, 500),
    'mids':      (500, 2000),
    'high-mids': (2000, 6000),
    'highs':     (6000, 22050),
}

def fmt_time(t):
    mins = int(t) // 60
    secs = t - mins * 60
    return f"{mins}:{secs:05.2f}"


def make_bar(val, max_val, width=30):
    """Create a simple bar chart character string."""
    if max_val == 0:
        return " " * width
    filled = int(round(val / max_val * width))
    filled = min(filled, width)
    return "#" * filled + "." * (width - filled)


def main():
    print(f"Loading audio: {AUDIO_PATH}")
    y, sr = librosa.load(AUDIO_PATH, sr=SR, mono=True)
    print(f"Loaded: {len(y)} samples, {len(y)/sr:.1f}s, sr={sr}")
    print(f"First beat at sample {FIRST_BEAT_SAMPLE} = {FIRST_BEAT_TIME:.3f}s")
    print(f"Bar duration: {BAR_DURATION:.3f}s, Beat duration: {BEAT_DURATION:.3f}s")
    print()

    num_bars = 17  # bars 0 through 16
    n_fft = 4096
    hop_length = 512

    # =========================================================================
    # PART 1: Per-bar band energy table
    # =========================================================================
    print("=" * 100)
    print("PART 1: PER-BAR FREQUENCY BAND ENERGY (RMS)")
    print("=" * 100)

    header = f"{'Bar':>3} {'Time':>8} | {'sub-bass':>9} {'bass':>9} {'lo-mid':>9} {'mids':>9} {'hi-mid':>9} {'highs':>9} | {'VocRatio':>8}"
    print(header)
    print("-" * len(header))

    bar_data = []
    for bar in range(num_bars):
        bar_start = FIRST_BEAT_TIME + bar * BAR_DURATION
        bar_end = bar_start + BAR_DURATION
        segment = y[int(bar_start * sr):int(bar_end * sr)]

        S = np.abs(librosa.stft(segment, n_fft=n_fft, hop_length=hop_length))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        band_rms = {}
        for name, (lo, hi) in BANDS.items():
            mask = (freqs >= lo) & (freqs < hi)
            band_rms[name] = np.sqrt(np.mean(S[mask, :] ** 2))

        vocal_e = band_rms['low-mids'] + band_rms['mids'] + band_rms['high-mids']
        kick_e = band_rms['sub-bass'] + band_rms['bass']
        ratio = vocal_e / kick_e if kick_e > 0 else 0

        bar_data.append((bar, bar_start, band_rms, ratio))

        row = f"{bar:>3} {fmt_time(bar_start):>8} |"
        for name in BANDS:
            row += f" {band_rms[name]:9.2f}"
        row += f" | {ratio:8.4f}"
        print(row)

    # Highlight anomalies
    ratios = [d[3] for d in bar_data]
    mean_r = np.mean(ratios[1:15])  # use bars 1-14 as baseline (skip bar 0 as it has intro effects)
    std_r = np.std(ratios[1:15])
    print()
    print(f"Baseline vocal ratio (bars 1-14): mean={mean_r:.4f}, std={std_r:.4f}")
    print("Bars with elevated vocal ratio (>mean+2*std):")
    threshold = mean_r + 2 * std_r
    for bar, t, brms, ratio in bar_data:
        if ratio > threshold:
            print(f"  *** Bar {bar} at {fmt_time(t)}: ratio={ratio:.4f} (threshold={threshold:.4f})")

    # =========================================================================
    # PART 2: Per-beat vocal energy comparison
    # =========================================================================
    print()
    print("=" * 100)
    print("PART 2: PER-BEAT VOCAL ENERGY (250-6000 Hz) - normalized to show relative changes")
    print("Each beat is ~0.464s. Looking for 'da da da' pattern (tonal hits on specific beats).")
    print("=" * 100)
    print()

    # Collect all beat vocal energies first to find global max for bar charts
    all_vocal = []
    all_beat_data = []
    for bar in range(num_bars):
        bar_start = FIRST_BEAT_TIME + bar * BAR_DURATION
        beat_vocals = []
        for beat in range(4):
            beat_start = bar_start + beat * BEAT_DURATION
            beat_end = beat_start + BEAT_DURATION
            seg = y[int(beat_start * sr):int(beat_end * sr)]

            S_b = np.abs(librosa.stft(seg, n_fft=2048, hop_length=256))
            f_b = librosa.fft_frequencies(sr=sr, n_fft=2048)

            vocal_mask = (f_b >= 250) & (f_b < 6000)
            vocal_rms = np.sqrt(np.mean(S_b[vocal_mask, :] ** 2))

            kick_mask = (f_b >= 20) & (f_b < 250)
            kick_rms = np.sqrt(np.mean(S_b[kick_mask, :] ** 2))

            beat_vocals.append(vocal_rms)
            all_vocal.append(vocal_rms)

        all_beat_data.append((bar, bar_start, beat_vocals))

    max_vocal = max(all_vocal) if all_vocal else 1

    for bar, bar_start, beat_vocals in all_beat_data:
        # Check if this bar has notably different beat-to-beat pattern
        mean_v = np.mean(beat_vocals)
        std_v = np.std(beat_vocals)
        pattern_flag = ""

        # Check for "da da da" = 3 hits out of 4 beats
        above = [v > mean_v * 1.1 for v in beat_vocals]
        if sum(above) == 3:
            pattern_flag = " <-- 3-hit pattern?"

        beats_str = "  ".join(
            f"B{i+1}={v:.2f} [{make_bar(v, max_vocal, 15)}]"
            for i, v in enumerate(beat_vocals)
        )
        print(f"Bar {bar:>2} ({fmt_time(bar_start)}): {beats_str}{pattern_flag}")

    # =========================================================================
    # PART 3: 8th-note analysis for bars 0 and 15-16 (the standouts)
    # =========================================================================
    print()
    print("=" * 100)
    print("PART 3: 8TH-NOTE VOCAL ENERGY for bars 0, 15, 16 (elevated vocal content)")
    print("Each 8th note = ~0.232s. 'da da da' could be 3 consecutive 8th notes.")
    print("=" * 100)
    print()

    eighth_duration = BEAT_DURATION / 2
    interesting_bars = [0, 1, 3, 7, 11, 15, 16]

    for bar in interesting_bars:
        bar_start = FIRST_BEAT_TIME + bar * BAR_DURATION
        eighth_vocals = []
        for eighth in range(8):
            e_start = bar_start + eighth * eighth_duration
            e_end = e_start + eighth_duration
            seg = y[int(e_start * sr):int(e_end * sr)]

            S_e = np.abs(librosa.stft(seg, n_fft=2048, hop_length=128))
            f_e = librosa.fft_frequencies(sr=sr, n_fft=2048)

            vocal_mask = (f_e >= 250) & (f_e < 6000)
            vocal_rms = np.sqrt(np.mean(S_e[vocal_mask, :] ** 2))

            eighth_vocals.append(vocal_rms)

        max_ev = max(eighth_vocals)
        line = f"Bar {bar:>2} ({fmt_time(bar_start)}): "
        for i, v in enumerate(eighth_vocals):
            beat_num = i // 2 + 1
            half = "a" if i % 2 == 0 else "b"
            bar_vis = make_bar(v, max_ev, 12)
            line_part = f"{beat_num}{half}={v:.2f}[{bar_vis}] "
            line += line_part
        print(line)

    # =========================================================================
    # PART 4: Focus on what makes bar 0 and 16 different - spectral centroid
    # =========================================================================
    print()
    print("=" * 100)
    print("PART 4: SPECTRAL CENTROID per beat (higher = more tonal/vocal content)")
    print("=" * 100)
    print()

    for bar in range(num_bars):
        bar_start = FIRST_BEAT_TIME + bar * BAR_DURATION
        centroids = []
        for beat in range(4):
            beat_start = bar_start + beat * BEAT_DURATION
            beat_end = beat_start + BEAT_DURATION
            seg = y[int(beat_start * sr):int(beat_end * sr)]
            cent = librosa.feature.spectral_centroid(y=seg, sr=sr, n_fft=2048, hop_length=512)
            centroids.append(np.mean(cent))

        mean_c = np.mean(centroids)
        flag = " ***" if mean_c > 300 else ""
        cents_str = "  ".join(f"B{i+1}={c:7.1f}Hz" for i, c in enumerate(centroids))
        print(f"Bar {bar:>2} ({fmt_time(bar_start)}): {cents_str}  avg={mean_c:.1f}Hz{flag}")


if __name__ == "__main__":
    main()
