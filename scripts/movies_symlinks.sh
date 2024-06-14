#!/bin/bash

# Define source and target directories
SOURCE_DIR="/nfs/php1/ar1/P/HP1/REDUCTION/MOVIES"
TARGET_DIR="/nfs/hatops/ar0/hatpi-website/movies"
LOG_FILE="/nfs/hatops/ar0/hatpi-website/logs/movies_symlinks.log"

# Ensure the target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Created target directory $TARGET_DIR" >> "$LOG_FILE"
fi

# Reference date in YYYYMMDD format
reference_date="20240529"

# Iterate over each item in the source directory
for item in "$SOURCE_DIR"/*; do
    item_name=$(basename "$item")
    source_item="$SOURCE_DIR/$item_name"
    target_item="$TARGET_DIR/$item_name"
    
    if [ -d "$source_item" ]; then
        # Extract the date from the directory name
        dir_date=$(echo "$item_name" | grep -oP '1-\K[0-9]{8}')
        
        if [[ "$dir_date" > "$reference_date" ]]; then
            # Create a symlink for the directory in the target path
            if [ ! -e "$target_item" ]; then
                ln -s "$source_item" "$target_item"
                if [ $? -eq 0 ]; then
                    echo "$(date '+%Y-%m-%d %H:%M:%S') - Created symlink for $source_item -> $target_item" >> "$LOG_FILE"
                else
                    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: Failed to create symlink for $source_item -> $target_item" >> "$LOG_FILE"
                fi
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') - Symlink already exists for $target_item" >> "$LOG_FILE"
            fi
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Skipping directory $item_name (older than reference date)" >> "$LOG_FILE"
        fi
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Skipping non-directory item: $item_name" >> "$LOG_FILE"
    fi
done

echo "$(date '+%Y-%m-%d %H:%M:%S') - Symlinks creation completed." >> "$LOG_FILE"
