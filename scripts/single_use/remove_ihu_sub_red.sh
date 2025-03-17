#!/bin/bash
#
# remove_ihu_sub_red.sh
#
# Removes the "RED" and "SUB" subdirectories from each ihu-XX folder.

BASE="/nfs/hatops/ar0/hatpi-website"

for i in $(seq -w 01 64); do
    IHU="ihu-$i"
    IHU_PATH="$BASE/$IHU"

    if [ -d "$IHU_PATH" ]; then
        echo "Processing $IHU_PATH ..."
        # Remove RED/
        if [ -d "$IHU_PATH/RED" ]; then
            rm -rf "$IHU_PATH/RED"
            echo "  Removed RED/ folder."
        fi
        # Remove SUB/
        if [ -d "$IHU_PATH/SUB" ]; then
            rm -rf "$IHU_PATH/SUB"
            echo "  Removed SUB/ folder."
        fi
    else
        echo "Skipping $IHU_PATH (does not exist)."
    fi
done

echo "All RED/ and SUB/ subdirectories have been removed."
