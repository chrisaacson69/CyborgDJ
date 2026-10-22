"""The mix engine: render a spec to audio (stretch, EQ, crossfade, gain).

Needs grid results (tempo, first downbeat, bar frames), never analysis code: it must not
import librosa or dj-score's algorithms (enforced by import-linter, see pyproject.toml).
"""

from .mix import load_spec, render_mix, render_transition

__all__ = ["load_spec", "render_mix", "render_transition"]
