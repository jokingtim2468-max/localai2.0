"""The lead agent's turn: model -> tools -> model ... until it answers.

run_turn(history, emit, approve) calls emit(event, data) for: token, thinking, tool_call,
tool_result, notice, error, done. approve(name, args) -> bool blocks for the user's answer
(the server wires it to the approval card). Uses native tool calling.
"""
from __future__ import annotations

import json

from . import backends, context, memory, sandbox, settings, skills

SYSTEM_PROMPT = """You are the lead developer agent in a local workbench. You build apps,
games, GUIs and tools in the user's workspace folder using your tools.

Rules:
- ACT, don't ask. When the user wants something built, changed or run, call the tools now.
- The user types fast and makes typos. Read what they MEANT; never correct their spelling.
- Read a file before editing it. Never invent the contents of a file that should already exist.
- Build and run what you write (run_command), read the real errors, fix, run again.
- Never say you built, compiled, created or fixed something unless a tool call in THIS
  conversation returned success. If something failed, say so plainly.
- Know your limits: you can only touch the workspace; you cannot see the screen; check
  that a tool or program exists before relying on it.
- Use remember for durable facts (preferences, project decisions) as 'key: value'.
- Finish the whole request before answering. Answers are short and concrete."""

GATED = {"run_command", "write_file", "edit_file", "delete_file"}
TRUSTED_WHEN_SETTING = {"write_file", "edit_file", "delete_file"}   # jailed to the workspace


def system_prompt(task: str) -> str:
    parts = [SYSTEM_PROMPT, f"Workspace: {sandbox.workspace()}"]
    mem = memory.text()
    if mem:
        parts.append("# MEMORY (what you learned before)\n" + mem)
    sk = skills.block(task)
    if sk:
        parts.append(sk)
    if skills.SKILLS:
        parts.append("Skills you can load_skill: " + ", ".join(sorted(skills.SKILLS)))
    return "\n\n".join(parts)


def tool_schemas() -> list:
    return list(sandbox.SCHEMAS) + [memory.SCHEMA, skills.SCHEMA]


def needs_approval(name: str, ask: bool) -> bool:
    if not ask or name not in GATED:
        return False
    return not (name in TRUSTED_WHEN_SETTING and settings.load().get("trust_workspace", True))


def call_tool(name: str, args: dict) -> str:
    if name == "remember":
        return memory.remember(args.get("note", ""))
    if name == "load_skill":
        return skills.load_skill(args.get("name", ""))
    return sandbox.run_tool(name, args)


def failed(result: str) -> bool:
    return str(result).lstrip().startswith(("error", "FAILED", "blocked"))


def run_turn(history: list, emit, approve=lambda n, a: True, model: str = "",
             ask: bool = True, use_tools: bool = True, backend=None, max_rounds: int = 12) -> str:
    cfg = settings.load()
    be = backend or backends.get(cfg["backend"], cfg.get("backend_url", ""))
    if not model:
        model = cfg.get("model") or ""
    if not model:
        try:
            model = be.models()[0]["name"]
        except Exception:
            emit("error", "no model: start Ollama (or your backend) and pull a model first")
            emit("done", {})
            return ""
    task = "\n".join(m.get("content", "") for m in history if m.get("role") == "user"
                     and isinstance(m.get("content"), str))[-2000:]
    msgs = [{"role": "system", "content": system_prompt(task)}] + [dict(m) for m in history]
    schemas = tool_schemas() if use_tools else None
    think = None
    if cfg.get("think") is not None and hasattr(be, "capabilities") and "thinking" in be.capabilities(model):
        think = bool(cfg.get("think"))
    ctx = int(cfg.get("num_ctx") or 16384)

    def summarise(text: str) -> str:
        return be.chat(model, [{"role": "system", "content":
                                "Summarise this chat so far for yourself in under 120 words: what the user "
                                "wants, decisions, files written or deleted, open errors. Terse notes."},
                               {"role": "user", "content": text[-12000:]}], options={"num_ctx": ctx}).strip()

    shown, world, done_calls, strikes = "", 0, {}, 0
    try:
        for _ in range(max_rounds):
            context.collapse(msgs)
            info = context.compact(msgs, ctx * 3, summarise)
            if info["compacted"]:
                emit("notice", f"compacted {info['compacted']} earlier messages to stay inside the context window")
            acc, thought, calls = "", "", []
            for ev in be.stream_chat(model, msgs, tools=schemas, options={"num_ctx": ctx},
                                     think=think, keep_alive=-1 if be.kind == "ollama" else None):
                if ev.get("thinking"):
                    thought += ev["thinking"]
                    emit("thinking", ev["thinking"])
                if ev.get("content"):
                    acc += ev["content"]
                    emit("token", ev["content"])
                calls += ev.get("tool_calls") or []
            shown += acc
            msgs.append({"role": "assistant", "content": acc, **({"tool_calls": calls} if calls else {})})
            if not calls:
                if not shown.strip():
                    emit("token", f"({model} spent the turn thinking and never answered — turn Thinking off or ask more specifically.)"
                         if thought.strip() else f"({model} returned nothing. It may be out of context: start a new chat.)")
                break
            looping = False
            for tc in calls:
                fn = tc.get("function", {})
                name, args = fn.get("name", ""), fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                emit("tool_call", {"name": name, "args": args})
                sig = f"{name}|{json.dumps(args, sort_keys=True, default=str)}|{world}"
                done_calls[sig] = done_calls.get(sig, 0) + 1
                if done_calls[sig] > 1:
                    result = ("(already called with exactly these arguments and nothing changed since; "
                              "do the NEXT step or answer the user.)")
                    looping = True
                elif needs_approval(name, ask) and not approve(name, args):
                    result = "error: user denied this action"
                else:
                    result = call_tool(name, args)
                    if not failed(result) and name in sandbox.WRITE_TOOLS:
                        world += 1          # files changed: re-running a build is a new call
                emit("tool_result", {"name": name, "result": result})
                msgs.append({"role": "tool", "content": result, "name": name})
            if looping:
                strikes += 1
                if strikes > 1:
                    break
                msgs.append({"role": "user", "content": "(system) Stop repeating tools. Answer now using what they returned."})
    except Exception as e:  # noqa: BLE001
        emit("error", str(e))
    emit("done", {})
    return shown
