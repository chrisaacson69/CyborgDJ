"""Batch export all DJ Set 1 tracks to Rekordbox XML using Camelot analysis data.

Run with the camelot_from_youtube venv:
    /path/to/camelot/env1/Scripts/python.exe scripts/export_rekordbox.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add camelot project to path so we can import rekordbox_export
CAMELOT_DIR = Path(r"C:\Users\Chris.Isaacson\source\repos\camelot_from_youtube")
sys.path.insert(0, str(CAMELOT_DIR))

from rekordbox_export import export_set, load_store_data

MUSIC_DIR = Path(r"C:\Users\Chris.Isaacson\source\repos\music")
OUTPUT_XML = CAMELOT_DIR / "rekordbox_collection.xml"

# Map: (project folder name in camelot, audio filename in music/)
TRACKS = [
    ("Martin Roth - Deep Style (Original Mix)", "Martin Roth - Deep Style (Original Mix).mp3"),
    ("Marsh feat. Mimi Page - Foss (Official Music Video)", "Marsh feat. Mimi Page - Foss (Official Music Video).mp3"),
    ("Alone (Extended Mix)", "Alone (Extended Mix).mp3"),
    ("Kasablanca - Am I Dreaming\uff1f (@Kasablanca)", "Kasablanca - Am I Dreaming\uff1f (@Kasablanca).mp3"),
    ("Orbital - Oto\u00f1o", "Orbital - Oto\u00f1o.mp3"),
    ("Simon Doty - Lady Danger (Extended Mix)", "Simon Doty - Lady Danger (Extended Mix).mp3"),
    ("You Are Sleeping (PQM Meets Luke Chable Vocal Pass)", "You Are Sleeping (PQM Meets Luke Chable Vocal Pass).mp3"),
    ("Quivver - Brothers & Sisters (Original Mix)", "Quivver - Brothers & Sisters (Original Mix).mp3"),
    ("Below The Belt (Chris Micali Remix)", "Below The Belt (Chris Micali Remix).mp3"),
    ("Ronski Speed & Syntrobic feat. Renee Stahl-Pink Skye", "Ronski Speed & Syntrobic feat. Renee Stahl-Pink Skye.mp3"),
    ("LTN - Daylight (Original Mix) [Enhanced Progressive]", "LTN - Daylight (Original Mix) [Enhanced Progressive].mp3"),
]


def main():
    tracks_data = []
    for project_name, audio_file in TRACKS:
        project_dir = CAMELOT_DIR / project_name
        audio_path = MUSIC_DIR / audio_file

        print(f"Loading: {project_name}")
        if not (project_dir / "analysis_cache.json").exists():
            print(f"  WARNING: No analysis_cache.json — skipping")
            continue
        if not audio_path.exists():
            print(f"  WARNING: Audio file not found at {audio_path} — skipping")
            continue

        store_data = load_store_data(project_dir)
        tracks_data.append({
            "audio_path": str(audio_path),
            "store_data": store_data,
        })
        tempo = store_data.get("tempo", "?")
        key_block = store_data.get("key", {})
        dom = key_block.get("key_summary", {}).get("dominant", {}) if key_block else {}
        camelot = dom.get("camelot", "?")
        print(f"  BPM: {tempo} | Key: {camelot}")

    print(f"\nExporting {len(tracks_data)} tracks to: {OUTPUT_XML}")
    result_path, num_tracks = export_set(
        tracks_data,
        output_path=OUTPUT_XML,
        playlist_name="DJ Set 1",
    )
    print(f"Done! {num_tracks} tracks in XML.")
    print(f"\nPoint Rekordbox at: {result_path}")
    print("  Preferences > Advanced > rekordbox xml > Browse")


if __name__ == "__main__":
    main()
