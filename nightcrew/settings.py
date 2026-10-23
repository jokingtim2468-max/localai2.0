"""settings.json in the data dir. Unknown keys are kept; missing keys get defaults."""
from __future__ import annotations

import json
import os
import threading

from . import paths

DEFAULTS = {
    "backend": "ollama",          # ollama | llamacpp | mlx  (llamacpp/mlx = OpenAI-compatible server)
    "backend_url": "",            # blank = backend default
    "model": "qwen-abliterated",  # ONE model for every tier: no swaps, nothing reloads on 8 GB VRAM
    "worker_model": "qwen-abliterated",
    "num_ctx": 16384,
    "think": False,               # only sent to models that support thinking
    "trust_workspace": True,      # file edits inside the workspace need no approval
    "workdir": "",                # blank = data/workspace
    "web": False,                 # web tools off unless switched on
    "blender_path": "",           # blank = auto-detect (PATH, Program Files, /Applications)
}
_LOCK = threading.Lock()


def _file():
    return paths.data("settings.json")


def load() -> dict:
    s = dict(DEFAULTS)
    try:
        with open(_file(), encoding="utf-8") as f:
            s.update(json.load(f))
    except (OSError, ValueError):
        pass
    return s


def save(changes: dict) -> dict:
    with _LOCK:
        s = load()
        s.update(changes or {})
        tmp = str(_file()) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
        os.replace(tmp, _file())       # atomic: a crash never leaves half a file
        return s
