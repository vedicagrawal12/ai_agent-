import multiprocessing
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

bind = "0.0.0.0:5000"
workers = 1
worker_class = "gthread"
threads = 4
timeout = 120
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
