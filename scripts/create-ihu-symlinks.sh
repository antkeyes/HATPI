#!/bin/bash

# Base directory containing the "1-" directories
base_dir="/nfs/hatops/ar0/hatpi-website"

# Target directory for the new ihu directories
target_dir="${base_dir}/ihu"

# Create the target directory if it doesn't exist
mkdir -p "$target_dir"

# Loop through each "1-" directory in the base directory
for dir in "$base_dir"/1-*; do
  if [[ -d "$dir" ]]; then
    echo "Processing directory: $dir"
    # Loop through each file in the current directory
    for file in "$dir"/*; do
      if [[ -f "$file" ]]; then
        echo "Processing file: $file"
        # Extract the ihu number from the filename
        if [[ "$file" =~ ihu-([0-9]+) ]]; then
          ihu_number="${BASH_REMATCH[1]}"
        elif [[ "$file" =~ _([0-9]+)_ ]]; then
          ihu_number="${BASH_REMATCH[1]}"
        else
          echo "No ihu number found in file: $file"
          continue
        fi

        echo "Found ihu number: $ihu_number"
        # Create the new ihu directory if it doesn't exist
        ihu_dir="${target_dir}/ihu-${ihu_number}"
        mkdir -p "$ihu_dir"
        # Create a symlink to the file in the new ihu directory
        ln -s "$file" "$ihu_dir/"
        echo "Created symlink for $file in $ihu_dir"
      fi
    done
  fi
done

echo "Files organized successfully using symlinks."
