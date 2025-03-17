#!/bin/bash
#
# flatten_red_sub_symlinks.sh
#
# Symlinks all .jpg files from /hatops/ar0/hatpi-website/RED/*/ihuXX
# and /hatops/ar0/hatpi-website/SUB/*/ihuXX
# directly into each top-level /nfs/hatops/ar0/hatpi-website/ihu-XX/.
#
# That means no more subfolders under ihu-XX for red/sub images.

BASE="/nfs/hatops/ar0/hatpi-website"

for i in $(seq -w 01 64); do
    IHU="ihu-$i"
    IHU_PATH="$BASE/$IHU"

    if [ ! -d "$IHU_PATH" ]; then
        echo "Skipping $IHU_PATH (does not exist)."
        continue
    fi

    echo "Processing $IHU_PATH ..."

    # 1) Symlink all '-red-' .jpg from /RED/*/ihuXX
    # Actually no need to filter by '-red-' here if you want *all* .jpg
    # The filename itself has '-red-' so front-end can detect it.
    for DATE_DIR in "$BASE/RED/"*; do
        if [ -d "$DATE_DIR/ihu$i" ]; then
            for JPG in "$DATE_DIR/ihu$i"/*.jpg; do
                [ -f "$JPG" ] || continue
                BASENAME="$(basename "$JPG")"
                # Create a symlink in /ihu-XX pointing to $JPG
                ln -s "$JPG" "$IHU_PATH/$BASENAME" 2>/dev/null || true
            done
        fi
    done

    # 2) Symlink all '-sub-' .jpg from /SUB/*/ihuXX
    for DATE_DIR in "$BASE/SUB/"*; do
        if [ -d "$DATE_DIR/ihu$i" ]; then
            for JPG in "$DATE_DIR/ihu$i"/*.jpg; do
                [ -f "$JPG" ] || continue
                BASENAME="$(basename "$JPG")"
                ln -s "$JPG" "$IHU_PATH/$BASENAME" 2>/dev/null || true
            done
        fi
    done

    echo "  Done linking red/sub images for $IHU."
done

echo "All done linking flattened red/sub images."
