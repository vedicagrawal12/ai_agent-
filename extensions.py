import os
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# pyrefly: ignore [missing-import]
from flask_caching import Cache
from database import Database
from collectors.serpapi_collector import SerpApiCollector

cors = CORS()
limiter = Limiter(key_func=get_remote_address)
db = Database()
collector = SerpApiCollector()
cache = Cache()

# In-memory store for master API key, loaded from environment
API_KEY_STORE = {
    "serpapi": os.getenv("SERPAPI_KEY", "")
}
