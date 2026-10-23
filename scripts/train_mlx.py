"""LoRA fine-tune with MLX on Apple Silicon. Run by Eclipse inside .venv-train:

    .venv-train/bin/python scripts/train_mlx.py <config.json>

Same output protocol as train_unsloth.py (JSON lines; exit 3 = out of memory).
"""
import json
import os
import re
import subprocess
import sys


def say(**kw):
    print(json.dumps(kw), flush=True)


def main(cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    d = cfg["data_dir"]
    mlx_data = os.path.join(d, "mlx")
    os.makedirs(mlx_data, exist_ok=True)
    tools = json.load(open(os.path.join(d, "tools.json"), encoding="utf-8"))
    for src, dst in (("train.jsonl", "train.jsonl"), ("eval.jsonl", "valid.jsonl")):
        with open(os.path.join(d, src), encoding="utf-8") as fi, open(os.path.join(mlx_data, dst), "w", encoding="utf-8") as fo:
            for line in fi:
                ex = json.loads(line)
                row = {"messages": ex["messages"]}
                if any(m.get("tool_calls") or m.get("role") == "tool" for m in ex["messages"]):
                    row["tools"] = tools
                fo.write(json.dumps(row) + "\n")
    n = sum(1 for _ in open(os.path.join(mlx_data, "train.jsonl"), encoding="utf-8"))
    iters = max(50, n * cfg["epochs"] // max(1, cfg["batch"]))
    adapters = os.path.join(d, "adapters")
    cmd = [sys.executable, "-m", "mlx_lm", "lora", "--model", cfg["base"], "--train", "--data", mlx_data,
           "--batch-size", str(cfg["batch"]), "--iters", str(iters), "--max-seq-length", str(cfg["max_seq_len"]),
           "--learning-rate", str(cfg["lr"]), "--adapter-path", adapters, "--grad-checkpoint", "--mask-prompt"]
    say(event="log", text=" ".join(cmd[2:]))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = []
    for line in p.stdout:
        tail = (tail + [line])[-30:]
        m = re.search(r"Iter (\d+): Train loss ([\d.]+)", line)
        if m:
            say(event="step", step=int(m.group(1)), total=iters, loss=float(m.group(2)))
        m = re.search(r"Iter (\d+): Val loss ([\d.]+)", line)
        if m:
            say(event="step", step=int(m.group(1)), total=iters, eval_loss=float(m.group(2)))
    if p.wait() != 0:
        text = "".join(tail)
        say(event="error", text=text[-800:], oom="memory" in text.lower())
        sys.exit(3 if "memory" in text.lower() else 1)
    merged = os.path.join(d, "merged")
    subprocess.run([sys.executable, "-m", "mlx_lm", "fuse", "--model", cfg["base"], "--adapter-path", adapters,
                    "--save-path", merged, "--dequantize"], check=True)
    say(event="done", merged=merged)


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception as e:  # noqa: BLE001
        say(event="error", text=str(e)[-800:], oom=False)
        sys.exit(1)
