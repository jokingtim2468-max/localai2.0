"""QLoRA fine-tune with Unsloth (NVIDIA). Run by Eclipse inside .venv-train:

    .venv-train/Scripts/python scripts/train_unsloth.py <config.json>

Prints one JSON object per line ({"event": ...}) so the app can draw progress.
Exit codes: 0 ok, 3 out of GPU memory (the app retries with smaller settings), 1 other error.
"""
import json
import os
import random
import sys


def say(**kw):
    print(json.dumps(kw), flush=True)


def rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def cpp_examples(spec, limit):
    """Public C++ instruction data, filtered to C/C++ only."""
    from datasets import load_dataset
    out = []
    per = max(1, limit // max(1, len(spec)))
    for s in spec:
        try:
            ds = load_dataset(s["hf"], split="train")
            col, want = next(iter(s["filter"].items()))
            ds = ds.filter(lambda r: str(r.get(col, "")).lower() in want)
            ds = ds.shuffle(seed=7).select(range(min(per, len(ds))))
            out += [{"messages": [{"role": "user", "content": r[s["q"]]}, {"role": "assistant", "content": r[s["a"]]}]} for r in ds]
            say(event="log", text=f"C++: {min(per, len(ds))} examples from {s['hf']} ({s['licence']})")
        except Exception as e:  # noqa: BLE001
            say(event="log", text=f"C++: skipped {s['hf']}: {e}")
    return out


def fix_args(msgs):
    """Tool-call arguments must be objects for the chat template."""
    for m in msgs:
        for tc in m.get("tool_calls") or []:
            a = tc["function"].get("arguments")
            if isinstance(a, str):
                try:
                    tc["function"]["arguments"] = json.loads(a)
                except ValueError:
                    tc["function"]["arguments"] = {}
            tc.setdefault("type", "function")
    return msgs


def main(cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    d = cfg["data_dir"]
    import torch
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only
    from datasets import Dataset
    from transformers import TrainerCallback
    from trl import SFTConfig, SFTTrainer

    say(event="log", text=f"loading {cfg['base']} in 4-bit")
    model, tok = FastLanguageModel.from_pretrained(model_name=cfg["base"], max_seq_length=cfg["max_seq_len"],
                                                   load_in_4bit=True, dtype=None)
    model = FastLanguageModel.get_peft_model(
        model, r=cfg["lora_r"], lora_alpha=cfg["lora_alpha"], lora_dropout=0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=3407)

    tools = json.load(open(os.path.join(d, "tools.json"), encoding="utf-8"))
    train = rows(os.path.join(d, "train.jsonl"))
    evals = rows(os.path.join(d, "eval.jsonl"))
    if cfg.get("cpp"):
        train += cpp_examples(cfg["cpp"], cfg.get("cpp_max", 6000))
    random.Random(1).shuffle(train)

    def text(ex):
        uses_tools = any(m.get("tool_calls") or m.get("role") == "tool" for m in ex["messages"])
        return tok.apply_chat_template(fix_args(ex["messages"]), tools=tools if uses_tools else None, tokenize=False)

    def to_ds(items):
        out = []
        for ex in items:
            t = text(ex)
            if len(tok(t)["input_ids"]) <= cfg["max_seq_len"]:      # too long would be cut mid-answer
                out.append({"text": t})
        return Dataset.from_list(out)
    tr, ev = to_ds(train), to_ds(evals)
    say(event="data", train=len(tr), eval=len(ev))

    class Progress(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kw):
            logs = logs or {}
            say(event="step", step=state.global_step, total=state.max_steps,
                loss=logs.get("loss"), eval_loss=logs.get("eval_loss"))

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    args = SFTConfig(
        output_dir=os.path.join(d, "run"), dataset_text_field="text", max_seq_length=cfg["max_seq_len"],
        per_device_train_batch_size=cfg["batch"], gradient_accumulation_steps=cfg["grad_accum"],
        num_train_epochs=cfg["epochs"], learning_rate=cfg["lr"], warmup_ratio=0.03, lr_scheduler_type="linear",
        optim="adamw_8bit", weight_decay=0.01, logging_steps=1, eval_strategy="epoch" if len(ev) else "no",
        save_strategy="no", report_to="none", bf16=bf16, fp16=not bf16, seed=3407)
    try:
        trainer = SFTTrainer(model=model, processing_class=tok, train_dataset=tr, eval_dataset=ev if len(ev) else None,
                             args=args, callbacks=[Progress()])
    except TypeError:                                   # older trl
        trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=tr, eval_dataset=ev if len(ev) else None,
                             args=args, callbacks=[Progress()])
    # learn only the assistant's turns, not to imitate the user or tool output
    trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\n",
                                      response_part="<|im_start|>assistant\n")
    say(event="log", text="training")
    trainer.train()
    if len(ev):
        say(event="eval", **{k: v for k, v in trainer.evaluate().items() if isinstance(v, (int, float))})
    out = os.path.join(d, "merged")
    say(event="log", text="merging the LoRA into the full model (needs ~16 GB free disk)")
    model.save_pretrained_merged(out, tok, save_method="merged_16bit")
    say(event="done", merged=out)          # the app imports it with: ollama create -q q4_K_M


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception as e:  # noqa: BLE001
        oom = "out of memory" in str(e).lower() or type(e).__name__ == "OutOfMemoryError"
        say(event="error", text=str(e)[-800:], oom=oom)
        sys.exit(3 if oom else 1)
