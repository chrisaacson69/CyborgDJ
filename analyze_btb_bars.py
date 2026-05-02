"""
Analyze frequency content per bar for the first 16 bars of
"Below The Belt (Chris Micali Remix)" to find vocal 'da da da' pattern.

BPM: 129.2
first_beat_sample: 8688 (at 44100 Hz = 0.197s)
Bar duration: 4 beats * 60/129.2 = 1.8576 seconds
"""

import numpy as np
import librosa

# ── Parameters ──────────────────────────────────────────────────────
AUDIO_PATH = r"C:\Users\Chris.Isaacson\source\repos\music\Below The Belt (Chris Micali Remix).mp3"
BPM = 129.2
FIRST_BEAT_SAMPLE = 8688
SR = 44100
BAR_BEATS = 4
BAR_DURATION = BAR_BEATS * 60.0 / BPM  # ~1.8576 s
FIRST_BEAT_TIME = FIRST_BEAT_SAMPLE / SR  # ~0.197 s
NUM_BARS = 16

# Frequency bands
BANDS = {
    "sub-bass  (20-80)":   (20, 80),
    "bass     (80-250)":   (80, 250),
    "low-mid (250-500)":   (250, 500),
    "mids   (500-2000)":   (500, 2000),
    "hi-mid (2k-6k)":      (2000, 6000),
    "highs    (6k+)":      (6000, None),  # None means up to Nyquist
}

# ── Load audio ──────────────────────────────────────────────────────
print(f"Loading audio: {AUDIO_PATH}")
print(f"BPM={BPM}, first_beat={FIRST_BEAT_TIME:.3f}s, bar_duration={BAR_DURATION:.4f}s")
print(f"Analyzing bars 0-{NUM_BARS - 1} (time {FIRST_BEAT_TIME:.3f}s to {FIRST_BEAT_TIME + NUM_BARS * BAR_DURATION:.3f}s)")
print()

# Only load what we need (first 16 bars + a bit of margin)
duration_needed = FIRST_BEAT_TIME + (NUM_BARS + 1) * BAR_DURATION
y, sr = librosa.load(AUDIO_PATH, sr=SR, mono=True, duration=duration_needed)

# ── Compute STFT once ──────────────────────────────────────────────
N_FFT = 4096
HOP = 512
S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=HOP)

def rms_in_band(S, freqs, f_lo, f_hi, col_start, col_end):
    """RMS of spectral magnitude in a frequency band over a time range."""
    if f_hi is None:
        f_hi = freqs[-1]
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    region = S[mask, col_start:col_end]
    if region.size == 0:
        return 0.0
    return np.sqrt(np.mean(region ** 2))

# ── Per-bar analysis ───────────────────────────────────────────────
header_bands = list(BANDS.keys())
# Print header
print(f"{'Bar':>4} {'Start':>7} {'End':>7}  ", end="")
for b in header_bands:
    print(f"{b:>20}", end="")
print(f"  {'vocal_ratio':>12}")
print("-" * (4 + 7 + 7 + 2 + 20 * len(header_bands) + 14))

results = []
for bar in range(NUM_BARS):
    t_start = FIRST_BEAT_TIME + bar * BAR_DURATION
    t_end = t_start + BAR_DURATION

    # Find STFT frame range for this bar
    col_start = np.searchsorted(times, t_start)
    col_end = np.searchsorted(times, t_end)
    if col_end <= col_start:
        col_end = col_start + 1

    band_rms = {}
    for name, (f_lo, f_hi) in BANDS.items():
        band_rms[name] = rms_in_band(S, freqs, f_lo, f_hi, col_start, col_end)

    # Vocal ratio: energy in mids+hi-mids relative to sub-bass+bass
    low_energy = band_rms["sub-bass  (20-80)"] + band_rms["bass     (80-250)"]
    vocal_energy = band_rms["mids   (500-2000)"] + band_rms["hi-mid (2k-6k)"]
    vocal_ratio = vocal_energy / low_energy if low_energy > 0 else 0.0

    results.append((bar, t_start, t_end, band_rms, vocal_ratio))

    print(f"{bar:>4} {t_start:>7.3f} {t_end:>7.3f}  ", end="")
    for name in header_bands:
        print(f"{band_rms[name]:>20.6f}", end="")
    print(f"  {vocal_ratio:>12.4f}")

# ── Summary ────────────────────────────────────────────────────────
print()
print("=" * 80)
print("SUMMARY: Bars with elevated vocal content (vocal_ratio > typical kick-only)")
print("=" * 80)

# Use the minimum vocal_ratio as the baseline (pure kick bar)
ratios = [r[4] for r in results]
baseline = min(ratios)
mean_ratio = np.mean(ratios)

print(f"  Baseline vocal_ratio (min): {baseline:.4f}")
print(f"  Mean vocal_ratio:           {mean_ratio:.4f}")
print()

# Flag bars where vocal_ratio is notably above baseline
threshold = baseline * 1.3  # 30% above baseline
print(f"  Threshold (baseline * 1.3): {threshold:.4f}")
print()
for bar, t_start, t_end, band_rms, vr in results:
    flag = " <<<< VOCAL CONTENT" if vr > threshold else ""
    print(f"  Bar {bar:>2} ({t_start:>6.2f}s - {t_end:>6.2f}s): vocal_ratio={vr:.4f}{flag}")

# ── Also do per-beat analysis for bars with high vocal ratio ───────
print()
print("=" * 80)
print("PER-BEAT DETAIL for bars with vocal content")
print("=" * 80)
beat_dur = 60.0 / BPM

for bar, t_start, t_end, band_rms, vr in results:
    if vr <= threshold:
        continue
    print(f"\n  Bar {bar} ({t_start:.3f}s - {t_end:.3f}s):")
    for beat in range(4):
        bt_start = t_start + beat * beat_dur
        bt_end = bt_start + beat_dur
        col_s = np.searchsorted(times, bt_start)
        col_e = np.searchsorted(times, bt_end)
        if col_e <= col_s:
            col_e = col_s + 1

        sub = rms_in_band(S, freqs, 20, 80, col_s, col_e)
        bass = rms_in_band(S, freqs, 80, 250, col_s, col_e)
        mid = rms_in_band(S, freqs, 500, 2000, col_s, col_e)
        himid = rms_in_band(S, freqs, 2000, 6000, col_s, col_e)
        low = sub + bass
        voc = mid + himid
        r = voc / low if low > 0 else 0
        print(f"    Beat {beat} ({bt_start:.3f}s): sub={sub:.5f} bass={bass:.5f} mid={mid:.5f} hi-mid={himid:.5f}  vocal_ratio={r:.4f}")

print("\nDone.")
