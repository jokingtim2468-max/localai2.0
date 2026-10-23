"""Training source `blender_code`: real, licensed Blender Python code as examples.

Each top-level function/class with a docstring becomes "Write a Blender (bpy) function `name`
that <docstring>" -> its source; each short script becomes "Write a Blender script that <module
docstring or file name>" -> the file. Only repositories WITH a licence are used (no licence =
all rights reserved). GPL code is fine for training a model you use yourself.
"""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
from pathlib import Path

from .. import paths

REPOS = [  # (git url, licence) - checked 2026-10-23
    ("https://github.com/bowber/bpy-city", "MIT"),
    ("https://github.com/lsimic/ProceduralBuildingGenerator", "GPL-3.0"),
    ("https://github.com/ChestMimic/blender-scripts", "GPL"),
]
MAX_CHARS = 9000


def blender_scripts_dir() -> Path | None:
    """Blender's bundled scripts folder (templates, startup, add-ons), from the installed Blender."""
    from . import media
    exe = media.find("blender")
    if not exe:
        return None
    root = Path(exe).resolve().parent
    for p in sorted(root.rglob("templates_py")):
        return p.parent              # scripts/: templates, startup operators, bundled add-ons (all GPL)
    return None


def fetch(log=print) -> list[Path]:
    """Clone (or reuse) the licensed repos into data/training/blender_code/."""
    base = paths.data("training", "blender_code")
    base.mkdir(parents=True, exist_ok=True)
    out = []
    for url, lic in REPOS:
        d = base / url.rstrip("/").split("/")[-1]
        if not d.exists() and shutil.which("git"):
            r = subprocess.run(["git", "clone", "-q", "--depth", "1", url, str(d)], capture_output=True, text=True, timeout=300)
            if r.returncode:
                log(f"blender_code: could not clone {url}: {r.stderr.strip()[:120]}")
                continue
        if d.exists():
            out.append(d)
    t = blender_scripts_dir()
    if t:
        out.append(t)
    return out


def _uses_bpy(src: str) -> bool:
    return "bpy" in src or "bmesh" in src or "mathutils" in src


def from_file(path: Path) -> list[dict]:
    src = path.read_text(encoding="utf-8", errors="ignore")
    if not _uses_bpy(src):
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    out, lines = [], src.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node)
            code = "\n".join(lines[node.lineno - 1: node.end_lineno])
            if doc and 80 < len(code) <= MAX_CHARS:
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                out.append({"messages": [
                    {"role": "user", "content": f"Write a Blender (bpy) {kind} `{node.name}` that {doc.strip().splitlines()[0].rstrip('.').lower()}."},
                    {"role": "assistant", "content": f"```python\n{code}\n```"}], "source": "blender_code"})
    if len(src) <= MAX_CHARS:
        what = ast.get_docstring(tree) or path.stem.replace("_", " ")
        out.append({"messages": [
            {"role": "user", "content": f"Write a complete Blender Python script: {what.strip().splitlines()[0]}"},
            {"role": "assistant", "content": f"```python\n{src}\n```"}], "source": "blender_code"})
    return out


def examples(log=print) -> list[dict]:
    rows = []
    for d in fetch(log):
        for f in sorted(d.rglob("*.py")):
            rows += from_file(f)
    log(f"blender_code: {len(rows)} examples from licensed Blender code")
    return rows
