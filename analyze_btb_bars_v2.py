"""
Deeper analysis of bars 0-16 in "Below The Belt (Chris Micali Remix)"
looking for a subtle vocal "da da da" pattern.

This script:
1. Shows per-beat RMS across all 64 beats (16 bars x 4 beats)
2. Uses a narrower vocal band (150-800 Hz) since a low male "da" vocal
   could sit in the low-mid range, below the typical vocal range
3. Separates kick transient from sustain/tail to isolate tonal content
4. Looks at spectral flatness (tonal vs noise) per beat
"""

import numpy as np
import librosa

AUDIO_PATH = r"C:\Users\Chris.Isaacson\source\repos\music\Below The Belt (Chris Micali Remix).mp3"
BPM = 129.2
FIRST_BEAT_SAMPLE = 8688
SR = 44100
FIRST_BEAT_TIME = FIRST_BEAT_SAMPLE / SR
BEAT_DUR = 60.0 / BPM
BAR_DUR = 4 * BEAT_DUR
NUM_BARS = 16

duration_needed = FIRST_BEAT_TIME + (NUM_BARS + 1) * BAR_DUR
y, sr = librosa.load(AUDIO_PATH, sr=SR, mono=True, duration=duration_needed)

N_FFT = 4096
HOP = 512
S = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=HOP)

def band_rms(f_lo, f_hi, col_s, col_e):
    if f_hi is None:
        f_hi = freqs[-1]
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    region = S[mask, col_s:col_e]
    if region.size == 0:
        return 0.0
    return np.sqrt(np.mean(region ** 2))

def spectral_flatness_band(f_lo, f_hi, col_s, col_e):
    """Spectral flatness in a band. Low = tonal, High = noisy."""
    if f_hi is None:
        f_hi = freqs[-1]
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    region = S[mask, col_s:col_e]
    if region.size == 0:
        return 0.0
    power = region ** 2
    mean_power = np.mean(power)
    if mean_power == 0:
        return 0.0
    geo_mean = np.exp(np.mean(np.log(power + 1e-20)))
    return geo_mean / (mean_power + 1e-20)

# ── Analysis 1: Per-beat in the "tail" portion (skip first 30ms of each beat to avoid kick transient) ──
print("=" * 110)
print("PER-BEAT ANALYSIS: Tail portion of each beat (30ms-end) to isolate tonal content from kick transient")
print("=" * 110)
print(f"{'Bar':>4}.{'Bt':>2} {'Time':>7}  {'sub(20-80)':>12} {'bass(80-250)':>12} {'lo-vocal(150-500)':>18} {'vocal(500-2k)':>14} {'flatness(150-2k)':>16}  note")
print("-" * 110)

# Collect per-beat vocal energy for pattern detection
beat_vocal_energies = []
beat_lowvocal_energies = []

TRANSIENT_SKIP = 0.030  # skip 30ms of kick attack

for bar in range(NUM_BARS):
    for beat in range(4):
        global_beat = bar * 4 + beat
        bt_start = FIRST_BEAT_TIME + global_beat * BEAT_DUR + TRANSIENT_SKIP
        bt_end = FIRST_BEAT_TIME + (global_beat + 1) * BEAT_DUR

        col_s = np.searchsorted(times, bt_start)
        col_e = np.searchsorted(times, bt_end)
        if col_e <= col_s:
            col_e = col_s + 1

        sub = band_rms(20, 80, col_s, col_e)
        bass = band_rms(80, 250, col_s, col_e)
        lo_vocal = band_rms(150, 500, col_s, col_e)
        vocal = band_rms(500, 2000, col_s, col_e)
        flat = spectral_flatness_band(150, 2000, col_s, col_e)

        beat_vocal_energies.append(vocal)
        beat_lowvocal_energies.append(lo_vocal)

        t = FIRST_BEAT_TIME + global_beat * BEAT_DUR
        note = ""
        print(f"{bar:>4}.{beat:>2} {t:>7.3f}  {sub:>12.4f} {bass:>12.4f} {lo_vocal:>18.4f} {vocal:>14.4f} {flat:>16.6f}  {note}")

    if bar < NUM_BARS - 1:
        print()  # blank line between bars

# ── Analysis 2: Look at variance across beats ──
print()
print("=" * 110)
print("STATISTICAL ANALYSIS: Beat-to-beat variation")
print("=" * 110)

vocal_arr = np.array(beat_vocal_energies)
lo_vocal_arr = np.array(beat_lowvocal_energies)

print(f"  Vocal (500-2k) RMS:     mean={vocal_arr.mean():.4f}  std={vocal_arr.std():.4f}  min={vocal_arr.min():.4f}  max={vocal_arr.max():.4f}  CV={vocal_arr.std()/vocal_arr.mean()*100:.1f}%")
print(f"  Lo-vocal (150-500) RMS: mean={lo_vocal_arr.mean():.4f}  std={lo_vocal_arr.std():.4f}  min={lo_vocal_arr.min():.4f}  max={lo_vocal_arr.max():.4f}  CV={lo_vocal_arr.std()/lo_vocal_arr.mean()*100:.1f}%")

# ── Analysis 3: Compare bars 0-3 vs bars 4-15 to see if early bars differ ──
print()
print("=" * 110)
print("COMPARISON: First 4 bars vs remaining 12 bars")
print("=" * 110)

for label, beat_range in [("Bars 0-3 (beats 0-15)", slice(0,16)), ("Bars 4-15 (beats 16-63)", slice(16,64))]:
    v = vocal_arr[beat_range]
    lv = lo_vocal_arr[beat_range]
    print(f"  {label}:")
    print(f"    Vocal (500-2k):     mean={v.mean():.4f}  std={v.std():.4f}")
    print(f"    Lo-vocal (150-500): mean={lv.mean():.4f}  std={lv.std():.4f}")

# ── Analysis 4: Check for periodic pattern in vocal energy ──
print()
print("=" * 110)
print("PATTERN DETECTION: Autocorrelation of vocal energy")
print("=" * 110)

# Normalize
vn = vocal_arr - vocal_arr.mean()
if np.std(vn) > 0:
    vn = vn / np.std(vn)
    autocorr = np.correlate(vn, vn, mode='full')
    autocorr = autocorr[len(vn)-1:]  # positive lags only
    autocorr = autocorr / autocorr[0]  # normalize

    print("  Autocorrelation of vocal(500-2k) energy at different beat lags:")
    for lag in range(1, min(17, len(autocorr))):
        bar_frac = lag / 4.0
        stars = "*" * int(max(0, autocorr[lag]) * 20)
        print(f"    Lag {lag:>2} beats ({bar_frac:>5.2f} bars): r={autocorr[lag]:>7.4f}  {stars}")

# ── Analysis 5: Per-eighth-note in first 4 bars for fine detail ──
print()
print("=" * 110)
print("FINE DETAIL: Per-eighth-note RMS in bars 0-3 (150-800Hz band, tail only)")
print("=" * 110)

eighth_dur = BEAT_DUR / 2
for bar in range(4):
    print(f"  Bar {bar}:")
    for eighth in range(8):
        t_s = FIRST_BEAT_TIME + bar * BAR_DUR + eighth * eighth_dur + TRANSIENT_SKIP
        t_e = t_s + eighth_dur - TRANSIENT_SKIP
        cs = np.searchsorted(times, t_s)
        ce = np.searchsorted(times, t_e)
        if ce <= cs:
            ce = cs + 1
        lv = band_rms(150, 800, cs, ce)
        mid = band_rms(500, 2000, cs, ce)
        beat_num = eighth / 2
        pos = f"{int(beat_num)+1}{'&' if eighth % 2 else ' '}"
        bar_char = "|" if eighth == 0 else " "
        energy_bar = "#" * int(lv * 2)
        print(f"    {bar_char} {pos} ({t_s:.3f}s): lo-vocal={lv:>8.4f}  mid={mid:>8.4f}  {energy_bar}")

print("\nDone.")
