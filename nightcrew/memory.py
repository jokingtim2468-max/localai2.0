"""Persistent memory: MEMORY.md as terse `key: value` lines in the data dir.
A same-key note overwrites the old one. Injected into the lead's system prompt."""
from __future__ import annotations

import re

from . import paths

BUDGET = 2000


def _file():
    return paths.data("MEMORY.md")


def lines() -> list[str]:
    try:
        return [l for l in _file().read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return []


def text() -> str:
    return "\n".join(lines())[-BUDGET:]


def remember(note: str) -> str:
    note = re.sub(r"\s+", " ", (note or "")).strip()
    if not note:
        return "error: empty note"
    key = note.split(":", 1)[0].strip().lower() if ":" in note else None
    keep = [l for l in lines() if not (key and l.split(":", 1)[0].strip().lower() == key)]
    keep.append(note)
    while sum(len(l) + 1 for l in keep) > BUDGET and len(keep) > 1:
        keep.pop(0)                       # oldest first
    _file().write_text("\n".join(keep) + "\n", encoding="utf-8")
    return "OK: remembered"


SCHEMA = {"type": "function", "function": {"name": "remember",
          "description": "Save one durable fact for future chats as 'key: value' (user preference, project decision). Same key overwrites.",
          "parameters": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]}}}
