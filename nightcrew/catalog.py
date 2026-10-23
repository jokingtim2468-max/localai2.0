"""Model recommendations: an abliterated list and a regular list, each sorted by how well it
fits THIS machine. Every name below was checked on ollama.com (2026-10-23); sizes are the
default Q4 download. `need` adds ~1.5 GB for a 16k context with a q4_0 KV cache.

fit: "fits" = whole model on the GPU / in unified memory (fast)
     "tight" = a little spills to RAM (works, slower)
     "too big" = do not bother on this machine
"""
from __future__ import annotations

from . import hardware

CTX_GB = 1.5

# (name, gb on disk, kind, best for, tools?, thinks?)
MODELS = [
    # ---- abliterated (refusals removed) ----
    ("qwen-abliterated", 4.7, "abliterated", "Night Crew's standard: all-round agent + code", True, False),
    ("huihui_ai/qwen2.5-coder-abliterate:3b", 1.9, "abliterated", "fast small coder, low memory", True, False),
    ("huihui_ai/qwen2.5-coder-abliterate:7b", 4.7, "abliterated", "coding", True, False),
    ("huihui_ai/qwen2.5-coder-abliterate:14b", 9.0, "abliterated", "coding, bigger projects", True, False),
    ("huihui_ai/qwen2.5-coder-abliterate:32b", 20.0, "abliterated", "best abliterated coder", True, False),
    ("huihui_ai/qwen2.5-abliterate:7b", 4.7, "abliterated", "general chat + tools", True, False),
    ("huihui_ai/qwen2.5-abliterate:14b", 9.0, "abliterated", "general, stronger reasoning", True, False),
    ("huihui_ai/qwen3-abliterated:4b", 2.5, "abliterated", "small, can think step by step", True, True),
    ("huihui_ai/qwen3-abliterated:8b", 5.2, "abliterated", "agent work, can think", True, True),
    ("huihui_ai/qwen3-abliterated:14b", 9.3, "abliterated", "agent work, stronger", True, True),
    ("huihui_ai/qwen3-abliterated:30b", 19.0, "abliterated", "fast MoE (3B active), strong", True, True),
    ("huihui_ai/qwen3-abliterated:32b", 20.0, "abliterated", "strongest qwen3 abliterated", True, True),
    ("huihui_ai/qwen3-coder-abliterated:30b", 19.0, "abliterated", "coding agent, MoE", True, False),
    ("huihui_ai/deepseek-r1-abliterated:8b", 5.2, "abliterated", "reasoning / hard bugs (slow)", False, True),
    ("huihui_ai/deepseek-r1-abliterated:14b", 9.0, "abliterated", "reasoning, stronger", False, True),
    ("huihui_ai/gemma3-abliterated:12b", 8.1, "abliterated", "chat + reads images", False, False),
    ("huihui_ai/llama3.3-abliterated:70b", 43.0, "abliterated", "biggest general model", True, False),
    # ---- regular ----
    ("llama3.2:3b", 2.0, "regular", "tiny, fast, low memory", True, False),
    ("qwen2.5-coder:3b", 1.9, "regular", "small coder / worker", True, False),
    ("qwen2.5-coder:7b", 4.7, "regular", "coding", True, False),
    ("qwen2.5-coder:14b", 9.0, "regular", "coding, bigger projects", True, False),
    ("qwen2.5-coder:32b", 20.0, "regular", "best open coder in this size", True, False),
    ("qwen3:4b", 2.5, "regular", "small agent, can think", True, True),
    ("qwen3:8b", 5.2, "regular", "agent work, can think", True, True),
    ("qwen3:14b", 9.3, "regular", "agent work, stronger", True, True),
    ("qwen3:30b", 19.0, "regular", "fast MoE, strong", True, True),
    ("qwen3-coder:30b", 19.0, "regular", "coding agent, MoE", True, False),
    ("llama3.1:8b", 4.9, "regular", "general chat + tools", True, False),
    ("deepseek-coder-v2:16b", 8.9, "regular", "coding, MoE", False, False),
    ("gemma3:4b", 3.3, "regular", "small, reads images", False, False),
    ("gemma3:12b", 8.1, "regular", "chat + reads images", False, False),
    ("gemma3:27b", 17.0, "regular", "strong, reads images", False, False),
    ("llama3.3:70b", 43.0, "regular", "biggest general model", True, False),
]


def fit(need: float, usable: float) -> str:
    if need <= usable:
        return "fits"
    if need <= usable * 1.25:
        return "tight"
    return "too big"


def recommend(info: dict | None = None, installed: set | None = None) -> dict:
    info = info or hardware.detect()
    usable = hardware.usable_gb(info)
    have = installed or set()
    order = {"fits": 0, "tight": 1, "too big": 2}
    out = {"usable_gb": round(usable, 1), "abliterated": [], "regular": []}
    for name, gb, kind, good, tools, thinks in MODELS:
        need = round(gb + CTX_GB, 1)
        out[kind].append({"name": name, "gb": gb, "need_gb": need, "fit": fit(need, usable),
                          "good_for": good, "tools": tools, "thinks": thinks,
                          "installed": name in have or f"{name}:latest" in have})
    for kind in ("abliterated", "regular"):
        # best first: things that fit, then the biggest (= strongest) of those, agents before chat-only
        out[kind].sort(key=lambda m: (order[m["fit"]], not m["tools"], -m["gb"] if m["fit"] != "too big" else m["gb"]))
        top = next((m for m in out[kind] if m["fit"] == "fits" and m["tools"]), None)
        out[kind + "_pick"] = top["name"] if top else ""
    return out
