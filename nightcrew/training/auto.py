"""Pick training settings from the hardware and the dataset size. No knobs to turn."""
from __future__ import annotations

from .. import hardware

BASE = "huihui-ai/Qwen2.5-7B-Instruct-abliterated-v2"   # the full-precision original of qwen-abliterated
BASE_14B = BASE   # huihui-ai 14B v2 original is no longer public (checked 2026-10-23)


def pick(n_examples: int, info: dict | None = None) -> dict:
    info = info or hardware.detect()
    vram = info.get("vram_gb") or 0
    mac = bool(info.get("apple_silicon"))
    mem = hardware.usable_gb(info)
    if mac:
        method, ok = "mlx", mem >= 16          # bf16 7B + LoRA: ~16 GB of unified memory
        seq, batch, base = (4096, 2, BASE) if mem >= 24 else (2048, 1, BASE)
    elif vram:
        method, ok = "unsloth", vram >= 6
        if vram >= 22:
            seq, batch, base = 4096, 4, BASE
        elif vram >= 12:
            seq, batch, base = 4096, 1, BASE
        else:
            seq, batch, base = 2048, 1, BASE            # RTX 4060 8 GB lands here
    else:
        method, ok, seq, batch, base = "none", False, 0, 0, BASE
    # small datasets need more passes; big ones fewer (avoids memorising)
    epochs = 3 if n_examples < 1500 else 2 if n_examples < 6000 else 1
    accum = max(1, 8 // max(1, batch))
    steps_per_epoch = max(1, n_examples // (max(1, batch) * accum))
    why = ""
    if method == "none":
        why = "Training needs an NVIDIA GPU (6 GB+) or an Apple Silicon Mac. This machine has neither."
    elif not ok:
        why = f"Only {vram or mem} GB available; 7B training needs about 6 GB VRAM (NVIDIA) or 16 GB free unified memory (a 24 GB+ Mac)."
    return {"ok": ok, "why": why, "method": method, "base": base, "max_seq_len": seq, "batch": batch,
            "grad_accum": accum, "epochs": epochs, "lr": 2e-4, "lora_r": 16, "lora_alpha": 16,
            "load_in_4bit": method == "unsloth", "gradient_checkpointing": True,
            "est_steps": steps_per_epoch * epochs, "quant": "q4_k_m", "out_model": "qwen-abliterated-tuned"}


def shrink(cfg: dict) -> dict | None:
    """After an out-of-memory crash: shorter sequences first, then batch 1. None = give up."""
    if cfg["max_seq_len"] > 1024:
        return {**cfg, "max_seq_len": cfg["max_seq_len"] // 2}
    if cfg["batch"] > 1:
        return {**cfg, "batch": 1, "grad_accum": cfg["grad_accum"] * cfg["batch"]}
    return None
