#!/bin/bash

# Define the base directories
SOURCE_DIR="/nfs/php1/ar1/P/HP1/REDUCTION/MOVIES"
TARGET_DIR="/nfs/hatops/ar0/hatpi-website"

# Iterate over each folder in the source directory
for folder in "$SOURCE_DIR"/*; do
    if [ -d "$folder" ]; then
        folder_name=$(basename "$folder")
        
        # Check if the folder exists in the target directory
        if [ -d "$TARGET_DIR/$folder_name" ]; then
            echo "Processing $folder_name"
            
            # Find all .mp4 files in the source folder and create symlinks in the target folder
            find "$folder" -type f -name "*.mp4" | while read file; do
                file_name=$(basename "$file")
                ln -sfn "$file" "$TARGET_DIR/$folder_name/$file_name"
                echo "Created symlink for $file_name in $TARGET_DIR/$folder_name"
            done
        else
            echo "Skipping $folder_name: target folder does not exist."
        fi
    fi
done

echo "Script completed."
