"""Old model vs tuned model on the held-out examples. For each one: give the model the
request (and the conversation up to the step being tested) and check whether its NEXT move
matches the reference: the right tool, or a direct answer when no tool is needed.
One model is loaded at a time (keep_alive=0) so 8 GB of VRAM is enough."""
from __future__ import annotations

import json

from .. import agent, backends, settings


def cases(eval_rows: list[dict], limit: int = 40) -> list[tuple[list, str]]:
    out = []
    for ex in eval_rows:
        msgs = ex["messages"]
        for i, m in enumerate(msgs):
            if m.get("role") == "assistant":
                want = (m.get("tool_calls") or [{}])[0].get("function", {}).get("name", "") or "<answer>"
                out.append((msgs[:i], want))
                break
        if len(out) >= limit:
            break
    return out


def score(model: str, tests: list[tuple[list, str]], backend=None, log=print) -> float:
    cfg = settings.load()
    be = backend or backends.get(cfg["backend"], cfg.get("backend_url", ""))
    tools = agent.tool_schemas()
    hits = 0
    for history, want in tests:
        got, text = "", ""
        for ev in be.stream_chat(model, [{"role": "system", "content": agent.SYSTEM_PROMPT}] + history,
                                 tools=tools, options={"num_ctx": 8192, "temperature": 0},
                                 keep_alive=0 if be.kind == "ollama" else None):
            text += ev.get("content", "")
            if ev.get("tool_calls") and not got:
                got = ev["tool_calls"][0]["function"]["name"]
        got = got or ("<answer>" if text.strip() else "")
        hits += got == want
    pct = round(100 * hits / max(1, len(tests)), 1)
    log(f"{model}: {hits}/{len(tests)} next steps right ({pct}%)")
    return pct


def compare(old: str, new: str, eval_rows: list[dict], backend=None, log=print) -> dict:
    tests = cases(eval_rows)
    a = score(old, tests, backend, log)
    b = score(new, tests, backend, log)
    return {"old": old, "new": new, "old_score": a, "new_score": b, "better": b > a, "n": len(tests)}
