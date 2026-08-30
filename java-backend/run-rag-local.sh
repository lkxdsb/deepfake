#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f .env ]]; then
  echo 'Missing java-backend/.env. Copy the local API variables there; never commit API keys.' >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
. ./.env
set +a
export SPRING_PROFILES_ACTIVE="${SPRING_PROFILES_ACTIVE:-rag-local}"
exec mvn spring-boot:run
