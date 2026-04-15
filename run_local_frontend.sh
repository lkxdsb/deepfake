#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export FRONTEND_ONLY="${FRONTEND_ONLY:-true}"

exec bash "$SCRIPT_DIR/run_local.sh"
