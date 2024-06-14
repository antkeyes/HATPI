#!/bin/bash

log_file="/nfs/hatops/ar0/hatpi-website/logs/run_all.log"

echo "started at $(date)" >> $log_file
echo "Current user: $(whoami)" >> $log_file
echo "Current groups: $(groups)" >> $log_file
echo "Permissions of target directory:" >> $log_file
ls -ld /nfs/hatops/ar0/hatpi-website >> $log_file
echo "Permissions of source directory:" >> $log_file
ls -ld /nfs/hatops/ar0/hatpi-plots >> $log_file

# Step 1: Rsync between source and destination directories
echo "Starting rsync at $(date)" >> $log_file
rsync -av --no-perms --no-owner --no-group --omit-dir-times --chmod=ugo=rwx --log-file=/nfs/hatops/ar0/hatpi-website/logs/rsync_detailed.log /nfs/hatops/ar0/hatpi-plots/ /nfs/hatops/ar0/hatpi-website/ >> $log_file 2>&1
if [ $? -ne 0 ]; then
  echo "Rsync failed at $(date)" >> $log_file
  exit 1
fi
echo "Rsync completed at $(date)" >> $log_file

# Step 2: Run movies_symlinks.sh
echo "Starting movies_symlinks.sh at $(date)" >> $log_file
/bin/bash /nfs/hatops/ar0/hatpi-website/scripts/movies_symlinks.sh >> $log_file 2>&1
if [ $? -ne 0 ]; then
  echo "movies_symlinks.sh failed at $(date)" >> $log_file
  exit 1
fi
echo "movies_symlinks.sh completed at $(date)" >> $log_file

# Step 3: Run movies_to_dates.sh
echo "Starting movies_to_dates.sh at $(date)" >> $log_file
/bin/bash /nfs/hatops/ar0/hatpi-website/scripts/movies_to_dates.sh >> $log_file 2>&1
if [ $? -ne 0 ]; then
  echo "movies_to_dates.sh failed at $(date)" >> $log_file
  exit 1
fi
echo "movies_to_dates.sh completed at $(date)" >> $log_file

# Step 4: Run movies_to_ihu.sh
echo "Starting movies_to_ihu.sh at $(date)" >> $log_file
/bin/bash /nfs/hatops/ar0/hatpi-website/scripts/movies_to_ihu.sh >> $log_file 2>&1
if [ $? -ne 0 ]; then
  echo "movies_to_ihu.sh failed at $(date)" >> $log_file
  exit 1
fi
echo "movies_to_ihu.sh completed at $(date)" >> $log_file

# Step 5: Run create-ihu-symlinks.sh
echo "Starting create-ihu-symlinks.sh at $(date)" >> $log_file
/bin/bash /nfs/hatops/ar0/hatpi-website/scripts/create-ihu-symlinks.sh >> $log_file 2>&1
if [ $? -ne 0 ]; then
  echo "create-ihu-symlinks.sh failed at $(date)" >> $log_file
  exit 1
fi
echo "create-ihu-symlinks.sh completed at $(date)" >> $log_file

# Step 6: Restart Flask application
echo "Starting restart_flask.sh at $(date)" >> $log_file
/bin/bash /nfs/hatops/ar0/hatpi-website/scripts/restart_flask.sh >> $log_file 2>&1
if [ $? -ne 0 ]; then
  echo "restart_flask.sh failed at $(date)" >> $log_file
  exit 1
fi
echo "restart_flask.sh completed at $(date)" >> $log_file

echo "All steps completed successfully at $(date)" >> $log_file
