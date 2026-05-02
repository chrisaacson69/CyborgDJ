import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json
import numpy as np
from pathlib import Path

CAMELOT_DIR = Path('C:/Users/Chris.Isaacson/source/repos/camelot_from_youtube')
SPEC_PATH = Path('C:/Users/Chris.Isaacson/source/repos/cyborgdj/specs/dj-set-1b.json')

spec = json.load(open(SPEC_PATH))
tracks = spec['tracks']
transitions = spec['transitions']

def find_track_dir(track):
    stem = Path(track['file']).stem
    d = CAMELOT_DIR / stem
    if d.exists():
        return d
    for p in CAMELOT_DIR.iterdir():
        if p.is_dir() and (p / 'analysis_cache.npz').exists():
            if stem.lower() in p.name.lower() or p.name.lower() in stem.lower():
                return p
    return None

track_data = {}
for t in tracks:
    tid = t['id']
    d = find_track_dir(t)
    if d and (d / 'analysis_cache.npz').exists():
        npz = np.load(str(d / 'analysis_cache.npz'))
        jdata = json.load(open(str(d / 'analysis_cache.json')))
        track_data[tid] = {
            'name': t['name'],
            'spectra': npz['bar_spectra'],
            'centers': npz['band_centers'],
            'n_bars': len(npz['bar_spectra']),
            'cue_in': int(t.get('cue_in_bar', 0)),
            'cue_out': int(t['cue_out_bar']),
            'lufs': jdata.get('lufs'),
            'loudness_dbfs': jdata.get('loudness_dbfs'),
        }
        print(f'  Track {tid}: {t["name"][:40]:40s} | {track_data[tid]["n_bars"]} bars | dir: {d.name}')
    else:
        print(f'  Track {tid}: {t["name"][:40]:40s} | NOT FOUND (dir: {d})')

print()
def find_crossover_bar(automation_points):
    if not automation_points:
        return None
    for i in range(1, len(automation_points)):
        prev_bar, prev_val = automation_points[i-1]
        curr_bar, curr_val = automation_points[i]
        if prev_val >= 0.5 and curr_val < 0.5:
            if prev_val == curr_val:
                return prev_bar
            frac = (0.5 - prev_val) / (curr_val - prev_val)
            return prev_bar + frac * (curr_bar - prev_bar)
        if prev_val <= 0.5 and curr_val > 0.5:
            frac = (0.5 - prev_val) / (curr_val - prev_val)
            return prev_bar + frac * (curr_bar - prev_bar)
    return None

for idx, trans in enumerate(transitions):
    from_id = trans['from_track']
    to_id = trans['to_track']

    if from_id not in track_data or to_id not in track_data:
        print(f'=== {from_id}->{to_id}: Missing track data, skipping ===')
        continue

    out_data = track_data[from_id]
    in_data = track_data[to_id]
    ttype = trans.get('type', 'crossfade')
    overlap = trans.get('overlap_bars', 0)

    if ttype == 'clean_cut' or overlap == 0:
        print(f'=== {from_id}->{to_id} ({out_data["name"][:20]} -> {in_data["name"][:20]}): CLEAN CUT ===')
        print()
        continue

    overlap_int = int(overlap)
    out_cue = out_data['cue_out']
    out_start = out_cue - overlap_int
    out_end = out_cue
    in_cue = in_data['cue_in']
    in_start = in_cue
    in_end = in_cue + overlap_int

    print(f'=== {from_id}->{to_id}: {out_data["name"][:30]} -> {in_data["name"][:30]} ===')
    print(f'  Type: {ttype}, Overlap: {overlap} bars')
    print(f'  Outgoing bars: {out_start}-{out_end} (of {out_data["n_bars"]})')
    print(f'  Incoming bars: {in_start}-{in_end} (of {in_data["n_bars"]})')

    out_start_c = max(0, out_start)
    out_end_c = min(out_data['n_bars'], out_end)
    in_start_c = max(0, in_start)
    in_end_c = min(in_data['n_bars'], in_end)

    if out_end_c <= out_start_c or in_end_c <= in_start_c:
        print(f'  WARNING: Invalid bar range, skipping')
        print()
        continue

    out_spec = out_data['spectra'][out_start_c:out_end_c]
    in_spec = in_data['spectra'][in_start_c:in_end_c]

    out_lufs = out_data.get('lufs')
    in_lufs = in_data.get('lufs')
    if out_lufs and in_lufs:
        out_offset = -out_lufs
        in_offset = -in_lufs
        out_spec_norm = out_spec + out_offset
        in_spec_norm = in_spec + in_offset
    else:
        out_spec_norm = out_spec
        in_spec_norm = in_spec

    out_energy = out_spec_norm.mean(axis=1)
    in_energy = in_spec_norm.mean(axis=1)

    min_len = min(len(out_energy), len(in_energy))
    crossover_bar = None
    for b in range(1, min_len):
        if in_energy[b] >= out_energy[b] and in_energy[b-1] < out_energy[b-1]:
            diff_prev = out_energy[b-1] - in_energy[b-1]
            diff_curr = out_energy[b] - in_energy[b]
            if diff_prev != diff_curr:
                frac = diff_prev / (diff_prev - diff_curr)
                crossover_bar = (b - 1) + frac
            else:
                crossover_bar = b
            break

    auto = trans.get('automation', {})
    outgoing_auto = auto.get('outgoing', [])
    incoming_auto = auto.get('incoming', [])

    out_handoff = find_crossover_bar(outgoing_auto) if outgoing_auto else None
    in_handoff = find_crossover_bar(incoming_auto) if incoming_auto else None
    handoff_bar = out_handoff or in_handoff

    if handoff_bar is None:
        fade_type = trans.get('fade_type', 'equal_power')
        if fade_type == 's_curve':
            handoff_bar = overlap_int / 2.0
        elif fade_type == 'exp':
            handoff_bar = overlap_int * 0.6
        else:
            handoff_bar = overlap_int / 2.0

    if crossover_bar is not None:
        print(f'  Energy crossover: bar {crossover_bar:.1f}')
    else:
        print(f'  Energy crossover: incoming never exceeds outgoing')
    print(f'  Automation handoff: bar {handoff_bar:.1f}')

    if crossover_bar is not None and handoff_bar is not None:
        delta = handoff_bar - crossover_bar
        if abs(delta) < 1.5:
            verdict = 'ALIGNED'
        elif delta > 0:
            verdict = f'LATE by {delta:.1f} bars (handoff after natural crossover)'
        else:
            verdict = f'EARLY by {-delta:.1f} bars (handoff before natural crossover)'
        print(f'  Timing: {verdict}')
    print(f'  Energy terrain (overlap bars, 2-bar avg):')
    for start in range(0, min_len, 2):
        end = min(start + 2, min_len)
        out_e = out_energy[start:end].mean()
        in_e = in_energy[start:end].mean()
        diff = in_e - out_e
        dominant = 'OUT' if out_e > in_e else 'IN '
        marker = ''
        if handoff_bar is not None and start <= handoff_bar < end:
            marker = ' << HANDOFF'
        if crossover_bar is not None and start <= crossover_bar < end:
            marker += ' << ENERGY CROSSOVER'
        print(f'    Bar {start:>3}-{end-1:>3}: OUT={out_e:>5.1f} IN={in_e:>5.1f} [{dominant}] gap={diff:>+5.1f}{marker}')

    out_mean = out_spec_norm.mean(axis=0)
    in_mean = in_spec_norm.mean(axis=0)
    centers = out_data['centers']

    bass_diff = in_mean[:8].mean() - out_mean[:8].mean()
    mid_diff = in_mean[8:20].mean() - out_mean[8:20].mean()
    high_diff = in_mean[20:].mean() - out_mean[20:].mean()

    print(f'  Spectral character diff (IN - OUT): bass={bass_diff:>+5.1f} mid={mid_diff:>+5.1f} high={high_diff:>+5.1f}')

    features = []
    if trans.get('eq_outgoing'):
        features.append('EQ out: ' + str([e['type'] + ' ' + str(e['frequency']) for e in trans['eq_outgoing']]))
    if trans.get('eq_incoming'):
        features.append('EQ in: ' + str([e['type'] + ' ' + str(e['frequency']) for e in trans['eq_incoming']]))
    if trans.get('eq_3band_outgoing'):
        features.append('3band out')
    if trans.get('eq_3band_incoming'):
        features.append('3band in')
    if trans.get('tempo_ramp'):
        tr = trans['tempo_ramp']
        features.append(f'tempo ramp {tr["start_bpm"]}->{tr["end_bpm"]}')
    if trans.get('overlap_gain_hump_db'):
        features.append(f'gain hump +{trans["overlap_gain_hump_db"]} dB')
    if features:
        print(f'  Features: {" | ".join(features)}')
    if min_len >= 4:
        out_deltas = np.diff(out_energy)
        in_deltas = np.diff(in_energy)

        big_out_drops = [(i, d) for i, d in enumerate(out_deltas) if d < -2.0]
        big_in_jumps = [(i, d) for i, d in enumerate(in_deltas) if d > 2.0]
        big_out_jumps = [(i, d) for i, d in enumerate(out_deltas) if d > 2.0]
        big_in_drops = [(i, d) for i, d in enumerate(in_deltas) if d < -2.0]

        if big_out_drops:
            print(f'  Notable outgoing energy drops: {[(f"bar {b}: {d:+.1f} dB") for b, d in big_out_drops]}')
        if big_in_jumps:
            print(f'  Notable incoming energy jumps: {[(f"bar {b}: {d:+.1f} dB") for b, d in big_in_jumps]}')
        if big_out_jumps:
            print(f'  Notable outgoing energy jumps: {[(f"bar {b}: {d:+.1f} dB") for b, d in big_out_jumps]}')
        if big_in_drops:
            print(f'  Notable incoming energy drops: {[(f"bar {b}: {d:+.1f} dB") for b, d in big_in_drops]}')

    print(f'  ---')
    if crossover_bar is not None and handoff_bar is not None:
        delta = handoff_bar - crossover_bar
        if abs(delta) > 3:
            print(f'  OPPORTUNITY: Handoff is {abs(delta):.1f} bars from natural crossover. Consider adjusting.')
        elif abs(delta) > 1.5:
            print(f'  MINOR: Handoff is {abs(delta):.1f} bars from natural crossover. Could fine-tune.')
        else:
            print(f'  GOOD: Handoff aligns with natural energy crossover.')

    if crossover_bar is None and min_len > 4:
        if (in_energy[:min_len] < out_energy[:min_len]).all():
            print(f'  NOTE: Incoming track is quieter throughout overlap. Current approach relies on EQ/filter to shape handoff.')
        elif (in_energy[:min_len] > out_energy[:min_len]).all():
            print(f'  NOTE: Incoming track is louder throughout overlap. Outgoing is already fading naturally.')

    print()
print('=== SUMMARY ===')
print('Transitions to investigate further:')
for idx, trans in enumerate(transitions):
    from_id = trans['from_track']
    to_id = trans['to_track']
    if from_id not in track_data or to_id not in track_data:
        continue
    if trans.get('type') == 'clean_cut':
        continue
    overlap_int = int(trans.get('overlap_bars', 0))
    if overlap_int == 0:
        continue
    out_data = track_data[from_id]
    in_data = track_data[to_id]
    out_cue = out_data['cue_out']
    in_cue = in_data['cue_in']
    out_start = max(0, out_cue - overlap_int)
    out_end = min(out_data['n_bars'], out_cue)
    in_start = max(0, in_cue)
    in_end = min(in_data['n_bars'], in_cue + overlap_int)
    out_spec = out_data['spectra'][out_start:out_end]
    in_spec = in_data['spectra'][in_start:in_end]
    min_len = min(len(out_spec), len(in_spec))
    if min_len < 2:
        continue
    out_energy = out_spec.mean(axis=1)
    in_energy = in_spec.mean(axis=1)

    mean_diff = abs(out_energy.mean() - in_energy.mean())
    print(f'  {from_id}->{to_id}: overlap={overlap_int} bars, mean energy diff={mean_diff:.1f} dB')
