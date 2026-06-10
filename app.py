"""
AI Lead Generation Agent — Main Flask Application

Refactored to support Modular Blueprints, clean configuration management,
and structured scaling boundaries.
"""

import os
import sys
from datetime import datetime, date
from flask import Flask, session, g, request, jsonify, redirect, url_for
from flask.json.provider import DefaultJSONProvider

from config import DevelopmentConfig, ProductionConfig
from extensions import cors, limiter, db, cache
from utils.logger import setup_logging

class SafeJSONProvider(DefaultJSONProvider):
    """Custom JSON provider to handle datetime objects from PostgreSQL."""
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)

def create_app(config_class=None):
    """Flask Application Factory."""
    app = Flask(__name__)
    
    # 1. Load Configurations
    if config_class is None:
        is_dev = "--dev" in sys.argv or os.getenv("FLASK_ENV") == "development"
        config_class = DevelopmentConfig if is_dev else ProductionConfig
    app.config.from_object(config_class)
    
    # 2. Setup JSON Serialization
    app.json_provider_class = SafeJSONProvider
    app.json = SafeJSONProvider(app)
    
    # 3. Setup Structured Logging
    logger = setup_logging(app)
    
    # 4. Initialize Extensions
    cors.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    
    # 5. Application Middleware for Auth Checks
    @app.before_request
    def handle_authentication():
        # Load user context dynamically
        user_id = session.get('user_id')
        if user_id:
            is_admin = db.is_user_admin(user_id)
            g.user = {
                "id": user_id, 
                "username": session.get('username'),
                "is_admin": is_admin
            }
        else:
            g.user = None
        
        # Define public endpoints and paths that bypass authentication
        public_endpoints = [
            'auth.login', 
            'auth.signup', 
            'dashboard.live_preview_mockup', 
            'static', 
            'dashboard.index',
            'health_check',
            'dashboard.terms',
            'dashboard.privacy'
        ]
        if request.endpoint in public_endpoints:
            return
            
        # Path-based fallback whitelist
        path = request.path
        if path == '/' or path == '/health' or path == '/terms' or path == '/privacy' or path.startswith('/login') or path.startswith('/signup') or path.startswith('/preview/') or path.startswith('/static/'):
            return
            
        # Enforce authentication for protected paths
        if not g.user:
            if path.startswith('/api/'):
                return jsonify({"error": "Unauthorized. Please login."}), 401
            return redirect(url_for('auth.login'))

    # 5.5 Register Context Processor for Template variables
    @app.context_processor
    def inject_user_status():
        is_admin = False
        is_logged_in = False
        if g.get('user'):
            is_admin = g.user.get('is_admin', False)
            is_logged_in = True
        return dict(is_admin=is_admin, is_logged_in=is_logged_in)

    # 6. Register Blueprints
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
    
    # 7. Add health check endpoint
    @app.route("/health")
    def health_check():
        """Health check for monitoring and load balancers."""
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            db._release_connection(conn)
            return jsonify({"status": "healthy", "database": "connected"}), 200
        except Exception as e:
            return jsonify({"status": "unhealthy", "error": str(e)}), 503
            
    return app

if __name__ == "__main__":
    app = create_app()
    
    is_dev = app.debug
    print("\n" + "=" * 60)
    print("  LeadHunter AI — Agent Dashboard")
    print("=" * 60)
    print("  Local URL: http://localhost:5000")
    print(f"  Mode:      {'DEVELOPMENT' if is_dev else 'PRODUCTION'}")
    print("=" * 60 + "\n")
    
    app.run(host="127.0.0.1", port=5000)
