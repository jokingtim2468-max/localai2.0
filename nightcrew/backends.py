"""One interface over model servers, so any model runs on any of them.

- ollama:   native API (http://127.0.0.1:11434)
- llamacpp: llama.cpp `llama-server` OpenAI-compatible API (http://127.0.0.1:8080/v1)
- mlx:      `mlx_lm.server` OpenAI-compatible API (http://127.0.0.1:8081/v1), Apple Silicon

stream_chat() yields dicts: {"content": str, "thinking": str, "tool_calls": [..], "done": bool}
"""
from __future__ import annotations

import json

import httpx

DEFAULT_URLS = {"ollama": "http://127.0.0.1:11434", "llamacpp": "http://127.0.0.1:8080/v1",
                "mlx": "http://127.0.0.1:8081/v1"}


class Backend:
    kind = "base"

    def __init__(self, url: str = ""):
        self.url = (url or DEFAULT_URLS.get(self.kind, "")).rstrip("/")

    def models(self) -> list[dict]:
        raise NotImplementedError

    def stream_chat(self, model, messages, tools=None, options=None, think=None, keep_alive=None):
        raise NotImplementedError

    def chat(self, model, messages, options=None) -> str:
        out = ""
        for ev in self.stream_chat(model, messages, options=options):
            out += ev.get("content", "")
        return out


class Ollama(Backend):
    kind = "ollama"

    def models(self):
        r = httpx.get(self.url + "/api/tags", timeout=5)
        r.raise_for_status()
        return [{"name": m["name"], "size": m.get("size", 0),
                 "quant": (m.get("details") or {}).get("quantization_level", ""),
                 "params": (m.get("details") or {}).get("parameter_size", "")}
                for m in r.json().get("models", [])]

    def capabilities(self, model: str) -> list[str]:
        try:
            r = httpx.post(self.url + "/api/show", json={"model": model}, timeout=5)
            return r.json().get("capabilities", []) or []
        except Exception:
            return []

    def stream_chat(self, model, messages, tools=None, options=None, think=None, keep_alive=None):
        body = {"model": model, "messages": messages, "stream": True, "options": options or {}}
        if tools:
            body["tools"] = tools
        if think is not None:
            body["think"] = think
        if keep_alive is not None:
            body["keep_alive"] = keep_alive
        with httpx.stream("POST", self.url + "/api/chat", json=body, timeout=None) as r:
            if r.status_code >= 400:
                raise RuntimeError(f"ollama: {r.read().decode(errors='replace')[:300]}")
            for line in r.iter_lines():
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("error"):
                    raise RuntimeError("ollama: " + d["error"])
                m = d.get("message") or {}
                yield {"content": m.get("content") or "", "thinking": m.get("thinking") or "",
                       "tool_calls": m.get("tool_calls") or [], "done": bool(d.get("done"))}


class OpenAICompat(Backend):
    """llama.cpp server and mlx_lm.server both speak this."""
    kind = "llamacpp"

    def models(self):
        r = httpx.get(self.url + "/models", timeout=5)
        r.raise_for_status()
        return [{"name": m["id"], "size": 0, "quant": "", "params": ""} for m in r.json().get("data", [])]

    def stream_chat(self, model, messages, tools=None, options=None, think=None, keep_alive=None):
        msgs = []
        for m in messages:                       # tool results need an id in this API
            m = dict(m)
            if m.get("role") == "tool":
                m.setdefault("tool_call_id", m.get("tool_call_id") or "call")
            msgs.append(m)
        body = {"model": model, "messages": msgs, "stream": True}
        if tools:
            body["tools"] = tools
        opt = options or {}
        if "temperature" in opt:
            body["temperature"] = opt["temperature"]
        calls: dict[int, dict] = {}
        with httpx.stream("POST", self.url + "/chat/completions", json=body, timeout=None) as r:
            if r.status_code >= 400:
                raise RuntimeError(f"{self.kind}: {r.read().decode(errors='replace')[:300]}")
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                d = json.loads(data)
                delta = (d.get("choices") or [{}])[0].get("delta") or {}
                for tc in delta.get("tool_calls") or []:
                    c = calls.setdefault(tc.get("index", 0), {"function": {"name": "", "arguments": ""}})
                    f = tc.get("function") or {}
                    c["function"]["name"] += f.get("name") or ""
                    c["function"]["arguments"] += f.get("arguments") or ""
                yield {"content": delta.get("content") or "",
                       "thinking": delta.get("reasoning_content") or "", "tool_calls": [], "done": False}
        out = []
        for c in calls.values():
            try:
                c["function"]["arguments"] = json.loads(c["function"]["arguments"] or "{}")
            except ValueError:
                c["function"]["arguments"] = {}
            out.append(c)
        yield {"content": "", "thinking": "", "tool_calls": out, "done": True}


class MLX(OpenAICompat):
    kind = "mlx"


KINDS = {"ollama": Ollama, "llamacpp": OpenAICompat, "mlx": MLX}


def get(kind: str = "ollama", url: str = "") -> Backend:
    return KINDS.get(kind, Ollama)(url)
