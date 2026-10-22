# localai2.0 — Night Crew core → Eclipse

A local AI development agent that runs on open models (Ollama, llama.cpp, MLX).
Nothing leaves your machine.

- `nightcrew/` — the core: agent loop, sandboxed file/shell tools, approvals, memory,
  skills router, context compaction, model backends, HTTP API.
- `static/` — the Night Crew web UI.
- `eclipse/` — the Eclipse desktop app (Tauri 2 + React), Windows and macOS. *(in progress)*
- `docs/eclipse-prompt.md` — the Eclipse spec.

## Run Night Crew
```
pip install -r requirements.txt
ollama pull qwen2.5-coder:7b
python run.py            # http://127.0.0.1:5173
```

## Test
```
python -m pytest -q tests
```
