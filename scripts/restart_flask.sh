#!/bin/bash

log_file="/nfs/hatops/ar0/hatpi-website/logs/restart_flask.log"

echo "Restart script started at $(date)" >> $log_file

# Kill any running Flask processes
pkill -f "flask run"
if [ $? -eq 0 ]; then
    echo "Flask process killed successfully" >> $log_file
else
    echo "Failed to kill Flask process or no process found" >> $log_file
fi

# Wait for a few seconds to ensure Flask processes are terminated
sleep 5

# Check if any Flask processes are still running
if pgrep -f "flask run" > /dev/null; then
    echo "Flask process still running after pkill" >> $log_file
    exit 1
fi

# Start Flask application
cd /nfs/hatops/ar0/hatpi-website
export FLASK_APP=app.py
export FLASK_ENV=production  # Set environment to production
nohup /usr/bin/python2.7 -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &

if [ $? -eq 0 ]; then
    echo "Flask started successfully at $(date)" >> $log_file
else
    echo "Failed to start Flask" >> $log_file
fi
