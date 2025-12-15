#!/bin/bash

set -euo pipefail

APP_DIR="/nfs/hatops/ar0/hatpi-website"
PID_FILE="$APP_DIR/gunicorn.pid"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping Gunicorn PID $PID..."
    kill -TERM "$PID"
    # Wait up to 20 seconds
    for i in $(seq 1 20); do
      if ps -p "$PID" > /dev/null 2>&1; then
        sleep 1
      else
        echo "Gunicorn stopped."
        exit 0
      fi
    done
    echo "Gunicorn did not stop gracefully; sending KILL."
    kill -KILL "$PID" || true
  else
    echo "No running Gunicorn process with PID $PID"
  fi
  rm -f "$PID_FILE"
else
  echo "PID file not found; Gunicorn may not be running."
fi


