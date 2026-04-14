#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
git fetch --all
git checkout "${1:-develop}"
git pull --ff-only origin "${1:-develop}"
docker compose pull || true
docker compose build --no-cache
docker compose up -d
./infra/scripts/migrate.sh
./infra/scripts/healthcheck.sh
