#!/usr/bin/env bash
set -euo pipefail

APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
APP_RELOAD="${APP_RELOAD:-true}"

if [[ "$APP_RELOAD" == "true" ]]; then
  uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT" --reload
else
  uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
fi
