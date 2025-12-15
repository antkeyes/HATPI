#!/bin/bash

set -euo pipefail

APP_DIR="/nfs/hatops/ar0/hatpi-website"
LOG_DIR="$APP_DIR/logs"
PID_FILE="$APP_DIR/gunicorn.pid"

mkdir -p "$LOG_DIR"
cd "$APP_DIR"

# Prefer system-wide gunicorn if available, else fallback to user install
if command -v gunicorn >/dev/null 2>&1; then
  GUNICORN_BIN="$(command -v gunicorn)"
else
  GUNICORN_BIN="$HOME/.local/bin/gunicorn"
fi

if [ ! -x "$GUNICORN_BIN" ]; then
  echo "gunicorn not found; install with: python3 -m pip install --user gunicorn" >&2
  exit 1
fi

# If already running, exit
if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" > /dev/null 2>&1; then
  echo "Gunicorn appears to be running with PID $(cat "$PID_FILE")."
  exit 0
fi

# Start in background
nohup "$GUNICORN_BIN" -c "$APP_DIR/gunicorn.conf.py" app:app \
  >> "$LOG_DIR/gunicorn.supervisor.log" 2>&1 &

echo "Gunicorn start initiated. Check logs in $LOG_DIR"


