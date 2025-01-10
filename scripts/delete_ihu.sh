#!/bin/bash

# Base directory containing the "ihu-" directories
base_dir="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/delete_files.log"

# Ensure the log file directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "Script started."

# Loop through each "ihu-" directory in the base directory
for dir in "$base_dir"/ihu-*; do
  if [[ -d "$dir" ]]; then
    log_message "Processing directory: $dir"
    # Loop through each file in the current directory
    for file in "$dir"/*; do
      if [[ -f "$file" ]]; then
        extension="${file##*.}"
        if [[ "$extension" == "mp4" ]]; then
          log_message "Deleting file: $file"
          rm "$file"
          if [ $? -eq 0 ]; then
            log_message "Deleted $file successfully"
          else
            log_message "ERROR: Failed to delete $file"
          fi
        else
          log_message "Skipping non-mp4 file: $file"
        fi
      else
        log_message "Skipping non-file item: $file"
      fi
    done
  else
    log_message "Skipping non-directory item: $dir"
  fi
done

log_message "File deletion completed successfully."
