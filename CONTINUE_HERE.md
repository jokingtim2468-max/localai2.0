# CONTINUE HERE — read first if the session restarts

Repo: jokingtim2468-max/localai2.0, branch claude/amazing-keller-dvibe7 (old repo
jokingtim24688/local-ai-with-claude-ui is GONE — account terminated; code was rebuilt from memory).

## Goal (user's order)
1. Rebuild Night Crew core (local agent on open models) — Python package `nightcrew/`.
2. Transform it into **Eclipse** (spec: docs/eclipse-prompt.md): Tauri 2 + React/Vite/TS,
   Python core as sidecar, builds for Windows AND macOS. Scaffold/test here (Linux cloud);
   Mac/Windows-only steps run via scripts on the real machine.

## Do NOT
- Do not write text-typed tool-call recovery (toolcalls) or desktop/screen control: both
  attempts were stopped. Agent uses native tool calling only.

## Done
- nightcrew/: paths, settings, sandbox (jail + tools), context (compaction), memory,
  skills (exact/fuzzy router), backends (ollama, llama.cpp, mlx), agent (loop, approval,
  repeat guard w/ world, never-empty turn, thinking), server (Flask SSE, X-NC guard).
- tests/: pytest with FakeBackend. Run `python -m pytest -q tests`.

## Next (Eclipse frontend works: shell, chat, models, settings, palette. Missing: src-tauri wrapper + sidecar, features 4.2-4.9)
- static/ web UI DONE (orbit, thinking, approvals). skills/ 6 starters DONE.
- skills/ content. Then Eclipse scaffold in eclipse/.

## Redo from scratch
Recreate files listed above per their docstrings; run tests; commit; push
`git push -u origin claude/amazing-keller-dvibe7`.

## Model + escalation (f553b2e)
- nightcrew/model_setup.py: ensure() = pull hf.co/QuantFactory/Qwen2.5-7B-Instruct-abliterated-v2-GGUF:Q4_K_M
  then copy -> qwen-abliterated; background thread at server start; /api/setup; CLI bar via
  `python -m nightcrew.model_setup`. Settings default model/worker = qwen-abliterated.
- nightcrew/escalation.py: buddy -> parent(Hermes) -> swarm(3 sequential) -> mr_debug, all on the
  resident model (keep_alive -1; foreign model keep_alive 0). Agent auto-nudges up a tier after
  2 consecutive failed run_command. Tests: tests/test_setup_escalation.py.
- scripts/setup_windows.ps1: OLLAMA_MAX_LOADED_MODELS=1, NUM_PARALLEL=1, FLASH_ATTENTION=1, KV q4_0.

## Desktop app
- desktop.py: single-instance lock (port 47615), core on a free port, pywebview native window.
- Core serves eclipse/dist at / (committed so the PC needs no Node); old UI at /nightcrew.
- make_shortcut.py: Windows Desktop + Start-menu .lnk (pythonw, icon.ico); macOS ~/Applications/Eclipse.app.
- Rebuild UI after changes: `cd eclipse && npx vite build` and commit dist.
