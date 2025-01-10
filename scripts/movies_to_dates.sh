#!/bin/bash

# Define the base directories
SOURCE_DIR="/nfs/php1/ar2/P/HP1/REDUCTION/MOVIES" #updated to new source location
TARGET_DIR="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/movies_to_dates.log"

# Ensure the log file directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Reference date in YYYYMMDD format
reference_date="20240629"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_message "Script started."

# Iterate over each folder in the source directory
for folder in "$SOURCE_DIR"/*; do
    if [ -d "$folder" ]; then
        folder_name=$(basename "$folder")

        # Extract the date from the folder name
        dir_date=$(echo "$folder_name" | cut -d'-' -f2)

        # Check if the folder date is greater than the reference date
        if [[ "$dir_date" > "$reference_date" ]]; then
            # Check if the folder exists in the target directory
            if [ -d "$TARGET_DIR/$folder_name" ]; then
                log_message "Processing $folder_name"

                # Find all .mp4 files in the source folder and create symlinks in the target folder
                find "$folder" -type f -name "*.mp4" | while read file; do
                    file_name=$(basename "$file")
                    relative_path="/nfs/php1/ar2/P/HP1/REDUCTION/MOVIES/$folder_name/$file_name"
                    target_symlink="$TARGET_DIR/$folder_name/$file_name"

                    # Check if the symlink already exists
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
            log_message "Skipping $folder_name: Older than reference date."
        fi
    else
        log_message "Skipping non-directory item: $folder"
    fi
done

log_message "Script completed."
