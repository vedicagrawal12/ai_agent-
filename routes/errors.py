import logging
from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for

logger = logging.getLogger(__name__)
errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(404)
def not_found(e):
    """Handle 404 Not Found errors globally."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Resource not found"}), 404
    return render_template("login.html"), 404

@errors_bp.app_errorhandler(500)
def server_error(e):
    """Handle 500 Internal Server errors globally."""
    logger.error(f"Internal server error: {e}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    flash("Something went wrong. Please try again.", "error")
    return redirect(url_for('auth.login'))

@errors_bp.app_errorhandler(429)
def rate_limited(e):
    """Handle rate limit exceeded errors globally."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Too many requests. Please slow down."}), 429
    flash("Too many attempts. Please wait a moment.", "error")
    return redirect(request.referrer or url_for('auth.login'))
