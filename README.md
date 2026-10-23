# localai2.0 — Night Crew core → Eclipse

A local AI development agent that runs on open models (Ollama, llama.cpp, MLX).
Nothing leaves your machine.

- `nightcrew/` — the core: agent loop, sandboxed file/shell tools, approvals, memory,
  skills router, context compaction, model backends, HTTP API.
- `static/` — the Night Crew web UI.
- `eclipse/` — the Eclipse desktop app (Tauri 2 + React), Windows and macOS. *(in progress)*
- `docs/eclipse-prompt.md` — the Eclipse spec.

## Install (Windows, once)
```
git clone -b claude/amazing-keller-dvibe7 https://github.com/jokingtim2468-max/localai2.0
cd localai2.0
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```
That sets Ollama for 8 GB VRAM, installs Python packages, downloads `qwen-abliterated`,
and puts an **Eclipse** shortcut on the Desktop and in the Start menu. Double-click it:
Eclipse opens in its own window (no browser).

Training (optional, NVIDIA): `powershell -ExecutionPolicy Bypass -File scripts\\install_training.ps1`, then Eclipse -> Training.

macOS: `python3 -m pip install -r requirements.txt && python3 make_shortcut.py` ->
`~/Applications/Eclipse.app`.

## Test
```
python -m pytest -q tests
```
