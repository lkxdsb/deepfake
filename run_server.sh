#!/bin/bash
set -euo pipefail

strip_cr() {
  printf '%s' "$1" | tr -d '\r'
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_HOST="$(strip_cr "${APP_HOST:-0.0.0.0}")"
APP_PORT="$(strip_cr "${APP_PORT:-8000}")"

export OMP_NUM_THREADS="$(strip_cr "${OMP_NUM_THREADS:-8}")"
export MODEL_CFG_PATH="$(strip_cr "${MODEL_CFG_PATH:-$SCRIPT_DIR/logs/DFD-FCG/na2vi8su/setting.yaml}")"
export MODEL_CKPT_PATH="$(strip_cr "${MODEL_CKPT_PATH:-$SCRIPT_DIR/logs/DFD-FCG/na2vi8su/checkpoints/epoch=29-step=33540.ckpt}")"
export OUTPUT_ROOT="$(strip_cr "${OUTPUT_ROOT:-$SCRIPT_DIR/outputs}")"

export VIDEO_CLIP_STEP="$(strip_cr "${VIDEO_CLIP_STEP:-4}")"
export VIDEO_BATCH_SIZE="$(strip_cr "${VIDEO_BATCH_SIZE:-16}")"

exec uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
