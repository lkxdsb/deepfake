#!/usr/bin/env bash
set -euo pipefail

APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
APP_RELOAD="${APP_RELOAD:-true}"
FRONTEND_ONLY="${FRONTEND_ONLY:-false}"

export APP_HOST
export APP_PORT
export APP_RELOAD
export FRONTEND_ONLY

echo "[run_local] APP_HOST=$APP_HOST APP_PORT=$APP_PORT APP_RELOAD=$APP_RELOAD FRONTEND_ONLY=$FRONTEND_ONLY"
if [[ "$APP_RELOAD" =~ ^([Tt][Rr][Uu][Ee]|1|[Yy][Ee][Ss]|[Oo][Nn])$ ]]; then
  uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT" --reload
else
  uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
fi
