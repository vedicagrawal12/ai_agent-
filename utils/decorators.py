from functools import wraps
from flask import g, redirect, url_for, jsonify, request, flash
from extensions import db

def admin_required(f):
    """Decorator that restricts a route to admin users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.user:
            return redirect(url_for('auth.login'))
        is_admin = db.is_user_admin(g.user['id'])
        if not is_admin:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Admin access required"}), 403
            flash("You don't have permission to access this page.", "error")
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated
