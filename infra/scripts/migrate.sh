#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
docker compose exec -T api alembic -c infra/migrations/alembic.ini upgrade head
