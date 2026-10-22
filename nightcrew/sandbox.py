"""File + shell tools, jailed to the workspace.

- Writes/edits/deletes resolve through `jail()`: nothing outside the workspace, ever.
- Reads may also reach extra read-only roots the user registered (`read_roots`).
- run_command runs WITH cwd inside the workspace, but its text can name any path, so it
  always needs approval (see agent.GATED); the file tools are trusted when
  settings.trust_workspace is on.
"""
from __future__ import annotations

import difflib
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import paths, settings


class ToolError(Exception):
    pass


EXTRA_READ_ROOTS: list[Path] = []
MAX_READ = 200_000
MAX_OUT = 12_000


def workspace() -> Path:
    w = settings.load().get("workdir") or ""
    p = Path(w).expanduser() if w else paths.data("workspace")
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def _inside(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


def jail(rel: str) -> Path:
    """Resolve a path the agent gave us; refuse anything outside the workspace."""
    root = workspace()
    rel = (rel or ".").strip().strip('"').strip("'")
    p = Path(rel).expanduser()
    p = (p if p.is_absolute() else root / p).resolve()
    if not _inside(p, root):
        raise ToolError(f"'{rel}' is outside the workspace ({root})")
    return p


def read_roots() -> list[Path]:
    return [workspace()] + [r.resolve() for r in EXTRA_READ_ROOTS if r.exists()]


def read_jail(rel: str) -> Path:
    try:
        return jail(rel)
    except ToolError:
        p = Path(rel).expanduser().resolve()
        if any(_inside(p, r) for r in read_roots()[1:]):
            return p
        raise


def near(rel: str) -> str:
    """On a miss, list real files with similar names so the model stops guessing."""
    root = workspace()
    name = Path(rel).name.lower()
    pool = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".") and d not in ("node_modules", "build", "target")]
        pool += [os.path.relpath(os.path.join(dp, f), root) for f in fn]
        if len(pool) > 4000:
            break
    hits = difflib.get_close_matches(name, [Path(x).name.lower() for x in pool], n=5, cutoff=0.5)
    out = [x for x in pool if Path(x).name.lower() in hits][:5]
    return (" Similar files: " + ", ".join(out)) if out else " The workspace has no file like it — do NOT invent its contents; ask the user or create it."


# ---------------------------------------------------------------- tools ----------

def read_file(path: str, start: int = 0, lines: int = 0) -> str:
    p = read_jail(path)
    if not p.is_file():
        raise ToolError(f"no file '{path}'." + near(path))
    text = p.read_text(encoding="utf-8", errors="replace")[:MAX_READ]
    if start or lines:
        rows = text.splitlines()
        text = "\n".join(rows[max(0, start):(start + lines) if lines else None])
    return text


def write_file(path: str, content: str) -> str:
    p = jail(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content if isinstance(content, str) else str(content), encoding="utf-8")
    return f"OK: wrote {p.relative_to(workspace())} ({len(content)} chars)"


def edit_file(path: str, old: str, new: str, all: bool = False) -> str:
    p = jail(path)
    if not p.is_file():
        raise ToolError(f"no file '{path}'." + near(path))
    text = p.read_text(encoding="utf-8")
    n = text.count(old)
    if n == 0:
        raise ToolError("the text to replace was not found; read_file first and copy it exactly")
    if n > 1 and not all:
        raise ToolError(f"the text appears {n} times; add more context or set all=true")
    p.write_text(text.replace(old, new) if all else text.replace(old, new, 1), encoding="utf-8")
    return f"OK: edited {p.relative_to(workspace())} ({n if all else 1} change)"


def delete_file(path: str, recursive: bool = False) -> str:
    p = jail(path)
    if p == workspace():
        raise ToolError("won't delete the workspace itself")
    if not p.exists():
        raise ToolError(f"no such path '{path}'." + near(path))
    if p.is_dir():
        if not recursive and any(p.iterdir()):
            raise ToolError("folder is not empty; set recursive=true to delete it and everything in it")
        shutil.rmtree(p)
    else:
        p.unlink()
    return f"OK: deleted {path}"


def list_dir(path: str = ".") -> str:
    p = read_jail(path)
    if not p.is_dir():
        raise ToolError(f"no folder '{path}'." + near(path))
    rows = []
    for c in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))[:400]:
        rows.append(c.name + ("/" if c.is_dir() else f"  ({c.stat().st_size} B)"))
    return "\n".join(rows) or "(empty)"


def glob(pattern: str) -> str:
    root = workspace()
    out = [str(x.relative_to(root)) for x in root.glob(pattern) if ".git" not in x.parts][:300]
    return "\n".join(out) or "(no matches)"


def grep(pattern: str, path: str = ".", ext: str = "") -> str:
    root = read_jail(path)
    try:
        rx = re.compile(pattern, re.I)
    except re.error as e:
        raise ToolError(f"bad regex: {e}")
    hits = []
    files = [root] if root.is_file() else root.rglob("*")
    for f in files:
        if not f.is_file() or ".git" in f.parts or "node_modules" in f.parts:
            continue
        if ext and not fnmatch.fnmatch(f.name, f"*{ext}"):
            continue
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{f.relative_to(root) if root.is_dir() else f.name}:{i}: {line.strip()[:200]}")
                    if len(hits) >= 200:
                        return "\n".join(hits)
        except OSError:
            continue
    return "\n".join(hits) or "(no matches)"


def trim(out: str, limit: int = MAX_OUT) -> str:
    """Errors first, then the tail — compilers bury the real error in the middle."""
    if len(out) <= limit:
        return out
    errs = [l for l in out.splitlines() if re.search(r"\berror\b|exception|failed|traceback", l, re.I)][:40]
    head = "\n".join(errs)[: limit // 3]
    return (head + "\n...\n" if head else "...\n") + out[-(limit - len(head) - 10):]


def run_command(command: str, cwd: str = ".", timeout: int = 300) -> str:
    d = jail(cwd)
    if not d.is_dir():
        raise ToolError(f"no folder '{cwd}' in the workspace")
    timeout = max(5, min(int(timeout or 300), 1800))
    shell = ["powershell", "-NoProfile", "-Command", command] if sys.platform == "win32" else ["/bin/sh", "-c", command]
    try:
        r = subprocess.run(shell, cwd=d, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError as e:
        raise ToolError(str(e))
    except subprocess.TimeoutExpired:
        return f"FAILED: timed out after {timeout}s"
    out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr.strip() else "")
    status = "OK" if r.returncode == 0 else f"FAILED (exit {r.returncode})"
    return f"{status}\n{trim(out.strip())}"


# ---------------------------------------------------------------- registry ---------

def _fn(name, desc, props=None, req=None):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props or {}, "required": req or []}}}


S, I, B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
SCHEMAS = [
    _fn("read_file", "Read a text file from the workspace. Read before you edit.", {"path": S, "start": I, "lines": I}, ["path"]),
    _fn("write_file", "Create or overwrite a file in the workspace with the FULL content.", {"path": S, "content": S}, ["path", "content"]),
    _fn("edit_file", "Replace exact text in a file (old must match exactly once unless all=true).", {"path": S, "old": S, "new": S, "all": B}, ["path", "old", "new"]),
    _fn("delete_file", "Delete a file or folder in the workspace (recursive=true for a non-empty folder).", {"path": S, "recursive": B}, ["path"]),
    _fn("list_dir", "List a folder in the workspace.", {"path": S}),
    _fn("glob", "Find files by pattern, e.g. **/*.py", {"pattern": S}, ["pattern"]),
    _fn("grep", "Search file contents with a regex.", {"pattern": S, "path": S, "ext": S}, ["pattern"]),
    _fn("run_command", "Run a shell command in the workspace (PowerShell on Windows, sh on macOS/Linux). Use it to build, test and run.", {"command": S, "cwd": S, "timeout": I}, ["command"]),
]
REGISTRY = {"read_file": read_file, "write_file": write_file, "edit_file": edit_file,
            "delete_file": delete_file, "list_dir": list_dir, "glob": glob, "grep": grep,
            "run_command": run_command}
WRITE_TOOLS = {"write_file", "edit_file", "delete_file"}


def run_tool(name: str, args: dict) -> str:
    fn = REGISTRY.get(name)
    if not fn:
        return f"error: unknown tool {name}"
    try:
        return fn(**(args or {}))
    except ToolError as e:
        return f"error: {e}"
    except TypeError as e:
        return f"error: bad arguments for {name}: {e}"
    except Exception as e:  # noqa: BLE001 — a tool must never crash the turn
        return f"error: {name} failed: {e}"
