#!/bin/bash
set -euo pipefail


APP_HOST=${APP_HOST:-0.0.0.0}
APP_PORT=${APP_PORT:-8000}

export OMP_NUM_THREADS=8
export MODEL_CFG_PATH=logs/2t2rpckz/setting.yaml
export MODEL_CKPT_PATH=logs/2t2rpckz/checkpoints/last.ckpt
export OUTPUT_ROOT=./outputs

export AUDIO_MODEL_SOURCE=/root/autodl-tmp/deepfake/audio/model.safetensors
export AUDIO_FAKE_THRESHOLD=0.5
export AUDIO_SAMPLE_RATE=16000

export VIDEO_CLIP_STEP=4
export VIDEO_BATCH_SIZE=4

exec uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
