# CyborgDJ audit — code, data, and the engine boundary (2026-10-22)

The same cleanup as camelot's ([dj-score `MIGRATION.md`](https://github.com/chrisaacson69/dj-score/blob/main/MIGRATION.md)):
this repo holds code only. Analysis belongs to dj-score, tracks and their analysis to the shared music library
(`../music`, `analysis/<track>/`), and mix work to per-project folders. Rule: copy → repoint → archive; nothing
is purged. Each script is sorted by the loop it serves (plan / render / verify / tune; see the vault's *CyborgDJ as
Controller* page).

## Headline: the specs render on contaminated tempos

The renderer already builds a **fixed-tempo grid** (`loader.compute_bar_frames`) from the spec's `original_bpm`
and a first downbeat. Those BPMs are camelot's tempogram bin centres (120.19, 123.05, 126.05, 129.2); the comb
grid (dj-score `rigidgrid`, identical to the September bench, matching Rekordbox on its native analyses)
measures:

| Track | spec | measured | error |
|---|---|---|---|
| Marsh – Foss | 123.05 | 121.997 | +0.86% |
| Orbital – Otoño | 126.05 | 124.988 | +0.85% |
| Flip of the Coin, Quicksilver (flip-quicksilver v1–v7) | 123.0 | 121.997 (Rekordbox 122.00) | +0.82% |
| Martin Roth – Deep Style | 120.19 | 120.995 | −0.67% |
| Below The Belt, LTN – Daylight | 129.2 | 129.999 | −0.61% |

A 0.86% error on a rigid grid drifts about 1 s (two beats) every two minutes. Every spec also carries a
hand-set `first_beat_sample`, re-tuned across versions (Quicksilver 33280 → 37616; Quivver 73735 → 73415 → 71729):
hand phase compensating for a wrong tempo. **Fix:** specs stop holding hand-typed grid numbers; the renderer
reads tempo and downbeat from the track's analysis in the library (comb grid), with a spec override only where
the ear disagrees.

## Code verdicts

| File | Loop | Verdict |
|---|---|---|
| `cyborgdj/engine.py`, `crossfader.py`, `effects.py`, `stretcher.py` | render | **keep** as the engine package |
| `cyborgdj/loader.py` | render + analysis | **split**: audio I/O stays in the engine (*corrected:* moving it to dj-score's `AudioLoader` would pull librosa into the engine, against finding 3 below; ffmpeg runs here, only `ffprobe` is blocked); `detect_first_downbeat` + `compute_bar_frames` (the third grid) → the dj-score grid, read from the library; `trim_to_bars`, `bar_to_sample`, `apply_loop` stay (render operations on a given grid) |
| `cyborgdj/cli.py` | render | **keep** the render CLI; its `analyze_tracks` report → `dj-score bpm --grid comb` |
| `tests/test_eq_automation.py` | render | **keep** |
| `scripts/spectral_collision.py` | plan | **retire** → `dj-score pair` (a fork) |
| `scripts/analyze_track.py` | plan | **retire** → dj-score services (a hand rebuild of camelot's pipeline) |
| `scripts/export_rekordbox.py` | plan | **retire** → `dj-score export`; unblocks archiving camelot's `rekordbox_export.py` |
| `scripts/snap_cues_to_bars.py` | plan | **decide**: fold into `dj-score export` (cues on the bar grid) or retire once export uses the comb grid |
| `spectral_terrain.py` | verify | **keep, repoint** (done): a controller report joining spec automation and spectra (crossover bar per transition). Caveat: it indexes camelot's cached spectra (DP-grid bars) by the spec's bar numbers (CyborgDJ's own grid), so its EARLY/LATE readings are only as good as the agreement between two grids; resolved when specs take their grid from the library |
| `scripts/render_eq_1_2.py`, `render_eq_test.py` | tune | **move to the dj-set-1b project**: hand A/B sweeps of EQ automation, the precursors of the knob-sweep loop |
| `analyze_btb_*.py` (6) | — | **archive**: one-off investigation of a vocal pattern in Below The Belt, bars 0–16 |
| `reverse-engineer/dinka-giga-mix/*.py` | tune | **its own project** (below); `align_to_master.py` is already converted (dj-score `alignment`) |
| `bootstrap.py` | — | **archive**: a 6-line base64 file writer with a hardcoded path, not part of the tool |

Every script outside the package hardcodes absolute paths (`C:\…\source\repos\camelot_from_youtube`,
`…\repos\music`), which are already stale since the repos moved. README drift: it lists pedalboard for EQ;
`effects.py` uses scipy.

## Data verdicts

| Today | What | Home |
|---|---|---|
| `music/*.vtt`, `*_transcript.txt` | DJ tutorial transcripts | the vault (`raw/` capture + page) |
| `music/Yes Baby.mp3`, `reverse-engineer/.../tracks/*` | tracks | the music library |
| `camelot/<track>/key_analysis.json` (5, tracked) | copied camelot output | the library's `analysis/<track>/`; **the only key analysis for 4 tracks**; Waves' copy is stale |
| `specs/*.json` (28) | mix projects: dj-set-1 (1, 1a, 1b), flip-quicksilver v1–v7, pqm-quivver t07, quivver-btb t08, warung-flip, dinka t01–t03 | per-project folders |
| `music/playlist.csv` | skeleton of another mix | its project folder |
| `output/` (628 MB, untracked) | renders | per-project folders |
| `reverse-engineer/dinka-giga-mix/` (556 MB, untracked) | a pro mix, its 4 source tracks, analysis scripts, transition renders | its own project (learn transition settings from a professional) |
| `rubberband-bin/`, `rubberband-win.zip` | tool binary | a documented install step, not repo content |

## The engine boundary (is the mixer its own library?)

1. **Run-time needs:** the renderer needs grid *results* (tempo, downbeat, bar frames) and cues, not analysis
   code; the one exception, `loader.detect_first_downbeat`, is replaced by the library's analysis.
2. **Second consumer:** already exists. `align_to_master.py` imports `cyborgdj.stretcher`, and the knob sweep
   will render trials in bulk.
3. **Dependencies:** the engine needs numpy, scipy, soundfile and pyrubberband, not librosa. Analysis is the
   reverse.

So the engine has a clean edge. Proposal: `cyborgdj/engine/` as its own package now, behind an import-linter
boundary (it may import dj-score's data model, never its algorithms). Split it into its own repo when the
sweep becomes a real consumer.

## Decided (Chris, 2026-10-22)

- **Project folders:** `music/CyborgProjects/<project>/` in the shared library, to become configurable.
- **Projects:** `dj-set-1b` (completed; its specs 1, 1a, 1b and transition studies t07/t08), the
  `playlist.csv` mix (only started), and `dinka-giga-mix` (a reverse-engineering proof of concept, resolved quickly).
  Open: `flip-quicksilver` (v1–v7) and `warung-flip` (v0–v3) use tracks outside all three.
- **`snap_cues_to_bars.py`:** fold into dj-score export. It was useful for placing approximate cues that the
  user then fine-tunes.
- **Tempo fix:** listen first. A/B renders of dj-set-1b transition 1 (Foss → Alone) are in
  `music/CyborgProjects/dj-set-1b/renders/foss-tempo-ab/`. A is the spec (123.05, hand anchor 14.687 s). B is the measured 121.997, with the anchor snapped
  +189 ms onto the nearest real beat (the hand anchor sat almost half a beat early). **Heard (Chris):** "so
  close that it is very hard to tell, but B does sound a little cleaner." By the overlap Foss's kicks have faded,
  so the mistiming sounds like a warble rather than double beats. These dense tracks are hard to separate by
  instrument, which is why a locked grid tends to beat a detector: it assumes the beat through the gaps. Small
  differences like this are what an objective check would catch: dj-score measuring kick alignment in the
  rendered overlap (the *verify* loop).
- **Fourth project:** Flip of the Coin / Warung / Quicksilver (`flip-quicksilver` v1–v7, `warung-flip` v0–v3).
  It started with some hard transitions and never got going.

## Status (2026-10-22)

Done, each step verified by the engine tests and a render oracle (4 transitions re-rendered byte-identical):

1. **Data out** (`5545168`): 60 moves, nothing deleted; tracked files copied and compared before removal.
2. **Engine package** (`61aae10`): `cyborgdj/engine/` behind an import-linter boundary (no librosa, no CLI;
   a planted violation is caught); specs resolve tracks and renders from their own location.
3. **`spectral_terrain`** (`4507bdf`): repointed; its output matches the original's line for line.
4. **Archive** (`458adf2`): superseded scripts moved to a local, gitignored `archive/<tool>/`; the project notes
   `scripts/EZ.txt` and `Loud.txt` moved to their projects.
5. **Docs**: README, requirements, spec files read as UTF-8.
6. **Engine split out** (Chris: "the dependency issues are key here"): `cyborgdj/engine/` became the library
   [dj-render](https://github.com/chrisaacson69/dj-render), so CyborgDJ is now a controller over dj-score and
   dj-render, with the MCP layer to sit on top of both. Renders through the new package: byte-identical.

Left, in order:
- **Grid from the library.** Specs keep their hand-typed `original_bpm` and `first_beat_sample` until the renderer
  can read the comb grid from `music/analysis/<track>/`. That changes renders, so it is gated on listening
  (the Foss A/B was "a little cleaner") and on an objective verify step (kick alignment in the overlap).
- **`snap_cues_to_bars`** folds into dj-score's export (approximate cues on the bar grid for the user to fine-tune).
- **camelot's `rekordbox_export.py`** can now be archived: nothing live imports it.
