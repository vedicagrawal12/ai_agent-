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

    import atexit
    @atexit.register
    def shutdown_db_pool():
        try:
            from extensions import db
            db.close()
        except Exception as e:
            app.logger.error(f"Error closing database pool at exit: {e}")
    
    # 4. Initialize Extensions
    allowed_origins = app.config.get("CORS_ALLOWED_ORIGINS", "*")
    if allowed_origins != "*":
        allowed_origins = [orig.strip() for orig in allowed_origins.split(",") if orig.strip()]
    cors.init_app(app, resources={r"/api/*": {"origins": allowed_origins}})
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
                "email": session.get('email'),
                "is_admin": is_admin
            }
        else:
            g.user = None
        
        # Define public endpoints and paths that bypass authentication
        public_endpoints = [
            'auth.login', 
            'auth.signup', 
            'auth.forgot_password',
            'auth.verify_otp',
            'auth.reset_password',
            'dashboard.live_preview_mockup', 
            'static', 
            'dashboard.index',
            'health_check',
            'dashboard.terms',
            'dashboard.privacy'
        ]
        if request.endpoint in public_endpoints or request.endpoint is None:
            return
            
        # Path-based fallback whitelist
        path = request.path
        if path == '/' or path == '/health' or path == '/terms' or path == '/privacy' or path.startswith('/login') or path.startswith('/signup') or path.startswith('/forgot-password') or path.startswith('/verify-otp') or path.startswith('/reset-password') or path.startswith('/preview/') or path.startswith('/static/'):
            return
            
        # Enforce authentication for protected paths
        if not g.user:
            if path.startswith('/api/'):
                return jsonify({"error": "Unauthorized. Please login."}), 401
            return redirect(url_for('auth.login'))

    @app.before_request
    def verify_csrf():
        if app.config.get('TESTING'):
            return
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            token_in_session = session.get('csrf_token')
            if not token_in_session:
                return jsonify({"error": "CSRF token missing or session expired."}), 400
            
            token_in_header = request.headers.get("X-CSRF-Token")
            token_in_form = request.form.get("csrf_token")
            token = token_in_header or token_in_form
            
            import secrets
            if not token or not secrets.compare_digest(token, token_in_session):
                if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
                    return jsonify({"error": "CSRF validation failed."}), 403
                from flask import flash
                flash("CSRF verification failed. Please try again.", "error")
                return redirect(request.referrer or url_for('auth.login'))

    @app.after_request
    def set_csrf_cookie(response):
        if 'csrf_token' not in session:
            import secrets
            session['csrf_token'] = secrets.token_hex(32)
        response.set_cookie('csrf_token', session['csrf_token'], samesite='Lax', secure=app.config.get('SESSION_COOKIE_SECURE', False))
        return response

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
