# CyborgDJ

Human writes the score, machine executes the mix.

A programmatic DJ mixing engine that reads a structured JSON spec and produces a continuous mixed audio file. Time-stretching, beat-aligned crossfades, EQ transitions, gain staging — all from a text config you can iterate on.

## The Idea

DJ mixing involves two kinds of work: **creative decisions** (track selection, transition design, energy arcs, EQ strategy) and **mechanical execution** (beat-matching, time-stretching, crossfading, rendering). CyborgDJ handles the execution. You handle the taste.

Your mix lives in a JSON spec file. Change a bar number, re-render, listen, repeat.

## Quick Start

### Install

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # the render library, dj-render (clone it beside this repo)
```

**System dependency:** the [Rubber Band](https://breakfastquay.com/rubberband/) command-line tool must be on `PATH`
for time-stretching (pyrubberband calls it). On Windows, unzip the release (e.g. `rubberband-4.0.0-gpl-executable-windows`)
and add its folder to `PATH`; on macOS `brew install rubberband`; on Linux `apt-get install rubberband-cli`.
MP3 sources are decoded with `ffmpeg`, which must also be on `PATH`.

### Where things live

Tracks and mix projects live in a **shared music library** outside this repo (commercial audio is never committed):

```
music/                              originals (mp3/wav), shared by every tool
music/analysis/<track>/             each track's analysis (dj-score / camelot caches)
music/CyborgProjects/<project>/     a mix project: specs/, renders/, notes
```

A spec finds its tracks from where the spec file lives (beside it, then the library root, then the project's
`tracks/`), and renders go to the project's `renders/` folder, so you can run from any directory.

### Run

```bash
# Render the full mix
python -m cyborgdj ../music/CyborgProjects/Preach/specs/dj-set-1b.json

# Render just one transition for quick iteration
python -m cyborgdj ../music/CyborgProjects/Preach/specs/dj-set-1b.json --transition 0

# List all transitions
python -m cyborgdj ../music/CyborgProjects/Preach/specs/dj-set-1b.json --list-transitions

# Where each transition's energy crossover falls against its automation handoff
python scripts/spectral_terrain.py ../music/CyborgProjects/Preach/specs/dj-set-1b.json
```

## Project Structure

```
cyborgdj/
├── cyborgdj/cli.py      # the controller's command line
├── scripts/             # controller-side tools (spectral_terrain, snap_cues_to_bars)
├── tests/
└── AUDIT.md             # 2026-10-22 cleanup: what moved where, and why
```

CyborgDJ is the **controller** over two libraries: [dj-score](https://github.com/chrisaacson69/dj-score) measures
(beat grids, key, events, spectra, Rekordbox export) and [dj-render](https://github.com/chrisaacson69/dj-render)
renders (stretch, EQ, crossfade, gain). It holds no analysis or rendering code of its own (`lint-imports`).

## The Mix Spec

Everything tunable lives in a JSON file. The engine just reads and executes.

```json
{
  "tracks": [
    {
      "id": 1,
      "name": "Martin Roth — Deep Style",
      "file": "deep-style.wav",
      "original_bpm": 120.19,
      "target_bpm": 123.05,
      "cue_in_bar": 59,
      "cue_out_bar": 175,
      "gain_db": 0
    }
  ],
  "transitions": [
    {
      "from_track": 1,
      "to_track": 2,
      "type": "crossfade",
      "overlap_bars": 16,
      "fade_type": "equal_power",
      "eq_outgoing": null,
      "eq_incoming": null
    }
  ]
}
```

### Track Fields

| Field | Description |
|-------|-------------|
| `original_bpm` | Track's native BPM (from analysis) |
| `target_bpm` | Desired BPM (engine time-stretches to match) |
| `cue_in_bar` | Start playback at this bar |
| `cue_out_bar` | End playback at this bar |
| `gain_db` | Volume adjustment in dB |

### Transition Fields

| Field | Description |
|-------|-------------|
| `type` | `"crossfade"` or `"clean_cut"` |
| `overlap_bars` | Number of bars where both tracks play |
| `fade_type` | `"linear"`, `"equal_power"`, or `"s_curve"` |
| `eq_outgoing` | EQ bands applied to outgoing track's overlap zone |
| `eq_incoming` | EQ bands applied to incoming track's overlap zone |

### EQ Bands

```json
{
  "type": "highpass",
  "frequency": 500,
  "q": 0.707
}
```

Types: `highpass`, `lowpass`, `low_shelf`, `high_shelf`, `peak`. Shelf and peak filters accept `gain_db`.

## Iteration Workflow

The whole point is fast iteration:

1. Edit a bar number or fade type in the JSON spec
2. Re-render just that transition: `--transition N`
3. Listen
4. Repeat

A single transition renders in seconds. The full 11-track set takes longer but you only render that once you're happy with individual transitions.

## Tech Stack

| Library | Role |
|---------|------|
| **soundfile** (+ ffmpeg for MP3) | Audio I/O |
| **pyrubberband** (Rubber Band CLI) | Time-stretching |
| **scipy** | EQ, filtering, onset detection for the first downbeat |
| **numpy** | Array math for mixing and crossfades |

## Related

- Built for [DJ Set 1](https://github.com/chrisaacson69/Vault/blob/main/projects/dj-set-1/README.md) — 11-track progressive/trance mix
- Analysis from [dj-score](https://github.com/chrisaacson69/dj-score) (the shared analysis library; formerly camelot_from_youtube)
- Part of the [Set Mastering Pipeline](https://github.com/chrisaacson69/Vault/blob/main/projects/set-mastering/README.md)
