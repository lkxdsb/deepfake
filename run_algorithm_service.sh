#!/usr/bin/env bash
set -euo pipefail

ALGORITHM_HOST="${ALGORITHM_HOST:-127.0.0.1}"
ALGORITHM_PORT="${ALGORITHM_PORT:-8100}"

exec uvicorn algorithm_service.main:app --host "$ALGORITHM_HOST" --port "$ALGORITHM_PORT"
