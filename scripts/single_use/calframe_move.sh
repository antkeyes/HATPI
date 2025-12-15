#!/usr/bin/env bash
# copy_calframes.sh

src="/nfs/hatops/ar0/hatpi-website/1-20250425"
dst="/nfs/hatops/ar0/hatpi-website/calframe_test"

mkdir -p "$dst"                 # create destination if it doesn’t exist
cp "$src"/*calframe_movie.mp4 "$dst"/
