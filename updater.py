"""Auto-update for the installed Windows app. On launch, ask GitHub for the "eclipse-latest" release; if
its build (commit sha in the release notes) differs from ours, download EclipseSetup.exe, run it silently
and start Eclipse again once it finishes. Never blocks for long and never fails the launch.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

REPO = "jokingtim2468-max/localai2.0"
TAG = "eclipse-latest"
ROOT = os.path.dirname(os.path.abspath(__file__))


def local_build() -> str:
    try:
        return open(os.path.join(ROOT, "version.txt"), encoding="utf-8").read().strip()
    except OSError:
        return ""


def latest() -> tuple[str, str]:
    """(build sha, installer url) of the newest release, or ("", "")."""
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "Eclipse-updater"})
    with urllib.request.urlopen(req, timeout=4) as r:
        rel = json.load(r)
    m = re.search(r"build:\s*([0-9a-f]{7,40})", rel.get("body") or "")
    url = next((a["browser_download_url"] for a in rel.get("assets", []) if a["name"] == "EclipseSetup.exe"), "")
    return (m.group(1) if m else ""), url


def check_and_update() -> bool:
    """True if an update was started (the caller should exit so the installer can replace files)."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False) or os.environ.get("ECLIPSE_NO_UPDATE"):
        return False
    try:
        mine = local_build()
        sha, url = latest()
        if not sha or not url or not mine or sha.startswith(mine) or mine.startswith(sha):
            return False
        setup = os.path.join(tempfile.gettempdir(), "EclipseSetup.exe")
        urllib.request.urlretrieve(url, setup)
        exe = sys.executable
        # wait for the silent install, then reopen Eclipse; detached so this process can exit now
        ps = (f"Start-Process -FilePath '{setup}' -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"
              f"'/CLOSEAPPLICATIONS','/DIR=\"{os.path.dirname(exe)}\"' -Wait; Start-Process -FilePath '{exe}'")
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                         creationflags=0x00000008 | 0x00000200)           # DETACHED_PROCESS | NEW_PROCESS_GROUP
        return True
    except Exception:
        return False
