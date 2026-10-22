"""4-tier debugging escalation: Buddy -> Parent (Hermes) -> Swarm -> Mr. Debug.

Every tier runs on the SAME resident model (settings.model, default qwen-abliterated), so
a handoff never loads a second model into the 8 GB card. Tiers are fresh calls (no chat
history) that see only the brief: the problem, the code/error excerpt, what was tried.

VRAM rules:
- resident model: keep_alive=-1 (stays loaded, the handoff costs nothing)
- any OTHER model a tier is configured to use: keep_alive=0, so it unloads right after,
  and settings never allow two models at once (Ollama started with MAX_LOADED_MODELS=1).
- Swarm runs its 3 attempts one after another, never in parallel.
"""
from __future__ import annotations

from . import backends, settings

TIERS = ["buddy", "parent", "swarm", "mr_debug"]

ROLE = {
    "buddy": "You are Buddy, a quick second pair of eyes. Read the error and code. Give the most likely cause in one sentence and the exact fix (a code patch). Keep it short.",
    "parent": "You are Hermes, the parent reviewer. Buddy's fix did not work. Re-read everything, list the 2-3 real candidate causes ranked, then give the fix for the top one as a code patch and how to verify it.",
    "swarm": "You are one member of a debugging swarm. Propose ONE independent hypothesis for this bug that differs from the previous attempts, with a code patch and a command that proves or disproves it.",
    "mr_debug": "You are Mr. Debug, the last resort. Work from first principles: restate the expected vs actual behaviour, trace the data flow step by step, name the exact line where it diverges, and give a minimal patch plus a test that would have caught it. If the information is not enough, say exactly which log, value or file you need.",
}


def _ask(be, model: str, role: str, brief: str, resident: str) -> str:
    keep = -1 if model == resident else 0          # a foreign model unloads right away
    out = ""
    for ev in be.stream_chat(model, [{"role": "system", "content": role}, {"role": "user", "content": brief}],
                             options={"num_ctx": int(settings.load().get("num_ctx") or 16384)},
                             keep_alive=keep if be.kind == "ollama" else None):
        out += ev.get("content", "")
    return out.strip() or "(no answer)"


def next_tier(tier: str) -> str:
    i = TIERS.index(tier) if tier in TIERS else -1
    return TIERS[min(i + 1, len(TIERS) - 1)]


def escalate(problem: str, tier: str = "buddy", tried: str = "", backend=None) -> str:
    cfg = settings.load()
    be = backend or backends.get(cfg["backend"], cfg.get("backend_url", ""))
    resident = cfg.get("model") or "qwen-abliterated"
    model = cfg.get(f"tier_{tier}_model") or resident
    tier = tier if tier in TIERS else "buddy"
    brief = f"PROBLEM:\n{problem}\n\nALREADY TRIED (did not work):\n{tried or 'nothing yet'}"
    if tier == "swarm":
        ideas = []
        for n in range(3):                      # sequential: one model in VRAM at a time
            seen = "\n\n".join(ideas) or "none"
            ideas.append(f"[swarm {n + 1}] " + _ask(be, model, ROLE["swarm"], brief + f"\n\nOTHER SWARM IDEAS:\n{seen}", resident))
        answer = "\n\n".join(ideas)
    else:
        answer = _ask(be, model, ROLE[tier], brief, resident)
    nxt = next_tier(tier)
    tail = f"\n\nIf this does not fix it, call escalate_debug with tier='{nxt}'." if nxt != tier else ""
    return f"[{tier}]\n{answer}{tail}"


SCHEMA = {"type": "function", "function": {"name": "escalate_debug",
          "description": "Ask for debugging help when a fix keeps failing. Tiers in order: buddy (quick fix), parent (ranked causes), swarm (3 independent hypotheses), mr_debug (first-principles trace). Start at buddy; go up one tier each time a fix fails.",
          "parameters": {"type": "object", "properties": {
              "problem": {"type": "string", "description": "the error text and the relevant code"},
              "tier": {"type": "string", "enum": TIERS},
              "tried": {"type": "string", "description": "fixes already tried"}},
              "required": ["problem"]}}}
