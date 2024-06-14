#!/bin/bash

LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/rsync.log"

# Run rsync and capture output and errors
rsync -av --no-perms --no-owner --no-group --omit-dir-times /nfs/hatops/ar0/hatpi-plots/ /nfs/hatops/ar0/hatpi-website/ >> "$LOG_FILE" 2>&1

# Check the exit status of the rsync command
if [ $? -ne 0 ]; then
  echo "rsync command failed. Check the log file at $LOG_FILE for details." >> "$LOG_FILE"
else
  echo "rsync command completed successfully." >> "$LOG_FILE"
fi
