#!/bin/bash
#
# sync_ihu_symlinks.sh
# 
# Creates a "RED" and "SUB" folder inside each ihu-XX directory, 
# then symlinks any available date subfolder from /hatops/ar0/hatpi-website/RED and SUB
# that actually contain "ihuXX".
#
# Usage: ./sync_ihu_symlinks.sh

# Base path to your main website directory
base="/nfs/hatops/ar0/hatpi-website"

# We assume IHU numbers range from 01 to 64
for i in $(seq -w 01 64); do
    ihu="ihu-${i}"
    ihuPath="${base}/${ihu}"

    # If the IHU folder doesn't exist, skip it
    if [ ! -d "$ihuPath" ]; then
        echo "Skipping $ihuPath (does not exist)."
        continue
    fi

    echo "Processing $ihuPath ..."
    
    # Create RED/ and SUB/ subdirectories if they don't already exist
    mkdir -p "${ihuPath}/RED"
    mkdir -p "${ihuPath}/SUB"
    
    # 1) Link all relevant date directories from $base/RED
    for dateDir in "$base/RED/"*; do
        # dateDir might be something like "/nfs/hatops/ar0/hatpi-website/RED/1-20250127"
        [ -d "$dateDir" ] || continue  # skip non-directories
        dateName=$(basename "$dateDir")  # e.g. "1-20250127"
        # Check if there's an "ihuXX" subdir in that date
        if [ -d "${dateDir}/ihu$i" ]; then
            # If the symlink doesn't exist in our IHU folder, create it
            if [ ! -L "${ihuPath}/RED/${dateName}" ]; then
                echo "  Linking RED ${dateName} -> $dateDir/ihu$i"
                ln -s "${dateDir}/ihu$i" "${ihuPath}/RED/${dateName}"
            fi
        fi
    done
    
    # 2) Link all relevant date directories from $base/SUB
    for dateDir in "$base/SUB/"*; do
        [ -d "$dateDir" ] || continue
        dateName=$(basename "$dateDir")
        if [ -d "${dateDir}/ihu$i" ]; then
            if [ ! -L "${ihuPath}/SUB/${dateName}" ]; then
                echo "  Linking SUB ${dateName} -> $dateDir/ihu$i"
                ln -s "${dateDir}/ihu$i" "${ihuPath}/SUB/${dateName}"
            fi
        fi
    done
done

echo "All symlinks created."
