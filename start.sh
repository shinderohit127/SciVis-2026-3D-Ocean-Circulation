#!/usr/bin/env bash
# start.sh — launch all THALASSA services and open the browser.
# Usage: bash start.sh
# Ctrl-C stops every service cleanly.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$REPO/thalassa/backend"
FRONTEND="$REPO/thalassa/frontend"
LOG_DIR="$REPO/.logs"
CONDA_ENV="ocean"

# ── colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()  { echo -e "${CYAN}[thalassa]${RESET} $*"; }
ok()    { echo -e "${GREEN}[  ok  ]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[ warn ]${RESET} $*"; }
fatal() { echo -e "${RED}[ fail ]${RESET} $*"; exit 1; }

# ── process tracking ───────────────────────────────────────────────────────────
PIDS=()
cleanup() {
  echo ""
  info "Shutting down…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  # Give processes a moment, then force-kill stragglers
  sleep 1
  for pid in "${PIDS[@]}"; do
    kill -9 "$pid" 2>/dev/null || true
  done
  ok "All services stopped."
}
trap cleanup EXIT INT TERM

mkdir -p "$LOG_DIR"

# ── helpers ────────────────────────────────────────────────────────────────────
wait_for_port() {
  local name=$1 port=$2 retries=${3:-30}
  local i=0
  while ! nc -z 127.0.0.1 "$port" 2>/dev/null; do
    i=$((i+1))
    if [ "$i" -ge "$retries" ]; then
      fatal "$name did not come up on port $port after ${retries}s — check .logs/$name.log"
    fi
    sleep 1
  done
  ok "$name ready on :$port"
}

# ── conda activation ───────────────────────────────────────────────────────────
CONDA_SH="$(conda info --base)/etc/profile.d/conda.sh"
[ -f "$CONDA_SH" ] || fatal "conda not found. Is Anaconda installed?"
# shellcheck disable=SC1090
source "$CONDA_SH"
conda activate "$CONDA_ENV" || fatal "conda env '$CONDA_ENV' not found"
PYTHON="$(which python)"
info "Python: $PYTHON"

# ── 1. Redis ───────────────────────────────────────────────────────────────────
info "Starting Redis…"
if nc -z 127.0.0.1 6379 2>/dev/null; then
  warn "Redis already running on :6379 — reusing it"
else
  redis-server --daemonize no \
    >> "$LOG_DIR/redis.log" 2>&1 &
  PIDS+=($!)
  wait_for_port redis 6379
fi

# ── 2. FastAPI backend ─────────────────────────────────────────────────────────
info "Starting FastAPI backend…"
(
  cd "$BACKEND"
  PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload \
    >> "$LOG_DIR/backend.log" 2>&1
) &
PIDS+=($!)
wait_for_port backend 8000

# ── 3. Celery worker ───────────────────────────────────────────────────────────
info "Starting Celery worker…"
(
  cd "$BACKEND"
  PYTHONPATH=. celery -A workers.celery_app worker \
    --loglevel=info --concurrency=2 \
    >> "$LOG_DIR/celery.log" 2>&1
) &
PIDS+=($!)
# Celery doesn't expose a TCP port, so just give it 5 s to start
sleep 5
ok "Celery worker started (pid ${PIDS[-1]})"

# ── 4. Vite frontend ───────────────────────────────────────────────────────────
info "Starting Vite dev server…"
(
  cd "$FRONTEND"
  npm run dev -- --force \
    >> "$LOG_DIR/frontend.log" 2>&1
) &
PIDS+=($!)
wait_for_port frontend 5173

# ── 5. Open browser ────────────────────────────────────────────────────────────
URL="http://localhost:5173"
if command -v xdg-open &>/dev/null; then
  xdg-open "$URL" &>/dev/null &
elif command -v open &>/dev/null; then
  open "$URL" &
fi

echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  THALASSA is running${RESET}"
echo -e "  Frontend  →  ${CYAN}http://localhost:5173${RESET}"
echo -e "  API       →  ${CYAN}http://localhost:8000/docs${RESET}"
echo -e "  Logs      →  ${YELLOW}$LOG_DIR/${RESET}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
info "Press Ctrl-C to stop all services."

# ── keep alive ─────────────────────────────────────────────────────────────────
wait
