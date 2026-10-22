# Eclipse — build spec (from the user, 2026-10-22)

Native-feeling desktop app **Eclipse** (Windows + macOS): a fully local AI development
workbench on open models. Nothing leaves the machine unless a feature that needs the
internet is switched on (web search, model downloads, Imgur upload), each with its own switch.

0. Hardware check (sysctl / system_profiler / sw_vers on Mac; equivalent on Windows) ->
   docs/hardware.md. Intel Mac: warn, 3B-8B only. Apple Silicon: Metal. Install missing
   tools with Homebrew / winget; never sudo without asking.
1. Models: backends Ollama (default), llama.cpp server, MLX (Apple Silicon). Memory tiers:
   8-16 GB Qwen2.5-Coder 7B Q4_K_M / Llama 3.1 8B Q4; 18-24 GB Qwen2.5-Coder 14B,
   DeepSeek-Coder-V2-Lite; 32-48 GB Qwen2.5-Coder 32B; 64 GB+ 70B-class + 7B draft.
   Model manager: pull, delete, quant, context length, disk used, tok/s benchmark.
   Power: plugged in / battery, thermal throttling warning.
2. Shell: Tauri 2 (Rust + React/Vite/TS), Python 3.12 sidecar. Menu-bar/tray icon with
   model status + "Stop all models". Data in the OS app-data folder as plain files.
3. Theme: bg #0A0A0A, panels #121212, raised #1A1A1A, borders #262626, text #E0E0E0,
   muted #8A8A8A, accent Cyber Orange #FF6D00 (hover #FF8C00), success #3DDC84,
   danger #FF3B30. Orange only on buttons, active tab, focus ring, cursor, selection.
   JetBrains Mono for code/terminal/numbers; Inter Tight / SF Pro for UI. Left icon rail,
   tabbed center, right inspector, bottom drawer (terminal + logs); dock/resize/hide;
   Cmd/Ctrl+K palette. 150 ms ease-out; respect Reduce motion. Spec in docs/ui-spec.md.
4. Features: chat + agent (tools, approvals, /context /model /tools /clear in-app);
   projects (tree, Monaco, git status, per-hunk diff review); game dev kit (Godot 4,
   Rust/Bevy, Three.js templates, build+run, live reload, frame-time HUD); GUI builder
   (PyQt6 / CustomTkinter / React with live preview); anti-tamper lab for the user's own
   games (server-authoritative netcode, validation, rate limits, signed saves, integrity
   checks, test harness + report); analysis bench for the user's own binaries/firmware
   (Ghidra headless, radare2/rizin, binwalk, strings, otool/nm, lldb; mitmproxy capture of
   own app -> OpenAPI draft; pyserial console; notes in analysis/); open-source adapter
   (clone, map, keep licence); assets library (+ optional Imgur, key in Keychain/Credential
   Manager); Obsidian sync.
5. Quality: unit tests, Playwright e2e with screenshots in test-results/, secrets in the OS
   keychain, file/shell tools jailed to the project, commit after each tested feature,
   honest measured numbers.
6. Cost check before anything paid (e.g. Apple Developer ID $99/yr, Windows code-signing cert).
