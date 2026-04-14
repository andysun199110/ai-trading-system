#!/usr/bin/env bash
set -euo pipefail
TARGET_TAG="${1:?usage: rollback.sh <git-ref>}"
cd "$(dirname "$0")/../.."
git checkout "$TARGET_TAG"
docker compose up -d --build
./infra/scripts/healthcheck.sh
