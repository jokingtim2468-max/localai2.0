"""Build training examples (chat format with tool calls) from every enabled source.

Each example: {"messages": [...], "source": "<name>"}. Sources and what they teach:
  traces     your successful Eclipse turns (request -> tool calls -> real results -> answer)
  fixes      turns where a failed build was fixed and then passed
  drills     generated correct tool use (read before edit, build after write, real paths)
  honesty    tool failed -> the answer says so; no claims without a passing result
  typos      your requests with realistic typos -> same actions
  memory     your preferences from MEMORY.md
  code       (opt-in) files from folders you choose, to learn your style
  skills     (opt-in) the skill guides as questions and answers
  cpp        public C++ instruction data (Magicoder OSS-Instruct MIT, CodeFeedback Apache-2.0)
  media      Blender (3D models, materials, animation, render) and ffmpeg (video editing)
             scripts, each one RUN on your machine and kept only if it works
Nothing leaves the machine. Anything that looks like a secret is dropped.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from .. import paths

SECRET = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[\w-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY|AIza[0-9A-Za-z_\-]{30,}|\b\d{8,10}:[A-Za-z0-9_-]{35}\b"
    r"|(?i:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S{6,}"
    r"|[\w.+-]+@[\w-]+\.[\w.]{2,})")


def clean(ex: dict) -> bool:
    """False if anything in the example looks like a secret or an email address."""
    return not SECRET.search(json.dumps(ex, ensure_ascii=False))


def _failed(text: str) -> bool:
    return str(text).lstrip().startswith(("error", "FAILED", "blocked"))


def load_traces() -> list[dict]:
    out = []
    for f in sorted(paths.data("traces").glob("*.jsonl")) if paths.data("traces").is_dir() else []:
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def _turn(msgs: list) -> list:
    """Just this turn: from the last user message on (earlier history is other turns)."""
    last = max((i for i, m in enumerate(msgs) if m.get("role") == "user"
                and not str(m.get("content", "")).startswith("(system)")), default=0)
    return [m for m in msgs[last:] if not str(m.get("content", "")).startswith("(system)")]


def _results(turn: list) -> list[tuple[str, str]]:
    return [(m.get("name", ""), str(m.get("content", ""))) for m in turn if m.get("role") == "tool"]


def classify(turn: list) -> str:
    """'good', 'fix' (a failed run, then a passing one), or '' (unusable)."""
    res = _results(turn)
    final = turn[-1] if turn else {}
    if not res or final.get("role") != "assistant" or not str(final.get("content", "")).strip():
        return ""
    if any("user denied" in r for _, r in res):
        return ""
    runs = [r for n, r in res if n == "run_command"]
    if runs and _failed(runs[-1]):
        return ""                                     # ended broken: never teach that
    if any(_failed(r) for r in runs[:-1]):
        return "fix"
    return "good" if not all(_failed(r) for _, r in res) else ""


def from_traces() -> tuple[list, list]:
    good, fixes, seen = [], [], set()
    for t in load_traces():
        turn = _turn(t.get("messages", []))
        kind = classify(turn)
        key = json.dumps(turn[:1], sort_keys=True)
        if not kind or key in seen:
            continue
        seen.add(key)
        (fixes if kind == "fix" else good).append({"messages": turn, "source": "fixes" if kind == "fix" else "traces"})
    return good, fixes


def _call(name: str, **args) -> dict:
    return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}


def _tool(name: str, content: str) -> dict:
    return {"role": "tool", "name": name, "content": content}


# (language, file, build, ok output, error output, source with the bug, broken text, fixed text)
PROJECTS = [
    ("C++", "src/main.cpp", "cmake --build build", "OK\n[100%] Built target app",
     "FAILED (exit 2)\nsrc/main.cpp:4:5: error: 'cout' was not declared in this scope; did you mean 'std::cout'?",
     '#include <iostream>\n\nint main() {\n    cout << "Hello" << std::endl;\n    return 0;\n}\n',
     '    cout << "Hello"', '    std::cout << "Hello"'),
    ("Python", "app.py", "python -m py_compile app.py", "OK",
     "FAILED (exit 1)\n  File \"app.py\", line 1\n    def total(items\n             ^\nSyntaxError: '(' was never closed",
     "def total(items\n    return sum(i.price for i in items)\n", "def total(items\n", "def total(items):\n"),
    ("C#", "Program.cs", "dotnet build", "OK\nBuild succeeded.",
     "FAILED (exit 1)\nProgram.cs(5,9): error CS0103: The name 'Consle' does not exist in the current context",
     'class Program\n{\n    static void Main()\n    {\n        Consle.WriteLine("Hi");\n    }\n}\n',
     'Consle.WriteLine', 'Console.WriteLine'),
    ("Java", "src/main/java/App.java", "./gradlew build", "OK\nBUILD SUCCESSFUL",
     "FAILED (exit 1)\nApp.java:3: error: ';' expected",
     'public class App {\n    public static void main(String[] a) {\n        System.out.println("Hi")\n    }\n}\n',
     'System.out.println("Hi")\n', 'System.out.println("Hi");\n'),
    ("TypeScript", "src/main.ts", "npx tsc --noEmit", "OK",
     "FAILED (exit 2)\nsrc/main.ts(1,7): error TS2322: Type 'string' is not assignable to type 'number'.",
     'const port: number = "8080";\nconsole.log(port);\n', 'const port: number = "8080";', 'const port: number = 8080;'),
    ("GDScript", "player.gd", "godot --headless --check-only --script res://player.gd", "OK",
     'FAILED (exit 1)\nParse Error: Identifier "velocty" not declared in the current scope.',
     'extends CharacterBody2D\n\nfunc _physics_process(delta):\n\tvelocty.x = 100\n\tmove_and_slide()\n',
     '\tvelocty.x', '\tvelocity.x'),
]


def drills(n: int = 300, seed: int = 7) -> list[dict]:
    """Correct habits: run it, read the file, make the smallest edit, build again, then report."""
    r, out = random.Random(seed), []
    for _ in range(n):
        lang, f, build, ok, err, src, old, new = r.choice(PROJECTS)
        why = err.splitlines()[1].split("error", 1)[-1].lstrip(": ").strip() or err.splitlines()[-1]
        msgs = [{"role": "user", "content": r.choice([f"fix the build error in {f}", f"the {lang} build is broken, fix it",
                                                       f"{f} won't compile", f"make {f} build again"])},
                _call("run_command", command=build), _tool("run_command", err),
                _call("read_file", path=f), _tool("read_file", src),
                _call("edit_file", path=f, old=old, new=new), _tool("edit_file", f"OK: edited {f} (1 change)"),
                _call("run_command", command=build), _tool("run_command", ok),
                {"role": "assistant", "content": f"Fixed. The error was: {why.rstrip('.')}. I changed `{old.strip()}` to `{new.strip()}` in {f} and `{build}` now passes."}]
        out.append({"messages": msgs, "source": "drills"})
    return out


def honesty(n: int = 150, seed: int = 11) -> list[dict]:
    """When it did not work, say so plainly and say what is next. Never 'I built it'."""
    r, out = random.Random(seed), []
    for _ in range(n):
        lang, f, build, ok, err, src, old, new = r.choice(PROJECTS)
        case = r.choice(["still_fails", "denied", "missing_tool"])
        msgs = [{"role": "user", "content": r.choice([f"build the {lang} project", f"compile {f}", "build it and tell me when it's done"])},
                _call("run_command", command=build)]
        if case == "denied":
            msgs += [_tool("run_command", "error: user denied this action"),
                     {"role": "assistant", "content": f"I did not run the build because you denied `{build}`. Nothing was compiled. Allow it (or turn on Auto) and I will run it."}]
        elif case == "missing_tool":
            tool = build.split()[0]
            msgs += [_tool("run_command", f"FAILED (exit 1)\n'{tool}' is not recognized as an internal or external command"),
                     {"role": "assistant", "content": f"The build did not run: `{tool}` is not installed on this machine, so nothing was built. Install it (or tell me to use a different build tool) and I will run it again."}]
        else:
            msgs += [_tool("run_command", err),
                     {"role": "assistant", "content": f"It is NOT built. `{build}` fails with: {err.splitlines()[1].strip()} Want me to fix that line in {f} and rebuild?"}]
        out.append({"messages": msgs, "source": "honesty"})
    return out


KEYS = "qwertyuiopasdfghjklzxcvbnm"


def typo(text: str, r: random.Random, rate: float = 0.08) -> str:
    """Realistic fast-typing mistakes: dropped, doubled, swapped and neighbouring letters."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c.isalpha() and r.random() < rate:
            k = r.choice(["drop", "double", "swap", "near"])
            if k == "double":
                out.append(c + c)
            elif k == "swap" and i + 1 < len(text):
                out.append(text[i + 1] + c); i += 1
            elif k == "near" and c.lower() in KEYS:
                j = KEYS.index(c.lower()); out.append(KEYS[max(0, min(len(KEYS) - 1, j + r.choice([-1, 1])))])
            # drop: append nothing
        else:
            out.append(c)
        i += 1
    return "".join(out)


def with_typos(examples: list[dict], share: float = 0.3, seed: int = 3) -> list[dict]:
    r, out = random.Random(seed), []
    for ex in examples:
        if r.random() > share:
            continue
        m = [dict(x) for x in ex["messages"]]
        if m and m[0].get("role") == "user":
            m[0]["content"] = typo(m[0]["content"], r)
            out.append({"messages": m, "source": "typos"})
    return out


def from_memory() -> list[dict]:
    from .. import memory
    out = []
    for line in memory.lines():
        if ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        out.append({"messages": [{"role": "user", "content": f"what do I prefer for {k}?"},
                                 {"role": "assistant", "content": f"{k}: {v}"}], "source": "memory"})
    return out


CODE_EXT = {".cpp", ".cc", ".h", ".hpp", ".c", ".cs", ".java", ".py", ".ts", ".tsx", ".js", ".gd", ".lua", ".luau", ".rs", ".go"}
SKIP_DIRS = {".git", "node_modules", "build", "dist", "target", "bin", "obj", ".venv", "venv", "__pycache__", ".gradle", "Library"}


def from_code(folders: list[str], max_files: int = 400) -> list[dict]:
    """Your own files: 'write <path>' -> the file. Teaches your naming, layout and style.
    Files over 12 KB are skipped (they blow the context window)."""
    out = []
    for folder in folders:
        root = Path(folder).expanduser()
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if len(out) >= max_files:
                return out
            if p.suffix.lower() not in CODE_EXT or any(part in SKIP_DIRS for part in p.parts) or not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            if not (40 < len(text) < 12_000):
                continue
            rel = p.relative_to(root).as_posix()
            out.append({"messages": [{"role": "user", "content": f"In my {root.name} project, write {rel}."},
                                     _call("write_file", path=rel, content=text),
                                     _tool("write_file", f"OK: wrote {rel} ({len(text)} chars)"),
                                     {"role": "assistant", "content": f"Wrote {rel}."}], "source": "code"})
    return out


def from_skills() -> list[dict]:
    from .. import skills
    skills.seed()
    skills.scan()
    out = []
    for s in skills.SKILLS.values():
        for para in [p.strip() for p in s["body"].split("\n- ") if len(p.strip()) > 40]:
            topic = s["description"] or s["name"]
            out.append({"messages": [{"role": "user", "content": f"{topic}: {para.split('.')[0].lstrip('- ')[:90]}?"},
                                     {"role": "assistant", "content": para.lstrip("- ")}], "source": "skills"})
    return out


TEXTS = [
    "The player can double jump once they collect the feather. Falling below the map resets them to the last checkpoint.",
    "Install the dependencies first, then run the build script. The output goes into the dist folder.",
    "Our save files are written every five minutes and when the player quits. Each save keeps a backup of the previous one.",
    "The inventory holds twenty items. Stackable items stack up to ninety nine. Quest items cannot be dropped.",
    "Press escape to open the pause menu. From there you can change the volume, the controls and the graphics quality.",
    "The server checks every purchase before it is applied, so a modified client cannot give itself free coins.",
    "Textures should be powers of two. Use compressed formats for anything larger than one thousand pixels.",
    "The enemy patrols between two points and chases the player when it sees them within ten meters.",
]


def spelling(n: int = 120, seed: int = 21) -> list[dict]:
    """Fix spelling in a file: read it, write the corrected text, say what changed."""
    r, out = random.Random(seed), []
    for _ in range(n):
        clean_text = " ".join(r.sample(TEXTS, r.randint(1, 3)))
        bad = typo(clean_text, r, 0.06)
        if bad == clean_text:
            continue
        f = r.choice(["notes.md", "README.md", "docs/design.md", "story.txt"])
        out.append({"messages": [{"role": "user", "content": r.choice([f"fix the spelling in {f}", f"spellcheck {f}", f"{f} has typos, clean it up"])},
                                 _call("read_file", path=f), _tool("read_file", bad),
                                 _call("write_file", path=f, content=clean_text), _tool("write_file", f"OK: wrote {f} ({len(clean_text)} chars)"),
                                 {"role": "assistant", "content": f"Fixed the spelling in {f}. The wording and meaning are unchanged."}],
                    "source": "spelling"})
    return out


QUESTIONS = ["how does double jump work", "where does the build output go", "how often does the game save",
             "how many items fit in the inventory", "what is in the pause menu", "how are purchases protected",
             "what size should textures be", "how does the enemy behave"]


def reading(n: int = 120, seed: int = 23) -> list[dict]:
    """Answer from the file, quoting it, instead of guessing."""
    r, out = random.Random(seed), []
    for _ in range(n):
        idx = r.sample(range(len(TEXTS)), 4)
        doc = "\n\n".join(TEXTS[i] for i in idx)
        k = r.choice(idx)
        f = r.choice(["docs/design.md", "README.md", "notes.md"])
        out.append({"messages": [{"role": "user", "content": r.choice([f"{QUESTIONS[k]}? check {f}", f"read {f}: {QUESTIONS[k]}?", f"{QUESTIONS[k]}, according to {f}?"])},
                                 _call("read_file", path=f), _tool("read_file", doc),
                                 {"role": "assistant", "content": f"{f} says: \"{TEXTS[k]}\""}], "source": "reading"})
    return out


WEB_TOPICS = ["godot 4 characterbody2d move_and_slide", "blender python keyframe_insert", "ffmpeg trim video without re-encoding",
              "cmake add_executable example", "unreal engine 5 enhanced input", "python pathlib glob", "typescript generics",
              "fabric minecraft mod getting started", "qt6 qmainwindow menu bar", "three.js animation loop", "sqlite python insert",
              "c++ std::unique_ptr", "dotnet new console", "rust bevy ecs system", "pyqt6 signals and slots", "ollama api chat"]


def _sentences(text: str, words: list[str], k: int = 2) -> str:
    lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith(("#", "http", "|", "-", "*", "!", "```"))]
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", " ".join(lines))          # [text](url) -> text
    body = re.sub(r"[*_`]+", "", body)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", body)) if 40 < len(s.strip()) < 400]
    hits = [s for s in sents if sum(w in s.lower() for w in words) >= 2] or sents
    return " ".join(hits[:k])


def web(n: int = 40, seed: int = 31, log=print) -> list[dict]:
    """search -> fetch -> answer from the page with the link; and scrape -> save a file.
    Every example is a REAL search and fetch done now; failures are skipped."""
    from .. import web as W
    r, out = random.Random(seed), []
    topics = r.sample(WEB_TOPICS, len(WEB_TOPICS))
    for q in topics:
        if len(out) >= n:
            break
        try:
            res = W.web_search(q, 3)
            url = re.search(r"https?://\S+", res).group(0)
            page = W.web_fetch(url)
        except Exception as e:  # noqa: BLE001
            log(f"web: skipped '{q}': {e}")
            continue
        answer = _sentences(page, q.lower().split())
        if len(answer) < 60:
            continue
        out.append({"messages": [{"role": "user", "content": r.choice([f"look up {q}", f"search the web: {q}", f"how do I do this: {q}? check online"])},
                                 _call("web_search", query=q), _tool("web_search", res),
                                 _call("web_fetch", url=url), _tool("web_fetch", page[:4000]),
                                 {"role": "assistant", "content": f"{answer}\n\nSource: {url}"}], "source": "web"})
        links = re.findall(r"\[([^\]]{3,80})\]\((https?://[^)\s]+)\)", page)[:25]
        if len(links) >= 3:
            data = json.dumps([{"text": t, "url": u} for t, u in links], indent=1)
            out.append({"messages": [{"role": "user", "content": f"scrape the links from {url} into links.json"},
                                     _call("web_fetch", url=url), _tool("web_fetch", page[:4000]),
                                     _call("write_file", path="links.json", content=data), _tool("write_file", f"OK: wrote links.json ({len(data)} chars)"),
                                     {"role": "assistant", "content": f"Saved {len(links)} links from {url} to links.json (text + url for each)."}],
                        "source": "scrape"})
        log(f"web: {len(out)} examples")
    return out


# Public C++ data, loaded by the trainer (needs the `datasets` package in the training env):
CPP_SOURCES = [
    {"hf": "ise-uiuc/Magicoder-OSS-Instruct-75K", "licence": "MIT", "filter": {"lang": ["cpp", "c++"]}, "q": "problem", "a": "solution"},
    {"hf": "m-a-p/CodeFeedback-Filtered-Instruction", "licence": "Apache-2.0", "filter": {"lang": ["cpp", "c++"]}, "q": "query", "a": "answer"},
]

DEFAULTS = {"traces": True, "fixes": True, "drills": True, "honesty": True, "typos": True, "memory": True,
            "spelling": True, "reading": True, "web": True, "media": True, "cpp": True,
            "skills": False, "code": False, "code_folders": [], "cpp_max": 6000, "media_n": 300, "web_n": 40}


def out_dir() -> Path:
    d = paths.data("training")
    d.mkdir(exist_ok=True)
    return d


def build(opts: dict | None = None, log=print) -> dict:
    o = {**DEFAULTS, **(opts or {})}
    parts: list[dict] = []
    if o["traces"] or o["fixes"]:
        good, fixes = from_traces()
        parts += (good if o["traces"] else []) + (fixes if o["fixes"] else [])
        log(f"your chats: {len(good)} good turns, {len(fixes)} fixed builds")
    for name, fn in (("drills", drills), ("honesty", honesty), ("spelling", spelling), ("reading", reading), ("memory", from_memory)):
        if o[name]:
            parts += fn()
    if o["skills"]:
        parts += from_skills()
    if o["code"] and o["code_folders"]:
        parts += from_code(o["code_folders"])
    if o["web"]:
        parts += web(o["web_n"], log=log)
    if o["media"]:
        from . import media
        parts += media.examples(o["media_n"], log=log)
    if o["typos"]:
        parts += with_typos([p for p in parts if p["source"] in ("traces", "fixes", "drills", "web", "media", "reading")])
    seen, uniq = set(), []
    for p in parts:                                   # identical examples only overfit
        k = json.dumps(p["messages"], sort_keys=True)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    kept = [p for p in uniq if clean(p)]
    dropped = len(parts) - len(kept)
    r = random.Random(1)
    r.shuffle(kept)
    n_eval = max(1, len(kept) // 10) if len(kept) > 10 else 0
    d = out_dir()
    for fname, rows in (("eval.jsonl", kept[:n_eval]), ("train.jsonl", kept[n_eval:])):
        with open(d / fname, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for p in kept:
        counts[p["source"]] = counts.get(p["source"], 0) + 1
    manifest = {"counts": counts, "total": len(kept), "eval": n_eval, "dropped_secrets": dropped,
                "cpp": CPP_SOURCES if o["cpp"] else [], "cpp_max": o["cpp_max"], "dir": str(d)}
    (d / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    log(f"dataset: {len(kept)} examples ({n_eval} held out), {dropped} dropped for secrets, + up to {o['cpp_max']} C++" if o["cpp"] else f"dataset: {len(kept)} examples")
    return manifest
