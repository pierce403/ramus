#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$ROOT_DIR/bot"
VENV_DIR="$BOT_DIR/.venv"
BRANCH="main"
REMOTE="origin"
HEALTH_CHECK_SECONDS=30
GIT_CHECK_INTERVAL_SECONDS=600
RESTART_DELAY_SECONDS=3
UPDATE_RESTART_DELAY_SECONDS=3
LOCK_FILE=""
LOCK_FD=200
BOT_PID_FILE=""

log() {
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*"
}

load_env() {
  local env_file=""
  if [[ -n "${RAMUS_ENV_FILE:-}" ]]; then
    env_file="$RAMUS_ENV_FILE"
  else
    if [[ -f "$ROOT_DIR/.env" ]]; then
      env_file="$ROOT_DIR/.env"
    elif [[ -f "$BOT_DIR/.env" ]]; then
      env_file="$BOT_DIR/.env"
    fi
  fi

  if [[ -n "$env_file" ]]; then
    log "Loading env from $env_file"
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

validate_env() {
  local missing=()
  local required_vars=()
  for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
      missing+=("$var")
    fi
  done

  if (( ${#missing[@]} )); then
    log "ERROR: Missing required env vars: ${missing[*]}"
    return 1
  fi

  return 0
}

ensure_repo() {
  if [[ ! -d "$ROOT_DIR/.git" ]]; then
    log "ERROR: Not a git repo: $ROOT_DIR"
    exit 1
  fi
}

ensure_single_instance() {
  local state_dir="$ROOT_DIR/state"
  mkdir -p "$state_dir"
  LOCK_FILE="$state_dir/ramus_bot.lock"
  BOT_PID_FILE="$state_dir/ramus_bot.pid"

  if command -v flock >/dev/null 2>&1; then
    exec {LOCK_FD}>"$LOCK_FILE"
    if ! flock -n "$LOCK_FD"; then
      local existing_pid=""
      existing_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
      if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
        log "Stopping existing supervisor PID $existing_pid"
        kill "$existing_pid" 2>/dev/null || true
        for _ in {1..5}; do
          sleep 1
          if flock -n "$LOCK_FD"; then
            break
          fi
        done
      fi
      if ! flock -n "$LOCK_FD"; then
        local supervisors=()
        if command -v pgrep >/dev/null 2>&1; then
          mapfile -t supervisors < <(pgrep -f "$ROOT_DIR/run-bot.sh" || true)
        fi
        for pid in "${supervisors[@]}"; do
          if [[ "$pid" =~ ^[0-9]+$ ]] && [[ "$pid" != "$$" ]]; then
            log "Stopping supervisor PID $pid"
            kill "$pid" 2>/dev/null || true
          fi
        done
        sleep 2
        if ! flock -n "$LOCK_FD"; then
          log "ERROR: Another supervisor is running; exiting."
          exit 1
        fi
      fi
    fi
    echo "$$" >"$LOCK_FILE"
  else
    log "WARNING: flock not available; skipping supervisor lock."
    if [[ -f "$LOCK_FILE" ]]; then
      local existing_pid=""
      existing_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
      if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
        log "ERROR: Another supervisor is running (PID $existing_pid); exiting."
        exit 1
      fi
    fi
    echo "$$" >"$LOCK_FILE"
  fi

  # Stop any stray bot processes from previous runs.
  cleanup_stray_bots ""

  trap 'cleanup_on_exit' EXIT INT TERM
}

cleanup_stray_bots() {
  local current_pid="${1:-}"
  local pids=()
  if command -v pgrep >/dev/null 2>&1; then
    mapfile -t pids < <(pgrep -f "python -m ramus_bot" || true)
  fi
  for pid in "${pids[@]}"; do
    if [[ -n "$pid" && "$pid" != "$$" && "$pid" != "$current_pid" ]]; then
      log "Stopping stray bot process PID $pid"
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        log "Force killing stray bot process PID $pid"
        kill -9 "$pid" 2>/dev/null || true
      fi
    fi
  done
}

cleanup_on_exit() {
  if [[ -n "$BOT_PID_FILE" && -f "$BOT_PID_FILE" ]]; then
    rm -f "$BOT_PID_FILE"
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
  ensure_single_instance
  ensure_venv
  install_deps

  while true; do
    load_env
    if ! validate_env; then
      log "Bot not started; retrying in ${RESTART_DELAY_SECONDS}s"
      sleep "$RESTART_DELAY_SECONDS"
      continue
    fi

    local restart_reason="exit"
    local last_git_check
    last_git_check="$(date +%s)"

    run_bot &
    BOT_PID=$!
    log "Bot PID: $BOT_PID"
    echo "$BOT_PID" >"$BOT_PID_FILE"

    while kill -0 "$BOT_PID" 2>/dev/null; do
      sleep "$HEALTH_CHECK_SECONDS"
      cleanup_stray_bots "$BOT_PID"

      local now
      now="$(date +%s)"
      if (( now - last_git_check >= GIT_CHECK_INTERVAL_SECONDS )); then
        last_git_check="$now"
        if pull_latest; then
          log "Repo updated; restarting bot in ${UPDATE_RESTART_DELAY_SECONDS}s"
          install_deps
          kill "$BOT_PID" 2>/dev/null || true
          wait "$BOT_PID" || true
          restart_reason="update"
          break
        fi
      fi
    done

    if ! kill -0 "$BOT_PID" 2>/dev/null; then
      if [[ "$restart_reason" == "update" ]]; then
        sleep "$UPDATE_RESTART_DELAY_SECONDS"
      else
        log "Bot exited; restarting in ${RESTART_DELAY_SECONDS}s"
        sleep "$RESTART_DELAY_SECONDS"
      fi
    fi
  done
}

main "$@"
