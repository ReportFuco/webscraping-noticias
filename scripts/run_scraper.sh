#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs

export PYTHONPATH="${ROOT_DIR}/src"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export LOG_FILE="${LOG_FILE:-${ROOT_DIR}/logs/news_scraper.log}"

. "${ROOT_DIR}/.venv/bin/activate"
python src/main.py
