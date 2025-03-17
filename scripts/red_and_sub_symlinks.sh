#!/bin/bash
# Script to create symlinks for Reduction (RED) and Subtraction (SUB) JPEG date directories
# from the source directories to the destination directories in your website.
#
# Source directories:
#   RED: /nfs/php2/ar0/P/HP1/REDUCTION/JPEGS/RED
#   SUB: /nfs/php2/ar0/P/HP1/REDUCTION/JPEGS/SUB
#
# Destination directories:
#   RED: /nfs/hatops/ar0/hatpi-website/RED
#   SUB: /nfs/hatops/ar0/hatpi-website/SUB

# Set source and destination paths
RED_SOURCE="/nfs/php2/ar0/P/HP1/REDUCTION/JPEGS/RED"
SUB_SOURCE="/nfs/php2/ar0/P/HP1/REDUCTION/JPEGS/SUB"

RED_DEST="/nfs/hatops/ar0/hatpi-website/RED"
SUB_DEST="/nfs/hatops/ar0/hatpi-website/SUB"

# Ensure destination directories exist
mkdir -p "$RED_DEST"
mkdir -p "$SUB_DEST"

echo "Starting symlink creation for RED directories from $RED_SOURCE..."
count=0
for dir in "$RED_SOURCE"/*; do
    if [ -d "$dir" ]; then
        dir_name=$(basename "$dir")
        ((count++))
        echo "  [$count] Creating symlink: $RED_DEST/$dir_name -> $dir"
        ln -sfn "$dir" "$RED_DEST/$dir_name"
    fi
done
echo "Finished processing RED directories. Total processed: $count"
echo ""

echo "Starting symlink creation for SUB directories from $SUB_SOURCE..."
count=0
for dir in "$SUB_SOURCE"/*; do
    if [ -d "$dir" ]; then
        dir_name=$(basename "$dir")
        ((count++))
        echo "  [$count] Creating symlink: $SUB_DEST/$dir_name -> $dir"
        ln -sfn "$dir" "$SUB_DEST/$dir_name"
    fi
done
echo "Finished processing SUB directories. Total processed: $count"
echo ""

echo "All symlinks created successfully."
