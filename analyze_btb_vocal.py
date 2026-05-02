"""
Analyze frequency content of bars 0-16 of Below The Belt (Chris Micali Remix)
to find where the "da da da" vocal pattern appears.

For each bar, compute RMS energy in frequency bands:
  sub-bass (20-80Hz), bass (80-250Hz), low-mids (250-500Hz),
  mids (500-2kHz), high-mids (2k-6kHz), highs (6k+)
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

# Frequency bands
BANDS = {
    'sub-bass':  (20, 80),
    'bass':      (80, 250),
    'low-mids':  (250, 500),
    'mids':      (500, 2000),
    'high-mids': (2000, 6000),
    'highs':     (6000, 22050),
}

def main():
    print(f"Loading audio: {AUDIO_PATH}")
    y, sr = librosa.load(AUDIO_PATH, sr=SR, mono=True)
    print(f"Loaded: {len(y)} samples, {len(y)/sr:.1f}s, sr={sr}")
    print(f"First beat at sample {FIRST_BEAT_SAMPLE} = {FIRST_BEAT_TIME:.3f}s")
    print(f"Bar duration: {BAR_DURATION:.3f}s")
    print()

    # We'll analyze bars 0-16 (17 bars total: bar 0 through bar 16)
    # But "bars 0-16" likely means 16 bars starting from bar 0 to bar 15,
    # or it could mean through bar 16. Let's do 0-16 inclusive to be thorough.
    num_bars = 17  # bars 0 through 16

    # For each bar, extract the audio segment and compute STFT-based band energy
    n_fft = 4096  # good frequency resolution (~10.7 Hz per bin at 44100)
    hop_length = 512

    # Print header
    header = f"{'Bar':>3} | {'Time':>8} | "
    header += " | ".join(f"{name:>9}" for name in BANDS.keys())
    header += " | Vocal Ratio"
    print(header)
    print("-" * len(header))

    results = []
    for bar in range(num_bars):
        bar_start_time = FIRST_BEAT_TIME + bar * BAR_DURATION
        bar_end_time = bar_start_time + BAR_DURATION

        start_sample = int(bar_start_time * sr)
        end_sample = int(bar_end_time * sr)

        segment = y[start_sample:end_sample]

        # Compute STFT
        S = np.abs(librosa.stft(segment, n_fft=n_fft, hop_length=hop_length))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        # Compute RMS energy per band
        band_rms = {}
        for band_name, (lo, hi) in BANDS.items():
            band_mask = (freqs >= lo) & (freqs < hi)
            band_power = S[band_mask, :] ** 2
            rms = np.sqrt(np.mean(band_power))
            band_rms[band_name] = rms

        # Vocal ratio: energy in vocal bands (mids + high-mids) relative to
        # energy in kick bands (sub-bass + bass)
        vocal_energy = band_rms['mids'] + band_rms['high-mids'] + band_rms['low-mids']
        kick_energy = band_rms['sub-bass'] + band_rms['bass']
        vocal_ratio = vocal_energy / kick_energy if kick_energy > 0 else 0

        results.append((bar, bar_start_time, band_rms, vocal_ratio))

        # Format time as M:SS.s
        mins = int(bar_start_time) // 60
        secs = bar_start_time - mins * 60
        time_str = f"{mins}:{secs:05.2f}"

        row = f"{bar:>3} | {time_str:>8} | "
        row += " | ".join(f"{band_rms[name]:9.4f}" for name in BANDS.keys())
        row += f" | {vocal_ratio:7.3f}"
        print(row)

    print()

    # Now do a beat-level analysis within each bar to find the "da da da" rhythm
    print("=" * 80)
    print("BEAT-LEVEL ANALYSIS (per-beat energy in mids+high-mids for bars with vocal content)")
    print("=" * 80)
    print()

    # Identify bars with above-average vocal ratio
    avg_ratio = np.mean([r[3] for r in results])
    print(f"Average vocal ratio: {avg_ratio:.3f}")
    print()

    beat_duration = 60.0 / BPM  # ~0.464s
    # Split each beat into 2 halves to catch 8th-note patterns
    subdivision = 2
    sub_duration = beat_duration / subdivision

    for bar, bar_start, band_rms, vocal_ratio in results:
        # Print beat-level detail for ALL bars to see the pattern
        mins = int(bar_start) // 60
        secs = bar_start - mins * 60
        time_str = f"{mins}:{secs:05.2f}"

        print(f"Bar {bar:>2} ({time_str}) vocal_ratio={vocal_ratio:.3f}:")

        beat_energies = []
        for beat in range(4):
            for sub in range(subdivision):
                sub_start = bar_start + beat * beat_duration + sub * sub_duration
                sub_end = sub_start + sub_duration

                s_start = int(sub_start * sr)
                s_end = int(sub_end * sr)
                seg = y[s_start:s_end]

                S_sub = np.abs(librosa.stft(seg, n_fft=2048, hop_length=256))
                f_sub = librosa.fft_frequencies(sr=sr, n_fft=2048)

                # Vocal band energy (250Hz - 6kHz)
                vocal_mask = (f_sub >= 250) & (f_sub < 6000)
                vocal_rms = np.sqrt(np.mean(S_sub[vocal_mask, :] ** 2))

                # Kick band energy (20-250Hz)
                kick_mask = (f_sub >= 20) & (f_sub < 250)
                kick_rms = np.sqrt(np.mean(S_sub[kick_mask, :] ** 2))

                beat_label = f"  beat {beat+1}" if sub == 0 else f"       "
                sub_label = "a" if sub == 0 else "b"
                bar_chart_vocal = "#" * int(vocal_rms * 200)
                bar_chart_kick = "#" * int(kick_rms * 200)
                print(f"{beat_label}{sub_label}: vocal={vocal_rms:.4f} [{bar_chart_vocal[:40]:<40}] "
                      f"kick={kick_rms:.4f} [{bar_chart_kick[:40]:<40}]")

                beat_energies.append((vocal_rms, kick_rms))
        print()


if __name__ == "__main__":
    main()
