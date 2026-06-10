import os
import sys
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or "dev-secret-key-change-in-production"
    
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

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

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
