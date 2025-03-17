#!/bin/bash
#
# remove_ihu01_symlinks.sh
#
# Removes all symlinks in /nfs/hatops/ar0/hatpi-website/ihu-01
# that contain "-red-bin" or "-sub-bin" in the filename.

IHU01_DIR="/nfs/hatops/ar0/hatpi-website/ihu-01"

echo "Removing symlinks matching *-red-bin* or *-sub-bin* in $IHU01_DIR ..."

# Use 'find' to locate symlinks (-type l) at max depth 1 (the folder itself),
# matching either "*-red-bin*" or "*-sub-bin*" in their name, then remove them.
find "$IHU01_DIR" -maxdepth 1 -type l \
    \( -name "*-red-bin*" -o -name "*-sub-bin*" \) \
    -exec rm -v {} \;

echo "Done."
