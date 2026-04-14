#!/usr/bin/env bash
set -euo pipefail
MODE="${1:?usage: run_mode.sh <research|shadow|staging|live|develop>}"
cd "$(dirname "$0")/../.."
ENV="$MODE" docker compose up -d --build
