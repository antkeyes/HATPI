#!/bin/bash

# Define the base directory
BASE_DIR="/nfs/hatops/ar0/hatpi-website"

# Find all directories starting with '1-'
for dir in "$BASE_DIR"/ihu-*; do
    # Check if it's a directory
    if [ -d "$dir" ]; then
        echo "Processing directory: $dir"
        
        # Find all .mp4 files or symlinks in the directory and delete them
        find "$dir" -type f -name "*.mp4" -o -type l -name "*.mp4" | while read -r file; do
            echo "Deleting: $file"
            rm "$file"
        done
        
        echo "Finished processing: $dir"
        echo "----------------------------"
    else
        echo "Skipping: $dir (Not a directory)"
    fi
done

echo "Script completed."