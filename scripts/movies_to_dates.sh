

# # Define the base directories
# # SOURCE_DIR="/nfs/php1/ar2/P/HP1/REDUCTION/MOVIES"
# SOURCE_DIR="/nfs/php2/ar0/P/HP1/REDUCTION/MOVIES"
# TARGET_DIR="/nfs/hatops/ar0/hatpi-website"
# LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/movies_to_dates.log"

# # Ensure the log file directory exists
# mkdir -p "$(dirname "$LOG_FILE")"

# # Function to log messages with timestamp
# log_message() {
#     echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
# }

# log_message "Script started."

# # Iterate over each folder in the source directory
# for folder in "$SOURCE_DIR"/*; do
#     if [ -d "$folder" ]; then
#         folder_name=$(basename "$folder")

#         # Check if the folder exists in the target directory
#         if [ -d "$TARGET_DIR/$folder_name" ]; then
#             log_message "Processing $folder_name"

#             # Find all .mp4 files in the source folder and create symlinks in the target folder
#             find "$folder" -type f -name "*.mp4" | while read file; do
#                 file_name=$(basename "$file")
#                 relative_path="/nfs/php2/ar0/P/HP1/REDUCTION/MOVIES/$folder_name/$file_name"
#                 target_symlink="$TARGET_DIR/$folder_name/$file_name"

#                 # Check if the symlink already exists
#                 if [ ! -e "$target_symlink" ]; then
#                     ln -s "$relative_path" "$target_symlink"
#                     if [ $? -eq 0 ]; then
#                         log_message "Created symlink for $relative_path in $TARGET_DIR/$folder_name"
#                     else
#                         log_message "ERROR: Failed to create symlink for $relative_path in $TARGET_DIR/$folder_name"
#                     fi
#                 else
#                     log_message "Skipping $file_name: Symlink already exists in $TARGET_DIR/$folder_name"
#                 fi
#             done
#         else
#             log_message "Skipping $folder_name: Target folder does not exist."
#         fi
#     else
#         log_message "Skipping non-directory item: $folder"
#     fi
# done

# log_message "Script completed."


#!/bin/bash

SOURCE_DIR="/nfs/php2/ar0/P/HP1/REDUCTION/MOVIES"
TARGET_DIR="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/movies_to_dates.log"

mkdir -p "$(dirname "$LOG_FILE")"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "Script started."

# Helper to check if folder date is <= 10 days old
is_within_10_days() {
    # Expect something like "1-20250120"
    folder_name="$1"
    # Extract "20250120"
    date_str="${folder_name#1-}"     # remove "1-" if present
    date_str="${date_str##*/}"       # just in case, strip any path
    # Convert to epoch (skip if invalid or if date is in the future)
    folder_epoch=$(date -d "$date_str" +%s 2>/dev/null) || return 1
    now_epoch=$(date +%s)
    diff_days=$(( (now_epoch - folder_epoch) / 86400 ))

    # diff_days < 0 => folder is in the future; skip
    # diff_days > 10 => folder is older than 10 days; skip
    [ $diff_days -ge 0 ] && [ $diff_days -le 10 ]
}

for folder in "$SOURCE_DIR"/*; do
    if [ -d "$folder" ]; then
        folder_name=$(basename "$folder")

        # Only proceed if within 10 days old
        if is_within_10_days "$folder_name"; then
            # Check if the same folder exists in the target
            if [ -d "$TARGET_DIR/$folder_name" ]; then
                log_message "Processing $folder_name"

                find "$folder" -type f -name "*.mp4" | while read file; do
                    file_name=$(basename "$file")
                    relative_path="$SOURCE_DIR/$folder_name/$file_name"
                    target_symlink="$TARGET_DIR/$folder_name/$file_name"

                    if [ ! -e "$target_symlink" ]; then
                        ln -s "$relative_path" "$target_symlink"
                        if [ $? -eq 0 ]; then
                            log_message "Created symlink for $relative_path in $TARGET_DIR/$folder_name"
                        else
                            log_message "ERROR: Failed to create symlink for $relative_path in $TARGET_DIR/$folder_name"
                        fi
                    else
                        log_message "Skipping $file_name: Symlink already exists in $TARGET_DIR/$folder_name"
                    fi
                done

            else
                log_message "Skipping $folder_name: Target folder does not exist."
            fi
        else
            log_message "Skipping $folder_name: Not within 10 days old."
        fi
    else
        log_message "Skipping non-directory item: $folder"
    fi
done

log_message "Script completed."
