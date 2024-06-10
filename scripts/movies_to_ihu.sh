#!/bin/bash

# Define the base directories
SOURCE_DIR="/nfs/php1/ar1/P/HP1/REDUCTION/MOVIES"
TARGET_DIR="/nfs/hatops/ar0/hatpi-website"

# Iterate over each folder in the source directory
for folder in "$SOURCE_DIR"/*; do
    if [ -d "$folder" ]; then
        folder_name=$(basename "$folder")

        echo "Processing folder $folder_name"
        
        # Find all .mp4 files in the source folder
        find "$folder" -type f -name "*.mp4" | while read file; do
            file_name=$(basename "$file")

            # Extract IHU number from the filename
            if [[ "$file_name" =~ _([0-9]+)_ ]]; then
                ihu_number=${BASH_REMATCH[1]}
                ihu_directory="ihu-$(printf "%02d" $ihu_number)"

                # Check if the corresponding IHU directory exists in the target
                if [ -d "$TARGET_DIR/$ihu_directory" ]; then
                    # Create symlink in the corresponding IHU directory
                    ln -sfn "$file" "$TARGET_DIR/$ihu_directory/$file_name"
                    echo "Created symlink for $file_name in $TARGET_DIR/$ihu_directory"
                else
                    echo "Skipping $file_name: IHU directory $ihu_directory does not exist in the target."
                fi
            else
                echo "Skipping $file_name: IHU number not found in filename."
            fi
        done
    fi
done

echo "Script completed."
