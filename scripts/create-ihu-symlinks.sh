#!/bin/bash

# Base directory containing the "1-" directories
base_dir="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/create_ihu_symlinks.log"
cutoff_date="20240529"

# Ensure the log file directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "Script started."

# Loop through each "1-" directory in the base directory
for dir in "$base_dir"/1-*; do
  if [[ -d "$dir" ]]; then
    dir_date=$(basename "$dir" | cut -d'-' -f2)
    if [[ "$dir_date" > "$cutoff_date" ]]; then
      log_message "Processing directory: $dir"
      # Loop through each file in the current directory
      for file in "$dir"/*; do
        if [[ -f "$file" ]]; then
          if [[ "$file" == *.jpg || "$file" == *.html ]]; then
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

            # Copy the file to the new ihu directory only if it doesn't already exist
            dest_file="${ihu_dir}/$(basename "$file")"
            if [[ ! -e "$dest_file" ]]; then
              cp "$file" "$dest_file"
              if [ $? -eq 0 ]; then
                log_message "Copied $file to $ihu_dir"
              else
                log_message "ERROR: Failed to copy $file to $ihu_dir"
              fi
            else
              log_message "File $file already exists in $ihu_dir"
            fi
          else
            log_message "Skipping non-jpg/html file: $file"
          fi
        else
          log_message "Skipping non-file item: $file"
        fi
      done
    else
      log_message "Skipping directory older than cutoff date: $dir"
    fi
  else
    log_message "Skipping non-directory item: $dir"
  fi
done

log_message "Files organized successfully using copies."
