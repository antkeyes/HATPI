import multiprocessing
import os

# Binding and workers
bind = "127.0.0.1:5004"
workers = max(2, multiprocessing.cpu_count() // 2)
worker_class = "sync"
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
log_dir = "/nfs/hatops/ar0/hatpi-website/logs"
os.makedirs(log_dir, exist_ok=True)
errorlog = os.path.join(log_dir, "gunicorn.error.log")
accesslog = os.path.join(log_dir, "gunicorn.access.log")
loglevel = "info"
capture_output = True

# Security/headers (left to reverse proxy if present)

# PID file (useful if not running under systemd)
pidfile = "/nfs/hatops/ar0/hatpi-website/gunicorn.pid"

# App module
wsgi_app = "app:app"


