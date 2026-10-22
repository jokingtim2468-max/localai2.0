"""Startup: make sure the standard model exists in Ollama, without freezing the UI.

Runs once in a background thread (server start). If `qwen-abliterated` is missing it runs
the two exact steps below, streaming pull progress into SETUP (served at /api/setup, drawn
as a progress bar by the UI). From a terminal: `python -m nightcrew.model_setup` shows a
CLI progress bar instead.

    ollama pull hf.co/QuantFactory/Qwen2.5-7B-Instruct-abliterated-v2-GGUF:Q4_K_M
    ollama cp   hf.co/QuantFactory/Qwen2.5-7B-Instruct-abliterated-v2-GGUF:Q4_K_M qwen-abliterated

Q4_K_M is ~4.7 GB on disk and fits fully in 8 GB VRAM with num_ctx 16384 and a q4_0 KV cache.
"""
from __future__ import annotations

import threading
import time

import httpx

SOURCE = "hf.co/QuantFactory/Qwen2.5-7B-Instruct-abliterated-v2-GGUF:Q4_K_M"
ALIAS = "qwen-abliterated"
URL = "http://127.0.0.1:11434"
SETUP = {"state": "idle", "status": "", "completed": 0, "total": 0, "error": ""}
_LOCK = threading.Lock()


def installed(url: str = URL) -> set[str]:
    r = httpx.get(url + "/api/tags", timeout=5)
    r.raise_for_status()
    names = set()
    for m in r.json().get("models", []):
        names.add(m["name"])
        names.add(m["name"].removesuffix(":latest"))
    return names


def pull(url: str = URL, on_progress=None) -> None:
    """Same as `ollama pull SOURCE`, streamed so progress can be shown."""
    with httpx.stream("POST", url + "/api/pull", json={"model": SOURCE, "stream": True}, timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line.strip():
                continue
            d = __import__("json").loads(line)
            if d.get("error"):
                raise RuntimeError(d["error"])
            if on_progress:
                on_progress(d)


def copy(url: str = URL) -> None:
    """Same as `ollama cp SOURCE ALIAS`."""
    r = httpx.post(url + "/api/copy", json={"source": SOURCE, "destination": ALIAS}, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"copy failed: {r.text[:200]}")


def wait_for_ollama(url: str = URL, seconds: int = 30) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            httpx.get(url + "/api/version", timeout=2)
            return True
        except httpx.HTTPError:
            time.sleep(1)
    return False


def _progress(d: dict) -> None:
    SETUP["status"] = d.get("status", "")
    if d.get("total"):
        SETUP["total"], SETUP["completed"] = d["total"], d.get("completed", 0)


def ensure(url: str = URL, on_progress=_progress) -> dict:
    """Idempotent: does nothing when the alias already exists."""
    if not _LOCK.acquire(blocking=False):
        return SETUP
    try:
        SETUP.update(state="checking", error="")
        if not wait_for_ollama(url):
            SETUP.update(state="error", error="Ollama is not running. Start it (ollama serve) and restart Eclipse.")
            return SETUP
        have = installed(url)
        if ALIAS in have:
            SETUP.update(state="ready", status=f"{ALIAS} installed")
            return SETUP
        if SOURCE not in have:
            SETUP.update(state="pulling", status="starting download")
            pull(url, on_progress)
        SETUP.update(state="copying", status=f"naming it {ALIAS}")
        copy(url)
        SETUP.update(state="ready", status=f"{ALIAS} installed")
    except Exception as e:  # noqa: BLE001
        SETUP.update(state="error", error=str(e))
    finally:
        _LOCK.release()
    return SETUP


def start_background(url: str = URL) -> None:
    threading.Thread(target=ensure, args=(url,), daemon=True, name="model-setup").start()


def _cli_bar(d: dict) -> None:
    total, done = d.get("total") or 0, d.get("completed") or 0
    if total:
        pct = done / total
        bar = "#" * int(pct * 30)
        print(f"\r{d.get('status', '')[:24]:24} [{bar:<30}] {pct:6.1%} {done / 2**30:5.2f}/{total / 2**30:.2f} GB", end="", flush=True)
    else:
        print(f"\r{d.get('status', '')[:70]:70}", end="", flush=True)


if __name__ == "__main__":
    r = ensure(on_progress=_cli_bar)
    print()
    print(r["error"] or r["status"])
