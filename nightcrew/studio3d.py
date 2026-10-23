"""3D model studio backend: list/serve/save .glb files in the workspace and keep per-part comments.

Files live in the workspace (sandbox.jail). A part comment is stored next to the model in
<model>.comments.json so the agent (and later sessions) can read what was asked for each part.
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from . import sandbox

EXTS = {".glb", ".gltf"}
MAX_FILES = 500
MAX_SAVE = 200 * 2**20          # 200 MB


def list_models() -> list[dict]:
    root = sandbox.workspace()
    out = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in EXTS and p.is_file() and "node_modules" not in p.parts:
            out.append({"path": str(p.relative_to(root)), "size": p.stat().st_size})
            if len(out) >= MAX_FILES:
                break
    return out


def model_path(rel: str) -> Path:
    p = sandbox.jail(rel)
    if p.suffix.lower() not in EXTS:
        raise sandbox.ToolError("only .glb / .gltf files")
    return p


def save(rel: str, b64: str) -> dict:
    p = model_path(rel)
    data = base64.b64decode(b64)
    if len(data) > MAX_SAVE:
        raise sandbox.ToolError("file too large")
    if p.exists():                                 # keep one backup of the previous version
        p.with_suffix(p.suffix + ".bak").write_bytes(p.read_bytes())
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(p)
    return {"ok": True, "path": rel, "bytes": len(data)}


def _comments_file(p: Path) -> Path:
    return p.with_name(p.name + ".comments.json")


def comments(rel: str) -> list[dict]:
    f = _comments_file(model_path(rel))
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def add_comment(rel: str, part: str, text: str, point=None) -> list[dict]:
    p = model_path(rel)
    items = comments(rel)
    items.append({"ts": int(time.time()), "part": part[:200], "text": text[:4000], "point": point})
    _comments_file(p).write_text(json.dumps(items, indent=1), encoding="utf-8")
    return items


def agent_prompt(rel: str, part: str, text: str, info: dict | None = None) -> str:
    """What the chat agent is told when the user right-clicks a part and asks for a change."""
    p = model_path(rel)
    extra = f"\nPart details from the viewer: {json.dumps(info)}" if info else ""
    return (f"3D model edit request.\nModel file: {p}\nPart (object/mesh name): {part}{extra}\n"
            f"Request: {text}\n\n"
            "Edit the model with a headless Blender Python script (blender --background --factory-startup "
            "--python-exit-code 1 --python <abs script> -- <args>): import the .glb, change only that part as asked, "
            "and export back to the same path as GLB. Keep other parts unchanged. Report what you changed.")
