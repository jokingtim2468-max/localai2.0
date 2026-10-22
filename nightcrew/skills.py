"""Skills: skills/<name>/SKILL.md with frontmatter (name, description, domain, triggers).

route(task) picks the skills whose triggers match. Scoring is (exact, fuzzy): exact always
wins; a fuzzy (typo) hit needs the same first letter, length within 2 and ratio >= 0.80 -
that rule stopped "make" matching "cmake".
"""
from __future__ import annotations

import difflib
import re
import shutil

from . import paths

SKILLS: dict[str, dict] = {}


def _parse(text: str) -> tuple[dict, str]:
    meta: dict = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return meta, text
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    trig = meta.get("triggers", "")
    meta["triggers"] = [t.strip().lower() for t in trig.strip("[]").split(",") if t.strip()]
    return meta, m.group(2)


def user_dir():
    return paths.data("skills")


def seed() -> None:
    """Copy built-in skills into the data dir, never overwriting the user's edits."""
    dst = user_dir()
    dst.mkdir(parents=True, exist_ok=True)
    if paths.SKILLS_BUILTIN.is_dir():
        for d in paths.SKILLS_BUILTIN.iterdir():
            if (d / "SKILL.md").is_file() and not (dst / d.name).exists():
                shutil.copytree(d, dst / d.name)


def scan() -> dict:
    root = user_dir()
    found = list(root.rglob("SKILL.md")) if root.is_dir() else []
    if not found:
        return SKILLS               # missing/empty folder never wipes a loaded catalogue
    SKILLS.clear()
    for f in found:
        meta, body = _parse(f.read_text(encoding="utf-8", errors="replace"))
        name = meta.get("name") or f.parent.name
        SKILLS[name] = {"name": name, "description": meta.get("description", ""),
                        "domain": meta.get("domain", ""), "triggers": meta.get("triggers", []),
                        "body": body.strip()}
    return SKILLS


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.]+", (text or "").lower())


def _fuzzy(word: str, trig: str) -> bool:
    return (len(word) >= 4 and word[0] == trig[0] and abs(len(word) - len(trig)) <= 2
            and difflib.SequenceMatcher(None, word, trig).ratio() >= 0.80)


def score(task: str, skill: dict) -> tuple[int, int]:
    text = " " + " ".join(_words(task)) + " "
    words = set(_words(task))
    exact = fuzzy = 0
    for t in skill.get("triggers", []):
        if " " in t:
            exact += f" {t} " in text
        elif t in words:
            exact += 1
        elif any(_fuzzy(w, t) for w in words):
            fuzzy += 1
    return exact, fuzzy


def route(task: str, limit: int = 2) -> list[dict]:
    if not SKILLS:
        scan()
    scored = [(score(task, s), s) for s in SKILLS.values()]
    hits = [x for x in scored if x[0][0] > 0]
    if not hits:                                      # fuzzy only decides when nothing matched
        hits = [x for x in scored if x[0][1] > 0]
    hits.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in hits[:limit]]


def domain_of(task: str) -> str:
    r = route(task, 1)
    return r[0].get("domain", "") if r else ""


def block(task: str, budget: int = 4000) -> str:
    """The routed skills, trimmed to a char budget, for the system prompt."""
    out, left = [], budget
    for s in route(task):
        chunk = f"## {s['name']}\n{s['body']}"[:left]
        out.append(chunk)
        left -= len(chunk)
        if left <= 200:
            break
    return ("# ACTIVE SKILL\n" + "\n\n".join(out)) if out else ""


def load_skill(name: str) -> str:
    if not SKILLS:
        scan()
    s = SKILLS.get(name)
    return s["body"] if s else "error: no skill '" + name + "'. Known: " + ", ".join(sorted(SKILLS))


SCHEMA = {"type": "function", "function": {"name": "load_skill",
          "description": "Load the full text of a skill (how-to reference) by name.",
          "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}}
