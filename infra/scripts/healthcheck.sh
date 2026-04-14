#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://127.0.0.1/health >/dev/null
curl -fsS http://127.0.0.1/admin/health >/dev/null
echo "healthcheck ok"
