#!/usr/bin/env bash
# start_server.sh — launch the local vision (llama-server) backend.
#
# Usage:
#   ./scripts/start_server.sh          # auto-detect GPU vs CPU
#   ./scripts/start_server.sh --cpu    # force CPU mode
#   ./scripts/start_server.sh --gpu    # force GPU mode (ROCm/HIP)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MODEL_DIR="${MODEL_DIR:-$PROJECT_DIR/models}"
PORT="${PORT:-8081}"

MODEL="$MODEL_DIR/Qwen3.5-0.8B-UD-Q4_K_XL.gguf"
MMPROJ="$MODEL_DIR/mmproj-F16.gguf"

if [[ ! -f "$MODEL" || ! -f "$MMPROJ" ]]; then
  echo "ERROR: model files not found in $MODEL_DIR"
  echo "Run scripts/download_models.sh first."
  exit 1
fi

# Find llama-server
LLAMA_SERVER="${LLAMA_SERVER:-$(which llama-server 2>/dev/null || true)}"
if [[ -z "$LLAMA_SERVER" ]]; then
  # Check common build locations
  for candidate in \
    "$PROJECT_DIR/../llama.cpp-build/build-rocm/bin/llama-server" \
    "$PROJECT_DIR/../llama.cpp-build/build/bin/llama-server"; do
    if [[ -x "$candidate" ]]; then
      LLAMA_SERVER="$candidate"
      break
    fi
  done
fi
if [[ -z "$LLAMA_SERVER" ]]; then
  echo "ERROR: llama-server not found. Install llama.cpp or set LLAMA_SERVER."
  exit 1
fi

# Decide GPU vs CPU
MODE="${1:-auto}"
NGL=99
if [[ "$MODE" == "--cpu" ]]; then
  NGL=0
elif [[ "$MODE" == "--gpu" ]]; then
  NGL=99
elif [[ "$MODE" == "auto" ]]; then
  if command -v rocminfo >/dev/null 2>&1 && rocminfo 2>/dev/null | grep -q "gfx1151"; then
    echo "Detected AMD ROCm GPU (gfx1151) — using GPU mode"
    NGL=99
  else
    echo "No ROCm GPU detected — using CPU mode"
    NGL=0
  fi
fi

echo "Starting vision server on :$PORT"
echo "  binary: $LLAMA_SERVER"
echo "  model:  $MODEL"
echo "  mmproj: $MMPROJ"
echo "  ngl:    $NGL"
exec "$LLAMA_SERVER" \
  --model "$MODEL" \
  --mmproj "$MMPROJ" \
  -ngl "$NGL" \
  --host 0.0.0.0 --port "$PORT" \
  --temp 0.6 --top-p 0.95 --top-k 20