# pyrefly: ignore [missing-import]
import pytest
import os
import sys
from dotenv import load_dotenv

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env variables and override DATABASE_URL for testing BEFORE importing database/extensions
load_dotenv()
db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/leadhunter_db")

def create_test_db_if_missing(original_db_url, test_db_name):
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    slash_idx = original_db_url.rfind('/')
    if slash_idx == -1:
        return
    base_url = original_db_url[:slash_idx + 1]
    admin_url = base_url + "postgres"
    
    conn = None
    try:
        conn = psycopg2.connect(admin_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (test_db_name,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(f'CREATE DATABASE "{test_db_name}";')
            print(f"[Testing conftest] Created test database: {test_db_name}")
    except Exception as e:
        print(f"[Testing conftest] Warning: Could not verify/create test database dynamically: {e}")
    finally:
        if conn:
            conn.close()

if "leadhunter_db" in db_url:
    create_test_db_if_missing(db_url, "leadhunter_test")
    test_db_url = db_url.replace("leadhunter_db", "leadhunter_test")
else:
    create_test_db_if_missing(db_url, "leadhunter_test")
    test_db_url = "postgresql://postgres:postgres@localhost:5432/leadhunter_test"
os.environ["DATABASE_URL"] = test_db_url

from app import create_app
from config import Config
from extensions import db as db_instance


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret-key-123"
    WTF_CSRF_ENABLED = False
    # Use dedicated testing database
    DATABASE_URL = os.environ.get("DATABASE_URL")
    RATELIMIT_ENABLED = False  # Disable rate limiter for testing to avoid 429 errors


@pytest.fixture(scope="session")
def app():
    # Dynamically inject/override env variables for testing
    os.environ["DATABASE_URL"] = TestConfig.DATABASE_URL
    app = create_app(TestConfig)
    
    # Run inline migrations and tables creation
    with app.app_context():
        # Ensure tables are built
        db_instance._init_db()
        
    yield app

@pytest.fixture(autouse=True)
def clean_db(app):
    """Truncate all tables and reset serial IDs before each test for total isolation."""
    conn = db_instance._get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("TRUNCATE TABLE message_log, search_history, leads, users, system_settings RESTART IDENTITY CASCADE;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[Testing conftest] Error during database truncation: {e}")
    finally:
        db_instance._release_connection(conn)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    return db_instance

@pytest.fixture
def auth_client(client):
    """Pre-authenticated test client context."""
    # Register test user
    client.post('/signup', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'phone': '1234567890'
    })
    # Login to set session cookie
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    return client
