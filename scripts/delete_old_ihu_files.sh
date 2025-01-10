#!/bin/bash
#
# housekeeping_ihu_files_by_name.sh
#
# Scans each "ihu-*" directory, looks for filenames containing an 8-digit date (YYYYMMDD),
# and removes the file if that date is more than 100 days old (based on today's date).

BASE_DIR="/nfs/hatops/ar0/hatpi-website"
CUTOFF_DAYS=100

# Get today's epoch
TODAY_EPOCH=$(date +%s)

# Loop through each "ihu-" directory
for dir in "$BASE_DIR"/ihu-*; do
    
    # Skip if it's not actually a directory
    [ -d "$dir" ] || continue
    
    echo "Checking directory: $dir"
    
    # Loop through each file in this directory
    for f in "$dir"/*; do
        
        # Skip if it's not a regular file
        [ -f "$f" ] || continue

        # Extract the first 8-digit sequence in the filename (YYYYMMDD)
        # Examples that match:
        #   1-20230413_01_aper_phot_quality.html  -> 20230413
        #   masterdark-ihu-01-20240130-01_...     -> 20240130
        FILE_DATE=$(basename "$f" | grep -Eo '[0-9]{8}' | head -n 1)

        # If we found a date, parse and compare
        if [ -n "$FILE_DATE" ]; then
            # Check if it's a valid date
            if date -d "$FILE_DATE" &>/dev/null; then
                FILE_EPOCH=$(date -d "$FILE_DATE" +%s)
                DIFF_DAYS=$(( (TODAY_EPOCH - FILE_EPOCH) / 86400 ))
                
                if (( DIFF_DAYS > CUTOFF_DAYS )); then
                    echo "  Removing old file: $f (dated $FILE_DATE, $DIFF_DAYS days old)."
                    rm -f "$f"
                else
                    echo "  Keeping file: $f (dated $FILE_DATE, $DIFF_DAYS days old)."
                fi
            else
                echo "  Skipping $f (invalid date $FILE_DATE)."
            fi
        else
            echo "  Skipping $f (no 8-digit date in filename)."
        fi
    done

done
