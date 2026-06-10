# 🗺️ LeadHunter AI — Complete Roadmap to 950+

> **Current Score:** 438 / 1000  
> **Target Score:** 950+ / 1000  
> **Estimated Total Effort:** 12–15 days of focused work (not 12 hours — 12 DAYS)  
> **Strategy:** Fix in dependency order. Don't skip phases.

---

## 📋 Phase Overview

```mermaid
gantt
    title LeadHunter 950+ Roadmap
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b

    section Phase 1 - Emergency
    Security Hardening           :p1, 2026-06-10, 2d

    section Phase 2 - Foundation
    Architecture Refactor        :p2, after p1, 3d

    section Phase 3 - Database
    DB Optimization              :p3, after p2, 1d

    section Phase 4 - Testing
    Test Infrastructure          :p4, after p3, 3d

    section Phase 5 - Scale
    Scalability & Performance    :p5, after p4, 2d

    section Phase 6 - DevOps
    Deployment Pipeline          :p6, after p5, 1d

    section Phase 7 - Polish
    Advanced Features            :p7, after p6, 2d
```

| Phase | Focus | Days | Score Impact |
|-------|-------|------|-------------|
| 1 | 🚨 Security Hardening | 2 | 438 → 550 |
| 2 | 🏗️ Architecture Refactor | 3 | 550 → 680 |
| 3 | 🗄️ Database Optimization | 1 | 680 → 740 |
| 4 | 🧪 Testing Infrastructure | 3 | 740 → 830 |
| 5 | 📈 Scalability & Performance | 2 | 830 → 890 |
| 6 | 🚀 DevOps & Deployment | 1 | 890 → 930 |
| 7 | ✨ Advanced Features & Polish | 2 | 930 → 960 |

---

## 🚨 Phase 1: Security Hardening (Day 1–2)

> **Goal:** Stop the app from being hackable. This is non-negotiable before anything else.
> **Score Impact:** 438 → 550 (+112)

### Step 1.1: Kill `debug=True` (10 minutes)

This is the most dangerous line in your entire codebase. `debug=True` in Flask enables the Werkzeug interactive debugger — anyone can execute Python code on your server through the browser.

#### [MODIFY] [app.py](file:///c:/Users/Sahil/Desktop/ai%20agents/app.py)

```diff
 if __name__ == "__main__":
-    app.run(debug=True, port=5000)
+    import sys
+    is_dev = "--dev" in sys.argv
+    app.run(debug=is_dev, port=5000)
```

Now you run:
- **Development:** `python app.py --dev` (debugger ON)
- **Production:** `python app.py` or `gunicorn` (debugger OFF)

---

### Step 1.2: Add Rate Limiting (2 hours)

Install `flask-limiter` and protect every endpoint.

```bash
pip install flask-limiter
```

#### [NEW] Add to `app.py` after Flask init:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use Redis in production
)
```

Then apply specific limits:

```python
# Login: 5 attempts per minute (anti brute-force)
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    ...

# Signup: 3 per hour (anti spam)
@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])
def signup():
    ...

# Search: 10 per minute (SerpApi credit protection)
@app.route("/api/search", methods=["POST"])
@limiter.limit("10 per minute")
def search_businesses():
    ...

# AI Generation: 5 per minute (Gemini credit protection)
@app.route("/api/outreach/generate-ai", methods=["POST"])
@limiter.limit("5 per minute")
def generate_ai_pitch():
    ...

# SMTP: 10 per hour (anti spam)
@app.route("/api/outreach/send-smtp-email", methods=["POST"])
@limiter.limit("10 per hour")
def send_smtp_email():
    ...
```

---

### Step 1.3: Session Security (30 minutes)

#### [MODIFY] [app.py](file:///c:/Users/Sahil/Desktop/ai%20agents/app.py)

```python
# After app init, add session config:
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['SESSION_COOKIE_SECURE'] = not app.debug  # HTTPS only in production

# In login route, after setting session:
session.permanent = True  # Makes session respect PERMANENT_SESSION_LIFETIME
```

---

### Step 1.4: Account Lockout After Failed Logins (1 hour)

#### [NEW] Create `utils/security.py`

```python
"""Login attempt tracking and account lockout."""
import time
from collections import defaultdict
import threading

class LoginTracker:
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300  # 5 minutes
    
    def __init__(self):
        self._attempts = defaultdict(list)  # username -> [timestamp, ...]
        self._lock = threading.Lock()
    
    def is_locked(self, username: str) -> bool:
        with self._lock:
            attempts = self._attempts.get(username, [])
            # Remove attempts older than lockout window
            now = time.time()
            recent = [t for t in attempts if now - t < self.LOCKOUT_SECONDS]
            self._attempts[username] = recent
            return len(recent) >= self.MAX_ATTEMPTS
    
    def record_failure(self, username: str):
        with self._lock:
            self._attempts[username].append(time.time())
    
    def clear(self, username: str):
        with self._lock:
            self._attempts.pop(username, None)
    
    def remaining_lockout(self, username: str) -> int:
        with self._lock:
            attempts = self._attempts.get(username, [])
            if len(attempts) < self.MAX_ATTEMPTS:
                return 0
            oldest_relevant = sorted(attempts)[-self.MAX_ATTEMPTS]
            return max(0, int(self.LOCKOUT_SECONDS - (time.time() - oldest_relevant)))

login_tracker = LoginTracker()
```

Wire it into the login route:

```python
from utils.security import login_tracker

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        
        if login_tracker.is_locked(username):
            remaining = login_tracker.remaining_lockout(username)
            flash(f"Account locked. Try again in {remaining} seconds.", "error")
            return render_template("login.html")
        
        user = db.get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            login_tracker.clear(username)  # Reset on success
            session.clear()
            session["user_id"] = user["id"]
            ...
        else:
            login_tracker.record_failure(username)
            flash("Invalid username or password.", "error")
```

---

### Step 1.5: Global Error Handlers (30 minutes)

#### [MODIFY] [app.py](file:///c:/Users/Sahil/Desktop/ai%20agents/app.py)

```python
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Resource not found"}), 404
    return render_template("error.html", code=404, message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    # Log the actual error (never expose to user)
    app.logger.error(f"Internal error: {e}")
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("error.html", code=500, message="Something went wrong"), 500

@app.errorhandler(429)
def rate_limited(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Too many requests. Please slow down."}), 429
    flash("Too many attempts. Please wait a moment.", "error")
    return redirect(request.referrer or url_for('index'))
```

#### [NEW] Create `templates/error.html`

Simple error page template with your dark theme styling.

---

### Step 1.6: Protect `/verify-db` with Admin Role (1 hour)

#### [MODIFY] [database.py](file:///c:/Users/Sahil/Desktop/ai%20agents/database.py)

Add `is_admin` column to users table:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
```

#### [MODIFY] [app.py](file:///c:/Users/Sahil/Desktop/ai%20agents/app.py)

```python
# Add admin check decorator
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user:
            return redirect(url_for('login'))
        # Check admin status from DB
        user = db.get_user_by_username(session.get('username'))
        if not user or not user.get('is_admin'):
            return "Forbidden", 403
        return f(*args, **kwargs)
    return decorated

@app.route("/verify-db")
@admin_required
def verify_db():
    ...
```

---

### Step 1.7: Add Python `logging` (1 hour)

Replace ALL `print()` calls with proper logging.

#### [NEW] Create `utils/logger.py`

```python
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    """Configure structured logging for the Flask app."""
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # File handler (rotates at 10MB, keeps 5 backups)
    file_handler = RotatingFileHandler(
        'logs/leadhunter.log', maxBytes=10_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)
    
    return app.logger
```

Then in `app.py`:
```python
from utils.logger import setup_logging
logger = setup_logging(app)

# Replace all print() with:
logger.info("...")
logger.warning("...")
logger.error("...")
```

---

## 🏗️ Phase 2: Architecture Refactor (Day 3–5)

> **Goal:** Make the codebase maintainable and extensible.
> **Score Impact:** 550 → 680 (+130)

### Step 2.1: Flask Blueprints (4 hours)

Split `app.py` (1,137 lines) into focused modules:

#### New file structure:

```
ai agents/
├── app.py                    # 50 lines — app factory only
├── config.py                 # [NEW] All configuration
├── extensions.py             # [NEW] Flask extensions (db, limiter, cors)
├── routes/
│   ├── __init__.py
│   ├── auth.py               # [NEW] login, signup, logout (60 lines)
│   ├── dashboard.py          # [NEW] index, verify_db, preview (80 lines)
│   ├── api_leads.py          # [NEW] search, CRUD, pipeline, reminders (200 lines)
│   ├── api_outreach.py       # [NEW] whatsapp, email, AI pitch (200 lines)
│   ├── api_config.py         # [NEW] settings, portfolio, export (100 lines)
│   └── errors.py             # [NEW] error handlers (30 lines)
├── models/                   
│   ├── __init__.py
│   └── database.py           # Existing — moved here
├── collectors/               # Existing — untouched
├── utils/                    # Existing — untouched
├── templates/
├── static/
└── tests/                    # [NEW] — Phase 4
```

#### [NEW] `config.py`

```python
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or os.urandom(32).hex()
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/leadhunter_db")
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 86400
    SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    RATELIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")
```

#### [NEW] `extensions.py`

```python
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.database import Database

cors = CORS()
limiter = Limiter(key_func=get_remote_address)
db = Database()
```

#### [MODIFY] `app.py` → App Factory Pattern (50 lines)

```python
from flask import Flask
from config import DevelopmentConfig, ProductionConfig
from extensions import cors, limiter, db

def create_app(config_class=None):
    app = Flask(__name__)
    
    if config_class is None:
        import sys
        config_class = DevelopmentConfig if "--dev" in sys.argv else ProductionConfig
    
    app.config.from_object(config_class)
    
    # Init extensions
    cors.init_app(app)
    limiter.init_app(app)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.api_leads import leads_bp
    from routes.api_outreach import outreach_bp
    from routes.api_config import config_bp
    from routes.errors import errors_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp, url_prefix="/api")
    app.register_blueprint(outreach_bp, url_prefix="/api")
    app.register_blueprint(config_bp, url_prefix="/api")
    app.register_blueprint(errors_bp)
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(port=5000)
```

#### [NEW] `routes/auth.py` (Example Blueprint)

```python
from flask import Blueprint, request, session, redirect, url_for, flash, render_template, g
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, limiter

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    # ... existing login code ...

@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])
def signup():
    # ... existing signup code ...

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('auth.login'))
```

---

### Step 2.2: Constants File (30 minutes)

#### [NEW] `constants.py`

```python
"""Application-wide constants. No magic strings anywhere else."""

PIPELINE_STAGES = ["NEW", "PITCHED", "INTERESTED", "CONVERTED", "IGNORED"]
PRIORITY_LEVELS = ["HIGH", "MEDIUM", "LOW", "IGNORE"]
PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "IGNORE": 3}

MAX_SEARCH_RESULTS = 100
MAX_DEEP_SCAN_ZONES = 10
SERP_RESULTS_PER_PAGE = 20
SERP_RATE_LIMIT_SECONDS = 1

WEBSITE_CHECK_MAX_WORKERS = 5
WEBSITE_CHECK_TIMEOUT = 15
WEBSITE_CHECK_MAX_SITES = 20

CLEANUP_UNCONTACTED_DAYS = 14
CLEANUP_IGNORED_DAYS = 7
CLEANUP_HISTORY_DAYS = 30

SESSION_LIFETIME_SECONDS = 86400
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300
```

---

### Step 2.3: Split Frontend (4 hours)

Break the 165KB `app.js` into modules using ES6 modules (no bundler needed):

```
static/js/
├── app.js              # Main entry — imports modules, initializes app
├── modules/
│   ├── api.js          # All API calls (fetch wrappers)
│   ├── search.js       # Search tab logic
│   ├── leads.js        # Saved leads tab logic
│   ├── pipeline.js     # Pipeline tab logic
│   ├── outreach.js     # WhatsApp + Email + AI pitch logic
│   ├── settings.js     # Settings tab logic
│   ├── ui.js           # Tab switching, modals, toasts, animations
│   └── utils.js        # Helpers (formatDate, debounce, etc.)
```

In your HTML, change:
```html
<script type="module" src="/static/js/app.js"></script>
```

Each module exports its functions:
```javascript
// modules/api.js
export async function searchLeads(query, city, options = {}) {
    const response = await fetch('/api/search', { ... });
    return response.json();
}
```

---

### Step 2.4: Move Prompts to Config (2 hours)

#### [NEW] `prompts/` directory

```
prompts/
├── whatsapp_pitch.yaml
├── whatsapp_pitch_broken.yaml
├── email_pitch.yaml
└── refinement.yaml
```

Each YAML file contains structured prompt templates:
```yaml
# whatsapp_pitch.yaml
name: "WhatsApp Pitch - No Website"
version: "2.0"
variables:
  - business_name
  - city
  - category
  - rating
  - reviews
  - project_sample
  - mockup_link
template: |
  You are an Elite B2B Growth Strategist...
  ...
```

Then `ai_writer.py` loads from YAML instead of hardcoded strings:
```python
import yaml

def _load_prompt(template_name: str) -> str:
    with open(f"prompts/{template_name}.yaml") as f:
        data = yaml.safe_load(f)
    return data["template"]
```

---

## 🗄️ Phase 3: Database Optimization (Day 6)

> **Goal:** Make queries fast and the schema correct.
> **Score Impact:** 680 → 740 (+60)

### Step 3.1: Add Indexes (30 minutes)

#### [MODIFY] [database.py](file:///c:/Users/Sahil/Desktop/ai%20agents/database.py) — inside `_init_db()`

Add after table creation:

```python
# Performance indexes
index_queries = [
    "CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city);",
    "CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority);",
    "CREATE INDEX IF NOT EXISTS idx_leads_pipeline ON leads(pipeline_stage);",
    "CREATE INDEX IF NOT EXISTS idx_leads_contacted ON leads(contacted);",
    "CREATE INDEX IF NOT EXISTS idx_leads_remind ON leads(remind_status, remind_date);",
    "CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_search_user_id ON search_history(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_search_date ON search_history(searched_at);",
    "CREATE INDEX IF NOT EXISTS idx_msglog_lead ON message_log(lead_id);",
    "CREATE INDEX IF NOT EXISTS idx_msglog_user ON message_log(user_id);",
]
for idx_query in index_queries:
    try:
        cursor.execute(idx_query)
    except Exception as idx_err:
        print(f"Index creation warning: {idx_err}")
```

### Step 3.2: Fix Column Types (1 hour)

Add migration in `_init_db()`:

```python
# Type corrections (safe migrations)
type_migrations = [
    # contacted: INTEGER → BOOLEAN
    "ALTER TABLE leads ALTER COLUMN contacted TYPE BOOLEAN USING contacted::boolean;",
    "ALTER TABLE leads ALTER COLUMN contacted SET DEFAULT FALSE;",
    # is_broken_website: INTEGER → BOOLEAN
    "ALTER TABLE leads ALTER COLUMN is_broken_website TYPE BOOLEAN USING is_broken_website::boolean;",
    "ALTER TABLE leads ALTER COLUMN is_broken_website SET DEFAULT FALSE;",
    # remind_date: VARCHAR → DATE (nullable)
    "ALTER TABLE leads ALTER COLUMN remind_date TYPE DATE USING NULLIF(remind_date, '')::date;",
    # contact_date: VARCHAR → TIMESTAMP (nullable)
    "ALTER TABLE leads ALTER COLUMN contact_date TYPE TIMESTAMP USING NULLIF(contact_date, '')::timestamp;",
]
```

> [!WARNING]
> Run these migrations ONCE on your existing data, then remove them. Better yet, use Alembic (Step 3.4).

### Step 3.3: Connection Pooling (1 hour)

```python
from psycopg2 import pool

class Database:
    _pool = None
    
    def __init__(self, db_url=None):
        if not db_url:
            db_url = os.getenv("DATABASE_URL", "...")
        self.db_url = db_url
        
        if Database._pool is None:
            Database._pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                dsn=db_url,
                cursor_factory=psycopg2.extras.DictCursor
            )
        self._init_db()
    
    def _get_connection(self):
        return Database._pool.getconn()
    
    def _release_connection(self, conn):
        Database._pool.putconn(conn)
```

Then change ALL `conn.close()` to `self._release_connection(conn)`.

### Step 3.4: Alembic Migrations (2 hours)

```bash
pip install alembic sqlalchemy
alembic init migrations
```

Configure `alembic.ini` with your `DATABASE_URL` and use proper versioned migrations instead of raw `ALTER TABLE` in `_init_db()`.

---

## 🧪 Phase 4: Testing Infrastructure (Day 7–9)

> **Goal:** Go from 0 tests to 80%+ critical path coverage.
> **Score Impact:** 740 → 830 (+90)

### Step 4.1: Setup Testing Framework (1 hour)

```bash
pip install pytest pytest-cov pytest-flask
```

#### [NEW] `tests/conftest.py`

```python
import pytest
from app import create_app
from config import TestConfig

class TestConfig:
    TESTING = True
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/leadhunter_test"
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """Pre-authenticated test client."""
    # Create test user
    client.post('/signup', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123',
        'confirm_password': 'testpass123'
    })
    # Login
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    return client
```

### Step 4.2: Write Tests (3 days — target 50 tests minimum)

#### [NEW] `tests/test_auth.py` (~15 tests)

```python
def test_signup_success(client):
    resp = client.post('/signup', data={...})
    assert resp.status_code == 302  # Redirect to login

def test_signup_weak_password(client):
    resp = client.post('/signup', data={'password': '123', ...})
    assert b"at least 8 characters" in resp.data

def test_signup_invalid_email(client):
    ...

def test_signup_duplicate_username(client):
    ...

def test_login_success(client):
    ...

def test_login_wrong_password(client):
    ...

def test_login_lockout_after_5_failures(client):
    ...

def test_logout_clears_session(auth_client):
    ...

def test_protected_route_redirects_unauthenticated(client):
    resp = client.get('/api/leads')
    assert resp.status_code == 401

def test_session_expires(client):
    ...
```

#### [NEW] `tests/test_api_leads.py` (~15 tests)

```python
def test_get_leads_empty(auth_client):
    resp = auth_client.get('/api/leads')
    assert resp.json["success"] is True
    assert resp.json["leads"] == []

def test_search_missing_query(auth_client):
    resp = auth_client.post('/api/search', json={"city": "bhopal"})
    assert resp.status_code == 400

def test_search_missing_city(auth_client):
    ...

def test_delete_lead(auth_client):
    ...

def test_delete_lead_cross_user(auth_client):
    """User A cannot delete User B's lead."""
    ...

def test_pipeline_update(auth_client):
    ...

def test_pipeline_invalid_stage(auth_client):
    ...

def test_schedule_reminder(auth_client):
    ...

def test_dismiss_reminder(auth_client):
    ...
```

#### [NEW] `tests/test_database.py` (~10 tests)

```python
def test_create_user():
    ...

def test_save_leads():
    ...

def test_get_leads_filtered_by_user():
    """User A cannot see User B's leads."""
    ...

def test_cleanup_respects_reminders():
    ...

def test_connection_pool():
    ...
```

#### [NEW] `tests/test_utils.py` (~10 tests)

```python
def test_phone_standardization():
    assert DataCleaner.standardize_phone("9876543210") == "+91 98765 43210"

def test_phone_with_country_code():
    assert DataCleaner.standardize_phone("+919876543210") == "+91 98765 43210"

def test_email_validation():
    assert EmailScraper.is_valid_email("hello@test.com") is True
    assert EmailScraper.is_valid_email("sentry@test.com") is False

def test_ssrf_blocks_localhost():
    assert EmailScraper._is_safe_url("http://localhost:5432") is False

def test_ssrf_blocks_private_ip():
    assert EmailScraper._is_safe_url("http://192.168.1.1") is False

def test_ssrf_allows_public():
    assert EmailScraper._is_safe_url("https://google.com") is True

def test_priority_assignment():
    ...

def test_duplicate_removal():
    ...
```

### Step 4.3: Add `pytest` commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=html

# Run specific file
pytest tests/test_auth.py -v
```

Add to `requirements.txt`:
```
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-flask>=1.2.0
```

---

## 📈 Phase 5: Scalability & Performance (Day 10–11)

> **Goal:** Handle 50+ concurrent users without dying.
> **Score Impact:** 830 → 890 (+60)

### Step 5.1: Background Task Queue for Search (4 hours)

The search + website health check blocks the HTTP request for 15-30 seconds. Move it to a background thread.

#### [NEW] `utils/task_runner.py`

```python
import threading
import uuid
from datetime import datetime

class TaskRunner:
    """Simple in-process background task runner."""
    _tasks = {}  # task_id -> {status, result, error, started_at}
    _lock = threading.Lock()
    
    @classmethod
    def submit(cls, func, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())[:8]
        with cls._lock:
            cls._tasks[task_id] = {
                "status": "RUNNING",
                "result": None,
                "error": None,
                "started_at": datetime.now()
            }
        
        def wrapper():
            try:
                result = func(*args, **kwargs)
                with cls._lock:
                    cls._tasks[task_id]["status"] = "DONE"
                    cls._tasks[task_id]["result"] = result
            except Exception as e:
                with cls._lock:
                    cls._tasks[task_id]["status"] = "FAILED"
                    cls._tasks[task_id]["error"] = str(e)
        
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return task_id
    
    @classmethod
    def get_status(cls, task_id: str) -> dict:
        with cls._lock:
            return cls._tasks.get(task_id, {"status": "NOT_FOUND"})
```

Then change the search endpoint:
```python
# POST /api/search → returns task_id immediately
# GET /api/search/status/<task_id> → polls for results
```

### Step 5.2: API Pagination (2 hours)

#### [MODIFY] `get_all_leads()` in database.py

```python
def get_all_leads(self, user_id, priority_filter=None, city_filter=None, 
                  page=1, per_page=50) -> dict:
    """Paginated leads query."""
    offset = (page - 1) * per_page
    
    # ... build query ...
    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    # Also get total count
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    
    return {
        "leads": [dict(row) for row in rows],
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "pages": (total_count + per_page - 1) // per_page
    }
```

### Step 5.3: Add Caching (2 hours)

```bash
pip install flask-caching
```

```python
from flask_caching import Cache
cache = Cache(config={'CACHE_TYPE': 'simple'})  # Use Redis in production

# Cache dashboard stats for 60 seconds
@app.route("/api/stats")
@cache.cached(timeout=60, key_prefix=lambda: f"stats_{g.user['id']}")
def get_stats():
    ...
```

### Step 5.4: Gunicorn Production Config (30 minutes)

#### [NEW] `gunicorn.conf.py`

```python
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
timeout = 120
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
```

Run with: `gunicorn -c gunicorn.conf.py "app:create_app()"`

---

## 🚀 Phase 6: DevOps & Deployment (Day 12)

> **Goal:** One-command deployment. Reproducible environments.
> **Score Impact:** 890 → 930 (+40)

### Step 6.1: Docker (2 hours)

#### [NEW] `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:create_app()"]
```

#### [NEW] `docker-compose.yml`

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/leadhunter_db
      - SERPAPI_KEY=${SERPAPI_KEY}
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=leadhunter_db
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"

volumes:
  pgdata:
```

Run: `docker-compose up --build`

### Step 6.2: GitHub Actions CI/CD (1 hour)

#### [NEW] `.github/workflows/ci.yml`

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: leadhunter_test
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=. --cov-report=xml -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/leadhunter_test
          FLASK_SECRET_KEY: ci-test-key
```

### Step 6.3: Health Check Endpoint (15 minutes)

```python
@app.route("/health")
def health_check():
    """Health check for monitoring and load balancers."""
    try:
        conn = db._get_connection()
        conn.cursor().execute("SELECT 1")
        db._release_connection(conn)
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503
```

---

## ✨ Phase 7: Advanced Features & Polish (Day 13–14)

> **Goal:** Go from "good enough" to "impressive."
> **Score Impact:** 930 → 960 (+30)

### Step 7.1: Privacy & Compliance (2 hours)

- Add **"Delete My Account"** endpoint — deletes user + all their leads, searches, messages
- Add **Terms of Service** page (`/terms`)
- Add **Privacy Policy** page (`/privacy`)
- Add **data export** (GDPR "right to portability") — download all your data as ZIP

### Step 7.2: Notification System for Reminders (2 hours)

- Check reminders on each dashboard load
- Show browser notification badge for overdue reminders
- Optional: Email reminders using the user's configured SMTP

### Step 7.3: Lead Import from CSV (2 hours)

```python
@app.route("/api/leads/import", methods=["POST"])
def import_leads():
    """Import leads from CSV file upload."""
    file = request.files.get('file')
    # Parse CSV, validate columns, save to DB
```

### Step 7.4: Admin Dashboard (3 hours)

- User management (view all users, deactivate accounts)
- System stats (total users, total leads, API credit usage)
- Server health monitoring

### Step 7.5: Multi-Language Prompt Support (1 hour)

Move Hinglish-specific directives to a language config so prompts work for:
- Pure English
- Pure Hindi
- Tamil/Telugu (South India market)

---

## 📊 Final Expected Score After All Phases

| Category | Before | After | Change |
|----------|--------|-------|--------|
| 🔐 Security | 350 | 900 | +550 |
| 🏗️ Architecture | 380 | 920 | +540 |
| 🗄️ Database | 450 | 950 | +500 |
| 📝 Code Quality | 480 | 900 | +420 |
| ⚠️ Error Handling | 420 | 900 | +480 |
| 🧪 Testing | 0 | 850 | +850 |
| 📈 Scalability | 250 | 880 | +630 |
| 🚀 DevOps | 200 | 920 | +720 |
| 🎨 Frontend | 520 | 850 | +330 |
| 🤖 AI/ML | 620 | 900 | +280 |
| 🔒 Privacy | 350 | 900 | +550 |
| 💼 Business Logic | 650 | 950 | +300 |
| **Weighted Total** | **357** | **~910** | **+553** |

> [!IMPORTANT]
> To cross 950, you'd also need:
> - **900+ in Testing** → requires 100+ tests with mocking, integration tests, and E2E browser tests (Playwright/Selenium)
> - **950 in Frontend** → requires a proper framework (React/Vue), component library, and accessibility audit
> - **950 in Scalability** → requires Redis, Celery, WebSocket support, and CDN
> 
> These are "next level" improvements that take weeks, not days. The roadmap above gets you to **910-930** which is genuinely production-grade.

---

## ⚡ Quick Start: What To Do TODAY

If you can only do 4 hours today, do these in order:

```bash
# 1. Kill debug=True (2 minutes)
# Edit app.py line 1136

# 2. Install rate limiting (30 minutes)
pip install flask-limiter

# 3. Add database indexes (15 minutes)
# Add CREATE INDEX statements to _init_db()

# 4. Add global error handlers (30 minutes)
# Add @app.errorhandler(404), (500), (429)

# 5. Add logging (1 hour)
# Create utils/logger.py, replace print() calls

# 6. Write first 5 tests (1.5 hours)
pip install pytest pytest-flask
# Create tests/test_auth.py with 5 basic tests
```

This alone takes you from 438 → ~580. That's a 32% improvement in one sitting. 💪
