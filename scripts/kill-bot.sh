#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/state"
LOCK_FILE="$STATE_DIR/ramus_bot.lock"
PID_FILE="$STATE_DIR/ramus_bot.pid"

log() {
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"
}

stop_pid() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return
  fi
  if kill -0 "$pid" 2>/dev/null; then
    log "Stopping PID $pid"
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      log "Force killing PID $pid"
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
}

stop_supervisors() {
  if [[ -f "$LOCK_FILE" ]]; then
    local lock_pid=""
    lock_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
    if [[ "$lock_pid" =~ ^[0-9]+$ ]]; then
      stop_pid "$lock_pid"
    fi
  fi

  if command -v pgrep >/dev/null 2>&1; then
    local supervisors=()
    mapfile -t supervisors < <(pgrep -f "$ROOT_DIR/run-bot.sh" || true)
    for pid in "${supervisors[@]}"; do
      stop_pid "$pid"
    done
  fi
}

stop_bots() {
  if command -v pgrep >/dev/null 2>&1; then
    local bots=()
    mapfile -t bots < <(pgrep -f "python -m ramus_bot" || true)
    for pid in "${bots[@]}"; do
      stop_pid "$pid"
    done
  fi
}

cleanup_files() {
  rm -f "$LOCK_FILE" "$PID_FILE"
}

mkdir -p "$STATE_DIR"
stop_supervisors
stop_bots
cleanup_files

log "Ramus bot processes stopped."
