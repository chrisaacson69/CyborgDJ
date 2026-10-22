"""The controller CLI on a synthetic music library: spec in a project, tracks at the library root."""

import json
import sys

import pytest

from cyborgdj import cli


def test_list_transitions_from_a_project_spec(tmp_path, monkeypatch, capsys):
    (tmp_path / "analysis").mkdir()
    for f in ("a.wav", "b.wav"):
        (tmp_path / f).write_bytes(b"")
    specs = tmp_path / "CyborgProjects" / "P" / "specs"
    specs.mkdir(parents=True)
    spec = {
        "tracks": [{"id": 1, "name": "A", "file": "a.wav", "original_bpm": 124, "target_bpm": 124},
                   {"id": 2, "name": "B", "file": "b.wav", "original_bpm": 124, "target_bpm": 124}],
        "transitions": [{"from_track": 1, "to_track": 2, "type": "crossfade", "overlap_bars": 16}],
        "tracks_dir": "../music/",
    }
    (specs / "s.json").write_text(json.dumps(spec), encoding="utf-8")
    monkeypatch.chdir(tmp_path.parent)  # anywhere but the repo or the library
    monkeypatch.setattr(sys, "argv", ["cyborgdj", str(specs / "s.json"), "--list-transitions"])
    with pytest.raises(SystemExit) as done:  # --list-transitions lists and exits
        cli.main()
    assert done.value.code == 0
    out = capsys.readouterr().out
    assert "[0] A -> B (crossfade, 16 bars)" in out
