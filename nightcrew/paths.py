"""Where things live. Data is user-owned plain files.

Windows: %APPDATA%\\NightCrew   macOS: ~/Library/Application Support/NightCrew
Linux/dev: ~/.local/share/NightCrew.  Override with NIGHTCREW_DATA.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP = os.environ.get("NIGHTCREW_APP", "NightCrew")


def data_dir() -> Path:
    if os.environ.get("NIGHTCREW_DATA"):
        p = Path(os.environ["NIGHTCREW_DATA"])
    elif sys.platform == "win32":
        p = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / APP
    else:
        p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP
    p.mkdir(parents=True, exist_ok=True)
    return p


def data(*parts: str) -> Path:
    return data_dir().joinpath(*parts)


HERE = Path(__file__).resolve().parent
SKILLS_BUILTIN = HERE / "skills"
