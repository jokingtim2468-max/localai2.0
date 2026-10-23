#!/bin/sh
# One-time (macOS, Apple Silicon): MLX fine-tuning tools in .venv-train.
#   sh scripts/install_training.sh
set -e
cd "$(dirname "$0")/.."
[ "$(uname -m)" = "arm64" ] || { echo "Training on a Mac needs Apple Silicon (M1 or newer)."; exit 1; }
python3 -m venv .venv-train
.venv-train/bin/python -m pip install --upgrade pip
.venv-train/bin/python -m pip install mlx-lm datasets
.venv-train/bin/python -c "import mlx_lm; print('MLX ready')"
echo "Training tools installed. Open Eclipse -> Training."
