import os
import sys
from datetime import timedelta
from dotenv import load_dotenv

import secrets
import logging

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        logging.warning("FLASK_SECRET_KEY environment variable not found! Generating a secure random key dynamically for session security.")
        SECRET_KEY = secrets.token_hex(32)
    
    # Session Settings
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=86400)  # 24 hours
    
    # Rate Limiting Settings
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    
    # Cache Settings
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    
    # SerpApi Configuration
    SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
    
    # CORS Allowed Origins
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    # Celery Settings
    CELERY_ENABLED = os.getenv("CELERY_ENABLED", "false").lower() == "true"
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # System SMTP settings for OTP / Onboarding emails
    SYSTEM_SMTP_HOST = os.getenv("SYSTEM_SMTP_HOST", "smtp.gmail.com")
    SYSTEM_SMTP_PORT = int(os.getenv("SYSTEM_SMTP_PORT", "465"))
    SYSTEM_SMTP_EMAIL = os.getenv("SYSTEM_SMTP_EMAIL", "")
    SYSTEM_SMTP_PASSWORD = os.getenv("SYSTEM_SMTP_PASSWORD", "")
    SYSTEM_SMTP_USE_SSL = os.getenv("SYSTEM_SMTP_USE_SSL", "true").lower() == "true"

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # Can configure to use Redis storage for rate limits if REDIS_URL is provided
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_ENABLED = False
