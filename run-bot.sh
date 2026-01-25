#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$ROOT_DIR/bot"
VENV_DIR="$BOT_DIR/.venv"
BRANCH="main"
REMOTE="origin"
CHECK_INTERVAL_SECONDS=60

log() {
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"
}

ensure_repo() {
  if [[ ! -d "$ROOT_DIR/.git" ]]; then
    log "ERROR: Not a git repo: $ROOT_DIR"
    exit 1
  fi
}

ensure_venv() {
  if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    log "Creating virtualenv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
}

install_deps() {
  log "Installing Python deps"
  pip install --upgrade pip
  pip install -r "$BOT_DIR/requirements-dev.txt"
}

pull_latest() {
  git -C "$ROOT_DIR" fetch "$REMOTE" "$BRANCH"
  local local_rev
  local remote_rev
  local_rev=$(git -C "$ROOT_DIR" rev-parse HEAD)
  remote_rev=$(git -C "$ROOT_DIR" rev-parse "$REMOTE/$BRANCH")
  if [[ "$local_rev" != "$remote_rev" ]]; then
    log "Updating repo from $local_rev to $remote_rev"
    git -C "$ROOT_DIR" pull --ff-only "$REMOTE" "$BRANCH"
    return 0
  fi
  return 1
}

run_bot() {
  log "Starting Ramus bot"
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
  PYTHONPATH="$BOT_DIR/src" python -m ramus_bot
}

main() {
  ensure_repo
  ensure_venv
  install_deps

  while true; do
    run_bot &
    BOT_PID=$!
    log "Bot PID: $BOT_PID"

    while kill -0 "$BOT_PID" 2>/dev/null; do
      sleep "$CHECK_INTERVAL_SECONDS"
      if pull_latest; then
        log "Repo updated; restarting bot"
        install_deps
        kill "$BOT_PID" || true
        wait "$BOT_PID" || true
        break
      fi
    done

    if ! kill -0 "$BOT_PID" 2>/dev/null; then
      log "Bot exited; restarting in ${CHECK_INTERVAL_SECONDS}s"
      sleep "$CHECK_INTERVAL_SECONDS"
    fi
  done
}

main "$@"
