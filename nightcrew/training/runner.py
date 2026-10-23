"""Run a whole training job in a background thread; STATE is polled by /api/train.

1. build the dataset (+ tools.json, the tool schemas the agent really uses)
2. pick settings from the hardware (auto.py)
3. unload every Ollama model so the GPU is free
4. run the trainer in .venv-train (Unsloth on NVIDIA, MLX on a Mac); on out-of-memory,
   shrink the settings and retry
5. import the merged model into Ollama as qwen-abliterated-tuned (q4_K_M), copying the
   chat/tool template from qwen-abliterated so tool calling keeps working
6. score old vs new on the held-out examples (evaluate.py)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from .. import backends, paths, settings
from . import auto, dataset

ROOT = paths.HERE.parent
STATE = {"state": "idle", "phase": "", "step": 0, "total": 0, "loss": None, "eval_loss": None,
         "log": [], "error": "", "settings": {}, "manifest": {}, "result": {}}
_LOCK = threading.Lock()


def log(text: str) -> None:
    STATE["log"] = (STATE["log"] + [time.strftime("%H:%M:%S ") + str(text)])[-200:]


def venv_python() -> Path:
    v = ROOT / ".venv-train"
    return v / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ready() -> tuple[bool, str]:
    if not venv_python().is_file():
        script = "scripts\\install_training.ps1" if os.name == "nt" else "scripts/install_training.sh"
        return False, f"The training tools are not installed yet. Run {script} once (about 6 GB download)."
    return True, ""


def free_gpu() -> None:
    cfg = settings.load()
    try:
        n = backends.get(cfg["backend"], cfg.get("backend_url", "")).stop_all()
        log(f"unloaded {n} model(s) from the GPU")
    except Exception as e:  # noqa: BLE001
        log(f"could not unload models: {e}")


def run_trainer(cfg: dict) -> int:
    """Start the trainer script; stream its JSON lines into STATE. Returns its exit code."""
    script = ROOT / "scripts" / ("train_mlx.py" if cfg["method"] == "mlx" else "train_unsloth.py")
    cfg_path = Path(cfg["data_dir"]) / "config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    flags = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW
    p = subprocess.Popen([str(venv_python()), str(script), str(cfg_path)], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=flags)
    STATE["pid"] = p.pid
    for line in p.stdout:
        try:
            ev = json.loads(line)
        except ValueError:
            if line.strip():
                log(line.strip()[:300])
            continue
        kind = ev.get("event")
        if kind == "step":
            STATE.update(step=ev.get("step", 0), total=ev.get("total", 0))
            STATE["loss"] = ev.get("loss") if ev.get("loss") is not None else STATE["loss"]
            STATE["eval_loss"] = ev.get("eval_loss") if ev.get("eval_loss") is not None else STATE["eval_loss"]
        elif kind in ("log", "data", "eval"):
            log(ev.get("text") or json.dumps({k: v for k, v in ev.items() if k != "event"}))
        elif kind == "done":
            STATE["result"]["merged"] = ev.get("merged", "")
        elif kind == "error":
            STATE["error"] = ev.get("text", "")
    return p.wait()


def import_to_ollama(merged: str, name: str, like: str = "qwen-abliterated") -> None:
    """ollama create <name> -q q4_K_M from the merged safetensors, with the same chat/tool
    template as the model it was trained from."""
    import httpx
    tpl, params = "", ""
    try:
        d = httpx.post("http://127.0.0.1:11434/api/show", json={"model": like}, timeout=20).json()
        tpl, params = d.get("template", ""), d.get("parameters", "")
    except Exception as e:  # noqa: BLE001
        log(f"could not read {like}'s template ({e}); Ollama will guess it")
    lines = [f"FROM {Path(merged).as_posix()}"]
    if tpl:
        lines.append('TEMPLATE """' + tpl.replace('"""', '\\"\\"\\"') + '"""')
    for p in params.splitlines():
        if p.strip():
            k, _, v = p.strip().partition(" ")
            lines.append(f"PARAMETER {k} {v.strip()}")
    mf = Path(merged).parent / "Modelfile"
    mf.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"importing into Ollama as {name} (quantizing to q4_K_M)")
    r = subprocess.run(["ollama", "create", name, "-q", "q4_K_M", "-f", str(mf)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=7200)
    if r.returncode != 0:
        raise RuntimeError("ollama create failed: " + (r.stderr or r.stdout)[-600:])


def job(opts: dict) -> None:
    from .. import agent, web
    try:
        STATE.update(state="running", phase="dataset", error="", log=[], step=0, total=0, loss=None, eval_loss=None, result={})
        man = dataset.build(opts, log=log)
        STATE["manifest"] = man
        d = Path(man["dir"])
        (d / "tools.json").write_text(json.dumps(agent.tool_schemas() + web.SCHEMAS), encoding="utf-8")
        cfg = auto.pick(man["total"] + (man["cpp_max"] if man["cpp"] else 0))
        if not cfg["ok"]:
            raise RuntimeError(cfg["why"])
        ok, why = ready()
        if not ok:
            raise RuntimeError(why)
        cfg.update(data_dir=str(d), cpp=man["cpp"], cpp_max=man["cpp_max"])
        STATE["settings"] = cfg
        free_gpu()
        STATE["phase"] = "training"
        while True:
            log(f"training: {cfg['method']}, {cfg['max_seq_len']} tokens per example, batch {cfg['batch']} x {cfg['grad_accum']}, {cfg['epochs']} epochs")
            code = run_trainer(cfg)
            if code == 0:
                break
            if code == 3 and (smaller := auto.shrink(cfg)):
                log("ran out of GPU memory - retrying with smaller settings")
                cfg = {**smaller, "data_dir": cfg["data_dir"], "cpp": cfg["cpp"], "cpp_max": cfg["cpp_max"]}
                STATE["settings"] = cfg
                continue
            raise RuntimeError(STATE["error"] or f"trainer exited with code {code}")
        STATE["phase"] = "importing"
        import_to_ollama(STATE["result"]["merged"], cfg["out_model"])
        STATE["phase"] = "evaluating"
        from . import evaluate
        rows = [json.loads(l) for l in (d / "eval.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        res = evaluate.compare(settings.load().get("model") or "qwen-abliterated", cfg["out_model"], rows, log=log)
        STATE["result"].update(res)
        log("the tuned model scored better - switch to it in Models" if res["better"]
            else "the tuned model did NOT score better; keep using the original")
        STATE.update(state="done", phase="done")
    except Exception as e:  # noqa: BLE001
        STATE.update(state="error", error=str(e))
        log("stopped: " + str(e))


def start(opts: dict | None = None) -> bool:
    if STATE["state"] == "running":
        return False
    threading.Thread(target=job, args=(opts or {},), daemon=True, name="training").start()
    return True


def stop() -> bool:
    pid = STATE.get("pid")
    if STATE["state"] != "running" or not pid:
        return False
    try:
        import psutil
        p = psutil.Process(pid)
        for c in p.children(recursive=True):
            c.kill()
        p.kill()
    except Exception:
        return False
    return True
