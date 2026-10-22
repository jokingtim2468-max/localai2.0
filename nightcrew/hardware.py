"""Step 0: what is this machine, and which models fit it.

detect() works on macOS (sysctl/system_profiler/pmset), Windows (wmic/PowerShell/nvidia-smi)
and Linux. recommend() maps memory to model tiers. write_report() -> docs/hardware.md.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys


def _run(cmd: list[str], timeout: int = 8) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def detect() -> dict:
    info = {"os": platform.system(), "os_version": platform.version(), "arch": platform.machine(),
            "cpu": platform.processor() or "", "cores": os.cpu_count(), "ram_gb": None,
            "gpu": "", "vram_gb": None, "gpu_cores": None, "apple_silicon": False,
            "disk_free_gb": round(shutil.disk_usage(os.path.expanduser("~")).free / 2**30, 1)}
    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
    except Exception:
        pass
    if sys.platform == "darwin":
        info["cpu"] = _run(["sysctl", "-n", "machdep.cpu.brand_string"]) or info["cpu"]
        mem = _run(["sysctl", "-n", "hw.memsize"])
        if mem.isdigit():
            info["ram_gb"] = round(int(mem) / 2**30, 1)
        info["os_version"] = _run(["sw_vers", "-productVersion"]) or info["os_version"]
        info["apple_silicon"] = info["arch"] == "arm64"
        try:
            d = json.loads(_run(["system_profiler", "-json", "SPDisplaysDataType"], 20) or "{}")
            g = (d.get("SPDisplaysDataType") or [{}])[0]
            info["gpu"] = g.get("sppci_model", "")
            info["gpu_cores"] = int(g.get("sppci_cores")) if str(g.get("sppci_cores", "")).isdigit() else None
        except Exception:
            pass
        if info["apple_silicon"]:
            info["vram_gb"] = info["ram_gb"]            # unified memory
    else:
        smi = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
        if smi:
            name, mem = [x.strip() for x in smi.splitlines()[0].split(",")]
            info["gpu"], info["vram_gb"] = name, round(float(mem) / 1024, 1)
        elif sys.platform == "win32":
            info["gpu"] = _run(["powershell", "-NoProfile", "-Command",
                                "(Get-CimInstance Win32_VideoController | Select -First 1).Name"])
        if sys.platform == "win32":
            info["cpu"] = _run(["powershell", "-NoProfile", "-Command",
                                "(Get-CimInstance Win32_Processor | Select -First 1).Name"]) or info["cpu"]
    return info


TIERS = [  # (min usable GB, models)
    (58, ["qwen2.5:72b-instruct-q4_K_M", "llama3.3:70b-instruct-q4_K_M", "qwen2.5-coder:7b (draft)"]),
    (26, ["qwen2.5-coder:32b-instruct-q4_K_M"]),
    (12, ["qwen2.5-coder:14b-instruct-q4_K_M", "deepseek-coder-v2:16b-lite-instruct-q4_K_M"]),
    (2,  ["qwen2.5-coder:7b-instruct-q4_K_M", "llama3.1:8b-instruct-q4_K_M"]),
    (0,  ["qwen2.5-coder:3b", "llama3.2:3b"]),
]


def usable_gb(info: dict) -> float:
    """Memory a model can use: unified RAM minus ~6 GB on Apple Silicon, else GPU VRAM
    (CPU offload works but is slow), else RAM minus 6."""
    if info.get("apple_silicon"):
        return max(0.0, (info.get("ram_gb") or 0) - 6)
    if info.get("vram_gb"):
        return float(info["vram_gb"])
    return max(0.0, (info.get("ram_gb") or 0) - 6)


def recommend(info: dict) -> dict:
    gb = usable_gb(info)
    models = next(m for floor, m in TIERS if gb >= floor)
    warn = ""
    if info.get("os") == "Darwin" and not info.get("apple_silicon"):
        warn = "Intel Mac: local models run on the CPU and will be slow. Stick to 3B-8B models."
    elif not info.get("apple_silicon") and not info.get("vram_gb"):
        warn = "No dedicated GPU found: models run on the CPU. 3B-8B models only."
    return {"usable_gb": round(gb, 1), "models": models, "warning": warn,
            "backends": ["ollama", "llamacpp"] + (["mlx"] if info.get("apple_silicon") else [])}


def power() -> dict:
    out = {"plugged_in": None, "battery": None, "throttled": False, "note": ""}
    try:
        import psutil
        b = psutil.sensors_battery()
        if b:
            out["plugged_in"], out["battery"] = bool(b.power_plugged), round(b.percent)
        else:
            out["plugged_in"] = True                 # desktop: no battery
    except Exception:
        pass
    if sys.platform == "darwin":
        t = _run(["pmset", "-g", "therm"])
        for line in t.splitlines():
            if "CPU_Speed_Limit" in line:
                try:
                    out["throttled"] = int(line.split("=")[-1].strip()) < 100
                except ValueError:
                    pass
        if out["throttled"]:
            out["note"] = "This Mac is thermally throttling: expect fewer tokens per second."
    return out


def write_report(path: str) -> str:
    info, rec = detect(), None
    rec = recommend(info)
    lines = ["# Hardware", "", "| | |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in info.items()]
    lines += ["", f"Usable for models: **{rec['usable_gb']} GB**", "",
              "Recommended: " + ", ".join(rec["models"]), "", rec["warning"] or ""]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    print(write_report(sys.argv[1] if len(sys.argv) > 1 else "docs/hardware.md"))
