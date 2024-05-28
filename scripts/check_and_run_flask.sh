#!/bin/bash

# Check if Flask is running
if ! pgrep -f "flask run" > /dev/null
then
    echo "Flask is not running. Starting Flask..."
    cd /nfs/hatops/ar0/hatpi-website  # app.py (flask application) location
    export FLASK_APP=app.py
    export FLASK_ENV=production  # Set environment to production
    nohup /usr/bin/python2.7 -m flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &
else
    echo "Flask is already running."
fi
