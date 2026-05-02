"""
Final focused analysis: Is the offbeat tonal energy in bars 1-15 a kick tail
or a separate tonal element? Compare the spectral shape of the offbeat energy
to confirm. Also do a proper dB-scale comparison for clarity.
"""

import numpy as np
import librosa

AUDIO_PATH = r"C:\Users\Chris.Isaacson\source\repos\music\Below The Belt (Chris Micali Remix).mp3"
BPM = 129.2
FIRST_BEAT_SAMPLE = 8688
SR = 44100
FIRST_BEAT_TIME = FIRST_BEAT_SAMPLE / SR
BAR_DURATION = 4 * 60.0 / BPM
BEAT_DURATION = 60.0 / BPM

def fmt_time(t):
    mins = int(t) // 60
    secs = t - mins * 60
    return f"{mins}:{secs:05.2f}"

def to_db(val, ref=1.0):
    return 20 * np.log10(max(val, 1e-10) / ref)

def make_bar(val_db, min_db=-60, max_db=0, width=25):
    """Bar chart on dB scale."""
    range_db = max_db - min_db
    if range_db == 0:
        return "." * width
    pos = (val_db - min_db) / range_db
    pos = max(0, min(1, pos))
    filled = int(round(pos * width))
    return "#" * filled + "." * (width - filled)

def main():
    print("Loading audio...")
    y, sr = librosa.load(AUDIO_PATH, sr=SR, mono=True)
    print(f"Loaded. Analyzing bars 0-16.")
    print()

    num_bars = 17
    eighth = BEAT_DURATION / 2

    # =========================================================================
    # dB-scale per-bar band energy table
    # =========================================================================
    print("=" * 110)
    print("PER-BAR FREQUENCY BAND ENERGY (dB relative to full scale)")
    print("=" * 110)
    print()

    n_fft = 4096
    header = (f"{'Bar':>3} {'Time':>8} | {'sub-bass':>8} {'bass':>8} {'lo-mid':>8} "
              f"{'mids':>8} {'hi-mid':>8} {'highs':>8} | {'VocRatio':>8} {'loMidJump':>9}")
    print(header)
    print("-" * len(header))

    prev_lo_mid = None
    for bar in range(num_bars):
        bar_start = FIRST_BEAT_TIME + bar * BAR_DURATION
        seg = y[int(bar_start * sr):int((bar_start + BAR_DURATION) * sr)]

        S = np.abs(librosa.stft(seg, n_fft=n_fft, hop_length=512))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        bands = {
            'sub-bass':  (20, 80),
            'bass':      (80, 250),
            'lo-mid':    (250, 500),
            'mids':      (500, 2000),
            'hi-mid':    (2000, 6000),
            'highs':     (6000, 22050),
        }

        rms = {}
        for name, (lo, hi) in bands.items():
            mask = (freqs >= lo) & (freqs < hi)
            rms[name] = np.sqrt(np.mean(S[mask, :] ** 2))

        vocal_e = rms['lo-mid'] + rms['mids'] + rms['hi-mid']
        kick_e = rms['sub-bass'] + rms['bass']
        ratio = vocal_e / kick_e if kick_e > 0 else 0

        lo_mid_jump = ""
        if prev_lo_mid is not None:
            pct = (rms['lo-mid'] - prev_lo_mid) / prev_lo_mid * 100
            if abs(pct) > 5:
                lo_mid_jump = f"{pct:+.1f}%"
        prev_lo_mid = rms['lo-mid']

        row = f"{bar:>3} {fmt_time(bar_start):>8} |"
        for name in bands:
            db = to_db(rms[name])
            row += f" {db:8.1f}"
        row += f" | {ratio:8.4f} {lo_mid_jump:>9}"
        print(row)

    # =========================================================================
    # Check for a tonal/pitched element in the offbeat
    # =========================================================================
    print()
    print("=" * 110)
    print("PITCH DETECTION: Looking for tonal content in offbeat 8th notes")
    print("Using librosa.pyin for pitch estimation on each 8th note")
    print("If the offbeat has a detectable pitch, it's a tonal element (not just kick tail)")
    print("=" * 110)
    print()

    for bar in [0, 2, 5, 8, 12, 15, 16]:
        bar_start = FIRST_BEAT_TIME + bar * BAR_DURATION
        print(f"Bar {bar} ({fmt_time(bar_start)}):")

        for e in range(8):
            e_start = bar_start + e * eighth
            e_end = e_start + eighth
            seg = y[int(e_start * sr):int(e_end * sr)]

            # Pitch detection using pyin
            f0, voiced_flag, voiced_prob = librosa.pyin(
                seg, fmin=50, fmax=2000, sr=sr,
                frame_length=2048, hop_length=256
            )

            # Get the most common pitch
            valid_f0 = f0[~np.isnan(f0)]
            beat_num = e // 2 + 1
            half = "a" if e % 2 == 0 else "&"

            if len(valid_f0) > 0:
                median_f0 = np.median(valid_f0)
                voiced_pct = np.sum(voiced_flag) / len(voiced_flag) * 100
                # Convert to note name (replace sharp symbol for Windows console)
                note = librosa.hz_to_note(median_f0).replace('\u266f', '#')
                midi = librosa.hz_to_midi(median_f0)
                print(f"  {beat_num}{half}: pitch={median_f0:7.1f}Hz ({note:>4}) "
                      f"voiced={voiced_pct:4.0f}% "
                      f"confidence={np.mean(voiced_prob[voiced_flag]):5.3f}")
            else:
                print(f"  {beat_num}{half}: no pitch detected (unpitched/noise)")

        print()

    # =========================================================================
    # FINAL: Compare bar 15 beat 3&-4 to bar 16 beat 1-2
    # This is the exact transition where "da da da" might start
    # =========================================================================
    print()
    print("=" * 110)
    print("TRANSITION DETAIL: Bar 15 beat 3 through Bar 16 beat 2")
    print("16th-note resolution to catch exact onset of vocal pattern")
    print("=" * 110)
    print()

    sixteenth = BEAT_DURATION / 4

    # Bar 15, beats 3-4 and Bar 16, beats 1-2
    for bar in [15, 16]:
        bar_start = FIRST_BEAT_TIME + bar * BAR_DURATION
        start_beat = 0 if bar == 16 else 2  # beats 3-4 of bar 15, beats 1-2 of bar 16
        end_beat = 2 if bar == 16 else 4

        print(f"Bar {bar} ({fmt_time(bar_start)}):")
        for beat in range(start_beat, end_beat):
            for sub in range(4):  # 16th notes
                s_start = bar_start + beat * BEAT_DURATION + sub * sixteenth
                s_end = s_start + sixteenth
                seg = y[int(s_start * sr):int(s_end * sr)]

                # RMS in formant range
                S = np.abs(librosa.stft(seg, n_fft=2048, hop_length=64))
                f = librosa.fft_frequencies(sr=sr, n_fft=2048)

                lo_mask = (f >= 20) & (f < 250)
                mid_mask = (f >= 250) & (f < 3000)
                hi_mask = (f >= 3000) & (f < 16000)

                lo_rms = np.sqrt(np.mean(S[lo_mask, :] ** 2))
                mid_rms = np.sqrt(np.mean(S[mid_mask, :] ** 2))
                hi_rms = np.sqrt(np.mean(S[hi_mask, :] ** 2))

                beat_label = f"  B{beat+1}" if sub == 0 else "    "
                sub_labels = ['a', 'e', '&', 'a']  # standard 16th note names: 1-e-&-a
                sub_name = sub_labels[sub]

                lo_bar = make_bar(to_db(lo_rms), -30, 0, 12)
                mid_bar = make_bar(to_db(mid_rms), -30, 0, 12)

                print(f"{beat_label} {sub_name}: lo={to_db(lo_rms):6.1f}dB[{lo_bar}] "
                      f"mid={to_db(mid_rms):6.1f}dB[{mid_bar}] "
                      f"hi={to_db(hi_rms):6.1f}dB")

        print()


if __name__ == "__main__":
    main()
