#!/bin/bash

dir="/nfs/hatops/ar0/hatpi-website/1-20240611"
target_dir="/nfs/hatops/ar0/hatpi-website/ihu"

# Create the target directory if it doesn't exist
mkdir -p "$target_dir"

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
      echo "Created or found directory: $ihu_dir"

      # Create a symlink to the file in the new ihu directory only if it doesn't already exist
      link_name="${ihu_dir}/$(basename "$file")"
      if [[ ! -e "$link_name" ]]; then
        ln -s "$file" "$link_name"
        echo "Created symlink for $file in $ihu_dir"
      else
        echo "Symlink for $file already exists in $ihu_dir"
      fi
    else
      echo "Skipping non-file item: $file"
    fi
  done
else
  echo "Skipping non-directory item: $dir"
fi

echo "Files organized successfully using symlinks."
