#!/bin/bash
#
# housekeeping_by_dirname.sh
#
# Removes directories named 1-YYYYMMDD older than N days based on the YYYYMMDD in their name,
# rather than actual filesystem modification time.

BASE_DIR="/nfs/hatops/ar0/hatpi-website"
CUTOFF_DAYS=100

cd "$BASE_DIR" || {
    echo "ERROR: Could not cd into $BASE_DIR"
    exit 1
}

TODAY_EPOCH=$(date +%s)

# Loop over all directories starting with "1-"
for dir in 1-*; do
    
    # Skip if not a directory
    [ -d "$dir" ] || continue

    # Extract the date portion: for "1-20240726" => "20240726"
    DIR_DATE=$(echo "$dir" | cut -d'-' -f2)

    # Ensure DIR_DATE looks like YYYYMMDD
    if ! date -d "$DIR_DATE" &>/dev/null; then
        echo "Skipping invalid directory name (no valid YYYYMMDD): $dir"
        continue
    fi

    # Convert DIR_DATE to epoch seconds
    DIR_EPOCH=$(date -d "$DIR_DATE" +%s)

    # Compute day difference
    DIFF_DAYS=$(( (TODAY_EPOCH - DIR_EPOCH) / 86400 ))

    if (( DIFF_DAYS > CUTOFF_DAYS )); then
        echo "Removing directory $dir (dated $DIR_DATE, $DIFF_DAYS days old)..."
        rm -rf "$dir"
    else
        echo "Keeping directory $dir (dated $DIR_DATE, $DIFF_DAYS days old)."
    fi

done
