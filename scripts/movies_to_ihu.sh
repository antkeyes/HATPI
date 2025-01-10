#!/bin/bash

# Define the base directories
SOURCE_DIR="/nfs/php1/ar2/P/HP1/REDUCTION/MOVIES"  # Updated to the new source location
TARGET_DIR="/nfs/hatops/ar0/hatpi-website"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/movies_to_ihu.log"

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
for folder in "$SOURCE_DIR"/1-*; do
    if [ -d "$folder" ]; then
        folder_name=$(basename "$folder")

        # Extract the date from the folder name
        dir_date=$(echo "$folder_name" | cut -d'-' -f2)

        # Check if the folder date is greater than the reference date
        if [[ "$dir_date" > "$reference_date" ]]; then
            log_message "Processing folder $folder_name"
            
            # Find all .mp4 files in the source folder
            find "$folder" -type f -name "*.mp4" | while read file; do
                file_name=$(basename "$file")

                # Extract IHU number from the filename
                if [[ "$file_name" =~ _([0-9]+)_ ]]; then
                    ihu_number=${BASH_REMATCH[1]}
                    
                    # Format the IHU number to ensure it is two digits with leading zeros as needed
                    ihu_directory="ihu-$(printf "%02d" "$ihu_number")"

                    # Check if the corresponding IHU directory exists in the target
                    if [ -d "$TARGET_DIR/$ihu_directory" ]; then
                        # Create the relative path to the source file
                        relative_path="/nfs/php1/ar2/P/HP1/REDUCTION/MOVIES/$folder_name/$file_name"
                        target_symlink="$TARGET_DIR/$ihu_directory/$file_name"

                        # Check if the symlink already exists
                        if [ ! -e "$target_symlink" ]; then
                            # Create symlink in the corresponding IHU directory using the relative path
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
            log_message "Skipping $folder_name: Older than reference date."
        fi
    else
        log_message "Skipping non-directory item: $folder"
    fi
done

log_message "Script completed."
