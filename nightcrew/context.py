"""Keep a chat inside the model's context window.

collapse(): old tool output -> head/tail. compact(): when still too big, SUMMARISE the
oldest turns into one "[earlier in this chat]" note (deleting them made the model forget
files it had just written). Newest messages stay verbatim; a tool result is never split
from its call; summaries are cached by span fingerprint.
"""
from __future__ import annotations

import hashlib
import json

_CACHE: dict[str, str] = {}


def size(msgs) -> int:
    return sum(len(json.dumps(m, default=str)) for m in msgs)


def collapse(msgs, keep_recent: int = 6, limit: int = 1500) -> None:
    for m in msgs[:-keep_recent]:
        c = m.get("content")
        if m.get("role") == "tool" and isinstance(c, str) and len(c) > limit:
            m["content"] = c[: limit // 2] + f"\n…({len(c) - limit} chars collapsed)…\n" + c[-limit // 2:]


def _cut(msgs, start: int, keep_recent: int) -> int:
    """End index of the span to summarise, never leaving a tool result orphaned."""
    end = max(start, len(msgs) - keep_recent)
    while end < len(msgs) and msgs[end].get("role") == "tool":
        end += 1
    return end


def trim(msgs, budget: int, keep_recent: int = 6) -> int:
    head = 1 if msgs and msgs[0].get("role") == "system" else 0
    dropped = 0
    while size(msgs) > budget and len(msgs) - head > keep_recent:
        msgs.pop(head)
        dropped += 1
        while len(msgs) > head and msgs[head].get("role") == "tool":
            msgs.pop(head)
            dropped += 1
    return dropped


def compact(msgs, budget: int, summarise=None, keep_recent: int = 6) -> dict:
    if size(msgs) <= budget:
        return {"compacted": 0}
    head = 1 if msgs and msgs[0].get("role") == "system" else 0
    end = _cut(msgs, head, keep_recent)
    span = msgs[head:end]
    if not span:
        return {"compacted": 0}
    if summarise is None:
        return {"compacted": trim(msgs, budget, keep_recent)}
    text = "\n".join(f"{m.get('role')}: {str(m.get('content') or '')[:2000]}" for m in span)
    key = hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()
    try:
        note = _CACHE.get(key) or summarise(text)
    except Exception:
        note = ""
    if not note:
        return {"compacted": trim(msgs, budget, keep_recent)}
    _CACHE[key] = note
    msgs[head:end] = [{"role": "user", "content": "[earlier in this chat] " + note}]
    extra = trim(msgs, budget, keep_recent) if size(msgs) > budget else 0
    return {"compacted": len(span) + extra}
