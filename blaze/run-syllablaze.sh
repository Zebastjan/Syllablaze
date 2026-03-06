#!/bin/bash
# Syllablaze startup script that ensures the virtual environment is used

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# Set CUDA library path for GPU acceleration
export LD_LIBRARY_PATH=/opt/cuda/targets/x86_64-linux/lib:$LD_LIBRARY_PATH

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating one..."
    python -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install -e "$SCRIPT_DIR"
else
    source "$VENV_DIR/bin/activate"
fi

exec syllablaze "$@"
