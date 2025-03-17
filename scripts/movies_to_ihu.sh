

# # Define the base directories
# # SOURCE_DIR="/nfs/php1/ar2/P/HP1/REDUCTION/MOVIES" 
# SOURCE_DIR="/nfs/php2/ar0/P/HP1/REDUCTION/MOVIES"
# TARGET_DIR="/nfs/hatops/ar0/hatpi-website"
# LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/movies_to_ihu.log"

# # Ensure the log file directory exists
# mkdir -p "$(dirname "$LOG_FILE")"

# # Function to log messages with timestamp
# log_message() {
#     echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
# }

# log_message "Script started."

# # Iterate over each folder in the source directory
# for folder in "$SOURCE_DIR"/1-*; do
#     if [ -d "$folder" ]; then
#         folder_name=$(basename "$folder")
#         log_message "Processing folder $folder_name"

#         # Find all .mp4 files in the source folder
#         find "$folder" -type f -name "*.mp4" | while read file; do
#             file_name=$(basename "$file")

#             # Extract IHU number from the filename
#             if [[ "$file_name" =~ _([0-9]+)_ ]]; then
#                 ihu_number=$((10#${BASH_REMATCH[1]}))
                
#                 # Format the IHU number to ensure it is two digits with leading zeros if needed
#                 ihu_directory="ihu-$(printf "%02d" "$ihu_number")"

#                 # Check if the corresponding IHU directory exists in the target
#                 if [ -d "$TARGET_DIR/$ihu_directory" ]; then
#                     # Create the relative path to the source file
#                     relative_path="/nfs/php2/ar0/P/HP1/REDUCTION/MOVIES/$folder_name/$file_name"
#                     target_symlink="$TARGET_DIR/$ihu_directory/$file_name"

#                     # Check if the symlink already exists
#                     if [ ! -e "$target_symlink" ]; then
#                         # Create symlink in the corresponding IHU directory using the relative path
#                         ln -s "$relative_path" "$target_symlink"
#                         if [ $? -eq 0 ]; then
#                             log_message "Created symlink for $file_name in $TARGET_DIR/$ihu_directory"
#                         else
#                             log_message "ERROR: Failed to create symlink for $file_name in $TARGET_DIR/$ihu_directory"
#                         fi
#                     else
#                         log_message "Skipping $file_name: Symlink already exists in $TARGET_DIR/$ihu_directory"
#                     fi
#                 else
#                     log_message "Skipping $file_name: IHU directory $ihu_directory does not exist in the target."
#                 fi
#             else
#                 log_message "Skipping $file_name: IHU number not found in filename."
#             fi
#         done
#     else
#         log_message "Skipping non-directory item: $folder"
#     fi
# done

# log_message "Script completed."


#!/bin/bash

SOURCE_DIR="/nfs/php2/ar0/P/HP1/REDUCTION/MOVIES"
TARGET_DIR="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/movies_to_ihu.log"

mkdir -p "$(dirname "$LOG_FILE")"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "Script started."

# Helper function to check if folder name is <= 10 days old
is_within_10_days() {
    # Expect something like "1-20250120"
    folder_name="$1"
    date_str="${folder_name#1-}"
    folder_epoch=$(date -d "$date_str" +%s 2>/dev/null) || return 1
    now_epoch=$(date +%s)
    diff_days=$(( (now_epoch - folder_epoch) / 86400 ))

    [ $diff_days -ge 0 ] && [ $diff_days -le 10 ]
}

# Iterate over each folder in the source directory that starts with "1-"
for folder in "$SOURCE_DIR"/1-*; do
    if [ -d "$folder" ]; then
        folder_name=$(basename "$folder")

        # Check if <= 10 days old
        if is_within_10_days "$folder_name"; then
            log_message "Processing folder $folder_name"

            find "$folder" -type f -name "*.mp4" | while read file; do
                file_name=$(basename "$file")

                # Extract IHU number from the filename (the _XX_ pattern)
                if [[ "$file_name" =~ _([0-9]+)_ ]]; then
                    ihu_number=$((10#${BASH_REMATCH[1]}))
                    ihu_directory="ihu-$(printf "%02d" "$ihu_number")"

                    if [ -d "$TARGET_DIR/$ihu_directory" ]; then
                        relative_path="$SOURCE_DIR/$folder_name/$file_name"
                        target_symlink="$TARGET_DIR/$ihu_directory/$file_name"

                        if [ ! -e "$target_symlink" ]; then
                            ln -s "$relative_path" "$target_symlink"
                            if [ $? -eq 0 ]; then
                                log_message "Created symlink for $file_name in $TARGET_DIR/$ihu_directory"
                            else
                                log_message "ERROR: Failed to create symlink for $file_name in $TARGET_DIR/$ihu_directory"
                            fi
                        else
                            log_message "Skipping $file_name: Symlink already exists in $TARGET_DIR/$ihu_directory"
                        fi
                    else
                        log_message "Skipping $file_name: IHU directory $ihu_directory does not exist in the target."
                    fi
                else
                    log_message "Skipping $file_name: IHU number not found in filename."
                fi
            done

        else
            log_message "Skipping folder $folder_name: Not within 10 days old."
        fi
    else
        log_message "Skipping non-directory item: $folder"
    fi
done

log_message "Script completed."
