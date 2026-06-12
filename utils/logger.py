"""
Logging Configuration — Structured logging with file rotation.

Replaces all print() calls with proper Python logging.
Provides log levels (DEBUG, INFO, WARNING, ERROR) and automatic
log file rotation (10MB max, keeps 5 backups).
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(app):
    """
    Configure structured logging for the Flask app.
    
    Creates two handlers:
    - Console handler (visible in terminal)
    - File handler (logs/leadhunter.log with rotation)
    
    Returns the configured logger.
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # File handler (rotates at 10MB, keeps 5 backups)
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'leadhunter.log'),
        maxBytes=10_000_000,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Clear existing handlers and add ours
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)

    # Attach handlers to root logger to capture all module-level logging
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    return app.logger
