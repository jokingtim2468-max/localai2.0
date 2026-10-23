# One-time: the fine-tuning tools (Unsloth + CUDA PyTorch) in their own environment,
# .venv-train, so they never clash with the app's packages. About 6 GB download.
#   powershell -ExecutionPolicy Bypass -File scripts\install_training.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Write-Host "No NVIDIA driver found (nvidia-smi). Install the latest GeForce driver first."; exit 1 }
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
python -m venv .venv-train
$py = ".venv-train\Scripts\python.exe"
& $py -m pip install --upgrade pip
# CUDA 12.8 build of PyTorch: works on RTX 20/30/40/50 with a current driver
& $py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
& $py -c "import torch; assert torch.cuda.is_available(), 'PyTorch cannot see the GPU'; print('GPU OK:', torch.cuda.get_device_name(0))"
& $py -m pip install unsloth datasets
& $py -c "import unsloth, trl, datasets; print('Unsloth', unsloth.__version__, 'ready')"
Write-Host "Training tools installed. Open Eclipse -> Training."
