import multiprocessing
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

bind = "127.0.0.1:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
timeout = 120
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
