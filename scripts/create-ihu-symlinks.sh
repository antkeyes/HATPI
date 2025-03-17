

# # Base directory containing the "1-" directories
# base_dir="/nfs/hatops/ar0/hatpi-website"
# LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/create_ihu_symlinks.log"

# # Ensure the log file directory exists
# mkdir -p "$(dirname "$LOG_FILE")"

# # Function to log messages with timestamp
# log_message() {
#     echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
# }

# log_message "Script started (symlink version)."

# # Loop through each "1-" directory in the base directory
# for dir in "$base_dir"/1-*; do
#   # Make sure it really is a directory
#   if [[ -d "$dir" ]]; then
#     log_message "Processing directory: $dir"
#     # Loop through each file in the current directory
#     for file in "$dir"/*; do
#       # If it's a normal file (not a subdirectory, not a symlink, etc.)
#       if [[ -f "$file" ]]; then
        
#         # We only process .jpg or .html
#         if [[ "$file" == *.jpg || "$file" == *.html ]]; then
#           log_message "Processing file: $file"
          
#           # Extract the IHU number from the filename
#           # e.g., something like "xxx_45_yyy.html" or "ihu-45-whatever.jpg"
#           ihu_number=""
#           if [[ "$file" =~ ihu-([0-9]+) ]]; then
#             ihu_number="${BASH_REMATCH[1]}"
#           elif [[ "$file" =~ _([0-9]+)_ ]]; then
#             ihu_number="${BASH_REMATCH[1]}"
#           else
#             log_message "No ihu number found in file: $file"
#             continue
#           fi

#           log_message "Found ihu number: $ihu_number"

#           # Create the new ihu directory if it doesn't exist
#           ihu_dir="${base_dir}/ihu-${ihu_number}"
#           mkdir -p "$ihu_dir"

#           # The path for the symlink we want to create
#           dest_file="${ihu_dir}/$(basename "$file")"
          
#           # Check if something already exists at that name
#           if [[ ! -e "$dest_file" ]]; then
#             # Create a symlink from the IHU directory pointing to the original file
#             ln -s "$file" "$dest_file"
#             if [ $? -eq 0 ]; then
#               log_message "Created symlink: $dest_file -> $file"
#             else
#               log_message "ERROR: Failed to create symlink: $dest_file -> $file"
#             fi
#           else
#             log_message "File already exists (skipping): $dest_file"
#           fi
#         else
#           log_message "Skipping non-jpg/html file: $file"
#         fi
#       else
#         log_message "Skipping non-file item: $file"
#       fi
#     done
#   else
#     log_message "Skipping non-directory item: $dir"
#   fi
# done

# log_message "Script completed successfully (symlink version)."


#!/bin/bash

base_dir="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/create_ihu_symlinks.log"

mkdir -p "$(dirname "$LOG_FILE")"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "Script started (symlink version)."

# Helper to check if "1-YYYYMMDD" directory is <= 10 days old
is_within_10_days() {
    dir_path="$1"
    dir_name=$(basename "$dir_path")
    date_str="${dir_name#1-}"  # remove "1-"
    folder_epoch=$(date -d "$date_str" +%s 2>/dev/null) || return 1
    now_epoch=$(date +%s)
    diff_days=$(( (now_epoch - folder_epoch) / 86400 ))

    [ $diff_days -ge 0 ] && [ $diff_days -le 10 ]
}

# Loop through each "1-" directory in the base directory
for dir in "$base_dir"/1-*; do
  if [[ -d "$dir" ]]; then
    # Skip if older than 10 days
    if is_within_10_days "$dir"; then
      log_message "Processing directory: $dir"
      for file in "$dir"/*; do
        if [[ -f "$file" ]]; then
          if [[ "$file" == *.jpg || "$file" == *.html ]]; then
            log_message "Processing file: $file"

            # Extract the IHU number
            ihu_number=""
            if [[ "$file" =~ ihu-([0-9]+) ]]; then
              ihu_number="${BASH_REMATCH[1]}"
            elif [[ "$file" =~ _([0-9]+)_ ]]; then
              ihu_number="${BASH_REMATCH[1]}"
            else
              log_message "No ihu number found in file: $file"
              continue
            fi

            log_message "Found ihu number: $ihu_number"

            ihu_dir="${base_dir}/ihu-${ihu_number}"
            mkdir -p "$ihu_dir"

            dest_file="${ihu_dir}/$(basename "$file")"

            if [[ ! -e "$dest_file" ]]; then
              ln -s "$file" "$dest_file"
              if [ $? -eq 0 ]; then
                log_message "Created symlink: $dest_file -> $file"
              else
                log_message "ERROR: Failed to create symlink: $dest_file -> $file"
              fi
            else
              log_message "File already exists (skipping): $dest_file"
            fi
          else
            log_message "Skipping non-jpg/html file: $file"
          fi
        else
          log_message "Skipping non-file item: $file"
        fi
      done
    else
      log_message "Skipping directory (older/future): $dir"
    fi
  else
    log_message "Skipping non-directory item: $dir"
  fi
done

log_message "Script completed successfully (symlink version)."
