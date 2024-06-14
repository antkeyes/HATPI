#!/bin/bash

# Base directory containing the "1-" directories
base_dir="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/create_ihu_symlinks.log"

# Ensure the log file directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Reference date in YYYYMMDD format
reference_date="20240529"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "Script started."

# Loop through each "1-" directory in the base directory
for dir in "$base_dir"/1-*; do
  if [[ -d "$dir" ]]; then
    # Extract the date from the directory name
    dir_date=$(basename "$dir" | cut -d'-' -f2)
    
    # Check if the directory date is greater than the reference date
    if [[ "$dir_date" > "$reference_date" ]]; then
      log_message "Processing directory: $dir"
      # Loop through each file in the current directory
      for file in "$dir"/*; do
        if [[ -f "$file" ]]; then
          log_message "Processing file: $file"
          # Extract the ihu number from the filename
          if [[ "$file" =~ ihu-([0-9]+) ]]; then
            ihu_number="${BASH_REMATCH[1]}"
          elif [[ "$file" =~ _([0-9]+)_ ]]; then
            ihu_number="${BASH_REMATCH[1]}"
          else
            log_message "No ihu number found in file: $file"
            continue
          fi

          log_message "Found ihu number: $ihu_number"
          # Create the new ihu directory if it doesn't exist
          ihu_dir="${base_dir}/ihu-${ihu_number}"
          mkdir -p "$ihu_dir"

          # Create a symlink to the file in the new ihu directory only if it doesn't already exist
          link_name="${ihu_dir}/$(basename "$file")"
          if [[ ! -e "$link_name" ]]; then
            ln -s "$file" "$link_name"
            if [ $? -eq 0 ]; then
              log_message "Created symlink for $file in $ihu_dir"
            else
              log_message "ERROR: Failed to create symlink for $file in $ihu_dir"
            fi
          else
            log_message "Symlink for $file already exists in $ihu_dir"
          fi
        else
          log_message "Skipping non-file item: $file"
        fi
      done
    else
      log_message "Skipping directory: $dir (older than reference date)"
    fi
  else
    log_message "Skipping non-directory item: $dir"
  fi
done

log_message "Files organized successfully using symlinks."
