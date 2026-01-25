#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOT_DIR="$ROOT_DIR/bot"

cd "$BOT_DIR"

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

PYTHONPATH="$BOT_DIR/src" python -m ramus_bot
