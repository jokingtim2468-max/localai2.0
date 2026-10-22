# One-time setup on Windows (RTX 4060, 8 GB VRAM). Run in PowerShell from the repo folder:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
# 1) Ollama settings that keep ONE model in VRAM and shrink its context cache.
[Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_FLASH_ATTENTION", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_KV_CACHE_TYPE", "q4_0", "User")
Write-Host "Ollama env set. Quit Ollama from the tray and start it again so it picks them up."
# 2) Python deps + the model (pull + copy to qwen-abliterated, with a progress bar).
python -m pip install -r requirements.txt
python -m nightcrew.model_setup
