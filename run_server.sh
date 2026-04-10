#!/bin/bash
set -euo pipefail


APP_HOST=${APP_HOST:-0.0.0.0}
APP_PORT=${APP_PORT:-8000}

export OMP_NUM_THREADS=8
export MODEL_CFG_PATH=logs/2t2rpckz/setting.yaml
export MODEL_CKPT_PATH=logs/2t2rpckz/checkpoints/epoch=9-step=11220.ckpt
export OUTPUT_ROOT=./outputs

export VIDEO_CLIP_STEP=4
export VIDEO_BATCH_SIZE=8

exec uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
