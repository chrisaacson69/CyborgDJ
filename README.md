# CyborgDJ

Human writes the score, machine executes the mix.

A programmatic DJ mixing engine that reads a structured JSON spec and produces a continuous mixed audio file. Time-stretching, beat-aligned crossfades, EQ transitions, gain staging — all from a text config you can iterate on.

## The Idea

DJ mixing involves two kinds of work: **creative decisions** (track selection, transition design, energy arcs, EQ strategy) and **mechanical execution** (beat-matching, time-stretching, crossfading, rendering). CyborgDJ handles the execution. You handle the taste.

Your mix lives in a JSON spec file. Change a bar number, re-render, listen, repeat.

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

**System dependency:** The [Rubber Band Library](https://breakfastquay.com/rubberband/) must be installed for time-stretching.

- **Windows:** `pip install pyrubberband` includes pre-built binaries
- **macOS:** `brew install rubberband`
- **Linux:** `apt-get install rubberband-cli` or `apt-get install librubberband-dev`

### Run

```bash
# Render the full mix
python -m cyborgdj.cli specs/dj-set-1.json --tracks-dir /path/to/your/tracks/

# Render just one transition for quick iteration
python -m cyborgdj.cli specs/dj-set-1.json --transition 0 --tracks-dir /path/to/your/tracks/

# List all transitions
python -m cyborgdj.cli specs/dj-set-1.json --list-transitions
```

### Output

Rendered WAV files go to `output/` (gitignored).

## Project Structure

```
CyborgDJ/
├── cyborgdj/
│   ├── __init__.py
│   ├── loader.py        # Audio I/O, beat detection, bar grid computation
│   ├── stretcher.py     # Time-stretch via pyrubberband (Rubber Band Library)
│   ├── crossfader.py    # Crossfade math — fade curves, overlap mixing
│   ├── effects.py       # EQ and gain via pedalboard (Spotify/JUCE)
│   ├── engine.py        # Orchestrator — reads spec, coordinates everything
│   └── cli.py           # Command-line interface
├── specs/
│   └── dj-set-1.json    # Mix spec for DJ Set 1 (the tunable parameters)
├── output/              # Rendered audio (gitignored)
├── requirements.txt
└── README.md
```

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
| **soundfile** | Audio I/O (WAV, FLAC) |
| **librosa** | Beat detection, BPM analysis |
| **pyrubberband** | Time-stretching (Rubber Band Library) |
| **pedalboard** | EQ, filtering, gain (Spotify, JUCE-based) |
| **numpy** | Array math for mixing and crossfades |

## Related

- Built for [DJ Set 1](https://github.com/chrisaacson69/Vault/blob/main/projects/dj-set-1/README.md) — 11-track progressive/trance mix
- Analysis data from [Camelot From YouTube](https://github.com/chrisaacson69/camelot_from_youtube)
- Part of the [Set Mastering Pipeline](https://github.com/chrisaacson69/Vault/blob/main/projects/set-mastering/README.md)
